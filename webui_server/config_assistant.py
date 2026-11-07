"""ConfigAssistant：配置助手（v5 P2）——把主播的需求翻译成配置变更集。

产品形态（docs/agent-upgrade-design.md §12）：主播不懂功能怎么配、只会提需求
（"我想要观众能点歌"），助手理解需求 → 定位配置键 → 给出变更集与理由 →
按安全等级处理：manual 全部待主播确认；auto 安全变更自动落盘、敏感变更
仍待确认；full 全部自动落盘（对标 Codex 的自动化模式三档）。

运行位置：webui_server 进程（配置是它的领域，与主进程直播间 runtime 无关）——
因此本模块放 webui_server 而非 luna/agent：它必须直接实例化 provider，
而 luna/agent 的依赖守卫要求直播间 Agent 的 LLM 能力一律经 ctx.handle 注入，
两者是不同的架构约束。LLM 接入复用 luna.llm provider 注册表纯文本调用
（每轮现读配置现实例化，不缓存避免配置变更后拿旧参数）；输出走 JSON 变更集
协议而非工具循环——零 FC 依赖、全 provider 兼容，也贴合"需求 → 策略 → 确认"
的产品形态。配置知识库在 luna/agent/config_knowledge.py（webui → luna 合法方向）。
"""

import json
import re
import threading

from luna.agent.config_knowledge import INJECT_SECTIONS, KNOWLEDGE, SENSITIVE_KEY_HINTS
from luna.infra.my_log import logger

JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)

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

    def _call_llm(self, prompt):
        """webui 进程内直调 provider（每轮现读配置现实例化，不缓存避免旧参数）。"""
        config = self.runtime.read_config()
        chat_type = (config.get("agent", {}) or {}).get("config_assistant", {}).get("chat_type") or config.get(
            "chat_type"
        )
        from luna.llm.gpt import load_model_class

        cls = load_model_class(chat_type)
        if cls is None:
            return None
        if chat_type == "chatgpt":
            data_openai = config.get("openai")
            if not data_openai or not data_openai.get("api_key"):
                logger.warning("配置助手：openai key 为空，无法调用")
                return None
            model = cls(data_openai, config.get("chatgpt") or {})
            return model.get_gpt_resp("config-assistant", prompt)
        if chat_type in ("anythingllm", "custom_llm", "dify"):
            return cls(config.get(chat_type) or {}).get_resp({"prompt": prompt})
        return cls(config.get(chat_type) or {}).get_resp(prompt)

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

    def _system_prompt(self) -> str:
        config = self.runtime.read_config()
        inject = {}
        for section in INJECT_SECTIONS:
            value = config.get(section)
            if value is not None:
                inject[section] = value
        level = self.safety_level()
        return (
            "你是 AI Vtuber（Luna）的配置助手，帮主播把自然语言需求翻译成具体的配置变更。"
            "主播不懂各功能怎么配，只会说需求（例如「我想要观众能点歌」「弹幕太吵了」「换个温柔点的声线」），"
            "你的职责：理解需求 → 定位配置键 → 给出变更集与理由。\n\n"
            "【配置知识库】\n" + KNOWLEDGE.strip() + "\n\n"
            "【当前配置（重点段实际值）】\n"
            + json.dumps(inject, ensure_ascii=False, default=str)[:6000]
            + "\n\n【输出协议】严格输出一个 JSON 对象，不要输出任何其它内容：\n"
            '{"reply": "给主播的说明（改了什么/为什么这样配/已否生效）", '
            '"changes": [{"path": ["段名","键名"], "value": 新值, "reason": "这条改动的理由", "danger": false}], '
            '"questions": ["需要主播补充的问题"]}\n'
            "规则：\n"
            "- 不确定主播意图时宁可少改多问：changes 可为空数组，用 questions 追问\n"
            "- path 必须用知识库里真实存在的键；组合型需求拆成多条 change，每条给清晰理由\n"
            "- 涉及密钥/密码/登录态的变更 danger 必须为 true\n"
            "- 主播闲聊或提问（不涉及配置）时 changes 为空，直接回答\n"
            f"- 当前安全等级是 {level}（{SAFETY_LEVEL_NAMES.get(level, level)}）；"
            "配置落盘后需重启程序才能在直播间生效，回复里要提醒\n"
        )

    # ---------- 解析与安全 ----------

    def _parse_reply(self, raw):
        """提取 JSON 协议；解析失败整段当纯文本回复（宁可不改配置，不可误改）。"""
        text = (raw or "").strip()
        candidate = None
        match = JSON_BLOCK_RE.search(text)
        if match:
            candidate = match.group(1)
        else:
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end > start:
                candidate = text[start : end + 1]
        if candidate:
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError:
                data = None
            if isinstance(data, dict):
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
                return {
                    "reply": str(data.get("reply") or "").strip(),
                    "changes": changes,
                    "questions": [str(q) for q in (data.get("questions") or [])[:5]],
                }
        return {"reply": text or "（模型没有返回内容，请重试）", "changes": [], "questions": []}

    def _enforce_danger(self, path, danger: bool) -> bool:
        """敏感键复核：路径命中密钥/登录态类键名即强制 danger，模型说了不算。"""
        if danger:
            return True
        lowered = (str(key).lower() for key in path)
        return any(hint in key for key in lowered for hint in SENSITIVE_KEY_HINTS)

    # ---------- 主入口 ----------

    def chat(self, session_id: str, message: str) -> dict:
        prompt_parts = [self._system_prompt()]
        for role, text in self._history(session_id):
            prompt_parts.append(f"{'主播' if role == 'user' else '你'}：{text}")
        prompt_parts.append(f"主播：{message}")
        prompt_parts.append("你：（严格按输出协议回答）")
        raw = self._call_llm("\n\n".join(prompt_parts))
        result = self._parse_reply(raw)
        self._append_history(session_id, message, result["reply"])
        return result

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
                logger.error(f"配置助手写盘失败：{e}")
                return [{"path": r["path"], "ok": False} for r in results]
        return results

    def _update_config(self, path: list, value) -> bool:
        return self.apply_changes([{"path": path, "value": value}])[0]["ok"]
