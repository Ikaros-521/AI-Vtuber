"""异常文案：toast 要给出下一步动作，不能是一屏堆栈（走查 audit-28）。"""

import json

import pytest

from webui_app.errors import explain


def test_missing_module_names_the_right_distribution():
    """ModuleNotFoundError.name 是模块名，照着它让用户 pip install 会装错包。"""
    try:
        import serial  # noqa: F401  本机 .venv 里确实没装，正好走这条分支
    except ModuleNotFoundError as e:
        text = explain(e)
        assert "pyserial" in text
        assert "pip install serial " not in text
    else:
        pytest.skip("本机装了 pyserial，测不到缺依赖分支")


def test_permission_and_missing_path_are_actionable():
    assert "占用" in explain(PermissionError(13, "Permission denied"))
    assert "data/x.json" in explain(FileNotFoundError(2, "No such file", "data/x.json"))


def test_json_error_points_at_the_line():
    with pytest.raises(json.JSONDecodeError) as caught:
        json.loads('{"a": ')
    text = explain(caught.value)
    assert "第 1 行" in text


def test_long_message_is_cut_and_never_carries_a_stack():
    try:
        raise RuntimeError("boom\n" + "x" * 400)
    except RuntimeError as e:
        text = explain(e)
        assert len(text) <= 160
        assert "\n" not in text


def test_unknown_exception_still_says_something():
    assert explain(ZeroDivisionError()) == "ZeroDivisionError"
