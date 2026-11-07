"""query_danmu_summary 工具：近期弹幕原文回顾，回答「刚才大家在聊什么」。"""

from luna.agent.registry import Tool


class QueryDanmuSummary(Tool):
    name = "query_danmu_summary"
    description = "取最近一段直播间弹幕原文，用于回顾观众刚才在聊什么、总结气氛。"
    parameters = {
        "type": "object",
        "properties": {"count": {"type": "integer", "description": "取最近多少条弹幕，默认 20，最大 50"}},
    }

    def run(self, args: dict, ctx) -> str:
        db = ctx.handle.db
        if db is None:
            return "查询失败：数据库未就绪"
        try:
            count = max(1, min(int(args.get("count") or 20), 50))
        except (TypeError, ValueError):
            count = 20
        rows = db.fetch_all("SELECT username, content FROM danmu ORDER BY ts DESC LIMIT ?", (count,))
        if not rows:
            return "最近没有弹幕记录"
        users = {r[0] for r in rows}
        lines = [f"{r[0]}：{r[1]}" for r in reversed(rows)]  # 按时间由早到晚展示
        return f"最近 {len(rows)} 条弹幕（{len(users)} 位观众，由早到晚）：\n" + "\n".join(lines)
