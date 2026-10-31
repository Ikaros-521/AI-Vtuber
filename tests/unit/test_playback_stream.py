"""弹幕流与文案流各占一个播放通道（回归：以前两个名字指向同一个 pygame.mixer）。

`pygame.mixer.music` 是全局唯一的一条流，所以 `mixer_normal` 和 `mixer_copywriting`
都赋成 `pygame.mixer` 时，「暂停文案」会连正在播的弹幕回复一起暂停、`get_busy()`
互相牵制。这里用 SDL_AUDIODRIVER=dummy 真跑一遍 channel 行为来锁住这个回归。
"""

import json
import math
import os
import struct
import time
import wave

import pytest

os.environ["SDL_AUDIODRIVER"] = "dummy"

pygame = pytest.importorskip("pygame")

from utils.audio import Audio  # noqa: E402
from utils.audio_handle.playback_stream import PlaybackStream  # noqa: E402


def _tone(path, seconds, rate=8000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(2000 * math.sin(i / 8))) for i in range(int(rate * seconds))))
    return str(path)


@pytest.fixture(autouse=True)
def restore_audio_mixers():
    normal, copywriting = Audio.mixer_normal, Audio.mixer_copywriting
    yield
    Audio.mixer_normal, Audio.mixer_copywriting = normal, copywriting


@pytest.fixture(scope="module")
def mixer_ready():
    pygame.mixer.init()
    if pygame.mixer.get_init() is None:
        pytest.skip("pygame mixer 起不来")
    if pygame.mixer.get_num_channels() < 2:
        pytest.skip("pygame channel 不够分")
    yield
    pygame.mixer.quit()


@pytest.fixture
def streams(mixer_ready, tmp_path):
    made = []

    def _make(index, seconds=3.0):
        stream = PlaybackStream(index)
        stream.init()
        stream.load(_tone(tmp_path / ("tone_%d.wav" % index), seconds))
        made.append(stream)
        return stream

    yield _make

    for stream in made:
        stream.stop()


def test_the_two_streams_are_different_objects(tmp_path, monkeypatch):
    """回归点：Audio.mixer_normal is Audio.mixer_copywriting 时，暂停一路等于暂停全部。"""
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"play_audio": {"out_path": "out", "player": "pygame", "enable": True}}),
        encoding="utf-8",
    )

    class _NoThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

    # 只验证构造时的接线，别真把播放线程拉起来
    monkeypatch.setattr("utils.audio.threading.Thread", _NoThread)
    Audio(str(path), type=1)

    assert Audio.mixer_normal is not Audio.mixer_copywriting
    assert Audio.mixer_normal is not pygame.mixer
    assert Audio.mixer_copywriting is not pygame.mixer
    assert Audio.mixer_normal._channel_index == 0
    assert Audio.mixer_copywriting._channel_index == 1


def test_pausing_copywriting_leaves_the_reply_stream_playing(streams):
    reply, copywriting = streams(0), streams(1)
    reply.music.play()
    copywriting.music.play()
    time.sleep(0.2)

    copywriting.music.pause()

    # 共用一条 music 流时这一句必然为假：pause() 停的是那条唯一的流
    assert reply.music.get_busy() is True
    # 暂停了就没在出声，但这条流还占着这个位置，播完才会松开
    assert copywriting.music.get_busy() is True

    copywriting.music.unpause()
    time.sleep(0.2)
    assert copywriting.music.get_busy() is True
    assert reply.music.get_busy() is True


def test_stopping_one_stream_leaves_the_other(streams):
    reply, copywriting = streams(0), streams(1)
    reply.music.play()
    copywriting.music.play()
    time.sleep(0.2)

    copywriting.music.stop()

    assert copywriting.music.get_busy() is False
    assert reply.music.get_busy() is True


def test_quit_only_releases_its_own_channel(streams):
    """mixer.quit() 会关掉整个音频设备，另一路跟着哑掉，所以 quit 只能停自己。"""
    reply, copywriting = streams(0), streams(1)
    reply.music.play()
    copywriting.music.play()
    time.sleep(0.2)

    copywriting.quit()

    assert copywriting.music.get_busy() is False
    assert reply.music.get_busy() is True


def test_busy_clears_when_the_audio_finishes(streams):
    stream = streams(0, seconds=0.3)
    stream.music.play()
    assert stream.music.get_busy() is True

    deadline = time.time() + 5
    while stream.music.get_busy() and time.time() < deadline:
        time.sleep(0.05)

    assert stream.music.get_busy() is False


def test_fadeout_stops_the_stream_within_its_own_window(streams):
    stream = streams(0)
    stream.music.play()
    time.sleep(0.2)

    stream.music.fadeout(200)

    deadline = time.time() + 3
    while stream.music.get_busy() and time.time() < deadline:
        time.sleep(0.05)
    assert stream.music.get_busy() is False


def test_formats_that_sdl_mixer_reads_directly(mixer_ready, tmp_path):
    """wav/mp3/ogg/flac 都能直接播——换 channel 不能把原来 music 流能放的格式弄丢。"""
    try:
        from pydub import AudioSegment
    except Exception:  # pragma: no cover - 依赖缺失时跳过
        pytest.skip("pydub 不可用")

    wav_path = _tone(tmp_path / "src.wav", 0.3)
    try:
        segment = AudioSegment.from_file(wav_path)
        converted = []
        for fmt in ("mp3", "ogg", "flac"):
            out = tmp_path / ("src." + fmt)
            segment.export(str(out), format=fmt)
            converted.append(str(out))
    except Exception:  # pragma: no cover - 本机没有 ffmpeg 时跳过
        pytest.skip("本机 ffmpeg 转码不可用")

    for index, path in enumerate(converted):
        stream = PlaybackStream(index + 2)
        stream.init()
        stream.load(path)
        stream.music.play()
        assert stream.music.get_busy() is True, path
        stream.stop()


def test_missing_file_raises_so_the_player_logs_the_friendly_error(mixer_ready, tmp_path):
    """旧实现里 mixer.music.load 找不到文件抛 pygame.error，调用方按这个捕；
    换成 Sound 之后抛的是 FileNotFoundError，得让它照样冒出来才有提示。"""
    stream = PlaybackStream(4)
    stream.init()
    stream.load(str(tmp_path / "没有这个文件.wav"))

    with pytest.raises(FileNotFoundError):
        stream.music.play()


def test_play_without_load_does_nothing(mixer_ready):
    stream = PlaybackStream(5)
    stream.init()

    assert stream.music.play() is None
    assert stream.music.get_busy() is False
