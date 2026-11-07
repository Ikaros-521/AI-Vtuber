"""memory_save 工具：Agent 主动写入记忆（观众备注 / 直播高光）。

文件名刻意避开 luna/agent/memory.py，防止 import 时同名遮蔽。
"""

from luna.agent.registry import Tool


class MemorySave(Tool):
    name = "memory_save"
    description = (
        "记住值得长期保留的信息：观众的个人偏好/称呼/重要事实（viewer_note），或本场直播的高光时刻（highlight）。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["viewer_note", "highlight"], "description": "记忆类型"},
            "content": {"type": "string", "description": "要记住的内容，一句话"},
            "username": {"type": "string", "description": "kind=viewer_note 时对应的观众名，留空则为当前互动观众"},
        },
        "required": ["kind", "content"],
    }

    def run(self, args: dict, ctx) -> str:
        kind = str(args.get("kind") or "").strip()
        content = str(args.get("content") or "").strip()
        if not content:
            return "memory_save 失败：content 为空"
        if ctx.memory is None:
            return "记忆功能未启用"
        username = str(args.get("username") or ctx.event.get("username", "") or "").strip()
        if kind == "viewer_note":
            if not username:
                return "memory_save 失败：viewer_note 需要观众名"
            ctx.memory.save_note(ctx.event.get("platform", ""), username, content)
            return f"已记住 {username} 的备注"
        if kind == "highlight":
            ctx.memory.save_highlight(content, username)
            return "已记录本场高光"
        return f"memory_save 失败：未知 kind={kind}"
