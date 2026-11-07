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


def test_pause_resume_volume_tools():
    """v5 播放控制升级：暂停/继续双路径入口 + 音量百分比换算。"""
    from luna.agent.tools.playback import PausePlayback, ResumePlayback, SetVolume

    calls = []

    class AudioStub:
        def pause_current_audio(self):
            calls.append("pause")

        def resume_current_audio(self):
            calls.append("resume")

        def set_playback_volume(self, level):
            calls.append(("volume", level))
            return True

    handle = SimpleNamespace(audio=AudioStub())
    assert PausePlayback().run({}, make_ctx(handle)) == "已暂停播放"
    assert ResumePlayback().run({}, make_ctx(handle)) == "已继续播放"
    assert SetVolume().run({"level": 30}, make_ctx(handle)) == "音量已调到 30%"
    assert calls == ["pause", "resume", ("volume", 0.3)]


def test_set_volume_clamps_and_reports_unsupported():
    from luna.agent.tools.playback import SetVolume

    seen = []

    class AudioStub:
        def set_playback_volume(self, level):
            seen.append(level)
            return True

    class UnsupportedAudio:
        def set_playback_volume(self, level):
            return False

    assert "不支持" in SetVolume().run({"level": 50}, make_ctx(SimpleNamespace(audio=UnsupportedAudio())))
    assert SetVolume().run({"level": 250}, make_ctx(SimpleNamespace(audio=AudioStub()))) == "音量已调到 100%"
    assert seen[-1] == 1.0  # 250 被钳到 100%
    assert "整数" in SetVolume().run({"level": "abc"}, make_ctx(SimpleNamespace(audio=AudioStub())))


def test_observe_screen_tool_passes_question():
    from luna.agent.tools.vision import ObserveScreen

    seen = []

    class Handle:
        def observe_screen(self, question):
            seen.append(question)
            return f"画面：{question}"

    assert ObserveScreen().run({"question": "在玩什么游戏"}, make_ctx(Handle())) == "画面：在玩什么游戏"
    assert seen == ["在玩什么游戏"]
    # 留空走默认描述提示词
    ObserveScreen().run({}, make_ctx(Handle()))
    assert seen[-1] == "请描述一下画面里的内容"


def test_observe_screen_branches(handle, configure, monkeypatch):
    """My_handle.observe_screen：未启用 / 窗口截图 / 摄像头源 / 模型无返回。"""
    configure(
        {
            "image_recognition": {
                "enable": True,
                "img_save_path": "out",
                "screenshot_window_title": "游戏窗口",
                "model": "gemini",
                "cam_screenshot_enable": False,
            }
        }
    )
    captured = []
    monkeypatch.setattr(
        handle,
        "common",
        SimpleNamespace(
            capture_window_by_title=lambda path, title: captured.append(("window", title)) or "shot.png",
            capture_image=lambda path, idx: captured.append(("cam", idx)) or "cam.png",
        ),
    )
    monkeypatch.setattr(handle, "get_vision_model", lambda ct, cfg: None)
    handle.image_recognition_model = SimpleNamespace(get_resp_with_img=lambda prompt, img: f"看到 {img}")

    assert handle.observe_screen("看看") == "看到 shot.png"
    assert captured == [("window", "游戏窗口")]

    # 摄像头源
    configure(
        {
            "image_recognition": {
                "enable": True,
                "img_save_path": "out",
                "model": "gemini",
                "cam_screenshot_enable": True,
                "cam_index": 2,
            }
        }
    )
    assert handle.observe_screen("看看") == "看到 cam.png"
    assert captured[-1] == ("cam", 2)

    # 未启用
    configure({"image_recognition": {"enable": False}})
    assert "未启用" in handle.observe_screen("看看")

    # 截图失败
    configure(
        {
            "image_recognition": {
                "enable": True,
                "img_save_path": "out",
                "screenshot_window_title": "",
                "model": "gemini",
                "cam_screenshot_enable": False,
            }
        }
    )
    monkeypatch.setattr(
        handle,
        "common",
        SimpleNamespace(capture_window_by_title=lambda p, t: None, capture_image=lambda p, i: None),
    )
    assert "截图失败" in handle.observe_screen("看看")
