"""播放控制工具：停止 / 暂停 / 继续 / 音量。

stop_playback 与点歌取消命令（关键词链路 choose_song_handle 的 stop_cmd →
audio.stop_current_audio）同款停止语义，叠加清空待合成队列——不然停了当前的，
排队的歌还会接着来。pause/resume/volume 是 v5 给 Audio 补的升级能力：
audio_player 路径走播放器 HTTP 接口（pause/resume），pygame mixer 路径走
pygame.mixer.music 原生 pause/unpause/set_volume（此前没暴露）。
"""

from luna.agent.registry import Tool


def _audio(ctx):
    audio = ctx.handle.audio
    return audio


class StopPlayback(Tool):
    name = "stop_playback"
    description = (
        "停止当前正在播放的音频（歌/播报）并清空待播队列。"
        "观众说不想听了、别唱了、停一下、切歌，或你需要先打断当前播放再说话时调用。"
    )
    parameters = {"type": "object", "properties": {}}

    def run(self, args: dict, ctx) -> str:
        audio = _audio(ctx)
        if audio is None:
            return "音频模块未就绪"
        audio.stop_current_audio()
        ctx.handle.clear_queue("message_queue")
        return "已停止播放并清空待播队列"


class PausePlayback(Tool):
    name = "pause_playback"
    description = (
        "暂停当前正在播放的音频（歌/播报），可用 resume_playback 继续。"
        "观众说暂停一下、等会儿再放，或你需要临时停住当前内容时调用；想彻底不播用 stop_playback。"
    )
    parameters = {"type": "object", "properties": {}}

    def run(self, args: dict, ctx) -> str:
        audio = _audio(ctx)
        if audio is None:
            return "音频模块未就绪"
        audio.pause_current_audio()
        return "已暂停播放"


class ResumePlayback(Tool):
    name = "resume_playback"
    description = "继续播放之前暂停的音频。观众说继续、接着放时调用。"
    parameters = {"type": "object", "properties": {}}

    def run(self, args: dict, ctx) -> str:
        audio = _audio(ctx)
        if audio is None:
            return "音频模块未就绪"
        audio.resume_current_audio()
        return "已继续播放"


class SetVolume(Tool):
    name = "set_volume"
    description = (
        "调节播放音量（百分比 0-100）。观众说声音太大/小声点/音量调到多少时调用。"
        "注意：当前使用 audio_player 外置播放器时本工具不可用。"
    )
    parameters = {
        "type": "object",
        "properties": {"level": {"type": "integer", "description": "音量百分比，0-100"}},
        "required": ["level"],
    }

    def run(self, args: dict, ctx) -> str:
        audio = _audio(ctx)
        if audio is None:
            return "音频模块未就绪"
        try:
            level = int(args.get("level"))
        except (TypeError, ValueError):
            return "set_volume 失败：level 需要是 0-100 的整数"
        level = max(0, min(100, level))
        if not audio.set_playback_volume(level / 100.0):
            return "当前使用 audio_player 外置播放器，暂不支持音量调节"
        return f"音量已调到 {level}%"
