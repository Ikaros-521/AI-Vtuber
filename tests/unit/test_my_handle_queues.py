"""队列委托、时间间隔与去重：My_handle 里不碰网络的胶水逻辑。"""

import pytest

from fakes import FakeAudio


def test_clear_queue_delegates_to_audio(configure):
    handle = configure({"filter": {}})
    handle.audio = FakeAudio()

    assert handle.clear_queue("message_queue") is True
    assert handle.audio.calls == [("clear_queue", ("message_queue",))]


def test_clear_queue_returns_false_on_error(configure):
    handle = configure({"filter": {}})
    handle.audio = FakeAudio(raises=True)

    assert handle.clear_queue("voice_tmp_path_queue") is False
    assert handle.stop_audio() is False


def test_queue_predicates_delegate(configure):
    handle = configure({"filter": {}})
    handle.audio = FakeAudio()

    assert handle.is_playback_busy() is False
    assert handle.is_queue_less_or_greater_than("message_queue", less=5) is True
    assert handle.get_audio_info() == {"message_queue": 0}
    assert [c[0] for c in handle.audio.calls] == [
        "is_playback_busy",
        "is_queue_less_or_greater_than",
        "get_audio_info",
    ]


def test_is_handle_empty_reflects_shared_flag(configure):
    handle = configure({"filter": {}})

    handle.is_handleing = 1
    assert handle.is_handle_empty() == 1
    handle.is_handleing = 0
    assert handle.is_handle_empty() == 0


def test_get_room_id_reads_config(configure):
    handle = configure({"room_display_id": 12345})
    assert handle.get_room_id() == 12345


def test_get_interval_maps_each_timer_and_defaults(configure):
    handle = configure(
        {
            "filter": {
                "comment_forget_duration": 1.0,
                "gift_forget_duration": 5.0,
                "entrance_forget_duration": 5.0,
                "follow_forget_duration": 3.0,
                "talk_forget_duration": 0.1,
                "schedule_forget_duration": 0.2,
                "idle_time_task_forget_duration": 0.3,
            }
        }
    )

    assert handle.get_interval("comment") == 1.0
    assert handle.get_interval("gift") == 5.0
    assert handle.get_interval("idle_time_task") == 0.3
    assert handle.get_interval("没有这个定时器") == 0.1


def test_dedup_flags_repeated_comment(configure):
    handle = configure({"filter": {"limited_time_deduplication": {"enable": True}}})
    first = {"username": "甲", "content": "你好"}

    assert handle.is_data_repeat_in_limited_time("comment", first) is False
    assert handle.is_data_repeat_in_limited_time("comment", dict(first)) is True
    # 命中重复时不再入队，队列里只有第一条
    assert handle.live_data["comment"] == [first]


def test_dedup_treats_gift_by_username_only(configure):
    handle = configure({"filter": {"limited_time_deduplication": {"enable": True}}})

    assert handle.is_data_repeat_in_limited_time("gift", {"username": "甲", "giftname": "小花花"}) is False
    assert handle.is_data_repeat_in_limited_time("gift", {"username": "甲", "giftname": "大火箭"}) is True


def test_dedup_disabled_never_blocks_and_records_nothing(configure):
    handle = configure({"filter": {"limited_time_deduplication": {"enable": False}}})

    assert handle.is_data_repeat_in_limited_time("comment", {"username": "甲", "content": "你好"}) is False
    assert handle.live_data["comment"] == []


def test_dedup_ignores_empty_arguments(configure):
    handle = configure({"filter": {"limited_time_deduplication": {"enable": True}}})

    assert handle.is_data_repeat_in_limited_time(None, None) is False
    assert handle.is_data_repeat_in_limited_time("", {"username": "甲"}) is False


def test_abnormal_alarm_ignores_errors_while_disabled(configure):
    """关掉异常报警时不能攒计数——否则用户哪天打开后，
    第一个偶发错误就会把长期直播攒下的数直接顶过 auto_restart_error_num。"""
    handle = configure({"abnormal_alarm": {"llm": {"enable": False}}})
    before = handle.abnormal_alarm_data["llm"]["error_count"]

    assert handle.abnormal_alarm_handle("llm") is True
    assert handle.abnormal_alarm_data["llm"]["error_count"] == before


def test_abnormal_alarm_counts_only_once_enabled(configure):
    handle = configure({"abnormal_alarm": {"llm": {"enable": True, "type": "none"}}})
    before = handle.abnormal_alarm_data["llm"]["error_count"]

    assert handle.abnormal_alarm_handle("llm") is True
    assert handle.abnormal_alarm_data["llm"]["error_count"] == before + 1


@pytest.mark.parametrize("category", ["platform", "llm", "tts", "svc", "visual_body", "other"])
def test_abnormal_alarm_data_covers_every_category(handle, category):
    assert category in handle.abnormal_alarm_data
