"""utils/alarm.py 的行为测试。

重点盯住「连续错误窗口」：报警阈值本来就是「连续出错」的意思，
用累计值会把几小时前的历史错误算到当前这一次偶发错误头上，直播中途直接重启。
"""

import os

import pytest

from fakes import FakeAlarmCommon, FakeConfig
from luna.core import alarm


class Clock:
    def __init__(self, now=1_000_000.0):
        self.now = now

    def time(self):
        return self.now


class Synth:
    def __init__(self):
        self.messages = []

    def __call__(self, message):
        self.messages.append(message)


def make_config(**overrides):
    alarm_cfg = {
        "enable": True,
        "type": "local_audio",
        "start_alarm_error_num": 5,
        "auto_restart_error_num": 10,
        "local_audio_path": "data/异常报警/llm",
    }
    alarm_cfg.update(overrides)
    return FakeConfig(
        {
            "abnormal_alarm": {"llm": alarm_cfg},
            "webui": {"ip": "0.0.0.0", "port": "8846"},
            "audio_synthesis_type": "edge_tts",
            "edge_tts": {"speaker": "xiaoxiao"},
            "filter": {"username_convert_digits_to_chinese": True},
        }
    )


@pytest.fixture
def clock(monkeypatch):
    """alarm 里 time 是模块名，换掉它只影响这个模块。"""
    fake = Clock()
    monkeypatch.setattr(alarm, "time", fake)
    return fake


@pytest.fixture
def ctx(clock):
    common = FakeAlarmCommon(["data/异常报警/llm/a.mp3"])
    return make_config(), common, Synth(), alarm.new_state()


def test_disabled_alarm_records_nothing(ctx):
    config, common, synth, state = ctx
    config.config["abnormal_alarm"]["llm"]["enable"] = False

    assert alarm.report_error(state, "llm", config, common, synth) is True
    assert state["llm"]["error_count"] == 0
    assert synth.messages == []


def test_error_counts_but_stays_silent_when_alarm_type_is_not_audio(ctx):
    config, common, synth, state = ctx
    config.config["abnormal_alarm"]["llm"]["type"] = "none"

    for _ in range(20):
        assert alarm.report_error(state, "llm", config, common, synth) is True

    assert state["llm"]["error_count"] == 20
    assert synth.messages == []
    assert common.requests == []


def test_alarm_starts_at_the_configured_threshold(ctx):
    config, common, synth, state = ctx

    for _ in range(4):
        assert alarm.report_error(state, "llm", config, common, synth) is True
    assert synth.messages == []

    assert alarm.report_error(state, "llm", config, common, synth) is True
    assert len(synth.messages) == 1
    assert common.requests == []


def test_alarm_message_carries_the_chosen_audio_file(ctx):
    config, common, synth, state = ctx

    for _ in range(5):
        alarm.report_error(state, "llm", config, common, synth)

    message = synth.messages[0]
    assert message["type"] == "abnormal_alarm"
    assert message["username"] == "系统"
    assert message["tts_type"] == "edge_tts"
    assert message["data"] == {"speaker": "xiaoxiao"}
    assert message["config"] == config.get("filter")
    assert message["content"] == os.path.join("data/异常报警/llm", "a.mp3")


def test_restart_is_requested_at_the_auto_restart_threshold(ctx):
    config, common, synth, state = ctx

    for _ in range(9):
        alarm.report_error(state, "llm", config, common, synth)
    assert common.requests == []

    alarm.report_error(state, "llm", config, common, synth)
    url, method, data = common.requests[0]
    assert url == "http://127.0.0.1:8846/sys_cmd"
    assert method == "POST"
    assert data["type"] == "restart"


def test_lone_error_long_after_the_last_one_does_not_inherit_history(ctx, clock):
    """核心回归：越过重启阈值之后的第一个偶发错误不应该再把机器重启掉。"""
    config, common, synth, state = ctx

    for _ in range(10):
        alarm.report_error(state, "llm", config, common, synth)
    assert len(common.requests) == 1

    common.requests.clear()
    synth.messages.clear()
    clock.now += alarm.ERROR_COUNT_WINDOW + 1

    assert alarm.report_error(state, "llm", config, common, synth) is True
    assert state["llm"]["error_count"] == 1
    assert common.requests == []
    assert synth.messages == []


def test_errors_just_inside_the_window_still_accumulate(ctx, clock):
    config, common, synth, state = ctx

    for _ in range(4):
        alarm.report_error(state, "llm", config, common, synth)

    clock.now += alarm.ERROR_COUNT_WINDOW - 1
    assert alarm.report_error(state, "llm", config, common, synth) is True
    assert state["llm"]["error_count"] == 5
    assert len(synth.messages) == 1


def test_empty_audio_dir_warns_instead_of_crashing(ctx):
    config, common, synth, state = ctx
    common.path_list = []

    for _ in range(6):
        assert alarm.report_error(state, "llm", config, common, synth) is True

    assert synth.messages == []


def test_internal_failure_is_reported_as_false(ctx):
    class Boom(FakeAlarmCommon):
        def get_all_file_paths(self, folder_path):
            raise OSError("disk on fire")

    config, _, synth, state = ctx
    common = Boom()

    for _ in range(4):
        assert alarm.report_error(state, "llm", config, common, synth) is True
    assert alarm.report_error(state, "llm", config, common, synth) is False


def test_new_state_covers_every_alarm_category():
    state = alarm.new_state()

    assert set(state) == set(alarm.CATEGORIES)
    for record in state.values():
        assert record == {"error_count": 0, "last_error_time": 0.0}
