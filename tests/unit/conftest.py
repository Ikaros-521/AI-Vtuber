import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fakes import FakeConfig  # noqa: E402
from luna.common.helpers import Common  # noqa: E402
from luna.core.my_handle import My_handle  # noqa: E402


@pytest.fixture
def handle():
    """返回一个跳过 __init__ 的 My_handle 实例（状态为干净的实例属性）。"""
    # __init__ 会拉起 Audio/DB/定时器，单元测试不需要，直接绕过；
    # 实例状态由 _init_state() 就位（2026-10-31 实例属性化后不再有类级污染，
    # 也无需 save/restore）
    instance = My_handle.__new__(My_handle)
    instance._init_state()
    instance.data_lock = threading.Lock()
    instance.handle_lock = threading.Lock()
    instance.timers = {}
    instance.common = Common()
    try:
        yield instance
    finally:
        for timer in instance.timers.values():
            timer.cancel()


@pytest.fixture
def configure(handle):
    """把一份配置字典装到 handle.config 上，返回 handle 实例。"""

    def _configure(data):
        handle.config = FakeConfig(data)
        return handle

    return _configure
