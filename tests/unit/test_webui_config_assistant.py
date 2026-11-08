"""配置助手（v5 P2）：变更集解析 / 敏感键复核 / 安全等级 / 落盘 / 端点。"""

import json

import pytest
from fastapi.testclient import TestClient

from webui_server.config_assistant import CHANGES_MARKER, ConfigAssistant
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


def test_split_output_with_marker():
    assistant = ConfigAssistant(runtime)
    raw = (
        f"已开启点歌功能，重启后生效。\n{CHANGES_MARKER}\n"
        '{"changes": [{"path": ["choose_song","enable"], "value": true, "reason": "点歌需求"}], "questions": ["歌库目录在哪？"]}'
    )
    result = assistant._split_output(raw)
    assert result["reply"] == "已开启点歌功能，重启后生效。"
    assert result["changes"][0]["path"] == ["choose_song", "enable"]
    assert result["questions"] == ["歌库目录在哪？"]


def test_split_output_legacy_marker_still_accepted():
    """容错：模型输出旧版 <<<CHANGES>>> 标记也能解析。"""
    assistant = ConfigAssistant(runtime)
    result = assistant._split_output('ok\n<<<CHANGES>>>\n{"changes": [], "questions": []}')
    assert result["reply"] == "ok"


def test_split_output_without_marker_treats_all_as_reply():
    """模型没按协议输出（缺分隔行）：整段当说明、不出变更——宁可不改不可误改。"""
    assistant = ConfigAssistant(runtime)
    result = assistant._split_output("这只是普通回答，不涉及配置")
    assert result["changes"] == []
    assert "普通回答" in result["reply"]


def test_split_output_broken_changes_json():
    assistant = ConfigAssistant(runtime)
    result = assistant._split_output(f"说明文字\n{CHANGES_MARKER}\n{{broken json")
    assert result["reply"] == "说明文字"
    assert result["changes"] == []


def test_chat_stream_yields_deltas_then_done(tmp_config):
    """流式：delta 逐条透出，done 带安全等级处理后的变更状态。"""
    assistant = ConfigAssistant(runtime)
    assistant._call_llm_stream = lambda prompt: (
        iter(
            [
                f"已开启。\n{CHANGES_MARKER}\n",
                '{"changes": [{"path": ["choose_song","enable"], "value": true, "reason": "r"}], "questions": []}',
            ]
        ),
        None,
    )

    events = list(assistant.chat_stream("s1", "我要点歌"))
    deltas = [e["text"] for e in events if e["type"] == "reply_delta"]
    done = [e for e in events if e["type"] == "done"]
    assert "".join(deltas).startswith("已开启。")
    assert len(done) == 1
    assert done[0]["reply"] == "已开启。"
    assert done[0]["changes"][0]["status"] == "pending"  # manual 全挂起
    assert done[0]["elapsed_ms"] >= 0
    assert read_tmp_config(tmp_config)["choose_song"]["enable"] is False
    # 历史：完整说明（不含协议尾巴）入档
    assert assistant._history("s1")[-1] == ("assistant", "已开启。")


def test_chat_stream_error_event(tmp_config):
    assistant = ConfigAssistant(runtime)
    assistant._call_llm_stream = lambda prompt: (None, "模型没有返回内容")
    events = list(assistant.chat_stream("s1", "hi"))
    assert events == [{"type": "error", "message": "调用模型失败：模型没有返回内容"}]


def test_enforce_danger_for_sensitive_paths():
    assistant = ConfigAssistant(runtime)
    assert assistant._enforce_danger(["openai", "api_key"], False) is True
    assert assistant._enforce_danger(["login", "enable"], False) is True
    assert assistant._enforce_danger(["choose_song", "enable"], False) is False


# ---------- 会话历史 ----------


def test_history_roundtrip_and_reset(tmp_config):
    assistant = ConfigAssistant(runtime)
    assistant._call_llm = lambda prompt: ("这是回答", None)
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


def test_config_chat_stream_endpoint_sse(tmp_config, monkeypatch):
    """SSE 端点：事件按 data: 行输出，[DONE] 收尾。"""
    assistant = _get_assistant()

    def fake_stream(session_id, message):
        yield {"type": "reply_delta", "text": "你好"}
        yield {
            "type": "done",
            "reply": "你好",
            "changes": [
                {"path": ["choose_song", "enable"], "value": True, "reason": "r", "danger": False, "status": "pending"}
            ],
            "questions": [],
            "elapsed_ms": 12,
            "level": "manual",
        }

    monkeypatch.setattr(assistant, "chat_stream", fake_stream)

    with _client() as client:
        resp = client.post("/api/agent/config-chat-stream", json={"session_id": "t", "message": "hi"})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    assert "data: " in resp.text
    assert "reply_delta" in resp.text
    assert "[DONE]" in resp.text
