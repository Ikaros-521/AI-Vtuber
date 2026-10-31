"""「直播弹幕监听助手」这个统一入口。

快手2/拼多多/斗鱼/1688/淘宝的弹幕都不是本程序直连平台，而是外部助手（游猴）
用 websocket 推给本机的，所以这五个平台标识共用一个监听器。这里锁三件事：
旧值仍然认（老 config 不改也能收弹幕）、监听地址能配、缺配置时回落到
以前写死的那组值。再加上助手推过来的消息本身有两代脚本的字段形状，
两种都得认。
"""

import asyncio
import json

import pytest

from fakes import FakeConfig
from luna.platforms import PLATFORM_LISTENERS

ASSISTANT_MODULE = "luna.platforms.lx_live_monitor_assistant"
LEGACY_KEYS = ("ks2", "pdd", "douyu", "1688", "taobao")


def _captured_addr(monkeypatch, config):
    import luna.platforms.lx_live_monitor_assistant as lx

    captured = {}

    class FakeServer:
        async def wait_closed(self):
            return None

    async def fake_serve(handler, *args, **kwargs):
        captured["addr"] = args
        return FakeServer()

    monkeypatch.setattr(lx.websockets, "serve", fake_serve)
    lx.start_listen(config, None, None, "live_monitor_assistant")
    return captured["addr"]


def test_the_unified_key_routes_to_the_assistant_listener():
    assert PLATFORM_LISTENERS["live_monitor_assistant"] == ASSISTANT_MODULE


@pytest.mark.parametrize("legacy", LEGACY_KEYS)
def test_legacy_platform_names_still_route_to_it(legacy):
    """删掉下拉里的五项容易，让老 config.json 继续能收弹幕才是重点。"""
    assert PLATFORM_LISTENERS[legacy] == ASSISTANT_MODULE


def test_listener_binds_the_configured_address(monkeypatch):
    """以前 ip/端口写死在函数里，换端口只能改源码。"""
    addr = _captured_addr(
        monkeypatch,
        FakeConfig(
            {
                "live_monitor_assistant": {"ws_ip": "0.0.0.0", "ws_port": 5105},
            }
        ),
    )

    assert addr == ("0.0.0.0", 5105)


def test_a_port_saved_as_text_still_binds_the_right_number(monkeypatch):
    """页面上的端口是文本框，存进 config 可能是 "5105"。"""
    addr = _captured_addr(
        monkeypatch,
        FakeConfig(
            {
                "live_monitor_assistant": {"ws_port": "5105"},
            }
        ),
    )

    assert addr == ("127.0.0.1", 5105)


def test_missing_config_falls_back_to_the_old_hardcoded_values(monkeypatch):
    """老用户的 config.json 里没有这一段，得跟以前一样起在 127.0.0.1:5001。"""
    assert _captured_addr(monkeypatch, FakeConfig({})) == ("127.0.0.1", 5001)


@pytest.mark.parametrize("bad", ["", "abc", 0, -1, 70000, None])
def test_an_impossible_port_falls_back_instead_of_binding_somewhere_odd(monkeypatch, bad):
    """绑到错的端口上，用户看到的现象只是「一条弹幕都收不到」。"""
    addr = _captured_addr(
        monkeypatch,
        FakeConfig(
            {
                "live_monitor_assistant": {"ws_ip": "127.0.0.1", "ws_port": bad},
            }
        ),
    )

    assert addr == ("127.0.0.1", 5001)


# ---------- 助手推过来的消息 ----------


class _FakeSocket:
    def __init__(self, messages):
        self._messages = list(messages)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)


class _Handle:
    def __init__(self):
        self.batches = []
        self.alarms = []

    def process_data(self, data, timer_flag):
        self.batches.append((timer_flag, data))

    def abnormal_alarm_handle(self, type):
        self.alarms.append(type)


def _feed(monkeypatch, *payloads, platform="live_monitor_assistant"):
    """把助手会发的 JSON 原样灌进监听器，返回它交给 my_handle 的东西。"""
    import luna.infra.my_global as my_global
    import luna.platforms.lx_live_monitor_assistant as lx

    captured = {}

    class FakeServer:
        async def wait_closed(self):
            return None

    async def fake_serve(handler, *args, **kwargs):
        captured["handler"] = handler
        return FakeServer()

    monkeypatch.setattr(lx.websockets, "serve", fake_serve)

    handle = _Handle()
    config = FakeConfig({"idle_time_task": {"trigger_type": ["comment", "gift"]}})
    monkeypatch.setattr(my_global, "last_username_list", [""])

    lx.start_listen(config, None, handle, platform)
    messages = [p if isinstance(p, str) else json.dumps(p, ensure_ascii=False) for p in payloads]
    asyncio.run(captured["handler"](_FakeSocket(messages)))
    return handle


def test_comment_goes_to_the_comment_pipeline(monkeypatch):
    handle = _feed(
        monkeypatch,
        {
            "type": "comment",
            "username": "观众甲",
            "content": "主播好",
            "data": None,  # 新脚本每条消息都带这个字段
        },
    )

    assert handle.batches == [
        (
            "comment",
            {
                "platform": "live_monitor_assistant",
                "username": "观众甲",
                "content": "主播好",
            },
        )
    ]


def test_gift_from_the_new_payload_shape(monkeypatch):
    """新脚本统一成 {type, username, content, data:{gift}}。"""
    handle = _feed(
        monkeypatch,
        {
            "type": "gift",
            "username": "观众乙",
            "content": "小心心 x2",
            "data": {"gift": "小心心 x2"},
        },
    )

    timer_flag, data = handle.batches[0]
    assert timer_flag == "gift"
    assert data["gift_name"] == "小心心 x2"
    assert data["username"] == "观众乙"
    assert data["platform"] == "live_monitor_assistant"
    # 助手扒的是页面文字，没有数量和价格
    assert (data["num"], data["unit_price"], data["total_price"]) == (1, 0, 0)


def test_gift_name_prefers_the_data_field_over_content(monkeypatch):
    handle = _feed(
        monkeypatch,
        {
            "type": "gift",
            "username": "丙",
            "content": "送出了 火箭",
            "data": {"gift": "火箭"},
        },
    )

    assert handle.batches[0][1]["gift_name"] == "火箭"


@pytest.mark.parametrize(
    "payload, expected",
    [
        # 旧版洛曦脚本的礼物形状：没有 content，礼物名直接挂在 gift 上
        ({"type": "gift", "username": "丁", "gift": "棒棒糖"}, "棒棒糖"),
        # 只有 content 的变体
        ({"type": "gift", "username": "戊", "content": "大啤酒"}, "大啤酒"),
        # data 不是字典也不能崩
        ({"type": "gift", "username": "己", "content": "小花", "data": "脏数据"}, "小花"),
    ],
)
def test_gift_name_extraction_covers_both_script_generations(monkeypatch, payload, expected):
    handle = _feed(monkeypatch, payload)

    assert handle.batches[0][1]["gift_name"] == expected


def test_a_gift_without_any_name_is_skipped_not_fabricated(monkeypatch):
    """往积分表里塞一条名为「礼物」的记录，比丢掉这条更难查。"""
    handle = _feed(monkeypatch, {"type": "gift", "username": "庚", "content": ""})

    assert handle.batches == []
    assert handle.alarms == []


def test_like_is_ignored_without_breaking_the_stream(monkeypatch):
    """点赞没有对应的处理流程，但也不能因为它把后面的弹幕一起带走。"""
    handle = _feed(
        monkeypatch,
        {"type": "like", "username": "辛", "content": "点了个赞"},
        {"type": "comment", "username": "辛", "content": "还在吗"},
    )

    assert [flag for flag, _ in handle.batches] == ["comment"]


def test_an_unlisted_type_is_ignored(monkeypatch):
    handle = _feed(monkeypatch, {"type": "entrance", "username": "壬"})

    assert handle.batches == []


def test_broken_json_alarms_and_keeps_listening(monkeypatch):
    handle = _feed(monkeypatch, "{不是json", {"type": "comment", "username": "癸", "content": "hi"})

    assert handle.alarms == ["platform"]
    assert [flag for flag, _ in handle.batches] == ["comment"]


def test_the_platform_label_follows_whatever_key_was_configured(monkeypatch):
    """积分表按平台分列，旧别名照旧写自己的名字，不被并成一项。"""
    handle = _feed(
        monkeypatch,
        {"type": "comment", "username": "子", "content": "hi"},
        platform="pdd",
    )

    assert handle.batches[0][1]["platform"] == "pdd"
