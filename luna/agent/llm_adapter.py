"""LLMAdapter：Agent 决策循环的 LLM 双通道接入。

- 通道 A（native）：OpenAI 兼容链路的原生 Function Calling（P0 先验证 chatgpt）；
  旧版 openai SDK（0.x）或配置缺失时返回 None，自动回落通道 B。
- 通道 B（text）：任意 provider 的 ReAct 文本协议兜底——模型输出一行
  ``ACTION: {json}`` 表达工具调用，无 ACTION 视为最终文本；经 handle 上的
  provider 实例发起调用（llm_handle 同款分发），chatgpt 用一次性会话标识
  （agent-<uuid>），不污染观众主会话。

不改动现有 provider 类；工具清单以 specs（name/description/parameters）形式
喂给两个通道。
"""

import json
import re
import uuid
from dataclasses import dataclass, field

from luna.infra.my_log import logger

# P0 原生 FC 支持的 chat_type（OpenAI 兼容链路）
NATIVE_FC_TYPES = {"chatgpt"}

ACTION_RE = re.compile(r"ACTION\s*:\s*(\{.*\})", re.DOTALL)
THOUGHT_RE = re.compile(r"^\s*THOUGHT\s*:.*$", re.MULTILINE)


@dataclass
class AdapterResult:
    """两个通道归一后的单轮产出：要么文本、要么工具调用列表。"""

    text: str | None = None
    tool_calls: list = field(default_factory=list)  # [{"name", "args", "id"}]，id 为 None 表示文本协议


class LLMAdapter:
    def __init__(self, handle, chat_type: str, channel: str = "auto"):
        self.handle = handle
        self.chat_type = chat_type
        if channel == "auto":
            channel = "native" if chat_type in NATIVE_FC_TYPES else "text"
        self.channel = channel

    def call(self, messages: list, tool_specs: list) -> AdapterResult:
        if self.channel == "native":
            result = self._call_native(messages, tool_specs)
            if result is not None:
                return result
            logger.warning("Agent 原生 FC 通道不可用（旧版 openai SDK 或配置缺失），本次决策回落文本协议")
        return self._call_text(messages, tool_specs)

    # ---------- 通道 A：原生 Function Calling ----------

    def _call_native(self, messages: list, tool_specs: list):
        try:
            import openai
            from packaging import version
        except ImportError:
            return None
        if version.parse(openai.__version__) < version.parse("1.0.0"):
            return None

        cfg = self.handle.config
        api = cfg.get("openai", "api")
        keys = cfg.get("openai", "api_key") or []
        if not api or not keys:
            return None
        model = cfg.get("agent", "llm", "model") or cfg.get("chatgpt", "model") or "gpt-3.5-turbo"

        client = openai.OpenAI(base_url=api, api_key=keys[0])
        params = {"model": model, "messages": messages, "timeout": 30}
        if tool_specs:
            params["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": spec["name"],
                        "description": spec["description"],
                        "parameters": spec["parameters"],
                    },
                }
                for spec in tool_specs
            ]
        resp = client.chat.completions.create(**params)
        message = resp.choices[0].message

        tool_calls = []
        for tc in getattr(message, "tool_calls", None) or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append({"name": tc.function.name, "args": args, "id": tc.id})
        if tool_calls:
            return AdapterResult(tool_calls=tool_calls)
        return AdapterResult(text=(message.content or "").strip() or None)

    # ---------- 通道 B：ReAct 文本协议 ----------

    def _call_text(self, messages: list, tool_specs: list) -> AdapterResult:
        provider = self._provider_caller()
        if provider is None:
            return AdapterResult()
        prompt = self._render(messages)
        if tool_specs:
            prompt += "\n\n可用工具：\n" + "\n".join(
                f"- {spec['name']}：{spec['description']}（参数 JSON Schema：{json.dumps(spec['parameters'], ensure_ascii=False)}）"
                for spec in tool_specs
            )
            prompt += (
                '\n\n如需使用工具，输出一行 ACTION: {"tool": "工具名", "args": {...}} 后停止等待结果；'
                "无需工具则直接给出最终回复。"
            )
        resp = provider(f"agent-{uuid.uuid4().hex[:8]}", prompt)
        if not resp:
            return AdapterResult()
        resp = str(resp).strip()
        match = ACTION_RE.search(resp)
        if match:
            try:
                payload = json.loads(match.group(1))
                name = str(payload.get("tool") or payload.get("name") or "").strip()
                args = payload.get("args") or {}
                if name:
                    return AdapterResult(tool_calls=[{"name": name, "args": args, "id": None}])
            except json.JSONDecodeError:
                logger.warning("Agent 文本协议 ACTION 解析失败，按最终文本处理")
        text = THOUGHT_RE.sub("", resp).strip()
        return AdapterResult(text=text or None)

    def _provider_caller(self):
        """llm_handle 同款的 provider 分发，统一成 (sessionid, prompt) -> str 形状。"""
        handle = self.handle
        chat_type = self.chat_type
        if getattr(handle, chat_type, None) is None:
            handle.get_chat_model(chat_type, handle.config)
        model = getattr(handle, chat_type, None)
        if model is None:
            return None
        if chat_type == "chatgpt":
            return model.get_gpt_resp
        if chat_type in ("anythingllm", "custom_llm", "dify"):
            return lambda sessionid, prompt: model.get_resp({"prompt": prompt})
        return lambda sessionid, prompt: model.get_resp(prompt)

    @staticmethod
    def _render(messages: list) -> str:
        lines = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if not content:
                continue
            if role == "system":
                lines.append(f"[设定]\n{content}")
            elif role == "assistant":
                lines.append(f"[你上一轮的输出]\n{content}")
            elif role == "tool":
                lines.append(f"[工具结果]\n{content}")
            else:
                lines.append(f"[消息]\n{content}")
        return "\n\n".join(lines)
