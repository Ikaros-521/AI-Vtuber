"""app.api 内部 HTTP API 的 TestClient 单测（原先 main.py 内嵌路由零覆盖）。

用替身 state 驱动 FastAPI 应用工厂，不拉起 My_handle/Audio 真实依赖。
"""

from types import SimpleNamespace

from fastapi.testclient import TestClient

import utils.my_global as my_global
from app.api import create_api_app
from tests.unit.fakes import FakeConfig


class FakeHandle:
    """记录调用，便于断言 /send 的分发与 /callback 的副作用。"""

    def __init__(self):
        self.calls = []

    def reread_handle(self, data, **kwargs):
        self.calls.append(("reread_handle", data, kwargs))

    def process_data(self, data, flag):
        self.calls.append(("process_data", data, flag))

    def tuning_handle(self, data):
        self.calls.append(("tuning_handle", data))

    def gift_handle(self, data):
        self.calls.append(("gift_handle", data))

    def entrance_handle(self, data):
        self.calls.append(("entrance_handle", data))

    def llm_handle(self, type, data, webui_show=True):
        self.calls.append(("llm_handle", type, data, webui_show))
        return "llm 回复内容"

    def get_audio_info(self):
        return {"message_queue": 0}


def _make_state(tmp_config=None):
    config_data = tmp_config or {
        "idle_time_task": {"wait_play_audio_num_threshold": 10, "idle_time_reduce_to": 0},
        "webui": {"local_dir_to_endpoint": {"enable": False}},
        "api_port": 18000,
    }
    handle = FakeHandle()
    state = SimpleNamespace(config=FakeConfig(config_data), my_handle=handle, common=None, platform="talk")
    return state, handle


def _client(state):
    return TestClient(create_api_app(state))


def test_send_dispatch_reread():
    state, handle = _make_state()
    with _client(state) as client:
        resp = client.post("/send", json={"type": "reread", "data": {"platform": "p", "content": "hi"}})
    assert resp.status_code == 200
    assert resp.json()["code"] == 200
    assert handle.calls == [("reread_handle", {"platform": "p", "content": "hi", "type": "reread"}, {"type": "reread"})]


def test_send_dispatch_comment_gift_entrance_tuning():
    state, handle = _make_state()
    with _client(state) as client:
        assert client.post("/send", json={"type": "comment", "data": {"content": "c"}}).json()["code"] == 200
        assert client.post("/send", json={"type": "gift", "data": {"content": "g"}}).json()["code"] == 200
        assert client.post("/send", json={"type": "entrance", "data": {"content": "e"}}).json()["code"] == 200
        assert client.post("/send", json={"type": "tuning", "data": {"content": "t"}}).json()["code"] == 200
    flags = [c[0] for c in handle.calls]
    assert flags == ["process_data", "gift_handle", "entrance_handle", "tuning_handle"]
    assert handle.calls[0][2] == "comment"


def test_llm_endpoint():
    state, handle = _make_state()
    with _client(state) as client:
        resp = client.post("/llm", json={"type": "comment", "username": "u", "content": "问题"})
    assert resp.json()["code"] == 200
    assert resp.json()["data"] == {"content": "llm 回复内容"}
    assert handle.calls[0][0] == "llm_handle"
    assert handle.calls[0][1] == "comment"
    assert handle.calls[0][3] is False  # webui_show=False 与原实现一致


def test_callback_audio_playback_completed_updates_counters():
    state, _ = _make_state()
    my_global.wait_play_audio_num = 99
    my_global.wait_synthesis_msg_num = 5
    my_global.global_idle_time = 12345
    try:
        with _client(state) as client:
            resp = client.post(
                "/callback",
                json={
                    "type": "audio_playback_completed",
                    "data": {"wait_play_audio_num": 3, "wait_synthesis_msg_num": 1},
                },
            )
        assert resp.json()["code"] == 200
        assert my_global.wait_play_audio_num == 3
        assert my_global.wait_synthesis_msg_num == 1
    finally:
        my_global.wait_play_audio_num = 0
        my_global.wait_synthesis_msg_num = 0
        my_global.global_idle_time = 0


def test_callback_over_threshold_resets_idle_time():
    state, _ = _make_state()
    my_global.global_idle_time = 999
    try:
        with _client(state) as client:
            resp = client.post(
                "/callback",
                json={
                    "type": "audio_playback_completed",
                    "data": {"wait_play_audio_num": 11, "wait_synthesis_msg_num": 0},
                },
            )
        assert resp.json()["code"] == 200
        # 阈值10，回传11 > 10：闲时计时被压到 idle_time_reduce_to=0
        assert my_global.global_idle_time == 0
    finally:
        my_global.global_idle_time = 0


def test_get_sys_info():
    state, _ = _make_state()
    with _client(state) as client:
        resp = client.get("/get_sys_info")
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["audio"] == {"message_queue": 0}
    assert "wait_play_audio_num" in body["data"]["metahuman-stream"]
