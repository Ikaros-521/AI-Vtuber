"""MemorySystem：观众画像 + 高光事件的 sqlite 记忆（P0 范围）。

表挂在使用方传入的 SQLiteDB 上（My_handle.config_load 已建好其余业务表）；
agent 域不反向依赖 my_handle，db 经构造注入。写入双路：gift/entrance/弹幕
事件自动 touch_viewer + Agent 经 memory_save 工具主动备注/记高光。

语义约定：note 每观众一条（后写覆盖，主播可在 WebUI 里看/改）；platform+username
作主键——多数平台拿不到稳定 uid，用户名是现有 integral 表同款的现实选择。
"""

from datetime import datetime


class MemorySystem:
    def __init__(self, db, enable_profile: bool = True, enable_episodic: bool = True):
        self.db = db
        self.enable_profile = enable_profile
        self.enable_episodic = enable_episodic
        if db is not None:
            self._ensure_tables()

    def _ensure_tables(self) -> None:
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS viewer_profile (
                platform TEXT NOT NULL,
                username TEXT NOT NULL,
                first_seen DATETIME NOT NULL,
                last_seen DATETIME NOT NULL,
                interactions INT NOT NULL DEFAULT 0,
                note TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (platform, username)
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS agent_episodic (
                ts DATETIME NOT NULL,
                kind TEXT NOT NULL,
                username TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL
            )
        """)

    def touch_viewer(self, platform: str, username: str) -> None:
        """观众出现即更新画像：不存在建档，存在刷新 last_seen 并累计互动。"""
        if not self.enable_profile or self.db is None or not username:
            return
        rows = self.db.fetch_all(
            "SELECT first_seen FROM viewer_profile WHERE platform = ? AND username = ?", (platform, username)
        )
        now = datetime.now()
        if rows:
            self.db.execute(
                "UPDATE viewer_profile SET last_seen = ?, interactions = interactions + 1 "
                "WHERE platform = ? AND username = ?",
                (now, platform, username),
            )
        else:
            self.db.execute(
                "INSERT INTO viewer_profile (platform, username, first_seen, last_seen, interactions, note) "
                "VALUES (?, ?, ?, ?, 1, '')",
                (platform, username, now, now),
            )

    def viewer_summary(self, platform: str, username: str):
        """一行画像摘要，注入 system prompt；按预算截断由调用方负责。"""
        if not self.enable_profile or self.db is None or not username:
            return None
        rows = self.db.fetch_all(
            "SELECT interactions, note FROM viewer_profile WHERE platform = ? AND username = ?",
            (platform, username),
        )
        if not rows:
            return None
        interactions, note = rows[0]
        summary = f"互动 {interactions} 次"
        if note:
            summary += f"；备注：{note}"
        return summary

    def save_note(self, platform: str, username: str, content: str) -> None:
        if self.db is None or not username:
            return
        self.touch_viewer(platform, username)
        self.db.execute(
            "UPDATE viewer_profile SET note = ? WHERE platform = ? AND username = ?", (content, platform, username)
        )

    def save_highlight(self, content: str, username: str = "") -> None:
        if not self.enable_episodic or self.db is None or not content:
            return
        self.db.execute(
            "INSERT INTO agent_episodic (ts, kind, username, content) VALUES (?, 'highlight', ?, ?)",
            (datetime.now(), username, content),
        )

    def recent_highlights(self, limit: int = 3) -> list:
        if not self.enable_episodic or self.db is None:
            return []
        rows = self.db.fetch_all(
            "SELECT content FROM agent_episodic WHERE kind = 'highlight' ORDER BY ts DESC LIMIT ?", (limit,)
        )
        return [r[0] for r in rows]

    # ---------- 管理接口（WebUI 记忆管理页用；读侧不启用也允许查已存数据） ----------

    def list_viewers(self, keyword: str = "", limit: int = 100) -> list:
        """观众画像列表，按最近互动倒序；keyword 模糊匹配用户名。"""
        if self.db is None:
            return []
        try:
            if keyword:
                return self.db.fetch_all(
                    "SELECT platform, username, first_seen, last_seen, interactions, note "
                    "FROM viewer_profile WHERE username LIKE ? ORDER BY last_seen DESC LIMIT ?",
                    (f"%{keyword}%", limit),
                )
            return self.db.fetch_all(
                "SELECT platform, username, first_seen, last_seen, interactions, note "
                "FROM viewer_profile ORDER BY last_seen DESC LIMIT ?",
                (limit,),
            )
        except Exception:
            # 表还没建（agent 从未启用过）按空处理，WebUI 显示空态
            return []

    def delete_viewer(self, platform: str, username: str) -> bool:
        if self.db is None:
            return False
        self.db.execute("DELETE FROM viewer_profile WHERE platform = ? AND username = ?", (platform, username))
        return True

    def list_highlights(self, limit: int = 50) -> list:
        """高光时间线（带 rowid 供删除），按时间倒序。"""
        if self.db is None:
            return []
        try:
            return self.db.fetch_all(
                "SELECT rowid, ts, username, content FROM agent_episodic WHERE kind = 'highlight' "
                "ORDER BY ts DESC LIMIT ?",
                (limit,),
            )
        except Exception:
            return []

    def delete_highlight(self, row_id: int) -> bool:
        if self.db is None:
            return False
        self.db.execute("DELETE FROM agent_episodic WHERE rowid = ?", (row_id,))
        return True
