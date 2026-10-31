"""周期性触发定时器与取间隔。

这个定时器是自己给自己挂下一发的（每秒一次），以前重新挂放在函数最后一行、
外面又没有 try：函数体里任何一处抛异常，链条就断在这儿，之后整场直播的
念弹幕、本地问答、礼物/入场/关注答谢都不会再触发，而且只体现在 stderr 里。
"""

import pytest

from luna.core import my_handle as my_handle_module


class FakeTimer:
    def __init__(self, interval, func):
        self.interval = interval
        self.func = func

    def start(self):
        FAKE_TIMERS.append(self)


FAKE_TIMERS = []


@pytest.fixture
def timers(monkeypatch):
    del FAKE_TIMERS[:]
    monkeypatch.setattr(my_handle_module.threading, "Timer", FakeTimer)
    return FAKE_TIMERS


def test_body_exception_still_rearms_the_timer(configure, timers):
    # 开了念弹幕周期触发但没配 periodic_time_min，函数体会在 int(None) 上炸
    handle = configure({"read_comment": {"periodic_trigger": {"enable": True}}})
    handle.task_data = {"read_comment": {"time": 0, "data": []}}

    handle.periodic_trigger_data_handle()

    assert len(timers) == 1, "异常之后必须照样重新挂定时器，否则这条链就断了"
    assert timers[0].interval == 1
    assert timers[0].func.func == handle.periodic_trigger_data_handle


def test_rearms_once_per_pass(configure, timers):
    handle = configure({"read_comment": {"periodic_trigger": {"enable": False}}})

    handle.periodic_trigger_data_handle()
    handle.periodic_trigger_data_handle()

    assert len(timers) == 2


def test_interval_honours_the_image_recognition_schedule_config(configure):
    handle = configure({"filter": {"image_recognition_schedule_forget_duration": 2.5}})

    assert handle.get_interval("image_recognition_schedule") == 2.5


def test_missing_interval_config_falls_back_to_the_default(configure):
    handle = configure({"filter": {"comment_forget_duration": None}})

    assert handle.get_interval("comment") == 0.1
    assert handle.get_interval("没见过的计时器") == 0.1
