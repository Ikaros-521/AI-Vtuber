"""一条独立的 pygame 播放通道。

以前 `Audio.mixer_normal` 和 `Audio.mixer_copywriting` 都被赋成 `pygame.mixer` 模块
本身，而 `pygame.mixer.music` 是**全局唯一**的一条流：所谓「弹幕音频」和「文案音频」
两条通道其实共用一个播放器。后果是暂停文案会把正在播的弹幕回复一起暂停、
`music.get_busy()` 的忙等会互相牵制、两路音量/淡出无法分别控制。

这里给两条流各分一个 `pygame.mixer.Channel`。接口名保持成 `.music.load/play/...`，
和 `pygame.mixer` 原来那套一样，调用点不用改。
"""

from luna.infra.my_log import logger


class MusicFacade:
    """让调用方继续写 stream.music.load(...) / stream.music.play()。"""

    def __init__(self, stream):
        self._stream = stream

    def load(self, path):
        self._stream.load(path)

    def play(self):
        self._stream.play()

    def stop(self):
        self._stream.stop()

    def pause(self):
        self._stream.pause()

    def unpause(self):
        self._stream.unpause()

    def get_busy(self):
        return self._stream.get_busy()

    def fadeout(self, ms):
        self._stream.fadeout(ms)


class PlaybackStream:
    """占用一个固定 channel 的播放流。

    Args:
        channel_index (int): 这条流独占的 pygame channel 编号
    """

    def __init__(self, channel_index):
        self._channel_index = channel_index
        self._channel = None
        self._path = None
        self.music = MusicFacade(self)

    def init(self):
        import pygame

        if not pygame.mixer.get_init():
            pygame.mixer.init()
        if pygame.mixer.get_init() and self._channel is None:
            self._channel = pygame.mixer.Channel(self._channel_index)

    def quit(self):
        # 只停自己这条通道。不能调 pygame.mixer.quit()——那是把整个音频设备关掉，
        # 另一条流会跟着哑掉（以前两个对象是同一个模块时就是这个行为，属于 bug）
        self.stop()
        self._path = None

    def load(self, path):
        self._path = path

    def play(self):
        if self._path is None:
            logger.error("播放前没有 load 音频路径")
            return

        self.init()
        if self._channel is None:
            logger.error("pygame mixer 未就绪，无法播放 %s" % self._path)
            return

        self._channel.play(self._load_sound())

    def stop(self):
        if self._channel is not None:
            self._channel.stop()

    def pause(self):
        if self._channel is not None:
            self._channel.pause()

    def unpause(self):
        if self._channel is not None:
            self._channel.unpause()

    def get_busy(self):
        if self._channel is None:
            return False
        return self._channel.get_busy()

    def fadeout(self, ms):
        if self._channel is None:
            return
        sound = self._channel.get_sound()
        if sound is None:
            self.stop()
            return
        sound.fadeout(ms)

    def _load_sound(self):
        import pygame

        try:
            return pygame.mixer.Sound(self._path)
        except FileNotFoundError:
            raise
        except Exception:
            # m4a/aac 这类 SDL_mixer 的 Sound 支持面不确定，退一步用 pydub 转成 wav
            # 再读（旧代码走 music 流时这些格式是能放的，不能因为换 channel 就倒退）
            logger.debug("Sound 直接读取失败，转 wav 重试：%s" % self._path)
            return pygame.mixer.Sound(self._to_wav())

    def _to_wav(self) -> str:
        import os

        from pydub import AudioSegment

        wav_path = os.path.splitext(self._path)[0] + "_stream_fallback.wav"
        AudioSegment.from_file(self._path).export(wav_path, format="wav")
        return wav_path
