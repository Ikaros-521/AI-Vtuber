"""Chatgpt 会话历史：超长上下文重试不能把回复写两遍，会话表本身要有上限。

sessionid 传的是观众用户名（get_gpt_resp → chat(prompt, username)），所以
Chatgpt.sessions 是跨实例共享的类属性、按用户名累积。
"""

import pytest

from utils.gpt_model.chatgpt import Chatgpt

OVERFLOW = "This model's maximum context length is 409 tokens is exceeded"


@pytest.fixture
def chatgpt():
    Chatgpt.sessions.clear()
    instance = Chatgpt({"api_key": "sk-test"}, {"preset": "你是一个测试用的虚拟主播"})
    yield instance
    Chatgpt.sessions.clear()


def test_overflow_retry_leaves_one_assistant_message(chatgpt):
    replies = [OVERFLOW, "正常回复"]
    chatgpt.chat_with_gpt = lambda messages: replies.pop(0)

    assert chatgpt.chat("你好呀", "观众甲") == "正常回复"

    history = Chatgpt.sessions["观众甲"]["msg"]
    assert [m["role"] for m in history].count("assistant") == 1
    assert history[-1]["content"] == "正常回复"


def test_normal_reply_is_recorded_once(chatgpt):
    chatgpt.chat_with_gpt = lambda messages: "普通回复"

    assert chatgpt.chat("第一条", "观众乙") == "普通回复"

    history = Chatgpt.sessions["观众乙"]["msg"]
    assert [m["role"] for m in history].count("assistant") == 1


def test_none_response_is_passed_through_without_touching_history(chatgpt):
    chatgpt.chat_with_gpt = lambda messages: None

    assert chatgpt.chat("发条消息", "观众丙") is None

    assert [m["role"] for m in Chatgpt.sessions["观众丙"]["msg"]].count("assistant") == 0


def test_sessions_are_keyed_by_str_and_reused(chatgpt):
    chatgpt.chat_with_gpt = lambda messages: "回复"

    chatgpt.chat("一", 7)
    chatgpt.chat("二", 7)

    assert list(Chatgpt.sessions) == ["7"]
    assert [m["role"] for m in Chatgpt.sessions["7"]["msg"]].count("assistant") == 2


def test_default_cap_is_10000():
    assert Chatgpt.MAX_SESSIONS == 10000


def test_the_sessions_table_stops_growing_at_the_cap(chatgpt, monkeypatch):
    """观众名当 sessionid，一场直播几万个 key，每个还挂着一条只会变长的历史。"""
    monkeypatch.setattr(Chatgpt, "MAX_SESSIONS", 3)

    for name in ("甲", "乙", "丙", "丁", "戊"):
        chatgpt.get_chat_session(name)

    assert list(Chatgpt.sessions) == ["丙", "丁", "戊"]

    # 被丢掉的那位再发言不会炸，只是没有上下文了
    assert chatgpt.get_chat_session("甲")["id"] == "甲"


def test_an_active_viewer_is_not_the_one_evicted(chatgpt, monkeypatch):
    """淘汰要丢「最久没开口」的，不是「最早进直播间的」——老观众一直在说话。"""
    monkeypatch.setattr(Chatgpt, "MAX_SESSIONS", 3)

    for name in ("甲", "乙", "丙"):
        chatgpt.get_chat_session(name)

    chatgpt.get_chat_session("甲")  # 甲又说话了
    chatgpt.get_chat_session("丁")

    assert list(Chatgpt.sessions) == ["丙", "甲", "丁"]
