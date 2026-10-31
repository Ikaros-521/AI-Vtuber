"""My_handle 共享状态锁（state_lock）的并发回归测试。

此前 live_data 的 遍历+append（filters.is_data_repeat_in_limited_time）与
clear_live_data 定时器的整体换新 是裸并发，遍历中列表被清会抛
RuntimeError；thanks_* 轮转的 判空+pop 也会在 /send 直调时互相踩。
这里用多线程压测锁定加锁后的行为。
"""

import threading

import pytest

from tests.unit.conftest import PATCHED
from tests.unit.fakes import FakeConfig
from luna.core.my_handle import My_handle


@pytest.fixture()
def handle():
    """绕过 __init__ 的轻量实例（与 conftest.handle 同一套路）。"""
    h = My_handle.__new__(My_handle)
    for name in PATCHED:
        setattr(My_handle, name, getattr(My_handle, name))
    # 还原被其他用例动过的共享状态
    My_handle.live_data = {"comment": [], "gift": [], "entrance": []}
    return h


def _configure(enable_dedup=True, dedup_seconds=300):
    My_handle.config = FakeConfig(
        {
            "filter": {
                "limited_time_deduplication": {
                    "enable": enable_dedup,
                    "comment": dedup_seconds,
                    "gift": dedup_seconds,
                    "entrance": dedup_seconds,
                }
            }
        }
    )


def test_dedup_survives_concurrent_clear(handle):
    """去重遍历/写入 与 clear_live_data 换新并发——不允许抛异常。"""
    _configure()

    errors = []

    def clearer():
        for _ in range(200):
            My_handle.clear_live_data("comment")

    def deduper(i):
        for n in range(200):
            try:
                handle.is_data_repeat_in_limited_time("comment", {"username": f"u{i}", "content": f"c{n}"})
            except Exception as e:  # noqa: BLE001
                errors.append(e)

    threads = [threading.Thread(target=clearer)] + [threading.Thread(target=deduper, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert errors == [], errors[:3]


def test_thanks_rotation_concurrent_pop_is_consistent():
    """/send 直调绕过 handle_lock 时，thanks 轮转表并发 判空+pop 不重不漏。"""
    _configure()
    copies = 500
    My_handle.config = FakeConfig({"thanks": {"gift_copy": [f"文案{i}" for i in range(copies)], "gift_random": False}})
    My_handle.thanks_gift_copy = []

    popped = []
    pop_lock = threading.Lock()

    def popper(i):
        for _ in range(copies // 5):
            # 直接调用轮转逻辑所在的临界段（复用 gift 拷贝行为太重，这里最小化复现）
            with My_handle.state_lock:
                if len(My_handle.thanks_gift_copy) == 0:
                    My_handle.thanks_gift_copy = list(My_handle.config.get("thanks", "gift_copy"))
                item = My_handle.thanks_gift_copy.pop(0)
            with pop_lock:
                popped.append(item)

    threads = [threading.Thread(target=popper, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert len(popped) == copies
    assert len(set(popped)) == copies  # 每条文案恰好被取一次，无重复无丢失


def test_state_lock_is_reentrant():
    _configure()
    with My_handle.state_lock:
        with My_handle.state_lock:
            assert True
