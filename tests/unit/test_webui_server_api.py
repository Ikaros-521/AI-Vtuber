"""webui_server (v3 FastAPI 后端) 的 TestClient 单测——此前零覆盖。

用 tmp_path 隔离配置文件（monkeypatch runtime.config_path），
不碰仓库根目录的 config.json，也不拉起 main.py/Audio 真实依赖。
"""

import json

import pytest
from fastapi.testclient import TestClient

from webui_server.app import create_app
from webui_server.auth_api import _sessions
from webui_server.chat_log import chat_log
from webui_server.runtime import runtime


@pytest.fixture()
def tmp_config(tmp_path, monkeypatch):
    """把 runtime 的配置指向临时文件，返回该文件对象。"""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(
        json.dumps({"platform": "talk", "api_port": 18000, "login": {"enable": False}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(runtime, "config_path", str(cfg_file))
    return cfg_file


@pytest.fixture(autouse=True)
def _clean_session_and_chat_log():
    _sessions.clear()
    yield
    _sessions.clear()
    chat_log.messages.clear()


def _client(**kwargs):
    return TestClient(create_app(), **kwargs)


# ---------- auth ----------


def test_auth_status_login_disabled(tmp_config):
    with _client() as client:
        body = client.get("/api/auth/status").json()
    assert body["code"] == 200
    assert body["enabled"] is False
    assert body["authed"] is False


def test_login_flow_and_session_expiry(tmp_config):
    cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
    cfg["login"] = {"enable": True, "username": "admin", "password": "pw"}
    tmp_config.write_text(json.dumps(cfg), encoding="utf-8")

    with _client() as client:
        # 错误密码
        assert client.post("/api/auth/login", json={"username": "admin", "password": "bad"}).json()["code"] == -1
        # 正确登录拿到 cookie
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "pw"})
        assert resp.json()["code"] == 200
        status = client.get("/api/auth/status").json()
        assert status["authed"] is True and status["username"] == "admin"
        # 登出后会话失效
        client.post("/api/auth/logout")
        assert client.get("/api/auth/status").json()["authed"] is False


def test_expired_session_rejected(tmp_config):
    import time

    from webui_server.auth_api import COOKIE_NAME, is_valid_session

    _sessions["tok"] = ("admin", time.time() - 1)  # 已过期
    assert is_valid_session("tok") is False
    assert "tok" not in _sessions  # 过期即清理

    with _client() as client:
        client.cookies.set(COOKIE_NAME, "ghost")
        body = client.get("/api/auth/status").json()
    assert body["authed"] is False


# ---------- 登录门禁：/api/* 服务端强制 ----------


def test_login_guard_blocks_api_when_enabled(tmp_config):
    cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
    cfg["login"] = {"enable": True, "username": "admin", "password": "pw"}
    tmp_config.write_text(json.dumps(cfg), encoding="utf-8")

    with _client() as client:
        # 未登录：人机接口 401，auth 接口与机机接口不受影响
        assert client.get("/api/ops/status").status_code == 401
        assert client.get("/api/auth/status").json()["code"] == 200
        assert client.get("/get_sys_info").status_code == 200  # compat 机机接口

        # 登录后放行
        client.post("/api/auth/login", json={"username": "admin", "password": "pw"})
        assert client.get("/api/ops/status").json()["code"] == 200


def test_login_guard_inactive_when_login_disabled(tmp_config):
    with _client() as client:
        assert client.get("/api/ops/status").json()["code"] == 200


# ---------- 配置读写 ----------


def test_config_get_and_save_roundtrip(tmp_config):
    with _client() as client:
        got = client.get("/api/config").json()
        assert got["code"] == 200 and got["config"]["api_port"] == 18000

        resp = client.post(
            "/api/config/save",
            json={"base_sha256": got["sha256"], "changes": [{"path": ["api_port"], "value": 19000}]},
        ).json()
        assert resp["code"] == 200

        # 磁盘确实落盘
        on_disk = json.loads(tmp_config.read_text(encoding="utf-8"))
        assert on_disk["api_port"] == 19000


def test_config_save_conflict_409(tmp_config):
    with _client() as client:
        got = client.get("/api/config").json()
        stale_sha = got["sha256"]

        # 外部程序先改了文件（模拟 /set_config 抢写）
        cfg = json.loads(tmp_config.read_text(encoding="utf-8"))
        cfg["api_port"] = 1
        tmp_config.write_text(json.dumps(cfg), encoding="utf-8")

        resp = client.post(
            "/api/config/save",
            json={"base_sha256": stale_sha, "changes": [{"path": ["api_port"], "value": 2}]},
        ).json()
        assert resp["code"] == 409


def test_set_config_merges_and_writes(tmp_config):
    with _client() as client:
        resp = client.post("/set_config", json={"config_path": str(tmp_config), "data": {"new_key": "v"}}).json()
        assert resp["code"] == 200
        assert json.loads(tmp_config.read_text(encoding="utf-8"))["new_key"] == "v"


# ---------- 聊天记录 ----------


def test_callback_feeds_chat_log(tmp_config):
    payload = {
        "type": "llm",
        "data": {
            "type": "answer",
            "username": "主播",
            "content_type": "answer",
            "content": "回答内容",
            "timestamp": "2026-10-31 00:00:00",
        },
    }
    with _client() as client:
        assert client.post("/callback", json=payload).json()["code"] == 200
        body = client.get("/api/chat-log?after=0").json()
        assert body["code"] == 200
        assert any(m["content"] == "回答内容" for m in body["messages"])


def test_run_log_missing_file_is_not_500(tmp_path, tmp_config, monkeypatch):
    monkeypatch.setattr("webui_server.logs_api.log_file_path", str(tmp_path / "nope.log"))
    with _client() as client:
        body = client.get("/api/logs/run").json()
    assert body["code"] == 200
    assert body["lines"] == []


# ---------- 全局异常兜底 ----------


def test_uncaught_exception_returns_envelope(tmp_config, monkeypatch, tmp_path):
    # dist 存在时 / 是静态兜底挂载，会吞掉后注册的测试路由；指到不存在的目录绕开
    monkeypatch.setattr("webui_server.app.DIST_DIR", tmp_path / "no-dist")
    app = create_app()

    @app.get("/_boom")
    async def _boom():
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/_boom")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == -1
    assert "boom" in body["message"]
