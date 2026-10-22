import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fakes import FakeConfig  # noqa: E402
from utils.common import Common  # noqa: E402
from utils.my_handle import My_handle  # noqa: E402

# 这些是类属性（My_handle 用类当全局状态袋），测试期间会被改写，必须逐个还原
PATCHED = ("config", "common", "audio", "my_translate", "live_data", "task_data",
           "abnormal_alarm_data", "is_handleing",
           "thanks_gift_copy", "thanks_entrance_copy", "thanks_follow_copy")


def pytest_addoption(parser):
    parser.addoption(
        "--update-ui-baseline",
        action="store_true",
        default=False,
        help="重新生成 tests/unit/webui_render_baseline.json（确认差异是有意的之后再用）",
    )


@pytest.fixture
def handle():
    """返回一个跳过 __init__ 的 My_handle 实例，并把类属性还原干净。"""
    saved = {name: getattr(My_handle, name, None) for name in PATCHED}

    My_handle.common = Common()
    My_handle.live_data = {"comment": [], "gift": [], "entrance": []}
    My_handle.is_handleing = 0

    # __init__ 会拉起 Audio/DB/定时器，单元测试不需要，直接绕过
    instance = My_handle.__new__(My_handle)
    # 绕过 __init__ 之后，缓冲那一套要自己补上，否则 process_data 一进来就 AttributeError
    instance.data_lock = threading.Lock()
    instance.handle_lock = threading.Lock()
    instance.timers = {}
    try:
        yield instance
    finally:
        for timer in instance.timers.values():
            timer.cancel()
        for name, value in saved.items():
            setattr(My_handle, name, value)


@pytest.fixture
def configure(handle):
    """把一份配置字典装到 My_handle.config 上，返回 handle 实例。"""

    def _configure(data):
        My_handle.config = FakeConfig(data)
        return handle

    return _configure
