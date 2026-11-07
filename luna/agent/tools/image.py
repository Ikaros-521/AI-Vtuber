"""generate_image 工具：按提示词提交 Stable Diffusion 画图。

能力入口是 My_handle.generate_image_by_prompt（经 ctx.handle 注入）；弹幕
画图命令链路（sd_handle，含翻译与 prompt 润色）与此并行，互不影响。
"""

from luna.agent.registry import Tool


class GenerateImage(Tool):
    name = "generate_image"
    description = (
        "调用 Stable Diffusion 画一张图并展示在直播间画面。观众想看画/起哄看图时使用；"
        "提示词会直接传给 SD，请写成适合文生图模型的画面描述。响应较慢，一句话内不要重复调用。"
    )
    parameters = {
        "type": "object",
        "properties": {"prompt": {"type": "string", "description": "画面描述（文生图提示词）"}},
        "required": ["prompt"],
    }

    def run(self, args: dict, ctx) -> str:
        prompt = str(args.get("prompt") or "").strip()
        if not prompt:
            return "generate_image 失败：prompt 为空"
        return ctx.handle.generate_image_by_prompt(ctx.event.get("username", ""), prompt)
