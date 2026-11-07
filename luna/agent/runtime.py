"""AgentRuntime：有界决策循环 + handle_chat 门面入口。

集成契约（docs/agent-upgrade-design.md §4.2/§4.7）：
- My_handle.config_load 在 agent.enabled 时构造本类；agent_handle_chat 门面在
  _interaction_pipeline 的 LLM 段之前调用 handle_chat——返回 True 表示本次回复
  已由 Agent 接管（已播报或被违禁过滤刻意沉默），False 则落回原有 LLM 直答
  路径。规则引擎从「被替代者」变成「安全网」。
- 循环有界：轮次/超时任一触顶、无产出、或循环内任何异常，一律降级返回 False。
- 成本熔断：小时预算（agent.budget.tokens_per_hour，字符折算）超限后直接降级，
  不再请求 LLM，直播不中断。
"""

import json
import threading
import time
import traceback

from luna.agent.context import AgentContext, Budget
from luna.agent.intent import IntentRouter
from luna.agent.llm_adapter import LLMAdapter
from luna.agent.memory import MemorySystem
from luna.agent.registry import ToolRegistry
from luna.agent.safety import SafetyGuard
from luna.agent.tools.basic import speak_via
from luna.agent.trace import Trace
from luna.infra.my_log import logger


class AgentRuntime:
    def __init__(self, handle, adapter=None):
        self.handle = handle
        config = handle.config
        self.registry = ToolRegistry(config)
        self.safety = SafetyGuard(config)
        memory_cfg = config.get("agent", "memory") or {}
        self.memory = MemorySystem(
            handle.db,
            enable_profile=bool(memory_cfg.get("viewer_profile", True)),
            enable_episodic=bool(memory_cfg.get("episodic", True)),
        )
        self.intent = IntentRouter(config)
        self.adapter = adapter  # 测试注入；None 则按 chat_type 构造

        # 急停开关（WebUI 一键急停用）：置位后本进程内 Agent 立即静默降级，
        # 不落盘——持久开关仍是 config 的 agent.enabled，重启后以配置为准。
        self.kill_switch = False

        # 小时预算：滚动 1 小时窗口的 token 折算计数（<=0 视为不限）
        self._hour_started = time.monotonic()
        self._hour_used = 0
        self._budget_lock = threading.Lock()

    def handle_chat(self, data_json: dict, source: str) -> bool:
        """处理一条已过滤的待回复消息。True=接管完成，False=降级（落回原 LLM 路径）。"""
        if self.kill_switch:
            return False
        try:
            return self._run(data_json, source)
        except Exception:
            logger.error("Agent 决策异常，降级到规则引擎路径：\n" + traceback.format_exc())
            return False

    def _run(self, data_json: dict, source: str) -> bool:
        config = self.handle.config
        username = data_json.get("username", "")
        trace = Trace(event_type=source, username=username, source=source)
        budget = Budget(
            max_tool_rounds=int(config.get("agent", "max_tool_rounds") or 3),
            timeout_seconds=float(config.get("agent", "timeout_seconds") or 8),
        )

        # 小时预算熔断：超限直接降级，不请求 LLM
        if not self._hour_budget_allow():
            trace.finish(degraded=True, reason="hourly_budget_exhausted")
            return False

        event = {
            "type": source,
            "username": username,
            "content": data_json.get("content", ""),
            "platform": data_json.get("platform") or config.get("platform") or "unknown",
        }
        self.memory.touch_viewer(event["platform"], username)
        viewer_summary = self.memory.viewer_summary(event["platform"], username)
        ctx = AgentContext(
            event=event,
            source=source,
            handle=self.handle,
            budget=budget,
            trace=trace,
            memory=self.memory,
            viewer={"summary": viewer_summary} if viewer_summary else None,
            state={
                "cur_time": self.handle.common.get_bj_time(5),
                "playback_busy": bool(self.handle.is_playback_busy()),
                "recent_highlights": self.memory.recent_highlights(3),
            },
        )
        if not self.intent.should_agent(ctx):
            trace.finish(degraded=True, reason="intent_declined")
            return False

        messages = [
            {"role": "system", "content": self._build_system_prompt(ctx, config)},
            {"role": "user", "content": self._build_user_message(username, event["content"], config)},
        ]
        budget.add_chars(messages[0]["content"], messages[1]["content"])

        chat_type = config.get("chat_type")
        adapter = self.adapter or LLMAdapter(self.handle, chat_type, config.get("agent", "llm", "channel") or "auto")
        specs = self.registry.specs()
        final_text = None
        stop_reason = "budget_exhausted"
        acted = False

        while not budget.exhausted():
            result = adapter.call(messages, specs)
            budget.add_chars(result.text or "")
            if result.tool_calls:
                budget.tool_rounds += 1
                self._hour_budget_charge(budget.prompt_chars)
                messages.append(self._assistant_tool_message(result))
                for tool_call in result.tool_calls:
                    observation, ok = self._execute_tool(tool_call, ctx)
                    acted = acted or ok
                    if tool_call.get("id"):
                        messages.append({"role": "tool", "tool_call_id": tool_call["id"], "content": observation})
                    else:
                        messages.append({"role": "user", "content": f"OBSERVATION：{observation}"})
                continue
            if result.text:
                final_text = result.text
                stop_reason = ""
                break
            stop_reason = "no_output"
            break

        if final_text is None:
            if acted:
                # 动作已执行而模型收尾无话：视为完成（静默），不降级——
                # 降级会触发一次无视工具结果的裸 LLM 回复，盖在已入队的音频上
                trace.finish(degraded=False, reason="acted_no_final", prompt_chars=budget.prompt_chars)
                return True
            trace.finish(degraded=True, reason=stop_reason, prompt_chars=budget.prompt_chars)
            return False

        # 输出侧违禁过滤（复用 My_handle）；被拦则刻意沉默——不回落原路径，避免二次生成浪费
        filtered = self.handle.prohibitions_handle(final_text.strip())
        if filtered is None:
            trace.finish(
                degraded=False, reason="output_blocked", output_chars=len(final_text), prompt_chars=budget.prompt_chars
            )
            return True

        filtered = filtered.replace("\n", "。").strip()
        # 回复模板对齐（与 llm_handle 尾部一致）：模板包裹后的文本也写回 data_json 供门面触发
        filtered = self._apply_reply_template(filtered, ctx, config)
        # 与原 LLM 直答路径对齐的回显与落库
        self.handle.webui_show_chat_log_callback("agent", data_json, filtered)
        self.handle.write_to_comment_log(filtered, {"username": username, "content": event["content"]})
        speak_via(ctx, filtered)

        # 供门面做回复侧 key_mapping/custom_cmd 触发（与原路径语义一致）
        data_json["content"] = filtered
        trace.finish(output_chars=len(filtered), prompt_chars=budget.prompt_chars)
        return True

    # ---------- 内部 ----------

    def _build_user_message(self, username: str, content: str, config) -> str:
        """观众消息组装；超长内容截断（粘贴长文不该烧掉整轮预算）。"""
        max_chars = int(config.get("agent", "intent", "max_content_chars") or 0)
        if max_chars > 0 and len(content) > max_chars:
            content = content[:max_chars] + "……（内容过长已截断）"
        return f"观众 {username} 说：{content}" if username else content

    def _apply_reply_template(self, text: str, ctx, config) -> str:
        """回复模板替换，与 llm_handle 的处理保持一致；失败回退原文。"""
        if not config.get("reply_template", "enable"):
            return text
        try:
            variables = {
                "username": ctx.event["username"][: int(config.get("reply_template", "username_max_len"))],
                "data": text,
                "cur_time": ctx.state["cur_time"],
            }
            template = self.handle.common.get_list_random_or_default(
                config.get("reply_template", "copywriting"), "{data}"
            )
            if any(var in template for var in variables):
                return template.format(**{var: value for var, value in variables.items() if var in template})
        except Exception:
            logger.error("Agent 回复模板处理失败：\n" + traceback.format_exc())
        return text

    def generate_proactive(self):
        """闲时主动话题：单轮生成（无工具），失败返回 None 由调用方回落文案池。

        上下文注入近期高光与最近弹幕，让话题接得上直播间正在聊的内容；
        计入小时预算（超限静默回落）。
        """
        try:
            config = self.handle.config
            if self.kill_switch or not self._hour_budget_allow():
                return None
            parts = [
                config.get("agent", "persona")
                or (config.get("before_prompt") or "") + (config.get("after_prompt") or "")
                or "你是直播间的主播助手。",
                "当前时间：" + self.handle.common.get_bj_time(5),
                "请主动开一个直播话题：一句话，口语化，适合朗读，有互动感；不要 Markdown 与换行。",
            ]
            highlights = self.memory.recent_highlights(3)
            if highlights:
                parts.append("近期高光：" + "；".join(highlights))
            recent = self._recent_danmu_digest(10)
            if recent:
                parts.append("观众最近在聊：" + recent)
            prompt = "\n".join(parts)
            self._hour_budget_charge(len(prompt))

            chat_type = config.get("chat_type")
            adapter = self.adapter or LLMAdapter(
                self.handle, chat_type, config.get("agent", "llm", "channel") or "auto"
            )
            result = adapter.call(
                [{"role": "system", "content": prompt}, {"role": "user", "content": "生成一句主动话题。"}],
                [],
            )
            text = (result.text or "").strip()
            return text or None
        except Exception:
            logger.error("Agent 主动话题生成失败：\n" + traceback.format_exc())
            return None

    def _recent_danmu_digest(self, limit: int) -> str:
        db = self.handle.db
        if db is None:
            return ""
        try:
            rows = db.fetch_all("SELECT content FROM danmu ORDER BY ts DESC LIMIT ?", (limit,))
        except Exception:
            return ""
        return "；".join(str(r[0]) for r in reversed(rows)) if rows else ""

    def _build_system_prompt(self, ctx, config) -> str:
        persona = config.get("agent", "persona")
        if not persona:
            persona = (config.get("before_prompt") or "") + (config.get("after_prompt") or "")
        parts = [persona or "你是直播间的主播助手，用简短口语化的中文回复。"]
        parts.append("当前时间：" + ctx.state["cur_time"])
        parts.append(
            "播放状态：" + ("正在播放音频（观众喊停可用 stop_playback）" if ctx.state.get("playback_busy") else "空闲")
        )
        viewer = (ctx.viewer or {}).get("summary")
        if viewer:
            parts.append("观众记忆：" + viewer)
        highlights = ctx.state["recent_highlights"]
        if highlights:
            parts.append("近期高光：" + "；".join(highlights))
        parts.append("回复要求：简短口语化，适合直播朗读；不要输出 Markdown 与换行。")
        parts.append(
            "行动顺序由你安排，工具按调用顺序即时执行（先调用的先播放）。"
            "既要说话又要执行动作（如点歌/画图）时：先用 speak 把要说的话说出来，再调用动作工具；"
            "动作做完若无话可说就直接结束。"
        )
        return "\n".join(parts)

    @staticmethod
    def _assistant_tool_message(result) -> dict:
        return {
            "role": "assistant",
            "content": result.text or "",
            "tool_calls": [
                {
                    "id": tool_call.get("id"),
                    "type": "function",
                    "function": {
                        "name": tool_call["name"],
                        "arguments": json.dumps(tool_call.get("args") or {}, ensure_ascii=False),
                    },
                }
                for tool_call in result.tool_calls
            ],
        }

    def _execute_tool(self, tool_call: dict, ctx):
        """执行单个工具调用，返回 (OBSERVATION 文本, 是否执行成功)。"""
        name = str(tool_call.get("name") or "").strip()
        args = tool_call.get("args") or {}
        started = time.monotonic()
        tool = self.registry.get(name)
        if tool is None:
            ctx.trace.tool_done(name, "", 0, False)
            return f"工具 {name} 不存在或未启用", False
        if not self.safety.viewer_rate_ok(ctx.event.get("username", "")):
            ctx.trace.tool_done(name, "", 0, False)
            return "工具调用过于频繁，本次已跳过，请直接回答", False
        try:
            observation = tool.run(args, ctx) or "（无返回）"
            ok = True
        except Exception:
            logger.error(f"Agent 工具 {name} 执行失败：\n" + traceback.format_exc())
            observation = f"工具 {name} 执行失败"
            ok = False
        ctx.trace.tool_done(name, json.dumps(args, ensure_ascii=False)[:100], (time.monotonic() - started) * 1000, ok)
        return observation, ok

    def _hour_budget_allow(self) -> bool:
        limit = int(self.handle.config.get("agent", "budget", "tokens_per_hour") or 0)
        if limit <= 0:
            return True
        now = time.monotonic()
        with self._budget_lock:
            if now - self._hour_started >= 3600:
                self._hour_started = now
                self._hour_used = 0
            return self._hour_used < limit

    def _hour_budget_charge(self, chars: int) -> None:
        # 中文场景按约 3 字符/token 折算，只做熔断用，不追求计费精度
        with self._budget_lock:
            self._hour_used += max(0, chars) // 3
