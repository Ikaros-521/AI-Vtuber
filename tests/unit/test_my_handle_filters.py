"""弹幕过滤：comment_check_and_replace 与 prohibitions_handle / blacklist_handle。

这些判断决定一条弹幕会不会被丢掉，是 my_handle 里最值得钉住的一段逻辑。
"""

import copy

import pytest

BASE_FILTER = {
    "before_must_str": [],
    "after_must_str": [],
    "before_filter_str": [],
    "after_filter_str": [],
    "emoji": False,
    "badwords": {
        "enable": False,
        "discard": False,
        "path": "",
        "bad_pinyin_path": "",
        "replace": "*",
    },
    "blacklist": {"enable": False, "username": []},
    "limited_time_deduplication": {"enable": False, "comment": 10, "gift": 10, "entrance": 60},
}


@pytest.fixture
def filter_config(configure):
    """装好一份完整 filter 配置，返回可改写的 dict。"""

    data = {"filter": copy.deepcopy(BASE_FILTER), "need_lang": "none"}
    handle = configure(data)
    handle.data = data
    return handle


def run(handle, content):
    return handle.comment_check_and_replace(content)


def test_passes_through_plain_comment(filter_config):
    assert run(filter_config, "你好呀") == "你好呀"


def test_before_filter_str_drops_comment(filter_config):
    filter_config.data["filter"]["before_filter_str"] = ["#"]
    assert run(filter_config, "#隐藏指令") is None


def test_after_filter_str_drops_comment(filter_config):
    filter_config.data["filter"]["after_filter_str"] = ["#"]
    assert run(filter_config, "尾部有井号#") is None


def test_before_must_str_requires_prefix_and_strips_it(filter_config):
    filter_config.data["filter"]["before_must_str"] = ["主播"]
    assert run(filter_config, "主播今天好看") == "今天好看"
    assert run(filter_config, "别人今天好看") is None


def test_after_must_str_requires_suffix_and_strips_it(filter_config):
    filter_config.data["filter"]["after_must_str"] = ["吗"]
    assert run(filter_config, "吃过了吗") == "吃过了"
    assert run(filter_config, "吃过了") is None


def test_punctuation_only_comment_is_dropped(filter_config):
    assert run(filter_config, "！！！") is None


def test_newline_becomes_comma(filter_config):
    assert run(filter_config, "第一行\n第二行") == "第一行,第二行"


def test_emoji_tag_is_stripped_when_enabled(filter_config):
    filter_config.data["filter"]["emoji"] = True
    assert run(filter_config, "你好[开心]") == "你好"


def test_emoji_tag_kept_when_disabled(filter_config):
    filter_config.data["filter"]["emoji"] = False
    assert run(filter_config, "你好[开心]") == "你好[开心]"


def test_url_is_rejected_by_prohibitions(filter_config):
    assert filter_config.prohibitions_handle("https://example.com/x") is None


def test_plain_text_survives_prohibitions(filter_config):
    assert filter_config.prohibitions_handle("今天天气不错") == "今天天气不错"


def test_badword_is_discarded_when_configured(filter_config, tmp_path):
    words = tmp_path / "badwords.txt"
    words.write_text("傻瓜\n", encoding="utf-8")
    bad = filter_config.data["filter"]["badwords"]
    bad.update({"enable": True, "discard": True, "path": str(words)})

    assert filter_config.prohibitions_handle("你个傻瓜") is None


def test_badword_is_replaced_when_not_discarding(filter_config, tmp_path):
    words = tmp_path / "badwords.txt"
    words.write_text("傻瓜\n", encoding="utf-8")
    bad = filter_config.data["filter"]["badwords"]
    bad.update({"enable": True, "discard": False, "path": str(words), "replace": "*"})

    assert filter_config.prohibitions_handle("你个傻瓜") == "你个*"


def test_blacklist_hits_and_misses(filter_config):
    bl = filter_config.data["filter"]["blacklist"]
    bl.update({"enable": True, "username": ["捣乱者"]})

    assert filter_config.blacklist_handle({"username": "捣乱者", "content": "x"}) is True
    assert filter_config.blacklist_handle({"username": "路人", "content": "x"}) is False

    bl["enable"] = False
    assert filter_config.blacklist_handle({"username": "捣乱者", "content": "x"}) is False
