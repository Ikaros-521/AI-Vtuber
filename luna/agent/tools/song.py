"""play_song 工具：按歌名点播本地歌曲（随机点歌传空歌名）。

能力入口是 My_handle.play_song_by_name（经 ctx.handle 注入）；弹幕关键词
点歌链路（choose_song_handle）与此并行，互不影响。
"""

from luna.agent.registry import Tool


class PlaySong(Tool):
    name = "play_song"
    description = (
        "点播本地曲库里的歌：传入歌名（会模糊匹配最近似的歌），歌名留空则随机点一首。"
        "观众用自然语言要求放歌/点歌时调用；明确的点歌命令弹幕由规则链路直接处理，无需你操心。"
    )
    parameters = {
        "type": "object",
        "properties": {"song_name": {"type": "string", "description": "歌名；留空则随机点一首"}},
    }

    def run(self, args: dict, ctx) -> str:
        song_name = str(args.get("song_name") or "").strip()
        return ctx.handle.play_song_by_name(ctx.event.get("username", ""), song_name)
