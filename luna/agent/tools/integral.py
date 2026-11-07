"""query_integral 工具：查询积分表（观众明细 / 排行榜）。

与 luna/core/integral.py 同一张 integral 表；这里只读，积分的增减仍由
积分系统自身的事件链路负责。
"""

from luna.agent.registry import Tool


class QueryIntegral(Tool):
    name = "query_integral"
    description = "查询直播间积分数据：某位观众的积分明细，或积分排行榜前 N 名。"
    parameters = {
        "type": "object",
        "properties": {
            "username": {"type": "string", "description": "要查询的观众名；留空则返回积分排行榜"},
            "top": {"type": "integer", "description": "排行榜条数，默认 5，最大 20"},
        },
    }

    def run(self, args: dict, ctx) -> str:
        db = ctx.handle.db
        if db is None:
            return "查询失败：数据库未就绪"
        username = str(args.get("username") or "").strip()
        if username:
            rows = db.fetch_all(
                "SELECT platform, integral, view_num, sign_num, total_price FROM integral WHERE username = ?",
                (username,),
            )
            if not rows:
                return f"观众 {username} 暂无积分记录"
            lines = [f"{r[0]}：积分{r[1]}，观看{r[2]}，签到{r[3]}天，累计礼物{r[4]}" for r in rows]
            return f"{username} 的积分记录：\n" + "\n".join(lines)
        try:
            top = max(1, min(int(args.get("top") or 5), 20))
        except (TypeError, ValueError):
            top = 5
        rows = db.fetch_all(
            "SELECT username, integral, sign_num, total_price FROM integral ORDER BY integral DESC LIMIT ?",
            (top,),
        )
        if not rows:
            return "积分榜暂无数据"
        lines = [f"{i + 1}. {r[0]} 积分{r[1]}（签到{r[2]}天，累计礼物{r[3]}）" for i, r in enumerate(rows)]
        return "积分排行榜：\n" + "\n".join(lines)
