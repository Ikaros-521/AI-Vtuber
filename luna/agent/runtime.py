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
        self.intent = IntentRouter()
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
            {"role": "user", "content": f"观众 {username} 说：{event['content']}" if username else event["content"]},
        ]
        budget.add_chars(messages[0]["content"], messages[1]["content"])

        chat_type = config.get("chat_type")
        adapter = self.adapter or LLMAdapter(self.handle, chat_type, config.get("agent", "llm", "channel") or "auto")
        specs = self.registry.specs()
        final_text = None
        stop_reason = "budget_exhausted"

        while not budget.exhausted():
            result = adapter.call(messages, specs)
            budget.add_chars(result.text or "")
            if result.tool_calls:
                budget.tool_rounds += 1
                self._hour_budget_charge(budget.prompt_chars)
                messages.append(self._assistant_tool_message(result))
                for tool_call in result.tool_calls:
                    observation = self._execute_tool(tool_call, ctx)
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
        # 与原 LLM 直答路径对齐的回显与落库
        self.handle.webui_show_chat_log_callback("agent", data_json, filtered)
        self.handle.write_to_comment_log(filtered, {"username": username, "content": event["content"]})
        speak_via(ctx, filtered)

        # 供门面做回复侧 key_mapping/custom_cmd 触发（与原路径语义一致）
        data_json["content"] = filtered
        trace.finish(output_chars=len(filtered), prompt_chars=budget.prompt_chars)
        return True

    # ---------- 内部 ----------

    def _build_system_prompt(self, ctx, config) -> str:
        persona = config.get("agent", "persona")
        if not persona:
            persona = (config.get("before_prompt") or "") + (config.get("after_prompt") or "")
        parts = [persona or "你是直播间的主播助手，用简短口语化的中文回复。"]
        parts.append("当前时间：" + ctx.state["cur_time"])
        viewer = (ctx.viewer or {}).get("summary")
        if viewer:
            parts.append("观众记忆：" + viewer)
        highlights = ctx.state["recent_highlights"]
        if highlights:
            parts.append("近期高光：" + "；".join(highlights))
        parts.append("回复要求：简短口语化，适合直播朗读；不要输出 Markdown 与换行。")
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

    def _execute_tool(self, tool_call: dict, ctx) -> str:
        name = str(tool_call.get("name") or "").strip()
        args = tool_call.get("args") or {}
        started = time.monotonic()
        tool = self.registry.get(name)
        if tool is None:
            ctx.trace.tool_done(name, "", 0, False)
            return f"工具 {name} 不存在或未启用"
        if not self.safety.viewer_rate_ok(ctx.event.get("username", "")):
            ctx.trace.tool_done(name, "", 0, False)
            return "工具调用过于频繁，本次已跳过，请直接回答"
        try:
            observation = tool.run(args, ctx) or "（无返回）"
            ok = True
        except Exception:
            logger.error(f"Agent 工具 {name} 执行失败：\n" + traceback.format_exc())
            observation = f"工具 {name} 执行失败"
            ok = False
        ctx.trace.tool_done(name, json.dumps(args, ensure_ascii=False)[:100], (time.monotonic() - started) * 1000, ok)
        return observation

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
