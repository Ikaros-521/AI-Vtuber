"""webui 保存配置时的类型写回：config_store 与 helpers。"""

from fakes import FakeConfig, FakeWidget
from webui_app.config_store import process_config_mapping, update_config, update_nested_dict
from webui_app.helpers import common_textarea_handle, select_value_or_none, textarea_data_change


def test_int_handler_casts_and_defaults_blank_to_zero():
    mapping = {"a": {"n": (FakeWidget("12"), "int"), "blank": (FakeWidget(""), "int")}}

    out = process_config_mapping({}, mapping)

    assert out == {"a": {"n": 12, "blank": 0}}


def test_float_handler_rounds_to_two_decimals():
    mapping = {"a": {"r": (FakeWidget("1.2345"), "float"), "blank": (FakeWidget(None), "float")}}

    out = process_config_mapping({}, mapping)

    assert out == {"a": {"r": 1.23, "blank": 0}}


def test_str_and_bool_handlers():
    mapping = {
        "a": {
            "s": (FakeWidget(8420), "str"),
            "on": (FakeWidget(True), "bool"),
            "off": (FakeWidget(0), "bool"),
        }
    }

    out = process_config_mapping({}, mapping)

    assert out == {"a": {"s": "8420", "on": True, "off": False}}


def test_unselected_dropdown_does_not_write_the_string_None():
    """下拉框未选中时 value 是 None，str(None) 会把 'None' 落进 config.json，
    下次启动看起来像用户真填了个窗口标题。"""
    mapping = {"image_recognition": {"screenshot_window_title": (FakeWidget(None), "str")}}

    out = process_config_mapping({}, mapping)

    assert out == {"image_recognition": {"screenshot_window_title": ""}}


def test_select_value_or_none():
    # 选项是运行时枚举出来的，配置里存的值可能已经不在了
    assert select_value_or_none("记事本", {"记事本": "记事本", "Chrome": "Chrome"}) == "记事本"
    assert select_value_or_none("已关闭的窗口", {"Chrome": "Chrome"}) is None
    assert select_value_or_none(0, {}) is None
    assert select_value_or_none(None, {"a": "a"}) is None
    assert select_value_or_none(2, [1, 2, 3]) == 2
    assert select_value_or_none(9, [1, 2, 3]) is None


def test_textarea_handler_splits_and_strips_lines():
    mapping = {"a": {"list": (FakeWidget("甲\n  乙  \n\n"), "textarea")}}

    out = process_config_mapping({}, mapping)

    assert out == {"a": {"list": ["甲", "乙"]}}


def test_deeply_nested_paths_are_created():
    out = process_config_mapping({}, {"sec": {"a": {"b": {"c": (FakeWidget("v"), "str")}}}})

    assert out == {"sec": {"a": {"b": {"c": "v"}}}}


def test_update_nested_dict_replaces_leaf_only():
    target = {"a": {"keep": 1}}

    update_nested_dict(target, ["a", "b"], 2)

    assert target == {"a": {"keep": 1, "b": 2}}


def test_update_config_skips_sections_hidden_by_show_card():
    config = FakeConfig({"webui": {"show_card": {"common_config": {"on": True, "off": False}}}})
    mapping = {
        "on": {"v": (FakeWidget("1"), "str")},
        "off": {"v": (FakeWidget("2"), "str")},
    }

    out = update_config(mapping, config, {}, "common_config")

    assert out == {"on": {"v": "1"}}


def test_update_config_with_none_type_ignores_show_card():
    config = FakeConfig({"webui": {"show_card": {"common_config": {}}}})
    mapping = {"anything": {"v": (FakeWidget("x"), "str")}}

    out = update_config(mapping, config, {}, None)

    assert out == {"anything": {"v": "x"}}


def test_update_config_preserves_unrelated_sections():
    config = FakeConfig({"webui": {"show_card": {}}})
    mapping = {"edit": {"v": (FakeWidget("new"), "str")}}

    out = update_config(mapping, config, {"edit": {"v": "old", "other": 1}, "keep": {"x": 1}}, None)

    assert out == {"edit": {"v": "new", "other": 1}, "keep": {"x": 1}}


def test_textarea_round_trip():
    original = ["甲", "乙", "丙"]

    assert common_textarea_handle(textarea_data_change(original)) == original
    assert textarea_data_change(None) == ""
