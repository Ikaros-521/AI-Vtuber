"""utils/common.py 里不依赖网络的纯函数。

Common 被 my_handle、audio_handle、各平台模块到处调用，这些小函数的行为一旦漂了，
影响面比 webui 大得多，所以先钉住。
"""

import os

import pytest


@pytest.fixture
def c():
    from utils.common import Common

    return Common()


def test_is_pure_number(c):
    assert c.is_pure_number("12345") is True
    assert c.is_pure_number("12.3") is False
    assert c.is_pure_number("") is False


def test_is_url_check(c):
    assert c.is_url_check("https://example.com/a") is True
    assert c.is_url_check("example.com") is False
    assert c.is_url_check("你好") is False


def test_is_valid_ip_and_port(c):
    assert c.is_valid_ip("127.0.0.1") is True
    assert c.is_valid_ip("0.0.0.0") is True
    assert c.is_valid_ip("999.1.1.1") is False
    assert c.is_valid_port("8420") is True
    assert c.is_valid_port(0) is False
    assert c.is_valid_port(65536) is False
    assert c.is_valid_port("abc") is False


def test_is_dir_or_file(c, tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x", encoding="utf-8")

    assert c.is_dir_or_file(str(tmp_path), "dir") is True
    assert c.is_dir_or_file(str(f), "file") is True
    assert c.is_dir_or_file(str(f), "dir") is False
    assert c.is_dir_or_file(str(tmp_path), "all") is True
    assert c.is_dir_or_file(str(tmp_path / "nope"), "all") is False


def test_find_key_by_value(c):
    d = {"a": 1, "b": 2, "cc": 1}

    assert c.find_keys_by_value(d, 1) == ["a", "cc"]
    assert c.find_key_by_value(d, 1) == "a"
    assert c.find_key_by_value(d, 99) is None


def test_is_json_convertible(c):
    assert c.is_json_convertible('{"a": 1}') is True
    assert c.is_json_convertible("[]") is True
    assert c.is_json_convertible("不是json") is False


def test_convert_digits_to_chinese(c):
    assert c.convert_digits_to_chinese("666") == "六六六"
    assert c.convert_digits_to_chinese("1号玩家") == "一号玩家"
    assert c.convert_digits_to_chinese("无数字") == "无数字"


def test_remove_extra_words_truncates_words_then_chars(c):
    long_text = " ".join(f"w{i}" for i in range(40))

    out = c.remove_extra_words(long_text, max_len=30, max_char_len=50)

    # 先按词数截断补省略号，再按字符数硬切，所以省略号会被切掉
    assert len(out) == 50
    assert out.startswith("w0 w1 w2")


def test_remove_extra_words_keeps_the_ellipsis_when_it_fits(c):
    long_text = " ".join(f"x{i}" for i in range(40))

    out = c.remove_extra_words(long_text, max_len=30, max_char_len=200)

    assert out.endswith("...")


def test_remove_extra_words_leaves_short_text_alone(c):
    assert c.remove_extra_words("一句话", max_len=30, max_char_len=50) == "一句话"


def test_check_sensitive_words(c, tmp_path):
    words = tmp_path / "w.txt"
    words.write_text("傻瓜\n混蛋\n", encoding="utf-8")

    assert c.check_sensitive_words(str(words), "你是傻瓜") is True
    assert c.check_sensitive_words(str(words), "你好") is False


def test_starts_with_any(c):
    assert c.starts_with_any("#指令", ["#", "@"]) == "#"
    assert c.starts_with_any("普通弹幕", ["#", "@"]) is None


def test_merge_consecutive_asterisks_only_collapses_long_trailing_runs(c):
    # 现实现把超过 3 个的尾部连续 * 收成 2 个（s[:i] + '*' + 最后一个 '*'），
    # 而不是注释里说的 1 个；先按实际行为钉住，将来要改这里就是显式的变更点。
    assert c.merge_consecutive_asterisks("好******") == "好**"
    assert c.merge_consecutive_asterisks("好****") == "好**"
    assert c.merge_consecutive_asterisks("好***") == "好***"
    assert c.merge_consecutive_asterisks("好*中间**") == "好*中间**"


def test_replace_special_characters(c):
    assert c.replace_special_characters("a/b\\c:d", "/\\:") == "abcd"


def test_parse_cookie_data(c):
    raw = "SESSDATA=abc123; bili_jct=def; DedeUserID=42"

    assert c.parse_cookie_data(raw, "SESSDATA") == "abc123"
    assert c.parse_cookie_data(raw, "DedeUserID") == "42"
    assert c.parse_cookie_data(raw, "missing") == ""


def test_dynamic_variable_replacement(c):
    data = {"username": "观众甲", "content": "你好"}

    assert c.dynamic_variable_replacement("{username} 说了 {content}", data) == "观众甲 说了 你好"
    # 未知占位符保持原样，不能把整条文案弄坏
    assert c.dynamic_variable_replacement("{unknown} 还在", data) == "{unknown} 还在"
    assert c.dynamic_variable_replacement("{username}", None) == "{username}"


def test_brackets_text_randomize(c):
    out = c.brackets_text_randomize("[哈哈|嘿嘿]你好")

    assert out in ("哈哈你好", "嘿嘿你好")


def test_get_random_str_in_list_and_format(c):
    from_list = c.get_random_str_in_list_and_format(ori_content="兜底", ori_list=["[a|b]值"], var_json={"n": 3})
    assert from_list["ret"] == 0
    assert from_list["content"].startswith(("a值", "b值"))

    fallback = c.get_random_str_in_list_and_format(ori_content="兜底", ori_list=[])
    assert fallback == {"ret": 0, "content": "兜底"}

    assert c.get_random_str_in_list_and_format() == {"ret": -1, "content": None}


def test_get_list_random_or_default(c):
    assert c.get_list_random_or_default([], "默认") == "默认"
    assert c.get_list_random_or_default(None, "默认") == "默认"
    assert c.get_list_random_or_default(["唯一"], "默认") == "唯一"


def test_punctuation_helpers(c):
    assert c.is_punctuation_string("！！！") is True
    assert c.is_punctuation_string("你好") is False
    assert c.is_all_space_and_punct("  ！  ") is True
    assert c.is_all_space_and_punct(" 哈 ") is False


def test_find_best_match_and_substring(c):
    words = ["今天天气", "明天天气"]

    assert c.find_best_match("今天天气", words, 1) == "今天天气"
    assert c.find_best_match("今天天气不错", words, 0.5) == "今天天气"
    assert c.find_best_match("完全不像的一句话", words, 0.99) is None

    assert c.find_substring_in_list("我的SESSDATA是x", ["SESSDATA"]) == "SESSDATA"
    assert c.find_substring_in_list("没有", ["SESSDATA"]) is None


def test_path_helpers(c):
    folder, name = c.split_path_and_filename("out/1.wav")

    assert name == "1.wav"
    assert folder.endswith("out/") or folder.endswith("out\\")
    assert c.extract_filename("out/1.wav") == "1"
    assert c.extract_filename("out/1.wav", True) == "1.wav"


def test_remove_extension_from_list(c):
    assert c.remove_extension_from_list(["a.wav", "b.mp3"]) == ["a", "b"]


def test_is_audio_file(c):
    for name in ("a.mp3", "a.wav", "a.MP3", "a.WAV", "a.ogg"):
        assert c.is_audio_file(name) is True, name
    # 当前只认这几种扩展名，flac 会被拒
    assert c.is_audio_file("a.flac") is False
    assert c.is_audio_file("a.txt") is False


def test_get_filename_from_path_reports_errors_in_dict(c, tmp_path):
    f = tmp_path / "x.wav"
    f.write_text("x", encoding="utf-8")

    assert c.get_filename_from_path(str(f))["data"] == "x.wav"
    assert c.get_filename_from_path("")["error"] == "路径不能为空"
    missing = c.get_filename_from_path(str(tmp_path / "nope.wav"))
    assert missing["data"] is None and missing["code"] == 404


def test_get_new_audio_path_is_always_absolute(c, tmp_path):
    absolute = c.get_new_audio_path(str(tmp_path), "1.wav")
    relative = c.get_new_audio_path("out", "1.wav")

    assert absolute == os.path.join(str(tmp_path), "1.wav")
    assert os.path.isabs(relative)
    assert relative.endswith(os.path.join("out", "1.wav"))


def test_get_bj_time_formats(c):
    stamp = c.get_bj_time(0)

    assert len(stamp) == 19 and stamp[4] == "-" and stamp[13] == ":"
    assert c.get_bj_time(2).isdigit()

    c.count = 0
    assert c.get_bj_time(4) == "1"
    assert c.get_bj_time(4) == "2"


def test_time_difference_in_seconds_sign(c):
    from datetime import datetime, timedelta

    future = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
    past = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")

    assert 3500 < c.time_difference_in_seconds(future) < 3700
    assert -3700 < c.time_difference_in_seconds(past) < -3500
