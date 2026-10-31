"""助播（副播）问答回复要带上原消息的队列位置。

insert_index 决定回复插回待合成队列的位置。两处守卫写成了
「检查刚新建出来的那个字典」，而新字典里当然没有这个键，于是条件永远不成立，
助播回复永远排到队尾。
"""

import pytest

from fakes import FakeAudio


class AnchorAudio(FakeAudio):
    """问答音频库命中：文件名列表给一个确定的 a / a.mp3。"""

    def get_dir_audios_filename(self, path, type=1):
        return ["a.mp3" if type == 0 else "a"]

    def search_files(self, path, name):
        return [name]


def base_config(local_qa):
    return {
        "visual_body": "none",
        "audio_synthesis_type": "edge_tts",
        "edge_tts": {"speaker": "xiaoxiao"},
        "filter": {},
        "assistant_anchor": {
            "enable": True,
            "username": "副播",
            "audio_synthesis_type": "edge_tts",
            "type": ["comment"],
            "local_qa": local_qa,
        },
    }


def comment_message(**over):
    data = {"type": "comment", "content": "今天天气怎么样", "username": "观众甲"}
    data.update(over)
    return data


def last_synthesis(audio):
    calls = [c for c in audio.calls if c[0] == "audio_synthesis"]
    return calls[-1][1][0]


@pytest.fixture
def text_anchor(configure):
    handle = configure(
        base_config(
            {
                "text": {"enable": True, "format": "text", "file_path": "data/qa", "similarity": 0.9},
            }
        )
    )
    handle.audio = AnchorAudio()
    handle.find_answer = lambda content, path, similarity: f"晴天:{content}"
    handle.write_to_comment_log = lambda *args: None
    return handle


def test_text_answer_keeps_the_queue_position(text_anchor):
    text_anchor.audio_synthesis_handle(comment_message(insert_index=0))

    message = last_synthesis(text_anchor.audio)
    assert message["type"] == "assistant_anchor_text"
    assert message["insert_index"] == 0


def test_text_answer_without_a_queue_position_stays_silent_on_the_key(text_anchor):
    text_anchor.audio_synthesis_handle(comment_message())

    assert "insert_index" not in last_synthesis(text_anchor.audio)


@pytest.fixture
def audio_anchor(configure):
    handle = configure(
        base_config(
            {
                "audio": {"enable": True, "type": "相似度匹配", "file_path": "data/qa", "similarity": 0},
            }
        )
    )
    handle.audio = AnchorAudio()
    # 命中问答库这件事本身不是被测点，直接让它必定命中
    handle.common.find_best_match = lambda text, lst, similarity=0.5: lst[0] if lst else None
    return handle


def test_audio_answer_keeps_the_queue_position(audio_anchor):
    audio_anchor.audio_synthesis_handle(comment_message(insert_index=2))

    message = last_synthesis(audio_anchor.audio)
    assert message["type"] == "assistant_anchor_audio"
    assert message["insert_index"] == 2
