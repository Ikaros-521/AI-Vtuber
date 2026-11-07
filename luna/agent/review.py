"""直播复盘（v5 P2）：把一场直播的数据聚合成复盘报告。

数据口径：按日期窗口（默认当天）聚合 sqlite 里的弹幕/礼物/入场/积分，
叠加 Agent 决策 trace 统计与记忆高光——全部本地数据，统计部分秒出；
AI 总结可选（LLM 失败静默回落纯统计，报告照样有值）。

报告存 agent_report 表（agent 域自管，与业务表隔离）。生成入口在主进程
机机接口 /agent_review/generate（webui 的 Agent 工作台代理调用）。
"""

import json
from datetime import datetime

from luna.infra.my_log import logger


def _ensure_table(db) -> None:
    db.execute("""
        CREATE TABLE IF NOT EXISTS agent_report (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts DATETIME NOT NULL,
            window_date TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)


def collect_stats(db, trace_records: list, window_date: str | None = None) -> dict:
    """按日期窗口聚合直播数据。db 为 None 时只出 Agent 侧统计。"""
    window = window_date or datetime.now().strftime("%Y-%m-%d")
    stats: dict = {
        "window": {"start": window, "end": window},
        "danmu": {},
        "gift": {},
        "entrance": {},
        "agent": {},
        "highlights": [],
    }

    if db is not None:
        try:
            rows = db.fetch_all("SELECT COUNT(*), COUNT(DISTINCT username) FROM danmu WHERE date(ts) = ?", (window,))
            stats["danmu"] = {"count": rows[0][0], "users": rows[0][1]}
            peak = db.fetch_all(
                "SELECT strftime('%H', ts) AS h, COUNT(*) AS c FROM danmu WHERE date(ts) = ? GROUP BY h ORDER BY c DESC LIMIT 3",
                (window,),
            )
            stats["danmu"]["peak_hours"] = [{"hour": f"{r[0]}点", "count": r[1]} for r in peak]

            rows = db.fetch_all("SELECT COUNT(*), IFNULL(SUM(total_price), 0) FROM gift WHERE date(ts) = ?", (window,))
            stats["gift"] = {"count": rows[0][0], "total_price": rows[0][1]}
            top_gift = db.fetch_all(
                "SELECT username, SUM(total_price) AS t FROM gift WHERE date(ts) = ? GROUP BY username ORDER BY t DESC LIMIT 3",
                (window,),
            )
            stats["gift"]["top"] = [{"username": r[0], "total_price": r[1]} for r in top_gift]

            rows = db.fetch_all("SELECT COUNT(*) FROM entrance WHERE date(ts) = ?", (window,))
            stats["entrance"] = {"count": rows[0][0]}

            top_viewers = db.fetch_all(
                "SELECT username, interactions FROM viewer_profile ORDER BY interactions DESC LIMIT 3", ()
            )
            stats["top_viewers"] = [{"username": r[0], "interactions": r[1]} for r in top_viewers]
        except Exception as e:
            logger.warning(f"复盘统计读取业务表失败（可能是表还没建）：{e}")

    # Agent 决策统计（trace 是最近 200 条滚动窗口，报告标注口径）
    records = list(trace_records)
    total = len(records)
    degraded = sum(1 for r in records if r.get("degraded"))
    tool_calls = [tc for r in records for tc in r.get("tool_calls", [])]
    stats["agent"] = {
        "decisions": total,
        "degraded": degraded,
        "degrade_rate": round(degraded / total * 100, 1) if total else 0.0,
        "fallback_used": sum(1 for r in records if r.get("reason") == "model_fallback"),
        "small_routed": sum(1 for r in records if r.get("reason") == "small_model_direct"),
        "tool_total": len(tool_calls),
        "tool_ok": sum(1 for tc in tool_calls if tc.get("ok")),
        "window_note": "最近200条决策滚动窗口（非严格按日）",
    }
    return stats


def build_report_text(stats: dict, llm_summary: str | None = None) -> str:
    window = stats.get("window", {})
    danmu = stats.get("danmu") or {}
    gift = stats.get("gift") or {}
    entrance = stats.get("entrance") or {}
    agent = stats.get("agent") or {}

    lines = [f"# 直播复盘 · {window.get('start', '')}", ""]
    lines.append("## 总览")
    if danmu:
        peak = "、".join(f"{p['hour']}（{p['count']}条）" for p in danmu.get("peak_hours", []))
        lines.append(
            f"- 弹幕 {danmu.get('count', 0)} 条（{danmu.get('users', 0)} 位观众）" + (f"，高峰：{peak}" if peak else "")
        )
    if entrance:
        lines.append(f"- 入场 {entrance.get('count', 0)} 人次")
    if gift:
        top = "、".join(f"{t['username']}（{t['total_price']}）" for t in gift.get("top", []))
        lines.append(
            f"- 礼物 {gift.get('count', 0)} 个，合计约 {gift.get('total_price', 0)}" + (f"，Top：{top}" if top else "")
        )
    if agent:
        lines.append(
            f"- Agent 决策 {agent.get('decisions', 0)} 次，降级率 {agent.get('degrade_rate', 0)}%"
            f"（备用模型 {agent.get('fallback_used', 0)} 次、小模型直答 {agent.get('small_routed', 0)} 次），"
            f"工具调用 {agent.get('tool_ok', 0)}/{agent.get('tool_total', 0)}"
        )
    viewers = stats.get("top_viewers") or []
    if viewers:
        lines.append("")
        lines.append("## 互动 Top")
        lines.extend(f"{i + 1}. {v['username']}（互动 {v['interactions']} 次）" for i, v in enumerate(viewers))
    highlights = stats.get("highlights") or []
    if highlights:
        lines.append("")
        lines.append("## 高光时刻")
        lines.extend(f"- {h}" for h in highlights)
    if llm_summary:
        lines.append("")
        lines.append("## AI 总结与建议")
        lines.append(llm_summary)
    return "\n".join(lines).strip()


def save_report(db, content: str, window_date: str) -> int:
    _ensure_table(db)
    db.execute(
        "INSERT INTO agent_report (ts, window_date, content) VALUES (?, ?, ?)", (datetime.now(), window_date, content)
    )
    rows = db.fetch_all("SELECT MAX(id) FROM agent_report")
    return int(rows[0][0])


def list_reports(db, limit: int = 20) -> list:
    _ensure_table(db)
    return db.fetch_all(
        "SELECT id, ts, window_date, LENGTH(content) FROM agent_report ORDER BY id DESC LIMIT ?", (limit,)
    )


def get_report(db, report_id: int):
    rows = db.fetch_all("SELECT id, ts, window_date, content FROM agent_report WHERE id = ?", (report_id,))
    return rows[0] if rows else None


def llm_summarize(handle, stats: dict):
    """AI 复盘总结：失败返回 None（报告回落纯统计，不阻塞生成）。"""
    try:
        from luna.agent.llm_adapter import LLMAdapter

        config = handle.config
        chat_type = config.get("chat_type")
        adapter = LLMAdapter(handle, chat_type, config.get("agent", "llm", "channel") or "auto")
        system = (
            "你是直播运营顾问。根据给出的直播统计 JSON 写一段简短复盘：亮点 2-3 条、问题 1-2 条、"
            "改进建议 2-3 条。口语化中文，直接输出正文，不要 Markdown 标题。"
        )
        prompt = json.dumps(stats, ensure_ascii=False, default=str)[:4000]
        result = adapter.call([{"role": "system", "content": system}, {"role": "user", "content": prompt}], [])
        return (result.text or "").strip() or None
    except Exception:
        logger.error("复盘 AI 总结失败：\n" + __import__("traceback").format_exc())
        return None
