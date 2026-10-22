"""「直播弹幕监听助手」这个统一入口。

快手2/拼多多/斗鱼/1688/淘宝的弹幕都不是本程序直连平台，而是外部助手（游猴）
用 websocket 推给本机的，所以这五个平台标识共用一个监听器。这里锁三件事：
旧值仍然认（老 config 不改也能收弹幕）、监听地址能配、缺配置时回落到
以前写死的那组值。
"""

import pytest

from fakes import FakeConfig
from utils.platforms import PLATFORM_LISTENERS
from webui_app.options import (
    LEGACY_LIVE_MONITOR_PLATFORMS,
    PLATFORM_OPTIONS,
    platform_options,
)

ASSISTANT_MODULE = "utils.platforms.lx_live_monitor_assistant"
LEGACY_KEYS = ("ks2", "pdd", "douyu", "1688", "taobao")


def _captured_addr(monkeypatch, config):
    import utils.platforms.lx_live_monitor_assistant as lx

    captured = {}

    class FakeServer:
        async def wait_closed(self):
            return None

    async def fake_serve(handler, *args, **kwargs):
        captured['addr'] = args
        return FakeServer()

    monkeypatch.setattr(lx.websockets, 'serve', fake_serve)
    lx.start_listen(config, None, None, 'live_monitor_assistant')
    return captured['addr']


def test_the_unified_key_routes_to_the_assistant_listener():
    assert PLATFORM_LISTENERS['live_monitor_assistant'] == ASSISTANT_MODULE


@pytest.mark.parametrize('legacy', LEGACY_KEYS)
def test_legacy_platform_names_still_route_to_it(legacy):
    """删掉下拉里的五项容易，让老 config.json 继续能收弹幕才是重点。"""
    assert PLATFORM_LISTENERS[legacy] == ASSISTANT_MODULE


def test_the_dropdown_only_offers_the_unified_name():
    for legacy in LEGACY_KEYS:
        assert legacy not in PLATFORM_OPTIONS
    assert PLATFORM_OPTIONS['live_monitor_assistant'] == '直播弹幕监听助手'


def test_a_saved_legacy_name_is_still_shown_in_the_dropdown():
    """老配置存的是 pdd，下拉里必须还能看见它。

    收成一五项之后如果不做这一步，用户打开页面看到的是空白平台，
    随手点一次保存就把自己的平台改没了。
    """
    options = platform_options('pdd')

    assert 'pdd' in options
    assert options['pdd'] == LEGACY_LIVE_MONITOR_PLATFORMS['pdd']


def test_the_unified_name_is_shown_without_any_legacy_entry():
    options = platform_options('live_monitor_assistant')

    assert 'pdd' not in options
    assert list(PLATFORM_OPTIONS) == list(options)


def test_listener_binds_the_configured_address(monkeypatch):
    """以前 ip/端口写死在函数里，换端口只能改源码。"""
    addr = _captured_addr(monkeypatch, FakeConfig({
        "live_monitor_assistant": {"ws_ip": "0.0.0.0", "ws_port": 5105},
    }))

    assert addr == ("0.0.0.0", 5105)


def test_a_port_saved_as_text_still_binds_the_right_number(monkeypatch):
    """页面上的端口是文本框，存进 config 可能是 "5105"。"""
    addr = _captured_addr(monkeypatch, FakeConfig({
        "live_monitor_assistant": {"ws_port": "5105"},
    }))

    assert addr == ("127.0.0.1", 5105)


def test_missing_config_falls_back_to_the_old_hardcoded_values(monkeypatch):
    """老用户的 config.json 里没有这一段，得跟以前一样起在 127.0.0.1:5001。"""
    assert _captured_addr(monkeypatch, FakeConfig({})) == ("127.0.0.1", 5001)


@pytest.mark.parametrize('bad', ["", "abc", 0, -1, 70000, None])
def test_an_impossible_port_falls_back_instead_of_binding_somewhere_odd(monkeypatch, bad):
    """绑到错的端口上，用户看到的现象只是「一条弹幕都收不到」。"""
    addr = _captured_addr(monkeypatch, FakeConfig({
        "live_monitor_assistant": {"ws_ip": "127.0.0.1", "ws_port": bad},
    }))

    assert addr == ("127.0.0.1", 5001)
