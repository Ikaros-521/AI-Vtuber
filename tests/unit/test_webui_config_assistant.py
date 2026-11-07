"""配置助手（v5 P2）：变更集解析 / 敏感键复核 / 安全等级 / 落盘 / 端点。"""

import json

import pytest
from fastapi.testclient import TestClient

from webui_server.config_assistant import ConfigAssistant
from webui_server.agent_api import _get_assistant
from webui_server.app import create_app
from webui_server.runtime import runtime


@pytest.fixture()
def tmp_config(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(
        json.dumps(
            {
                "platform": "talk",
                "chat_type": "chatgpt",
                "database": {"path": str(tmp_path / "t.db")},
                "login": {"enable": False},
                "choose_song": {"enable": False},
                "agent": {"enabled": True, "config_assistant": {"safety_level": "manual"}, "tools": {"enabled": []}},
                "webui": {"ip": "127.0.0.1", "port": 18888},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(runtime, "config_path", str(cfg_file))
    return cfg_file


def read_tmp_config(tmp_config):
    return json.loads(tmp_config.read_text(encoding="utf-8"))


# ---------- 解析协议 ----------


def test_parse_reply_json_block():
    assistant = ConfigAssistant(runtime)
    raw = '好的\n```json\n{"reply": "已开启点歌", "changes": [{"path": ["choose_song","enable"], "value": true, "reason": "点歌需求"}], "questions": []}\n```'
    result = assistant._parse_reply(raw)
    assert result["reply"] == "已开启点歌"
    assert result["changes"][0]["path"] == ["choose_song", "enable"]


def test_parse_reply_bare_json_and_failure_fallback():
    assistant = ConfigAssistant(runtime)
    result = assistant._parse_reply('{"reply": "直接给", "changes": [], "questions": ["歌库在哪个目录？"]}')
    assert result["questions"] == ["歌库在哪个目录？"]
    broken = assistant._parse_reply("这不是 JSON，就是一段普通回答")
    assert broken["changes"] == []
    assert "普通回答" in broken["reply"]


def test_enforce_danger_for_sensitive_paths():
    assistant = ConfigAssistant(runtime)
    assert assistant._enforce_danger(["openai", "api_key"], False) is True
    assert assistant._enforce_danger(["login", "enable"], False) is True
    assert assistant._enforce_danger(["choose_song", "enable"], False) is False


# ---------- 会话历史 ----------


def test_history_roundtrip_and_reset(tmp_config):
    assistant = ConfigAssistant(runtime)
    assistant._call_llm = lambda prompt: '{"reply": "r1", "changes": [], "questions": []}'
    assistant.chat("s1", "第一条")
    assistant.chat("s1", "第二条")
    history = assistant._history("s1")
    assert [role for role, _ in history] == ["user", "assistant", "user", "assistant"]
    assistant.reset_session("s1")
    assert assistant._history("s1") == []


# ---------- 安全等级与落盘 ----------


def test_safety_level_roundtrip(tmp_config):
    assistant = ConfigAssistant(runtime)
    assert assistant.safety_level() == "manual"
    ok, message = assistant.set_safety_level("auto")
    assert ok and "自动审核" in message
    assert assistant.safety_level() == "auto"
    assert read_tmp_config(tmp_config)["agent"]["config_assistant"]["safety_level"] == "auto"
    ok, _ = assistant.set_safety_level("nope")
    assert not ok


def test_apply_changes_writes_atomically(tmp_config):
    assistant = ConfigAssistant(runtime)
    results = assistant.apply_changes(
        [{"path": ["choose_song", "enable"], "value": True}, {"path": ["no_such", "deep", "key"], "value": 1}]
    )
    assert [r["ok"] for r in results] == [True, True]  # 深层缺失键按 setdefault 补齐
    data = read_tmp_config(tmp_config)
    assert data["choose_song"]["enable"] is True
    assert data["no_such"]["deep"]["key"] == 1


# ---------- 端点 ----------


def _client():
    return TestClient(create_app())


def test_config_chat_endpoint_manual_level_keeps_pending(tmp_config, monkeypatch):
    canned = {
        "reply": "开点歌需要两步",
        "changes": [
            {"path": ["choose_song", "enable"], "value": True, "reason": "点歌需求", "danger": False},
            {"path": ["openai", "api_key"], "value": "x", "reason": "换key", "danger": True},
        ],
        "questions": [],
    }
    monkeypatch.setattr(_get_assistant(), "chat", lambda sid, msg: canned)

    with _client() as client:
        body = client.post("/api/agent/config-chat", json={"session_id": "t", "message": "我要点歌"}).json()
    assert body["code"] == 200
    assert [c["status"] for c in body["changes"]] == ["pending", "pending"]  # manual 全挂起
    assert read_tmp_config(tmp_config)["choose_song"]["enable"] is False  # 没落盘


def test_config_chat_endpoint_auto_level_applies_safe_only(tmp_config, monkeypatch):
    canned = {
        "reply": "好",
        "changes": [
            {"path": ["choose_song", "enable"], "value": True, "reason": "点歌", "danger": False},
            {"path": ["openai", "api_key"], "value": "x", "reason": "换key", "danger": True},
        ],
        "questions": [],
    }
    assistant = _get_assistant()
    monkeypatch.setattr(assistant, "chat", lambda sid, msg: canned)
    monkeypatch.setattr(assistant, "safety_level", lambda: "auto")

    with _client() as client:
        body = client.post("/api/agent/config-chat", json={"session_id": "t", "message": "我要点歌"}).json()
    statuses = {tuple(c["path"]): c["status"] for c in body["changes"]}
    assert statuses[("choose_song", "enable")] == "applied"
    assert statuses[("openai", "api_key")] == "pending"  # 敏感变更 auto 也不自动落盘
    assert read_tmp_config(tmp_config)["choose_song"]["enable"] is True


def test_config_apply_endpoint(tmp_config):
    with _client() as client:
        body = client.post(
            "/api/agent/config-apply",
            json={"changes": [{"path": ["choose_song", "similarity"], "value": 0.3}]},
        ).json()
    assert body["code"] == 200
    assert read_tmp_config(tmp_config)["choose_song"]["similarity"] == 0.3


def test_assistant_settings_endpoint_roundtrip(tmp_config):
    with _client() as client:
        assert client.get("/api/agent/assistant-settings").json()["safety_level"] == "manual"
        assert client.post("/api/agent/assistant-settings", json={"safety_level": "full"}).json()["code"] == 200
        assert client.get("/api/agent/assistant-settings").json()["safety_level"] == "full"
