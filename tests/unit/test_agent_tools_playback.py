"""动作类工具（v5 P1）：play_song / generate_image 与 My_handle 干净入口的分支。

工具层用 FakeHandle 验证 OBSERVATION 透传；handle 方法分支用 handle fixture
+ 桩验证未启用/匹配失败/成功三条路径（点歌链路核心逻辑提炼后的行为锁定）。
"""

from types import SimpleNamespace

from fakes import FakeConfig
from luna.agent.context import AgentContext, Budget
from luna.agent.tools.image import GenerateImage
from luna.agent.tools.song import PlaySong
from luna.agent.trace import Trace


def make_ctx(handle, username="alice"):
    return AgentContext(
        event={"type": "comment", "username": username, "content": "", "platform": "bilibili"},
        source="comment",
        handle=handle,
        budget=Budget(),
        trace=Trace(event_type="comment", username=username, source="comment"),
    )


# ---------- 工具层：透传 handle 返回值 ----------


class FakeHandle:
    def __init__(self, result):
        self.config = FakeConfig({})
        self._result = result

    def play_song_by_name(self, username, song_name):
        return self._result

    def generate_image_by_prompt(self, username, prompt):
        return self._result


def test_play_song_tool_passes_song_name():
    handle = FakeHandle("已播放：晴天.mp3")
    observation = PlaySong().run({"song_name": "晴天"}, make_ctx(handle))
    assert observation == "已播放：晴天.mp3"


def test_generate_image_tool_requires_prompt():
    handle = FakeHandle("不该被调用")
    assert "prompt 为空" in GenerateImage().run({"prompt": "  "}, make_ctx(handle))
    assert GenerateImage().run({"prompt": "一只猫"}, make_ctx(handle)) == "不该被调用"


# ---------- handle 方法分支 ----------

ENABLED_SONG_CONFIG = {
    "choose_song": {
        "enable": True,
        "song_path": "song",
        "similarity": 0.3,
        "match_fail_copy": "没找到{content}",
    },
}


def test_play_song_by_name_branches(handle, configure, monkeypatch):
    configure(ENABLED_SONG_CONFIG)
    synthesized, logged = [], []
    monkeypatch.setattr(handle, "audio_synthesis_handle", lambda message: synthesized.append(message))
    monkeypatch.setattr(handle, "webui_show_chat_log_callback", lambda *a: logged.append(a))
    handle.audio = SimpleNamespace(
        get_dir_audios_filename=lambda path, flag: ["晴天", "七里香"],
        search_files=lambda path, name, flag: ["晴天.mp3"],
    )
    handle.common = SimpleNamespace(
        merge_consecutive_asterisks=lambda s: s,
        find_best_match=lambda name, lists, similarity: "晴天",
        random_search_a_audio_file=lambda path: None,
    )

    result = handle.play_song_by_name("alice", "晴天")
    assert result == "已播放：晴天.mp3"
    assert synthesized[0]["type"] == "song" and synthesized[0]["content"].endswith("晴天.mp3")

    # 匹配失败：回退配置文案
    monkeypatch.setattr(handle.common, "find_best_match", lambda name, lists, similarity: None)
    assert handle.play_song_by_name("alice", "不存在") == "没找到不存在"

    # 随机点歌：曲库为空
    assert "曲库为空" in handle.play_song_by_name("alice", "")


def test_play_song_by_name_disabled(handle, configure):
    configure({"choose_song": {"enable": False}})
    assert "未启用" in handle.play_song_by_name("alice", "晴天")


def test_generate_image_by_prompt_branches(handle, configure, monkeypatch):
    configure({"sd": {"enable": True}})
    submitted = []
    handle.sd = SimpleNamespace(process_input=lambda prompt: submitted.append(prompt))
    monkeypatch.setattr(handle, "prohibitions_handle", lambda text: None if "违禁" in text else text)

    assert "已提交画图" in handle.generate_image_by_prompt("alice", "一只猫")
    assert submitted == ["一只猫"]

    # 违禁提示词被拦截
    assert "违禁" in handle.generate_image_by_prompt("alice", "违禁内容")

    # 功能未启用
    configure({"sd": {"enable": False}})
    assert "未启用" in handle.generate_image_by_prompt("alice", "一只猫")


def test_stop_playback_tool_stops_and_clears():
    """观众喊停：停当前播放 + 清待播队列（真机回归点）。"""
    from luna.agent.tools.playback import StopPlayback

    calls = []

    class AudioStub:
        def stop_current_audio(self):
            calls.append("stop_current")

    handle = SimpleNamespace(audio=AudioStub(), clear_queue=lambda type: calls.append(("clear", type)))
    observation = StopPlayback().run({}, make_ctx(handle))
    assert observation == "已停止播放并清空待播队列"
    assert calls == ["stop_current", ("clear", "message_queue")]


def test_stop_playback_tool_reports_missing_audio():
    from luna.agent.tools.playback import StopPlayback

    handle = SimpleNamespace(audio=None, clear_queue=lambda type: None)
    assert "未就绪" in StopPlayback().run({}, make_ctx(handle))
