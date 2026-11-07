"""stop_playback 工具：停止当前播放并清空待播队列。

观众说"不听了/别唱了/停一下/切歌"时使用。与点歌取消命令（关键词链路
choose_song_handle 的 stop_cmd → audio.stop_current_audio）同款停止语义，
叠加清空待合成队列——不然停了当前的，排队的歌还会接着来。
"""

from luna.agent.registry import Tool


class StopPlayback(Tool):
    name = "stop_playback"
    description = (
        "停止当前正在播放的音频（歌/播报）并清空待播队列。"
        "观众说不想听了、别唱了、停一下、切歌，或你需要先打断当前播放再说话时调用。"
    )
    parameters = {"type": "object", "properties": {}}

    def run(self, args: dict, ctx) -> str:
        audio = ctx.handle.audio
        if audio is None:
            return "音频模块未就绪"
        audio.stop_current_audio()
        ctx.handle.clear_queue("message_queue")
        return "已停止播放并清空待播队列"
