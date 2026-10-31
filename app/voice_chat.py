"""按键/直接对话语音聊天链路：录音、ASR、唤醒/睡眠状态机。

拆分自 main.py 的"按键监听板块"（audio_listen / talk_handle /
do_listen_and_comment / on_key_press / key_listener / direct_run_talk），
原先靠闭包共享的可变状态收拢为 VoiceChat 实例属性。
"""

import os
import re
import threading
import time
import traceback
import wave

# 按键监听语音聊天板块
import keyboard
import numpy as np
import pyaudio
import speech_recognition as sr
from aip import AipSpeech

from utils.my_log import logger


class VoiceChat:
    """语音聊天服务：一个实例对应 main 进程的完整按键对话链路。"""

    # 按键冷却时间（秒）
    KEY_COOLDOWN = 0.5

    def __init__(self, state):
        self.state = state
        self.config = state.config
        self.common = state.common

        # 录音线程与停止事件
        self.do_listen_and_comment_thread = None
        self.stop_do_listen_and_comment_thread_event = None
        # ASR 模型懒加载缓存（加载一次共用，减少开销）
        self.faster_whisper_model = None
        self.sense_voice_model = None
        # 正在录音中 标志位
        self.is_recording = False
        # 聊天是否唤醒
        self.is_talk_awake = False

        # 触发键（start() 时从配置读取）
        self.trigger_key = None
        self.stop_trigger_key = None
        self._last_pressed = 0.0

        # 按键监听线程（talk 平台下主线程 join 它保持阻塞）
        self.key_listener_thread = None

    # ---------- 启动 ----------

    def start(self):
        """读取触发键配置，按需启动直接对话与按键监听线程。"""
        self.stop_do_listen_and_comment_thread_event = threading.Event()

        # 从配置文件中读取触发键的字符串配置
        self.trigger_key = self.config.get("talk", "trigger_key")
        self.stop_trigger_key = self.config.get("talk", "stop_trigger_key")

        # 是否启用了 按键监听
        if self.config.get("talk", "key_listener_enable"):
            logger.info(
                f"单击键盘 {self.trigger_key} 按键进行录音喵~ 由于其他任务还要启动，如果按键没有反应，请等待一段时间（如果使用本地ASR，请等待模型加载完成后使用）"
            )

        # 是否启用了直接运行对话，如果启用了，将在首次运行时直接进行语音识别，而不需手动点击开始按键。
        # 针对有些系统按键无法触发的情况下，配合连续对话和唤醒词使用
        if self.config.get("talk", "direct_run_talk"):
            logger.info(
                "直接运行对话模式，首次运行时将直接进行语音识别，而不需手动点击开始按键（如果使用本地ASR，请等待模型加载完成后使用）"
            )
            self.direct_run_talk()

        # 创建并启动按键监听线程，放着也是在聊天模式下，让程序一直阻塞用的
        self.key_listener_thread = threading.Thread(target=self.key_listener, name="key-listener")
        self.key_listener_thread.start()

    def join(self):
        """阻塞等待按键监听线程（talk 平台主线程靠它驻留）。"""
        if self.key_listener_thread is not None:
            self.key_listener_thread.join()

    # ---------- 录音 ----------

    def audio_listen(self, volume_threshold=800.0, silence_threshold=15):
        """阻塞采集麦克风音频直到静音，返回音频帧列表。

        THRESHOLD 设置音量阈值,默认值800.0,根据实际情况调整
        silence_threshold 设置沉默阈值，根据实际情况调整
        """
        audio = pyaudio.PyAudio()

        # 设置音频参数
        FORMAT = pyaudio.paInt16
        CHANNELS = self.config.get("talk", "CHANNELS")
        RATE = self.config.get("talk", "RATE")
        CHUNK = 1024

        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            input_device_index=int(self.config.get("talk", "device_index")),
        )

        frames = []  # 存储录制的音频帧

        is_speaking = False  # 是否在说话
        silent_count = 0  # 沉默计数
        speaking_flag = False  # 录入标志位 不重要

        logger.info("[即将开始录音……]")

        while True:
            # 播放中不录音
            if self.config.get("talk", "no_recording_during_playback"):
                # 存在待合成音频 或 已合成音频还未播放 或 正在播放 或 在数据处理中
                if self.state.my_handle.is_playback_busy() or self.state.my_handle.is_handle_empty() == 1:
                    time.sleep(float(self.config.get("talk", "no_recording_during_playback_sleep_interval")))
                    continue

            # 读取音频数据
            data = stream.read(CHUNK)
            audio_data = np.frombuffer(data, dtype=np.short)
            max_dB = np.max(audio_data)
            # logger.info(max_dB)
            if max_dB > volume_threshold:
                is_speaking = True
                silent_count = 0
            elif is_speaking is True:
                silent_count += 1

            if is_speaking is True:
                frames.append(data)
                if speaking_flag is False:
                    logger.info("[录入中……]")
                    speaking_flag = True

            if silent_count >= silence_threshold:
                break

        logger.info("[语音录入完成]")

        # 将音频保存为WAV文件
        """with wave.open(WAVE_OUTPUT_FILENAME, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(pyaudio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))"""
        return frames

    # ---------- 聊天逻辑 ----------

    def talk_handle(self, content: str):
        """处理聊天逻辑，传入 ASR 后的文本内容。"""

        def clear_queue_and_stop_audio_play(
            message_queue: bool = True, voice_tmp_path_queue: bool = True, stop_audio_play: bool = True
        ):
            """清空队列 或 停止播放音频"""
            if message_queue:
                ret = self.state.my_handle.clear_queue("message_queue")
                if ret:
                    logger.info("清空待合成消息队列成功！")
                else:
                    logger.error("清空待合成消息队列失败！")
            if voice_tmp_path_queue:
                ret = self.state.my_handle.clear_queue("voice_tmp_path_queue")
                if ret:
                    logger.info("清空待播放音频队列成功！")
                else:
                    logger.error("清空待播放音频队列失败！")
            if stop_audio_play:
                self.state.my_handle.stop_audio("pygame", True, True)

        try:
            # 检查并切换聊天唤醒状态
            check_resp = self._check_talk_awake(content)

            # 输出识别结果
            logger.info("识别结果：" + content)

            # 空内容过滤
            if content == "":
                return

            username = self.config.get("talk", "username")

            data = {"platform": "本地聊天", "username": username, "content": content}

            if check_resp["ret"] == 0:
                # 唤醒情况下
                if check_resp["is_talk_awake"]:
                    # 长期唤醒、且不是首次触发的情况下，后面的内容不会携带触发词，即使携带了也不应该进行替换操作
                    if self.config.get("talk", "wakeup_sleep", "mode") == "长期唤醒" and not check_resp["first"]:
                        pass
                    else:
                        # 替换触发词为空
                        content = content.replace(check_resp["trigger_word"], "").strip()

                    # 因为唤醒可能会有仅唤醒词的情况，所以可能出现首次唤醒，唤醒词被过滤，content为空清空，
                    # 导致不播放唤醒提示语，需要处理
                    if content == "" and not check_resp["first"]:
                        return

                    # 赋值给data
                    data["content"] = content

                    # 首次触发切换模式 播放唤醒文案
                    if check_resp["first"]:
                        # 随机获取文案 TODO: 如果此功能测试成功，所有的类似功能都将使用此函数简化代码
                        resp_json = self.common.get_random_str_in_list_and_format(
                            ori_list=self.config.get("talk", "wakeup_sleep", "wakeup_copywriting")
                        )
                        if resp_json["ret"] == 0:
                            data["content"] = resp_json["content"]
                            data["insert_index"] = -1
                            self.state.my_handle.reread_handle(data)
                    else:
                        # 如果启用了"打断对话"功能
                        if self.config.get("talk", "interrupt_talk", "enable"):
                            # 判断文本内容是否包含中断词
                            interrupt_word = self.common.find_substring_in_list(
                                data["content"], self.config.get("talk", "interrupt_talk", "keywords")
                            )
                            if interrupt_word:
                                logger.info(f"[聊天中断] 命中中断词：{interrupt_word}")
                                # 从配置中获取需要清除的数据类型
                                clean_type = self.config.get("talk", "interrupt_talk", "clean_type")
                                # 各类型数据是否清除
                                message_queue = "message_queue" in clean_type
                                voice_tmp_path_queue = "voice_tmp_path_queue" in clean_type
                                stop_audio_play = "stop_audio_play" in clean_type

                                clear_queue_and_stop_audio_play(message_queue, voice_tmp_path_queue, stop_audio_play)
                                return False

                        # 传递给my_handle进行进行后续一系列的处理
                        self.state.my_handle.process_data(data, "talk")

                        # 单次唤醒情况下，唤醒后关闭
                        if self.config.get("talk", "wakeup_sleep", "mode") == "单次唤醒":
                            self.is_talk_awake = False
                # 睡眠情况下
                else:
                    # 首次进入睡眠 播放睡眠文案
                    if check_resp["first"]:
                        resp_json = self.common.get_random_str_in_list_and_format(
                            ori_list=self.config.get("talk", "wakeup_sleep", "sleep_copywriting")
                        )
                        if resp_json["ret"] == 0:
                            data["content"] = resp_json["content"]
                            data["insert_index"] = -1
                            self.state.my_handle.reread_handle(data)
        except Exception:
            logger.error(traceback.format_exc())

    def _check_talk_awake(self, content: str) -> dict:
        """检查并切换聊天唤醒状态

        Args:
            content (str): 聊天内容

        Returns:
            dict:
                ret 是否需要触发
                is_talk_awake 当前唤醒状态
                first 是否是第一次触发 唤醒or睡眠，用于触发首次切换时的特殊提示语
        """
        # 判断是否启动了 唤醒词功能
        if self.config.get("talk", "wakeup_sleep", "enable"):
            if self.config.get("talk", "wakeup_sleep", "mode") == "长期唤醒":
                # 判断现在是否是唤醒状态
                if self.is_talk_awake is False:
                    # 判断文本内容是否包含唤醒词
                    trigger_word = self.common.find_substring_in_list(
                        content, self.config.get("talk", "wakeup_sleep", "wakeup_word")
                    )
                    if trigger_word:
                        self.is_talk_awake = True
                        logger.info("[聊天唤醒成功]")
                        return {
                            "ret": 0,
                            "is_talk_awake": self.is_talk_awake,
                            "first": True,
                            "trigger_word": trigger_word,
                        }
                    return {
                        "ret": -1,
                        "is_talk_awake": self.is_talk_awake,
                        "first": False,
                    }
                else:
                    # 判断文本内容是否包含睡眠词
                    trigger_word = self.common.find_substring_in_list(
                        content, self.config.get("talk", "wakeup_sleep", "sleep_word")
                    )
                    if trigger_word:
                        self.is_talk_awake = False
                        logger.info("[聊天睡眠成功]")
                        return {
                            "ret": 0,
                            "is_talk_awake": self.is_talk_awake,
                            "first": True,
                            "trigger_word": trigger_word,
                        }
                    return {
                        "ret": 0,
                        "is_talk_awake": self.is_talk_awake,
                        "first": False,
                    }
            elif self.config.get("talk", "wakeup_sleep", "mode") == "单次唤醒":
                # 无需判断当前是否是唤醒状态，因为默认都是状态清除
                # 判断文本内容是否包含唤醒词
                trigger_word = self.common.find_substring_in_list(
                    content, self.config.get("talk", "wakeup_sleep", "wakeup_word")
                )
                if trigger_word:
                    self.is_talk_awake = True
                    logger.info("[聊天唤醒成功]")
                    return {
                        "ret": 0,
                        "is_talk_awake": self.is_talk_awake,
                        # 单次唤醒下 没有首次唤醒提示
                        "first": False,
                        "trigger_word": trigger_word,
                    }
                return {
                    "ret": -1,
                    "is_talk_awake": self.is_talk_awake,
                    "first": False,
                }

        return {"ret": 0, "is_talk_awake": True, "trigger_word": "", "first": False}

    # ---------- 录音、识别&提交 ----------

    def do_listen_and_comment(self, status=True):
        try:
            self.is_recording = True

            # 刷新配置单例，读取 webui 侧写入的最新值
            self.config.reload()
            # 是否启用按键监听和直接对话，没启用的话就不用执行了
            if not self.config.get("talk", "key_listener_enable") and not self.config.get("talk", "direct_run_talk"):
                self.is_recording = False
                return

            # 针对faster_whisper情况，模型加载一次共用，减少开销
            if "faster_whisper" == self.config.get("talk", "type"):
                from faster_whisper import WhisperModel

                if self.faster_whisper_model is None:
                    logger.info("faster_whisper 模型加载中，请稍后...")
                    # Run on GPU with FP16
                    self.faster_whisper_model = WhisperModel(
                        model_size_or_path=self.config.get("talk", "faster_whisper", "model_size"),
                        device=self.config.get("talk", "faster_whisper", "device"),
                        compute_type=self.config.get("talk", "faster_whisper", "compute_type"),
                        download_root=self.config.get("talk", "faster_whisper", "download_root"),
                    )
                    logger.info("faster_whisper 模型加载完毕，可以开始说话了喵~")
            elif "sensevoice" == self.config.get("talk", "type"):
                from funasr import AutoModel

                logger.info("sensevoice 模型加载中，请稍后...")
                asr_model_path = self.config.get("talk", "sensevoice", "asr_model_path")
                vad_model_path = self.config.get("talk", "sensevoice", "vad_model_path")
                if self.sense_voice_model is None:
                    self.sense_voice_model = AutoModel(
                        model=asr_model_path,
                        vad_model=vad_model_path,
                        vad_kwargs={
                            "max_single_segment_time": int(
                                self.config.get("talk", "sensevoice", "vad_max_single_segment_time")
                            )
                        },
                        trust_remote_code=True,
                        device=self.config.get("talk", "sensevoice", "device"),
                        remote_code="./sensevoice/model.py",
                    )

                    logger.info("sensevoice 模型加载完毕，可以开始说话了喵~")

            while True:
                try:
                    # 检查是否收到停止事件
                    if self.stop_do_listen_and_comment_thread_event.is_set():
                        logger.info("停止录音~")
                        self.is_recording = False
                        break

                    self.config.reload()

                    keep_going = self._do_one_asr_round()
                    if keep_going is False:
                        # 内部要求终止录音线程（如 faster_whisper 识别为空）
                        return

                    self.is_recording = False

                    # 单轮模式：一轮录音识别后结束线程；连续模式继续
                    if not status:
                        return
                except Exception:
                    logger.error(traceback.format_exc())
                    self.is_recording = False
                    return
        except Exception:
            logger.error(traceback.format_exc())
            self.is_recording = False
            return

    def _do_one_asr_round(self):
        """单轮录音+ASR+提交；返回 False 时上层应结束本轮循环（与原实现一致）。"""
        config = self.config
        common = self.common

        # 根据接入的语音识别类型执行
        if config.get("talk", "type") in [
            "baidu",
            "faster_whisper",
            "sensevoice",
        ]:
            # 设置音频参数
            FORMAT = pyaudio.paInt16
            CHANNELS = config.get("talk", "CHANNELS")
            RATE = config.get("talk", "RATE")

            audio_out_path = config.get("play_audio", "out_path")

            if not os.path.isabs(audio_out_path):
                if not audio_out_path.startswith("./"):
                    audio_out_path = "./" + audio_out_path
            file_name = "asr_" + common.get_bj_time(4) + ".wav"
            WAVE_OUTPUT_FILENAME = common.get_new_audio_path(audio_out_path, file_name)
            # WAVE_OUTPUT_FILENAME = './out/asr_' + common.get_bj_time(4) + '.wav'

            frames = self.audio_listen(
                config.get("talk", "volume_threshold"),
                config.get("talk", "silence_threshold"),
            )

            # 将音频保存为WAV文件
            with wave.open(WAVE_OUTPUT_FILENAME, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(pyaudio.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b"".join(frames))

            if config.get("talk", "type") == "baidu":
                # 读取音频文件
                with open(WAVE_OUTPUT_FILENAME, "rb") as fp:
                    audio = fp.read()

                # 初始化 AipSpeech 对象
                baidu_client = AipSpeech(
                    config.get("talk", "baidu", "app_id"),
                    config.get("talk", "baidu", "api_key"),
                    config.get("talk", "baidu", "secret_key"),
                )

                # 识别音频文件
                res = baidu_client.asr(
                    audio,
                    "wav",
                    16000,
                    {
                        "dev_pid": 1536,
                    },
                )
                if res["err_no"] == 0:
                    content = res["result"][0]

                    self.talk_handle(content)
                else:
                    logger.error(f"百度接口报错：{res}")
            elif config.get("talk", "type") == "faster_whisper":
                logger.debug("faster_whisper模型加载中...")

                language = config.get("talk", "faster_whisper", "language")
                if language == "自动识别":
                    language = None

                segments, info = self.faster_whisper_model.transcribe(
                    WAVE_OUTPUT_FILENAME,
                    language=language,
                    beam_size=config.get("talk", "faster_whisper", "beam_size"),
                )

                logger.debug("识别语言为：'%s'，概率：%f" % (info.language, info.language_probability))

                content = ""
                for segment in segments:
                    logger.info("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
                    content += segment.text + "。"

                if content == "":
                    # 恢复录音标志位，并终止本轮录音线程
                    self.is_recording = False
                    return False

                self.talk_handle(content)
            elif config.get("talk", "type") == "sensevoice":
                res = self.sense_voice_model.generate(
                    input=WAVE_OUTPUT_FILENAME,
                    cache={},
                    language=config.get("talk", "sensevoice", "language"),
                    text_norm=config.get("talk", "sensevoice", "text_norm"),
                    batch_size_s=int(config.get("talk", "sensevoice", "batch_size_s")),
                    batch_size=int(config.get("talk", "sensevoice", "batch_size")),
                )

                def remove_angle_brackets_content(input_string: str):
                    # 使用正则表达式来匹配并删除 <> 之间的内容
                    return re.sub(r"<.*?>", "", input_string)

                content = remove_angle_brackets_content(res[0]["text"])

                self.talk_handle(content)
        elif "google" == config.get("talk", "type"):
            # 创建Recognizer对象
            r = sr.Recognizer()

            try:
                # 打开麦克风进行录音
                with sr.Microphone() as source:
                    logger.info("录音中...")
                    # 从麦克风获取音频数据
                    audio = r.listen(source)
                    logger.info("成功录制")

                    # 进行谷歌实时语音识别 en-US zh-CN ja-JP
                    content = r.recognize_google(
                        audio,
                        language=config.get("talk", "google", "tgt_lang"),
                    )

                    self.talk_handle(content)
            except sr.UnknownValueError:
                logger.warning("无法识别输入的语音")
            except sr.RequestError as e:
                logger.error("请求出错：" + str(e))

    # ---------- 按键 ----------

    def _spawn_recording_thread(self, continuous: bool):
        """启动一轮录音线程（continuous=True 为连续对话模式）。"""
        self.stop_do_listen_and_comment_thread_event.clear()
        self.do_listen_and_comment_thread = threading.Thread(
            target=self.do_listen_and_comment,
            args=(continuous,),
            name="do-listen-and-comment",
        )
        self.do_listen_and_comment_thread.start()

    def on_key_press(self, event):
        """keyboard 库的按键回调。"""
        # 是否启用按键监听，不启用的话就不用执行了
        if not self.config.get("talk", "key_listener_enable"):
            return

        # 按键CD
        current_time = time.time()
        if current_time - self._last_pressed < self.KEY_COOLDOWN:
            return
        self._last_pressed = current_time

        """
        触发按键部分的判断
        """
        trigger_key_lower = None
        stop_trigger_key_lower = None

        # trigger_key是字母, 整个小写
        if self.trigger_key.isalpha():
            trigger_key_lower = self.trigger_key.lower()

        # stop_trigger_key是字母, 整个小写
        if self.stop_trigger_key.isalpha():
            stop_trigger_key_lower = self.stop_trigger_key.lower()

        if trigger_key_lower:
            if event.name == self.trigger_key or event.name == trigger_key_lower:
                logger.info(f"检测到单击键盘 {event.name}，即将开始录音~")
            elif event.name == self.stop_trigger_key or event.name == stop_trigger_key_lower:
                logger.info(f"检测到单击键盘 {event.name}，即将停止录音~")
                self.stop_do_listen_and_comment_thread_event.set()
                return
            else:
                return
        else:
            if event.name == self.trigger_key:
                logger.info(f"检测到单击键盘 {event.name}，即将开始录音~")
            elif event.name == self.stop_trigger_key:
                logger.info(f"检测到单击键盘 {event.name}，即将停止录音~")
                self.stop_do_listen_and_comment_thread_event.set()
                return
            else:
                return

        if not self.is_recording:
            # 是否启用连续对话模式
            self._spawn_recording_thread(bool(self.config.get("talk", "continuous_talk")))
        else:
            logger.warning("正在录音中...请勿重复点击录音捏！")

    def key_listener(self):
        """按键监听线程主体：注册回调后阻塞等待按键。"""
        # 注册按键按下事件的回调函数
        keyboard.on_press(self.on_key_press)

        try:
            # 进入监听状态，等待按键按下
            keyboard.wait()
        except KeyboardInterrupt:
            os._exit(0)

    def direct_run_talk(self):
        """直接运行语音对话：无需按键，启动即开始录音。"""
        if not self.is_recording:
            self._spawn_recording_thread(bool(self.config.get("talk", "continuous_talk")))
