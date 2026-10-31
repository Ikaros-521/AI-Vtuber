"""合成消息的统一形状。

这个字典以前在 30 多个地方各写一份，字段名或取值写错不会报错，只会表现成
「某类消息播出来少个信息」或「用了错的 TTS 配置」。
"""

from fakes import FakeConfig
from utils.message import build, build_playback


CONFIG = FakeConfig(
    {
        "audio_synthesis_type": "edge_tts",
        "edge_tts": {"speaker": "xiaoxiao"},
        "gpt_sovits": {"api": "http://127.0.0.1:9880"},
        "assistant_anchor": {"audio_synthesis_type": "gpt_sovits"},
        "filter": {"badwords": {"enable": False}},
    }
)


def test_message_has_the_agreed_shape_and_order():
    message = build(CONFIG, "comment", "观众甲", "晚上好")

    assert list(message) == ["type", "tts_type", "data", "config", "username", "content"]
    assert message["tts_type"] == "edge_tts"
    assert message["data"] == {"speaker": "xiaoxiao"}
    assert message["config"] == {"badwords": {"enable": False}}


def test_type_specific_fields_are_carried_through():
    message = build(CONFIG, "gift", "观众甲", "谢谢", gift_info={"num": 3}, insert_index=0)

    assert message["gift_info"] == {"num": 3}
    assert message["insert_index"] == 0


def test_overriding_the_tts_also_moves_the_data_section():
    # 助播用自己那段 TTS 配置，data 必须跟着取那一段，否则会拿主 TTS 的参数去请求
    message = build(
        CONFIG, "assistant_anchor_text", "副播", "回答", tts_type=CONFIG.get("assistant_anchor", "audio_synthesis_type")
    )

    assert message["tts_type"] == "gpt_sovits"
    assert message["data"] == {"api": "http://127.0.0.1:9880"}


def test_missing_tts_section_yields_none_instead_of_raising():
    message = build(FakeConfig({"audio_synthesis_type": "edge-tts"}), "reread", "甲", "复读")

    assert message["tts_type"] == "edge-tts"
    assert message["data"] is None
    assert message["config"] is None


def test_playback_entry_skips_tts_and_carries_the_queue_position():
    entry = build_playback({"type": "song", "content": "out/a.mp3", "insert_index": 1}, "out/a.mp3")

    assert entry == {
        "type": "song",
        "tts_type": "none",
        "voice_path": "out/a.mp3",
        "content": "out/a.mp3",
        "insert_index": 1,
    }


def test_playback_entry_omits_the_queue_position_when_the_source_has_none():
    entry = build_playback({"type": "local_qa_audio", "content": "答"}, "data/qa/a.mp3")

    assert "insert_index" not in entry
    assert entry["voice_path"] == "data/qa/a.mp3"
