"""ConfigAssistant：配置助手（v5 P2）——把主播的需求翻译成配置变更集。

产品形态（docs/agent-upgrade-design.md §12）：主播不懂功能怎么配、只会提需求
（"我想要观众能点歌"），助手理解需求 → 定位配置键 → 给出变更集与理由 →
按安全等级处理：manual 全部待主播确认；auto 安全变更自动落盘、敏感变更
仍待确认；full 全部自动落盘（对标 Codex 的自动化模式三档）。

运行位置：webui_server 进程（配置是它的领域，与主进程直播间 runtime 无关）——
因此本模块放 webui_server 而非 luna/agent：它必须直接实例化 provider，
而 luna/agent 的依赖守卫要求直播间 Agent 的 LLM 能力一律经 ctx.handle 注入，
两者是不同的架构约束。LLM 接入复用 luna.llm provider 注册表纯文本调用
（每轮现读配置现实例化，不缓存避免配置变更后拿旧参数）。配置知识库在
luna/agent/config_knowledge.py（webui → luna 合法方向）。

输出协议（流式版）：模型先输出说明文本（经 SSE 边生成边推给前端），
然后一行 <<<CHANGES>>> 分隔，最后输出 {"changes": [...], "questions": [...]}
JSON。说明部分流式、变更部分完成时解析——纯 JSON 协议没法流式（回复藏在
JSON 里，前端要干等几十秒）。模型没按协议输出时整段当说明、不出变更
（宁可不改配置，不可误改）。
"""

import json
import re
import threading
import time
import uuid

from luna.agent.config_knowledge import INJECT_SECTIONS, KNOWLEDGE, SENSITIVE_KEY_HINTS
from luna.infra.my_log import logger

# 流式协议分隔行：说明文本在前（边生成边推给前端），变更 JSON 在后（完成时解析）
CHANGES_MARKER = "<<<CHANGES>>>"

SAFETY_LEVELS = ("manual", "auto", "full")
SAFETY_LEVEL_NAMES = {"manual": "人工审核", "auto": "自动审核", "full": "完全访问"}


class ConfigAssistant:
    # 每会话保留最近 N 轮（user+assistant 各算一条）
    MAX_HISTORY_ITEMS = 20

    def __init__(self, runtime):
        self.runtime = runtime  # webui_server.runtime.Runtime：read_config/write_config/get
        self._sessions: dict = {}
        self._lock = threading.Lock()

    # ---------- LLM 接入 ----------

    def _resolve_chat_type(self, config):
        return (config.get("agent", {}) or {}).get("config_assistant", {}).get("chat_type") or config.get("chat_type")

    def _call_llm(self, prompt):
        """非流式直调 provider，返回 (文本, 失败原因)。保留给不支持的 provider 兜底。

        每轮现读配置现实例化（不缓存避免旧参数）；chatgpt 用一次性会话 ID——
        固定会话会把每轮完整 prompt 追进 provider 的会话历史，第二轮起输入翻倍
        （真机实测 24s/轮的元凶之一），而多轮上下文已由本类自己的 history 承担。
        """
        config = self.runtime.read_config()
        chat_type = self._resolve_chat_type(config)
        from luna.llm.gpt import load_model_class

        logger.info(f"[配置助手] 非流式调用模型 {chat_type}，prompt {len(prompt)} 字")
        cls = load_model_class(chat_type)
        if cls is None:
            return None, f"模型 {chat_type} 加载失败（检查依赖是否安装）"
        try:
            if chat_type == "chatgpt":
                data_openai = config.get("openai")
                if not data_openai or not data_openai.get("api_key"):
                    logger.warning("[配置助手] openai key 为空，无法调用")
                    return None, "openai key 为空（基础设置 → 人设与大脑）"
                model = cls(data_openai, config.get("chatgpt") or {})
                text = model.get_gpt_resp(f"cfg-assistant-{uuid.uuid4().hex[:8]}", prompt)
            elif chat_type in ("anythingllm", "custom_llm", "dify"):
                text = cls(config.get(chat_type) or {}).get_resp({"prompt": prompt})
            else:
                text = cls(config.get(chat_type) or {}).get_resp(prompt)
        except Exception as e:
            logger.error(f"[配置助手] LLM 调用异常：\n{e}")
            return None, f"模型调用异常：{e}"
        if not text:
            return None, f"模型 {chat_type} 没有返回内容（检查模型服务/网关是否在运行）"
        return str(text), None

    def _call_llm_stream(self, prompt):
        """流式调用 provider，返回 (delta 迭代器, 失败原因)。

        chatgpt 走 chat_stream（openai SDK 流式，timeout 作用于两次读取之间，
        不会被长回答整体掐断）；其余 provider 没有流式接口，退化为整段单 delta。
        """
        config = self.runtime.read_config()
        chat_type = self._resolve_chat_type(config)
        from luna.llm.gpt import load_model_class

        logger.info(f"[配置助手] 流式调用模型 {chat_type}，prompt {len(prompt)} 字")
        cls = load_model_class(chat_type)
        if cls is None:
            return None, f"模型 {chat_type} 加载失败（检查依赖是否安装）"
        try:
            if chat_type == "chatgpt":
                data_openai = config.get("openai")
                if not data_openai or not data_openai.get("api_key"):
                    logger.warning("[配置助手] openai key 为空，无法调用")
                    return None, "openai key 为空（基础设置 → 人设与大脑）"
                model = cls(data_openai, config.get("chatgpt") or {})
                resp = model.chat_stream(f"cfg-assistant-{uuid.uuid4().hex[:8]}", prompt)
                if resp is None:
                    return None, f"模型 {chat_type} 没有返回内容（检查模型服务/网关是否在运行）"
                return self._iter_openai_stream(resp), None
            text, error = self._call_llm(prompt)
            if text is None:
                return None, error
            return iter([text]), None
        except Exception as e:
            logger.error(f"[配置助手] LLM 调用异常：\n{e}")
            return None, f"模型调用异常：{e}"

    @staticmethod
    def _iter_openai_stream(resp):
        """把 openai 流式响应规整成 delta 文本迭代器（兼容 0.x/1.x 与末尾 usage 块）。"""
        for chunk in resp:
            try:
                choices = getattr(chunk, "choices", None)
                if not choices:
                    continue
                delta = getattr(choices[0], "delta", None)
                content = getattr(delta, "content", None) if delta else None
            except (AttributeError, IndexError):
                content = None
            if content:
                yield content

    # ---------- 会话历史 ----------

    def reset_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def _history(self, session_id: str) -> list:
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def _append_history(self, session_id: str, user_text: str, assistant_text: str) -> None:
        with self._lock:
            history = self._sessions.setdefault(session_id, [])
            history.append(("user", user_text))
            history.append(("assistant", assistant_text))
            if len(history) > self.MAX_HISTORY_ITEMS:
                del history[: -self.MAX_HISTORY_ITEMS]

    # ---------- 提示词 ----------

    @staticmethod
    def _deep_trim(value, depth: int = 0):
        """递归压缩注入值：文案池数组只留前 3 条、长字符串截断。

        实测全量注入 13K chars（各文案池撑的），压缩后 ~2-3K——模型只需要
        「有什么键、大概什么值」，不需要逐条文案。
        """
        if isinstance(value, str):
            return value[:200] + "…(截断)" if len(value) > 200 else value
        if isinstance(value, list):
            if not value:
                return value
            head = [ConfigAssistant._deep_trim(item, depth + 1) for item in value[:3]]
            return head + [f"…(共{len(value)}条)"] if len(value) > 3 else head
        if isinstance(value, dict):
            if depth >= 3:
                return "…"
            return {key: ConfigAssistant._deep_trim(item, depth + 1) for key, item in value.items()}
        return value

    def _system_prompt(self) -> str:
        config = self.runtime.read_config()
        inject = {}
        for section in INJECT_SECTIONS:
            value = config.get(section)
            if value is not None:
                inject[section] = self._deep_trim(value)
        level = self.safety_level()
        return (
            "你是 AI Vtuber（Luna）的配置助手，帮主播把自然语言需求翻译成具体的配置变更。"
            "主播不懂各功能怎么配，只会说需求（例如「我想要观众能点歌」「弹幕太吵了」「换个温柔点的声线」），"
            "你的职责：理解需求 → 定位配置键 → 给出变更集与理由。\n\n"
            "【配置知识库】\n" + KNOWLEDGE.strip() + "\n\n"
            "【当前配置（重点段实际值）】\n"
            + json.dumps(inject, ensure_ascii=False, default=str)[:6000]
            + "\n\n【输出协议】分两段输出（说明文字会被流式展示，不要包代码块）：\n"
            "第一段：直接写给主播的说明（改了什么/为什么这样配/已否生效，控制在 200 字内，细节放追问）。\n"
            f"然后单独一行输出 {CHANGES_MARKER}\n"
            '最后输出一个 JSON 对象：{"changes": [{"path": ["段名","键名"], "value": 新值, "reason": "这条改动的理由", "danger": false}], "questions": ["需要主播补充的问题"]}\n'
            "规则：\n"
            "- 不确定主播意图时宁可少改多问：changes 可为空数组，用 questions 追问\n"
            "- path 必须用知识库里真实存在的键；组合型需求拆成多条 change，每条给清晰理由\n"
            "- 涉及密钥/密码/登录态的变更 danger 必须为 true\n"
            "- reply 控制在 200 字内，细节放到 questions 里追问\n"
            "- 主播问使用方法/教程类问题（不涉及改配置）时，说明里给简明步骤，changes 为空数组\n"
            "- 主播闲聊或提问（不涉及配置）时 changes 为空，直接回答\n"
            f"- 当前安全等级是 {level}（{SAFETY_LEVEL_NAMES.get(level, level)}）；"
            "配置落盘后需重启程序才能在直播间生效，回复里要提醒\n"
        )

    # ---------- 解析与安全 ----------

    def _clean_changes(self, data) -> list:
        changes = []
        for item in (data.get("changes") or [])[:20]:
            path = item.get("path")
            if isinstance(path, list) and path and "value" in item:
                changes.append(
                    {
                        "path": [str(key) for key in path],
                        "value": item.get("value"),
                        "reason": str(item.get("reason") or ""),
                        "danger": self._enforce_danger(path, bool(item.get("danger"))),
                    }
                )
        return changes

    def _split_output(self, text):
        """按流式协议切分模型输出：说明文本 + <<<CHANGES>>> + 变更 JSON。

        模型没按协议输出（缺分隔行 / JSON 坏）时整段当说明、不出变更——
        宁可不改配置，不可误改。
        """
        text = (text or "").strip()
        if CHANGES_MARKER not in text:
            return {"reply": text or "（模型没有返回内容，请重试）", "changes": [], "questions": []}
        reply_part, _, tail = text.partition(CHANGES_MARKER)
        reply = reply_part.strip()
        tail = tail.strip()
        match = re.search(r"\{.*\}", tail, re.DOTALL)
        data = None
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                logger.warning("[配置助手] 变更 JSON 解析失败，按无变更处理")
        if isinstance(data, dict):
            return {
                "reply": reply,
                "changes": self._clean_changes(data),
                "questions": [str(q) for q in (data.get("questions") or [])[:5]],
            }
        return {"reply": reply, "changes": [], "questions": []}

    def _enforce_danger(self, path, danger: bool) -> bool:
        """敏感键复核：路径命中密钥/登录态类键名即强制 danger，模型说了不算。"""
        if danger:
            return True
        lowered = (str(key).lower() for key in path)
        return any(hint in key for key in lowered for hint in SENSITIVE_KEY_HINTS)

    # ---------- 主入口（非流式，兜底） ----------

    def chat(self, session_id: str, message: str) -> dict:
        started = time.monotonic()
        prompt_parts = [self._system_prompt()]
        for role, text in self._history(session_id):
            prompt_parts.append(f"{'主播' if role == 'user' else '你'}：{text}")
        prompt_parts.append(f"主播：{message}")
        prompt_parts.append("你：（按输出协议回答）")
        raw, error = self._call_llm("\n\n".join(prompt_parts))
        if raw is None:
            return {
                "reply": f"调用模型失败：{error}",
                "changes": [],
                "questions": [],
                "elapsed_ms": round((time.monotonic() - started) * 1000),
                "error": True,
            }
        result = self._split_output(raw)
        result["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        self._append_history(session_id, message, result["reply"])
        logger.info(
            f"[配置助手] 会话 {session_id} 完成：耗时 {result['elapsed_ms']}ms，"
            f"changes {len(result['changes'])} 条，questions {len(result['questions'])} 条"
        )
        return result

    def chat_stream(self, session_id: str, message: str):
        """流式配置对话：SSE 事件生成器。

        事件：reply_delta{text} / done{reply, changes(带安全等级状态), questions,
        elapsed_ms, level} / error{message}。说明文本边生成边推，变更集在完成时
        解析并按安全等级处理。
        """
        started = time.monotonic()
        prompt_parts = [self._system_prompt()]
        for role, text in self._history(session_id):
            prompt_parts.append(f"{'主播' if role == 'user' else '你'}：{text}")
        prompt_parts.append(f"主播：{message}")
        prompt_parts.append("你：（按输出协议回答）")
        prompt = "\n\n".join(prompt_parts)
        logger.info(f"[配置助手] 会话 {session_id} 收到消息（{len(message)} 字），prompt {len(prompt)} 字")

        stream, error = self._call_llm_stream(prompt)
        if stream is None:
            logger.warning(f"[配置助手] 模型调用失败：{error}")
            yield {"type": "error", "message": f"调用模型失败：{error}"}
            return

        chunks = []
        try:
            for delta in stream:
                chunks.append(delta)
                yield {"type": "reply_delta", "text": delta}
        except Exception as e:
            lowered = str(e).lower()
            if "tim" in lowered and ("out" in lowered or "timeout" in lowered):
                reason = "模型响应超时（网关慢或模型思考过长；可在 agent.config_assistant.chat_type 换更快模型）"
            else:
                reason = str(e)
            logger.error(f"[配置助手] 流式读取中断：{reason}")
            yield {"type": "error", "message": f"生成中断：{reason}"}
            return

        text = "".join(chunks)
        elapsed_ms = round((time.monotonic() - started) * 1000)
        result = self._split_output(text)
        reply = result["reply"]
        logger.info(
            f"[配置助手] 会话 {session_id} 完成：耗时 {elapsed_ms}ms，输出 {len(text)} 字，"
            f"changes {len(result['changes'])} 条，questions {len(result['questions'])} 条"
        )
        self._append_history(session_id, message, reply)

        level = self.safety_level()
        for change in result["changes"]:
            if level == "full" or (level == "auto" and not change["danger"]):
                ok = self.apply_changes([change])[0]["ok"]
                change["status"] = "applied" if ok else "failed"
            else:
                change["status"] = "pending"
        yield {
            "type": "done",
            "reply": reply,
            "changes": result["changes"],
            "questions": result["questions"],
            "elapsed_ms": elapsed_ms,
            "level": level,
        }

    # ---------- 安全等级与变更应用 ----------

    def safety_level(self) -> str:
        level = self.runtime.get("agent", "config_assistant", "safety_level")
        return level if level in SAFETY_LEVELS else "manual"

    def set_safety_level(self, level: str):
        if level not in SAFETY_LEVELS:
            return False, f"未知的安全等级：{level}"
        ok = self._update_config(["agent", "config_assistant", "safety_level"], level)
        return ok, f"安全等级已设为「{SAFETY_LEVEL_NAMES[level]}」" if ok else "写入失败"

    def apply_changes(self, changes: list) -> list:
        """把变更集落盘（读改写一次，原子替换）。返回逐条结果 [{path, ok}]。"""
        config = self.runtime.read_config()
        results = []
        touched = False
        for change in changes:
            path = change.get("path") or []
            node = config
            ok = bool(path)
            for key in path[:-1]:
                if not isinstance(node, dict):
                    ok = False
                    break
                node = node.setdefault(key, {})
            if ok and isinstance(node, dict):
                node[path[-1]] = change.get("value")
                touched = True
            else:
                ok = False
            results.append({"path": [str(key) for key in path], "ok": ok})
        if touched:
            try:
                self.runtime.write_config(config)
            except Exception as e:
                logger.error(f"[配置助手] 写盘失败：{e}")
                return [{"path": r["path"], "ok": False} for r in results]
        return results

    def _update_config(self, path: list, value) -> bool:
        return self.apply_changes([{"path": path, "value": value}])[0]["ok"]
