"""Audio 的优先级队列：决定哪条内容先被合成/播放。

用 type=2 构造 Audio——那条分支在起线程之前就 return 了，所以能离线实例化。
"""

import json

import pytest

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
