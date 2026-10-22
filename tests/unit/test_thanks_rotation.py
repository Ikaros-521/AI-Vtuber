"""礼物/入场感谢的顺序取文案。

开「随机」时走 random.choice，关随机才是顺序弹队列——这条路径以前少了
「队列空了就从配置重新拷一份」那行，第一次送礼就 IndexError，被上层
except 吞成 return None，于是礼物感谢在顺序模式下永远不出声。
"""

import pytest

from fakes import FakeConfig
from utils.my_handle import My_handle


THANKS = {
    "username_max_len": 10,
    "lowest_price": 0,
    "gift_enable": True,
    "gift_random": False,
    "gift_copy": ["谢谢 {gift_name}", "老板大气", "感谢打赏"],
    "entrance_enable": True,
    "entrance_random": False,
    "entrance_copy": ["欢迎 {username}", "你来啦"],
}


@pytest.fixture
def thanks_handle(configure):
    handle = configure({"thanks": dict(THANKS)})
    # 这三个是把消息推给 TTS/助播/按键映射的旁路，和文案轮转无关
    handle.key_mapping_handle = lambda *a, **k: None
    handle.custom_cmd_handle = lambda *a, **k: None
    handle.audio_synthesis_handle = lambda message: None
    My_handle.thanks_gift_copy = []
    My_handle.thanks_entrance_copy = []
    return handle


def gift_data():
    return {"username": "小明", "gift_name": "小心心", "num": 1,
            "unit_price": 1, "total_price": 10}


def test_sequential_gift_thanks_rotates_through_the_config_copies(thanks_handle):
    contents = [thanks_handle.gift_handle(gift_data())["content"] for _ in range(3)]

    assert contents == ["谢谢 小心心", "老板大气", "感谢打赏"]


def test_sequential_gift_thanks_refills_after_the_queue_is_drained(thanks_handle):
    for _ in range(3):
        thanks_handle.gift_handle(gift_data())
    assert My_handle.thanks_gift_copy == []

    assert thanks_handle.gift_handle(gift_data())["content"] == "谢谢 小心心"


def test_gift_thanks_is_skipped_below_the_lowest_price(thanks_handle):
    My_handle.config = FakeConfig({"thanks": dict(THANKS, lowest_price=100)})

    assert thanks_handle.gift_handle(gift_data()) is None


def test_random_gift_thanks_does_not_consume_the_sequential_queue(thanks_handle):
    My_handle.config = FakeConfig({"thanks": dict(THANKS, gift_random=True)})

    for _ in range(5):
        assert thanks_handle.gift_handle(gift_data()) is not None

    assert My_handle.thanks_gift_copy == []


def test_entrance_thanks_rotates_and_refills(thanks_handle):
    first = thanks_handle.entrance_handle({"username": "小明"})["content"]

    for _ in range(3):
        thanks_handle.entrance_handle({"username": "小红"})

    assert first == "欢迎 小明"
    assert thanks_handle.entrance_handle({"username": "小刚"})["content"] == "欢迎 小刚"
