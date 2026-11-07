"""observe_screen 工具：截取直播画面并让视觉模型描述。

能力入口是 My_handle.observe_screen（经 ctx.handle 注入），截图源与模型
沿用图像识别配置（config.image_recognition）；定时画面识别链路与此并行。
"""

from luna.agent.registry import Tool


class ObserveScreen(Tool):
    name = "observe_screen"
    description = (
        "截取当前直播画面并让视觉模型描述给你，用于需要了解画面内容的场景"
        "（游戏直播解说、看观众发的画面、确认画图结果等）。响应较慢且有额外开销，"
        "一句话内不要重复调用；截图源与视觉模型按基础设置里的图像识别配置。"
    )
    parameters = {
        "type": "object",
        "properties": {"question": {"type": "string", "description": "想从画面里了解什么；留空则描述画面内容"}},
    }

    def run(self, args: dict, ctx) -> str:
        question = str(args.get("question") or "").strip() or "请描述一下画面里的内容"
        return ctx.handle.observe_screen(question)
