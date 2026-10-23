"""聊天记录面板（webui_app/chat_log.py）的多连接行为。

nicegui 3 每来一个浏览器连接就把 webui.py 重跑一遍，每个连接各有一棵组件树，
聊天页的滚动区因此是「每连接挂载一次」。这里用手工建的 Client 当浏览器连接，
盯住三件事：所有已打开的页面都收得到、新打开的页面补得上历史、关掉的页面不再往里堆。
"""

import pytest
from nicegui import Client, ui
from nicegui.page import page

from webui_app.chat_log import MAX_MESSAGES, ChatLog

TEST_PAGE = page('/chat-log-unit-test')


@pytest.fixture
def boxes():
    """造浏览器连接，用完把 client 删掉，别留给同一个 pytest 会话的其它用例。"""
    created = []

    def make():
        client = Client(TEST_PAGE)
        with client:
            scroll_area = ui.scroll_area()
        created.append(client)
        return scroll_area

    yield make

    for client in created:
        # 用例里自己删过的连接别删第二遍，nicegui 会 KeyError
        if not client.is_deleted:
            client.delete()


def question(text):
    return {"type": "llm", "data": {"type": "弹幕信息", "username": "观众",
                                    "content_type": "question", "content": text,
                                    "timestamp": "2026-10-22 21:40:50"}}


def answer(text):
    return {"type": "llm", "data": {"type": "chatgpt", "username": "观众",
                                    "content_type": "answer", "content": text,
                                    "timestamp": "2026-10-22 21:40:57"}}


def rendered(scroll_area):
    # 面板里除了消息还可能有「还没有聊天记录」占位，只数消息
    return [m._original_text[0] for m in scroll_area if hasattr(m, '_original_text')]


def placeholders(scroll_area):
    return [c for c in scroll_area if not hasattr(c, '_original_text')]


def test_every_open_page_gets_the_message(boxes):
    """两个页面同时开着，弹幕与 LLM 回复都要出现在两边（只记最后一个 = 先开的页面不再更新）。"""
    log = ChatLog()
    first, second = boxes(), boxes()
    log.mount(first)
    log.mount(second)

    log.add(question("巅峰赛不适合直播"))
    log.add(answer("确实不适合"))

    assert rendered(first) == ["巅峰赛不适合直播", "确实不适合"]
    assert rendered(second) == ["巅峰赛不适合直播", "确实不适合"]


def test_newly_opened_page_replays_history(boxes):
    """刷新/新开页面必须补上已收到的记录，否则聊天页是一片空白。"""
    log = ChatLog()
    first = boxes()
    log.mount(first)
    log.add(question("开了有啥用"))
    log.add(answer("那我闭嘴"))

    second = boxes()
    log.mount(second)

    assert rendered(second) == ["开了有啥用", "那我闭嘴"]


def test_closed_page_is_dropped(boxes):
    """页面关掉后别再往它那棵组件树里堆消息，登记项也要收掉。"""
    log = ChatLog()
    alive = boxes()
    dead = boxes()
    log.mount(alive)
    log.mount(dead)
    dead.client.delete()

    log.add(question("还在吗"))

    assert rendered(alive) == ["还在吗"]
    assert rendered(dead) == []
    assert log.scroll_areas == [alive]


def test_history_and_panel_capped(boxes):
    """历史与面板各有硬上限，长时间直播不能把 webui 撑爆。"""
    log = ChatLog()
    box = boxes()
    log.mount(box)

    for i in range(MAX_MESSAGES + 20):
        log.add(question(f"弹幕{i}"))

    assert len(log.messages) == MAX_MESSAGES
    assert len(list(box)) == MAX_MESSAGES
    assert rendered(box)[-1] == f"弹幕{MAX_MESSAGES + 19}"


def test_non_llm_callback_is_ignored(boxes):
    """/callback 也会收到别的类型，面板只认 llm。"""
    log = ChatLog()
    box = boxes()
    log.mount(box)

    log.add({"type": "other", "data": {"content_type": "question", "content": "不该出现"}})

    assert rendered(box) == []
    assert len(log.messages) == 0


def test_empty_panel_shows_placeholder(boxes):
    """一条消息都没有时得有个说明，否则看着像坏了；来消息就撤掉。"""
    log = ChatLog()
    box = boxes()
    log.mount(box)
    assert len(placeholders(box)) == 1
    assert rendered(box) == []

    log.add(question("在吗"))
    assert placeholders(box) == []
    assert rendered(box) == ["在吗"]


def test_replayed_history_has_no_placeholder(boxes):
    """有历史可补的时候不要挂占位，说明会和消息混在一起。"""
    log = ChatLog()
    first = boxes()
    log.mount(first)
    log.add(question("在吗"))

    second = boxes()
    log.mount(second)
    assert placeholders(second) == []
    assert rendered(second) == ["在吗"]
