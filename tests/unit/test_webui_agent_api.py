"""Agent 工作台（v5）的接口单测：webui_server/agent_api.py + app/api.py 机机接口。

webui 侧用 tmp 配置隔离（不碰仓库 config.json，不拉起 main.py）；
代理端点在主进程不运行时验证降级；记忆端点用 tmp sqlite 走真实读写。
"""

import json
import threading
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from luna.agent.trace import RECENT
from webui_server.app import create_app
from webui_server.runtime import runtime


@pytest.fixture()
def tmp_config(tmp_path, monkeypatch):
    """隔离配置：指向 tmp 文件，database 也指到 tmp sqlite。"""
    db_path = tmp_path / "t.db"
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(
        json.dumps(
            {
                "platform": "talk",
                "api_ip": "127.0.0.1",
                "api_port": 19777,  # 没有服务监听，代理端点应优雅降级
                "database": {"path": str(db_path)},
                "login": {"enable": False},
                "agent": {"enabled": True, "max_tool_rounds": 3, "tools": {"enabled": ["speak", "query_integral"]}},
                "webui": {"ip": "127.0.0.1", "port": 18888},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(runtime, "config_path", str(cfg_file))
    return cfg_file


@pytest.fixture(autouse=True)
def _clear_trace_recent():
    RECENT.clear()
    yield
    RECENT.clear()


def _client():
    return TestClient(create_app())


# ---------- webui 侧：总览 / 降级 / 记忆 ----------


def test_overview_merges_config_catalog_and_degraded_runtime(tmp_config):
    with _client() as client:
        body = client.get("/api/agent/overview").json()
    assert body["code"] == 200
    assert body["agent"]["enabled"] is True
    names = {tool["name"] for tool in body["tool_catalog"]}
    assert {"speak", "query_integral", "query_danmu_summary", "search_online", "memory_save"} <= names
    # 主进程没跑：running=False，运行态为空，不报 500
    assert body["running"] is False
    assert body["runtime"] is None


def test_trace_degrades_when_main_down(tmp_config):
    with _client() as client:
        body = client.get("/api/agent/trace").json()
    assert body["code"] == -1
    assert body["records"] == []
    assert "主进程" in body["message"]


def test_kill_degrades_when_main_down(tmp_config):
    with _client() as client:
        body = client.post("/api/agent/kill", json={"on": True}).json()
    assert body["code"] == -1


def test_memory_viewer_note_roundtrip(tmp_config):
    with _client() as client:
        assert (
            client.post(
                "/api/agent/memory/viewer/note",
                json={"platform": "bilibili", "username": "alice", "note": "喜欢点歌"},
            ).json()["code"]
            == 200
        )
        listed = client.get("/api/agent/memory/viewers?keyword=ali").json()
        assert listed["code"] == 200
        assert len(listed["viewers"]) == 1
        row = listed["viewers"][0]
        assert (row["username"], row["platform"], row["note"]) == ("alice", "bilibili", "喜欢点歌")

        assert (
            client.post(
                "/api/agent/memory/viewer/delete",
                json={"platform": "bilibili", "username": "alice"},
            ).json()["code"]
            == 200
        )
        assert client.get("/api/agent/memory/viewers").json()["viewers"] == []


def test_memory_highlight_roundtrip(tmp_config):
    from luna.agent.memory import MemorySystem
    from luna.infra.db import SQLiteDB

    db_path = json.loads(tmp_config.read_text(encoding="utf-8"))["database"]["path"]
    memory = MemorySystem(SQLiteDB(db_path))
    memory.save_highlight("第一条")
    memory.save_highlight("第二条", "alice")

    with _client() as client:
        listed = client.get("/api/agent/memory/highlights").json()
    assert listed["code"] == 200
    assert [h["content"] for h in listed["highlights"]] == ["第二条", "第一条"]  # 倒序
    row_id = listed["highlights"][0]["row_id"]
    with _client() as client:
        assert client.post("/api/agent/memory/highlight/delete", json={"row_id": row_id}).json()["code"] == 200
    assert len(memory.list_highlights()) == 1


# ---------- 主进程侧：app/api.py 机机接口 ----------


class StubRegistry:
    _tools = {"speak": object(), "query_integral": object()}


class StubRuntime:
    def __init__(self):
        self.kill_switch = False
        self.registry = StubRegistry()
        self._hour_used = 1234
        self._budget_lock = threading.Lock()


def _api_client(agent_runtime=None, enabled=True):
    from fakes import FakeConfig

    state = SimpleNamespace(
        config=FakeConfig({"agent": {"enabled": enabled, "budget": {"tokens_per_hour": 200000}}}),
        my_handle=SimpleNamespace(agent_runtime=agent_runtime),
    )
    from app.api import create_api_app

    return TestClient(create_api_app(state))


def test_machine_agent_status_without_runtime():
    with _api_client(agent_runtime=None) as client:
        body = client.get("/agent_status").json()
    assert body["code"] == 200
    assert body["data"] == {"enabled": True, "runtime": None}


def test_machine_agent_status_with_runtime():
    stub = StubRuntime()
    with _api_client(agent_runtime=stub) as client:
        body = client.get("/agent_status").json()
    assert body["code"] == 200
    runtime_info = body["data"]["runtime"]
    assert runtime_info["killed"] is False
    assert runtime_info["tools_enabled"] == ["speak", "query_integral"]
    assert runtime_info["hour_used"] == 1234
    assert runtime_info["hour_limit"] == 200000


def test_machine_agent_kill_toggles_switch():
    stub = StubRuntime()
    with _api_client(agent_runtime=stub) as client:
        assert client.post("/agent_kill", json={"on": True}).json()["code"] == 200
        assert stub.kill_switch is True
        assert client.post("/agent_kill", json={"on": False}).json()["code"] == 200
        assert stub.kill_switch is False


def test_machine_agent_kill_without_runtime_fails():
    with _api_client(agent_runtime=None) as client:
        body = client.post("/agent_kill", json={"on": True}).json()
    assert body["code"] == -1


def test_machine_agent_trace_returns_recent():
    from luna.agent.trace import Trace

    Trace(event_type="comment", username="alice", source="comment").finish(output_chars=5)
    with _api_client() as client:
        body = client.get("/agent_trace").json()
    assert body["code"] == 200
    assert body["data"]["records"][0]["username"] == "alice"
