"""MemorySystem：观众画像建档/累计、备注、高光时间线。"""

from luna.agent.memory import MemorySystem
from luna.infra.db import SQLiteDB


def make_memory(tmp_path, **kwargs):
    db = SQLiteDB(str(tmp_path / "mem.db"))
    return MemorySystem(db, **kwargs)


def test_touch_viewer_creates_then_accumulates(tmp_path):
    mem = make_memory(tmp_path)
    mem.touch_viewer("bilibili", "alice")
    mem.touch_viewer("bilibili", "alice")
    mem.touch_viewer("bilibili", "bob")
    rows = mem.db.fetch_all("SELECT username, interactions FROM viewer_profile ORDER BY username")
    assert rows == [("alice", 2), ("bob", 1)]


def test_viewer_summary_includes_note(tmp_path):
    mem = make_memory(tmp_path)
    assert mem.viewer_summary("bilibili", "alice") is None
    mem.touch_viewer("bilibili", "alice")
    summary = mem.viewer_summary("bilibili", "alice")
    assert summary is not None and "互动 1 次" in summary
    mem.save_note("bilibili", "alice", "喜欢点周杰伦的歌")
    assert "喜欢点周杰伦的歌" in mem.viewer_summary("bilibili", "alice")


def test_save_note_creates_profile_for_newcomer(tmp_path):
    mem = make_memory(tmp_path)
    mem.save_note("bilibili", "carol", "老粉")
    rows = mem.db.fetch_all("SELECT username, interactions, note FROM viewer_profile")
    assert rows == [("carol", 1, "老粉")]


def test_highlight_roundtrip_is_latest_first(tmp_path):
    mem = make_memory(tmp_path)
    for text in ("第一条", "第二条", "第三条"):
        mem.save_highlight(text)
    assert mem.recent_highlights(2) == ["第三条", "第二条"]
    assert len(mem.recent_highlights(10)) == 3


def test_disabled_layers_are_noop(tmp_path):
    db = SQLiteDB(str(tmp_path / "mem.db"))
    mem = MemorySystem(db, enable_profile=False, enable_episodic=False)
    mem.touch_viewer("bilibili", "alice")
    mem.save_highlight("x")
    assert db.fetch_all("SELECT * FROM viewer_profile") == []
    assert db.fetch_all("SELECT * FROM agent_episodic") == []
