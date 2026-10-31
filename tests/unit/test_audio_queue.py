"""Audio 的优先级队列：决定哪条内容先被合成/播放。

用 type=2 构造 Audio——那条分支在起线程之前就 return 了，所以能离线实例化。
"""

import json

import pytest

from utils import my_global
from utils.audio import Audio

CONFIG = {
    "play_audio": {"out_path": "out", "player": "pygame", "enable": True},
    "filter": {
        "priority_mapping": {"gift": 10, "comment": 5, "reread": 3, "schedule": 10},
        "message_queue_max_len": 5,
        "voice_tmp_path_queue_max_len": 3,
        "voice_tmp_path_queue_min_start_play": 0,
    },
}


@pytest.fixture
def audio(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(CONFIG), encoding="utf-8")

    # 队列是类属性，跨实例共享，必须逐个清干净
    Audio.message_queue = []
    Audio.voice_tmp_path_queue = []
    Audio.voice_tmp_path_queue_not_empty_flag = False

    instance = Audio(str(path), type=2)

    yield instance

    Audio.message_queue = []
    Audio.voice_tmp_path_queue = []
    Audio.voice_tmp_path_queue_not_empty_flag = False


def msg(audio_type, content):
    return {"type": audio_type, "content": content}


def test_unknown_type_goes_to_the_back(audio):
    audio.data_priority_insert("等待合成消息", msg("comment", "低优先级"))
    audio.data_priority_insert("等待合成消息", msg("没定义的类型", "插到最后"))

    assert [m["content"] for m in Audio.message_queue] == ["低优先级", "插到最后"]


def test_higher_priority_inserts_before_lower(audio):
    audio.data_priority_insert("等待合成消息", msg("reread", "复读"))
    audio.data_priority_insert("等待合成消息", msg("gift", "礼物"))

    assert [m["content"] for m in Audio.message_queue] == ["礼物", "复读"]


def test_equal_priority_keeps_arrival_order(audio):
    audio.data_priority_insert("等待合成消息", msg("gift", "先到的礼物"))
    audio.data_priority_insert("等待合成消息", msg("schedule", "同级的定时任务"))

    assert [m["content"] for m in Audio.message_queue] == ["先到的礼物", "同级的定时任务"]


def test_full_queue_discards_the_new_coming(audio):
    for i in range(5):
        audio.data_priority_insert("等待合成消息", msg("reread", f"占位{i}"))

    # 全是低优先级，新来的高优先级应插到最前而不是被丢
    result = audio.data_priority_insert("等待合成消息", msg("gift", "插队"))
    assert result["code"] == 200
    assert Audio.message_queue[0]["content"] == "插队"

    # 队列已满且新数据优先级最低，落到队尾索引 == 上限 → 丢弃
    dropped = audio.data_priority_insert("等待合成消息", msg("reread", "挤不进去"))
    assert dropped["code"] == 1
    assert "挤不进去" not in [m["content"] for m in Audio.message_queue]


def test_voice_queue_uses_a_separate_limit(audio):
    for i in range(3):
        audio.data_priority_insert("待播放音频路径", {"type": "reread", "voice_path": f"{i}.wav"})

    dropped = audio.data_priority_insert("待播放音频路径", {"type": "reread", "voice_path": "x.wav"})

    assert dropped["code"] == 1
    assert len(Audio.voice_tmp_path_queue) == 3


def test_clear_queue_empties_only_the_selected_queue(audio):
    audio.data_priority_insert("等待合成消息", msg("comment", "你好"))
    Audio.voice_tmp_path_queue.append({"type": "comment", "voice_path": "a.wav"})

    assert audio.clear_queue("message_queue") is True
    assert Audio.message_queue == []
    assert len(Audio.voice_tmp_path_queue) == 1, "清空消息队列不该动音频队列"

    assert audio.clear_queue("voice_tmp_path_queue") is True
    assert Audio.voice_tmp_path_queue == []


def test_clear_queue_on_unknown_type_returns_none(audio):
    # 没有 else 分支：认不出的队列名既不报错也不清任何东西
    assert audio.clear_queue("不存在的队列") is None
    assert len(Audio.message_queue) == 0


def test_get_audio_info_reports_both_queues(audio):
    audio.data_priority_insert("等待合成消息", msg("comment", "你好"))
    Audio.voice_tmp_path_queue.append({"type": "comment", "voice_path": "a.wav"})

    info = audio.get_audio_info()

    assert info == {"wait_play_audio_num": 1, "wait_synthesis_msg_num": 1}


def test_greater_of_zero_is_a_real_threshold(audio):
    """greater=0 表示「队列非空就返回 True」。以前写成 if greater，
    0 被当成没传，这条判断永远不会成立。"""
    assert audio.is_queue_less_or_greater_than("message_queue", greater=0) is False

    Audio.message_queue.append(msg("comment", "你好"))

    assert audio.is_queue_less_or_greater_than("message_queue", greater=0) is True


def test_less_and_greater_are_compared_against_the_selected_queue(audio):
    Audio.message_queue.extend([msg("comment", "一"), msg("comment", "二")])

    assert audio.is_queue_less_or_greater_than("message_queue", less=3) is True
    assert audio.is_queue_less_or_greater_than("message_queue", less=2) is False
    # 两个队列各算各的：音频队列这时是空的
    assert audio.is_queue_less_or_greater_than("voice_tmp_path_queue", less=3) is True
    assert audio.is_queue_less_or_greater_than("voice_tmp_path_queue", greater=1) is False
    assert audio.is_queue_less_or_greater_than("没这个队列", less=3) is False


def test_no_threshold_means_no_trigger(audio):
    Audio.message_queue.append(msg("comment", "你好"))

    assert audio.is_queue_less_or_greater_than("message_queue") is False


class _StubMusic:
    def __init__(self, busy):
        self._busy = busy

    def get_busy(self):
        return self._busy


class _StubMixer:
    def __init__(self, busy):
        self.music = _StubMusic(busy)


@pytest.fixture(autouse=True)
def restore_mixers():
    normal, copywriting = Audio.mixer_normal, Audio.mixer_copywriting
    yield
    Audio.mixer_normal, Audio.mixer_copywriting = normal, copywriting


def _audio_with(tmp_path, player):
    cfg = json.loads(json.dumps(CONFIG))
    cfg["play_audio"]["player"] = player
    path = tmp_path / ("cfg_" + player + ".json")
    path.write_text(json.dumps(cfg), encoding="utf-8")
    Audio.message_queue = []
    Audio.voice_tmp_path_queue = []
    return Audio(str(path), type=2)


def test_any_queued_audio_counts_as_busy(tmp_path):
    audio = _audio_with(tmp_path, "audio_player")
    Audio.message_queue.append({"type": "comment", "content": "你好"})

    assert audio.is_playback_busy() is True


def test_pygame_asks_the_mixers_directly(tmp_path):
    audio = _audio_with(tmp_path, "pygame")
    Audio.mixer_normal, Audio.mixer_copywriting = _StubMixer(False), _StubMixer(False)
    assert audio.is_playback_busy() is False

    Audio.mixer_copywriting = _StubMixer(True)
    assert audio.is_playback_busy() is True


def test_non_pygame_player_can_reach_idle(tmp_path, monkeypatch):
    """回归点：旧实现是个 0-15 位标志，第 4、8 位只有 pygame 才加，
    所以换成 audio_player 时永远凑不满 15，main.py 的 != 15 恒判"忙"，
    语音输入彻底录不了。"""
    audio = _audio_with(tmp_path, "audio_player_v2")
    monkeypatch.setattr(my_global, "wait_play_audio_num", 0)

    assert audio.is_playback_busy() is False


def test_external_player_backlog_counts_as_busy(tmp_path, monkeypatch):
    audio = _audio_with(tmp_path, "audio_player")
    monkeypatch.setattr(my_global, "wait_play_audio_num", 2)

    assert audio.is_playback_busy() is True
