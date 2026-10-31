"""回答回推给 webui 聊天面板的回调。"""

from fakes import FakeSender
from luna.core.my_handle import My_handle


def payload(**over):
    data = {"username": "观众甲", "content": "今天天气怎么样"}
    data.update(over)
    return data


def test_nothing_sent_when_chat_log_disabled(configure):
    handle = configure({"talk": {"show_chat_log": False}, "webui": {"ip": "127.0.0.1", "port": 8080}})
    My_handle.common = FakeSender()

    handle.webui_show_chat_log_callback("chatgpt", payload(), "晴天")

    assert My_handle.common.requests == []


def test_answer_is_pushed_to_callback_endpoint(configure):
    handle = configure({"talk": {"show_chat_log": True}, "webui": {"ip": "127.0.0.1", "port": 8080}})
    My_handle.common = FakeSender()
    data = payload()

    handle.webui_show_chat_log_callback("chatgpt", data, "晴天")

    url, method, body = My_handle.common.requests[0]
    assert url == "http://127.0.0.1:8080/callback"
    assert method == "POST"
    assert body["type"] == "llm"
    assert body["data"]["type"] == "chatgpt"
    assert body["data"]["content"] == "晴天"
    assert body["data"]["content_type"] == "answer"
    assert body["data"]["username"] == "观众甲"


def test_original_question_is_backfilled_into_payload(configure):
    handle = configure({"talk": {"show_chat_log": True}, "webui": {"ip": "0.0.0.0", "port": 8420}})
    My_handle.common = FakeSender()
    data = payload()

    handle.webui_show_chat_log_callback("gemini", data, "晴天")

    assert data["ori_username"] == "观众甲"
    assert data["ori_content"] == "今天天气怎么样"
    # 0.0.0.0 不能直接请求，回推时换成回环地址
    assert My_handle.common.requests[0][0] == "http://127.0.0.1:8420/callback"


def test_missing_answer_falls_back_to_placeholder(configure):
    handle = configure({"talk": {"show_chat_log": True}, "webui": {"ip": "127.0.0.1", "port": 8080}})
    My_handle.common = FakeSender()

    handle.webui_show_chat_log_callback("dify", payload(), None)

    content = My_handle.common.requests[0][2]["data"]["content"]
    assert "dify" in content and content != "None"


def test_send_failure_is_swallowed(configure):
    handle = configure({"talk": {"show_chat_log": True}, "webui": {"ip": "127.0.0.1", "port": 8080}})

    class Boom:
        def send_request(self, *a, **kw):
            raise RuntimeError("webui 没起来")

    My_handle.common = Boom()

    assert handle.webui_show_chat_log_callback("chatgpt", payload(), "晴天") is None
