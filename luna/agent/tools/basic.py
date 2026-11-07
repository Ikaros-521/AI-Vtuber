"""speak 工具与说话出口：Agent 最终回复与模型主动插话统一走这一个出口。

出口与现状完全一致：build_message() -> audio_synthesis_handle() -> Audio 队列，
TTS/播放/Live2D 链路零改动。luna.core.message 是依赖守卫里明确放行的纯工具模块。
"""

from luna.agent.registry import Tool
from luna.core.message import build as build_message


def speak_via(ctx, text: str) -> None:
    """把一段文本经现有出口送进 TTS 流水线。"""
    message = build_message(ctx.handle.config, ctx.source, ctx.event.get("username", ""), text)
    ctx.handle.audio_synthesis_handle(message)


class Speak(Tool):
    name = "speak"
    description = (
        "把要说的话提交给语音合成并立即播出。回答观众时直接给出文本即可，无需调用本工具；"
        "仅当你想在回答之外额外插话或分段播报时使用。"
    )
    parameters = {
        "type": "object",
        "properties": {"text": {"type": "string", "description": "要说出的内容"}},
        "required": ["text"],
    }

    def run(self, args: dict, ctx) -> str:
        text = str(args.get("text") or "").strip()
        if not text:
            return "speak 失败：text 为空"
        speak_via(ctx, text)
        return "已提交语音合成"
