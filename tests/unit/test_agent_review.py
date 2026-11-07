"""直播复盘（v5 P2）：统计聚合 / 报告文本 / 存取 / 机机端点。"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from types import SimpleNamespace

from luna.agent.review import (
    build_report_text,
    collect_stats,
    get_report,
    list_reports,
    llm_summarize,
    save_report,
)
from luna.infra.db import SQLiteDB


@pytest.fixture()
def seeded_db(tmp_path):
    db = SQLiteDB(str(tmp_path / "review.db"))
    now = datetime.now()
    db.execute("CREATE TABLE danmu (username TEXT, content TEXT, ts DATETIME)")
    db.execute(
        "CREATE TABLE gift (username TEXT, gift_name TEXT, gift_num INT, unit_price REAL, total_price REAL, ts DATETIME)"
    )
    db.execute("CREATE TABLE entrance (username TEXT, ts DATETIME)")
    db.execute("INSERT INTO danmu (username, content, ts) VALUES (?, ?, ?)", ("alice", "哈哈", now))
    db.execute("INSERT INTO danmu (username, content, ts) VALUES (?, ?, ?)", ("alice", "点歌", now))
    db.execute("INSERT INTO danmu (username, content, ts) VALUES (?, ?, ?)", ("bob", "来了", now))
    db.execute(
        "INSERT INTO gift (username, gift_name, gift_num, unit_price, total_price, ts) VALUES (?, ?, ?, ?, ?, ?)",
        ("alice", "小花", 2, 1.0, 2.0, now),
    )
    db.execute("INSERT INTO entrance (username, ts) VALUES (?, ?)", ("bob", now))
    db.execute(
        "CREATE TABLE viewer_profile (platform TEXT, username TEXT, first_seen DATETIME, last_seen DATETIME, "
        "interactions INT, note TEXT)"
    )
    db.execute("INSERT INTO viewer_profile VALUES ('bilibili', 'alice', ?, ?, 9, '')", (now, now))
    return db


def test_collect_stats_aggregates_local_tables(seeded_db):
    stats = collect_stats(seeded_db, [], "2020-01-01")  # 非当日：业务数据为 0
    assert stats["danmu"]["count"] == 0

    stats = collect_stats(seeded_db, [])
    assert stats["danmu"]["count"] == 3
    assert stats["danmu"]["users"] == 2
    assert stats["gift"]["count"] == 1
    assert stats["gift"]["total_price"] == 2.0
    assert stats["gift"]["top"][0]["username"] == "alice"
    assert stats["entrance"]["count"] == 1
    assert stats["top_viewers"][0] == {"username": "alice", "interactions": 9}


@pytest.fixture(autouse=True)
def _clear_trace_recent():
    """RECENT 是进程级滚动窗口，不清理会被其它测试的 trace 记录污染计数断言。"""
    from luna.agent.trace import RECENT

    RECENT.clear()
    yield
    RECENT.clear()


def test_collect_stats_agent_window(seeded_db):
    from luna.agent.trace import RECENT, Trace

    Trace(event_type="comment", username="a", source="comment").finish(output_chars=1)
    Trace(event_type="comment", username="b", source="comment").finish(degraded=True, reason="model_error")
    stats = collect_stats(seeded_db, list(RECENT))  # 与生产端点同口径：RECENT 里是 dict
    assert stats["agent"]["decisions"] == 2
    assert stats["agent"]["degrade_rate"] == 50.0


def test_build_report_text_contains_sections(seeded_db):
    stats = collect_stats(seeded_db, [])
    stats["highlights"] = ["观众点歌《晴天》"]
    text = build_report_text(stats, llm_summary="亮点：互动不错。建议：多接梗。")
    assert "# 直播复盘" in text
    assert "弹幕 3 条（2 位观众）" in text
    assert "礼物 1 个" in text
    assert "## AI 总结与建议" in text
    assert "多接梗" in text


def test_report_persist_roundtrip(seeded_db):
    report_id = save_report(seeded_db, "复盘内容A", "2026-11-07")
    save_report(seeded_db, "复盘内容B", "2026-11-08")
    rows = list_reports(seeded_db)
    assert len(rows) == 2
    assert rows[0][2] == "2026-11-08"  # 倒序
    assert get_report(seeded_db, report_id)[3] == "复盘内容A"


def test_llm_summarize_degrades_on_error(seeded_db):
    class BoomHandle:
        config = {}

        def __getattr__(self, name):
            raise RuntimeError("down")

    assert llm_summarize(BoomHandle(), {"x": 1}) is None


# ---------- 机机端点 ----------


def test_machine_review_endpoints(tmp_path, monkeypatch):
    from fakes import FakeConfig

    db = SQLiteDB(str(tmp_path / "t.db"))
    state = SimpleNamespace(
        my_handle=SimpleNamespace(db=db, agent_runtime=None),
        config=FakeConfig({"webui": {"local_dir_to_endpoint": {"enable": False}}}),
    )
    from app.api import create_api_app

    client = TestClient(create_api_app(state))

    resp = client.post("/agent_review/generate", json={"use_llm": False})
    assert resp.json()["code"] == 200
    content = resp.json()["data"]["content"]
    assert "直播复盘" in content

    listing = client.get("/agent_review/list").json()
    assert listing["data"]["reports"][0]["window_date"]

    got = client.get(f"/agent_review?report_id={listing['data']['reports'][0]['id']}").json()
    assert "直播复盘" in got["data"]["content"]
    assert client.get("/agent_review?report_id=999").json()["code"] == -1
