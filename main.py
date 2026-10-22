import os
import threading
import schedule
import random
import asyncio
import traceback
import copy
import re

from functools import partial


# 按键监听语音聊天板块
import keyboard
import pyaudio
import wave
import numpy as np
import speech_recognition as sr
from aip import AipSpeech
import signal
import time

import http.server
import socketserver

from utils.my_log import logger
from utils.common import Common
from utils.config import Config
from utils.my_handle import My_handle
from utils.platforms import start_platform_listen
import utils.my_global as my_global

r"""
	___ _                       
	|_ _| | ____ _ _ __ ___  ___ 
	 | || |/ / _` | '__/ _ \/ __|
	 | ||   < (_| | | | (_) \__ 	|___|_|\_\__,_|_|  \___/|___/

"""

config = None
common = None
my_handle = None


# 配置文件路径
config_path = "config.json"


# web服务线程
async def web_server_thread(web_server_port):
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", web_server_port), Handler) as httpd:
        logger.info(f"Web运行在端口：{web_server_port}")
        logger.info(
            f"可以直接访问Live2D页， http://127.0.0.1:{web_server_port}/Live2D/"
        )
        httpd.serve_forever()


r"""
                       _oo0oo_
                      o8888888o
                      88" . "88
                      (| -_- |)
                      0\  =  /0
                    ___/`---'\___
                  .' \|     |// '.
                 / \|||  :  |||//                 / _||||| -:- |||||-                |   | \\  - /// |   |
               | \_|  ''\---/''  |_/ |
               \  .-\__  '-'  ___/-. /
             ___'. .'  /--.--\  `. .'___
          ."" '<  `.___\_<|>_/___.' >' "".
         | | :  `- \`.;`\ _ /`;.`/ - ` : | |
         \  \ `_.   \_ __\ /__ _/   .-` /  /
     =====`-.____`.___ \_____/___.-`___.-'=====
                       `=---='


     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

         佛祖保佑       永不宕机     永无BUG
"""


# 点火起飞
def start_server():
    global \
        config, \
        common, \
        my_handle, \
        config_path
    global do_listen_and_comment_thread, stop_do_listen_and_comment_thread_event
    global faster_whisper_model, sense_voice_model, is_recording, is_talk_awake

    # 按键监听相关
    do_listen_and_comment_thread = None
    stop_do_listen_and_comment_thread_event = threading.Event()
    # 冷却时间 0.5 秒
    cooldown = 0.5
    last_pressed = 0
    # 正在录音中 标志位
    is_recording = False
    # 聊天是否唤醒
    is_talk_awake = False

    # 待播放音频数量（在使用 音频播放器 或者 metahuman-stream等不通过AI Vtuber播放音频的对接项目时，使用此变量记录是是否还有音频没有播放完）
    my_global.wait_play_audio_num = 0
    my_global.wait_synthesis_msg_num = 0

    # 获取 httpx 库的日志记录器
    # httpx_logger = logging.getLogger("httpx")
    # 设置 httpx 日志记录器的级别为 WARNING
    # httpx_logger.setLevel(logging.WARNING)

    # 最新的直播间数据
    my_global.last_liveroom_data = {
        "OnlineUserCount": 0,
        "TotalUserCount": 0,
        "TotalUserCountStr": "0",
        "OnlineUserCountStr": "0",
        "MsgId": 0,
        "User": None,
        "Content": "当前直播间人数 0，累计直播间人数 0",
        "RoomId": 0,
    }
    # 最新入场的用户名列表
    my_global.last_username_list = [""]

    my_handle = My_handle(config_path)
    if my_handle is None:
        logger.error("程序初始化失败！")
        os._exit(0)

    # Live2D线程
    try:
        if config.get("live2d", "enable"):
            web_server_port = int(config.get("live2d", "port"))
            threading.Thread(
                target=lambda: asyncio.run(web_server_thread(web_server_port))
            ).start()
    except Exception as e:
        logger.error(traceback.format_exc())
        os._exit(0)

    if platform != "wxlive":
        r"""

                  /@@@@@@@@          @@@@@@@@@@@@@@@].      =@@@@@@@       
                 =@@@@@@@@@^         @@@@@@@@@@@@@@@@@@`    =@@@@@@@       
                ,@@@@@@@@@@@`        @@@@@@@@@@@@@@@@@@@^   =@@@@@@@       
               .@@@@@@\@@@@@@.       @@@@@@@^   .\@@@@@@\   =@@@@@@@       
               /@@@@@/ \@@@@@\       @@@@@@@^    =@@@@@@@   =@@@@@@@       
              =@@@@@@. .@@@@@@^      @@@@@@@\]]]@@@@@@@@^   =@@@@@@@       
             ,@@@@@@^   =@@@@@@`     @@@@@@@@@@@@@@@@@@/    =@@@@@@@       
            .@@@@@@@@@@@@@@@@@@@.    @@@@@@@@@@@@@@@@/`     =@@@@@@@       
            /@@@@@@@@@@@@@@@@@@@\    @@@@@@@^               =@@@@@@@       
           =@@@@@@@@@@@@@@@@@@@@@^   @@@@@@@^               =@@@@@@@       
          ,@@@@@@@.       ,@@@@@@@`  @@@@@@@^               =@@@@@@@       
          @@@@@@@^         =@@@@@@@. @@@@@@@^               =@@@@@@@   

        """
        
        # HTTP API线程
        def http_api_thread():
            import uvicorn
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware
            from utils.models import (
                SendMessage,
                LLMMessage,
                CallbackMessage,
                CommonResult,
            )

            # 定义FastAPI应用
            app = FastAPI()

            # 允许跨域
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

            # 定义POST请求路径和处理函数
            @app.post("/send")
            async def send(msg: SendMessage):
                global my_handle, config

                try:
                    tmp_json = msg.dict()
                    logger.info(f"内部HTTP API send接口收到数据：{tmp_json}")
                    data_json = tmp_json["data"]
                    if "type" not in data_json:
                        data_json["type"] = tmp_json["type"]

                    if data_json["type"] in ["reread", "reread_top_priority"]:
                        my_handle.reread_handle(data_json, type=data_json["type"])
                    elif data_json["type"] == "comment":
                        my_handle.process_data(data_json, "comment")
                    elif data_json["type"] == "tuning":
                        my_handle.tuning_handle(data_json)
                    elif data_json["type"] == "gift":
                        my_handle.gift_handle(data_json)
                    elif data_json["type"] == "entrance":
                        my_handle.entrance_handle(data_json)

                    return CommonResult(code=200, message="成功")
                except Exception as e:
                    logger.error(f"发送数据失败！{e}")
                    return CommonResult(code=-1, message=f"发送数据失败！{e}")

            @app.post("/llm")
            async def llm(msg: LLMMessage):
                global my_handle, config

                try:
                    data_json = msg.dict()
                    logger.info(f"API收到数据：{data_json}")

                    resp_content = my_handle.llm_handle(
                        data_json["type"], data_json, webui_show=False
                    )

                    return CommonResult(
                        code=200, message="成功", data={"content": resp_content}
                    )
                except Exception as e:
                    logger.error(f"调用LLM失败！{e}")
                    return CommonResult(code=-1, message=f"调用LLM失败！{e}")

            from starlette.requests import Request

            @app.post('/tts')
            async def tts(request: Request):
                try:
                    data_json = await request.json()
                    logger.info(f"API收到数据：{data_json}")

                    resp_json = await My_handle.audio.tts_handle(data_json)

                    return {"code": 200, "message": "成功", "data": resp_json}
                except Exception as e:
                    logger.error(traceback.format_exc())
                    return CommonResult(code=-1, message=f"失败！{e}")
                
            @app.post("/callback")
            async def callback(msg: CallbackMessage):
                global my_handle, config

                try:
                    data_json = msg.dict()

                    # 特殊回调特殊处理
                    if data_json["type"] == "audio_playback_completed":
                        my_global.wait_play_audio_num = int(data_json["data"]["wait_play_audio_num"])
                        my_global.wait_synthesis_msg_num = int(data_json["data"]["wait_synthesis_msg_num"])
                        logger.info(f"内部HTTP API callback接口 音频播放完成回调，待播放音频数量：{my_global.wait_play_audio_num}，待合成消息数量：{my_global.wait_synthesis_msg_num}")
                    else:
                        logger.info(f"内部HTTP API callback接口收到数据：{data_json}")

                    # 音频播放完成
                    if data_json["type"] in ["audio_playback_completed"]:
                        my_global.wait_play_audio_num = int(data_json["data"]["wait_play_audio_num"])

                        # 如果等待播放的音频数量大于10
                        if data_json["data"]["wait_play_audio_num"] > int(
                            config.get(
                                "idle_time_task", "wait_play_audio_num_threshold"
                            )
                        ):
                            logger.info(
                                f'等待播放的音频数量大于限定值，闲时任务的闲时计时由 {my_global.global_idle_time} -> {int(config.get("idle_time_task", "idle_time_reduce_to"))}秒'
                            )
                            # 闲时任务的闲时计时 清零
                            my_global.global_idle_time = int(
                                config.get("idle_time_task", "idle_time_reduce_to")
                            )

                    return CommonResult(code=200, message="callback处理成功！")
                except Exception as e:
                    logger.error(f"callback处理失败！{e}")
                    return CommonResult(code=-1, message=f"callback处理失败！{e}")

            # 获取系统信息接口
            @app.get("/get_sys_info")
            async def get_sys_info():
                global my_handle, config

                try:
                    data = {
                        "audio": my_handle.get_audio_info(),
                        "metahuman-stream": {
                            "wait_play_audio_num": my_global.wait_play_audio_num,
                            "wait_synthesis_msg_num": my_global.wait_synthesis_msg_num,
                        }
                    }

                    return CommonResult(code=200, data=data, message="get_sys_info处理成功！")
                except Exception as e:
                    logger.error(f"get_sys_info处理失败！{e}")
                    return CommonResult(code=-1, message=f"get_sys_info处理失败！{e}")

            

            logger.info("HTTP API线程已启动！")

            # 将本地目录中的静态文件（如 CSS、JavaScript、图片等）暴露给 web 服务器，以便用户可以通过特定的 URL 访问这些文件。
            if config.get("webui", "local_dir_to_endpoint", "enable"):
                for tmp in config.get("webui", "local_dir_to_endpoint", "config"):
                    from fastapi.staticfiles import StaticFiles
                    app.mount(tmp['url_path'], StaticFiles(directory=tmp['local_dir']), name=tmp['local_dir'])
                    
            uvicorn.run(app, host="0.0.0.0", port=config.get("api_port"))
            #uvicorn.run(app, host="0.0.0.0", port=config.get("api_port"), ssl_certfile="F:\\FunASR_WS\\cert.pem", ssl_keyfile="F:\\FunASR_WS\\key.pem")

        # HTTP API线程并启动
        inside_http_api_thread = threading.Thread(target=http_api_thread)
        inside_http_api_thread.start()

    

    """
    按键监听板块
    """

    # THRESHOLD 设置音量阈值,默认值800.0,根据实际情况调整  silence_threshold 设置沉默阈值，根据实际情况调整
    def audio_listen(volume_threshold=800.0, silence_threshold=15):
        audio = pyaudio.PyAudio()

        # 设置音频参数
        FORMAT = pyaudio.paInt16
        CHANNELS = config.get("talk", "CHANNELS")
        RATE = config.get("talk", "RATE")
        CHUNK = 1024

        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            input_device_index=int(config.get("talk", "device_index")),
        )

        frames = []  # 存储录制的音频帧

        is_speaking = False  # 是否在说话
        silent_count = 0  # 沉默计数
        speaking_flag = False  # 录入标志位 不重要

        logger.info("[即将开始录音……]")

        while True:
            # 播放中不录音
            if config.get("talk", "no_recording_during_playback"):
                # 存在待合成音频 或 已合成音频还未播放 或 播放中 或 在数据处理中
                if (
                    my_handle.is_audio_queue_empty() != 15
                    or my_handle.is_handle_empty() == 1
                    or my_global.wait_play_audio_num > 0
                ):
                    time.sleep(
                        float(
                            config.get(
                                "talk", "no_recording_during_playback_sleep_interval"
                            )
                        )
                    )
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

    # 处理聊天逻辑 传入ASR后的文本内容
    def talk_handle(content: str):
        global is_talk_awake

        def clear_queue_and_stop_audio_play(message_queue: bool=True, voice_tmp_path_queue: bool=True, stop_audio_play: bool=True):
            """
            清空队列 或 停止播放音频
            """
            if message_queue:
                ret = my_handle.clear_queue("message_queue")
                if ret:
                    logger.info("清空待合成消息队列成功！")
                else:
                    logger.error("清空待合成消息队列失败！")
            if voice_tmp_path_queue:
                ret = my_handle.clear_queue("voice_tmp_path_queue")
                if ret:
                    logger.info("清空待播放音频队列成功！")
                else:
                    logger.error("清空待播放音频队列失败！")
            if stop_audio_play:
                ret = my_handle.stop_audio("pygame", True, True)

        try:
            # 检查并切换聊天唤醒状态
            def check_talk_awake(content: str):
                """检查并切换聊天唤醒状态

                Args:
                    content (str): 聊天内容

                Returns:
                    dict:
                        ret 是否需要触发
                        is_talk_awake 当前唤醒状态
                        first 是否是第一次触发 唤醒or睡眠，用于触发首次切换时的特殊提示语
                """
                global is_talk_awake

                # 判断是否启动了 唤醒词功能
                if config.get("talk", "wakeup_sleep", "enable"):
                    if config.get("talk", "wakeup_sleep", "mode") == "长期唤醒":
                        # 判断现在是否是唤醒状态
                        if is_talk_awake is False:
                            # 判断文本内容是否包含唤醒词
                            trigger_word = common.find_substring_in_list(
                                content, config.get("talk", "wakeup_sleep", "wakeup_word")
                            )
                            if trigger_word:
                                is_talk_awake = True
                                logger.info("[聊天唤醒成功]")
                                return {
                                    "ret": 0,
                                    "is_talk_awake": is_talk_awake,
                                    "first": True,
                                    "trigger_word": trigger_word,
                                }
                            return {
                                "ret": -1,
                                "is_talk_awake": is_talk_awake,
                                "first": False,
                            }
                        else:
                            # 判断文本内容是否包含睡眠词
                            trigger_word = common.find_substring_in_list(
                                content, config.get("talk", "wakeup_sleep", "sleep_word")
                            )
                            if trigger_word:
                                is_talk_awake = False
                                logger.info("[聊天睡眠成功]")
                                return {
                                    "ret": 0,
                                    "is_talk_awake": is_talk_awake,
                                    "first": True,
                                    "trigger_word": trigger_word,
                                }
                            return {
                                "ret": 0,
                                "is_talk_awake": is_talk_awake,
                                "first": False,
                            }
                    elif config.get("talk", "wakeup_sleep", "mode") == "单次唤醒":
                        # 无需判断当前是否是唤醒状态，因为默认都是状态清除
                        # 判断文本内容是否包含唤醒词
                        trigger_word = common.find_substring_in_list(
                            content, config.get("talk", "wakeup_sleep", "wakeup_word")
                        )
                        if trigger_word:
                            is_talk_awake = True
                            logger.info("[聊天唤醒成功]")
                            return {
                                "ret": 0,
                                "is_talk_awake": is_talk_awake,
                                # 单次唤醒下 没有首次唤醒提示
                                "first": False,
                                "trigger_word": trigger_word,
                            }
                        return {
                            "ret": -1,
                            "is_talk_awake": is_talk_awake,
                            "first": False,
                        }


                return {"ret": 0, "is_talk_awake": True, "trigger_word": "", "first": False}

            # 输出识别结果
            logger.info("识别结果：" + content)

            # 空内容过滤
            if content == "":
                return

            username = config.get("talk", "username")

            data = {"platform": "本地聊天", "username": username, "content": content}
            
            # 检查并切换聊天唤醒状态
            check_resp = check_talk_awake(content)
            if check_resp["ret"] == 0:
                # 唤醒情况下
                if check_resp["is_talk_awake"]:
                    # 长期唤醒、且不是首次触发的情况下，后面的内容不会携带触发词，即使携带了也不应该进行替换操作
                    if config.get("talk", "wakeup_sleep", "mode") == "长期唤醒" and not check_resp["first"]:
                        pass
                    else:
                        # 替换触发词为空
                        content = content.replace(check_resp["trigger_word"], "").strip()

                    # 因为唤醒可能会有仅唤醒词的情况，所以可能出现首次唤醒，唤醒词被过滤，content为空清空，导致不播放唤醒提示语，需要处理
                    if content == "" and not check_resp["first"]:
                        return
                    
                    # 赋值给data
                    data["content"] = content
                    
                    # 首次触发切换模式 播放唤醒文案
                    if check_resp["first"]:
                        # 随机获取文案 TODO: 如果此功能测试成功，所有的类似功能都将使用此函数简化代码
                        resp_json = common.get_random_str_in_list_and_format(
                            ori_list=config.get(
                                "talk", "wakeup_sleep", "wakeup_copywriting"
                            )
                        )
                        if resp_json["ret"] == 0:
                            data["content"] = resp_json["content"]
                            data["insert_index"] = -1
                            my_handle.reread_handle(data)
                    else:
                        # 如果启用了"打断对话"功能
                        if config.get("talk", "interrupt_talk", "enable"):
                            # 判断文本内容是否包含中断词
                            interrupt_word = common.find_substring_in_list(
                                data["content"], config.get("talk", "interrupt_talk", "keywords")
                            )
                            if interrupt_word:
                                logger.info(f"[聊天中断] 命中中断词：{interrupt_word}")
                                # 从配置中获取需要清除的数据类型
                                clean_type = config.get("talk", "interrupt_talk", "clean_type")
                                # 各类型数据是否清除
                                message_queue = "message_queue" in clean_type
                                voice_tmp_path_queue = "voice_tmp_path_queue" in clean_type
                                stop_audio_play = "stop_audio_play" in clean_type
                                
                                clear_queue_and_stop_audio_play(message_queue, voice_tmp_path_queue, stop_audio_play)
                                return False

                        # 传递给my_handle进行进行后续一系列的处理
                        my_handle.process_data(data, "talk")

                        # 单次唤醒情况下，唤醒后关闭
                        if config.get("talk", "wakeup_sleep", "mode") == "单次唤醒":
                            is_talk_awake = False
                # 睡眠情况下
                else:
                    # 首次进入睡眠 播放睡眠文案
                    if check_resp["first"]:
                        resp_json = common.get_random_str_in_list_and_format(
                            ori_list=config.get(
                                "talk", "wakeup_sleep", "sleep_copywriting"
                            )
                        )
                        if resp_json["ret"] == 0:
                            data["content"] = resp_json["content"]
                            data["insert_index"] = -1
                            my_handle.reread_handle(data)
        except Exception as e:
            logger.error(traceback.format_exc())

    # 执行录音、识别&提交
    def do_listen_and_comment(status=True):
        global \
            stop_do_listen_and_comment_thread_event, \
            faster_whisper_model, \
            sense_voice_model, \
            is_recording, \
            is_talk_awake

        try:
            is_recording = True

            config = Config(config_path)
            # 是否启用按键监听和直接对话，没启用的话就不用执行了
            if not config.get("talk", "key_listener_enable") and not config.get("talk", "direct_run_talk"):
                is_recording = False
                return

            # 针对faster_whisper情况，模型加载一次共用，减少开销
            if "faster_whisper" == config.get("talk", "type"):
                from faster_whisper import WhisperModel

                if faster_whisper_model is None:
                    logger.info("faster_whisper 模型加载中，请稍后...")
                    # Run on GPU with FP16
                    faster_whisper_model = WhisperModel(
                        model_size_or_path=config.get(
                            "talk", "faster_whisper", "model_size"
                        ),
                        device=config.get("talk", "faster_whisper", "device"),
                        compute_type=config.get(
                            "talk", "faster_whisper", "compute_type"
                        ),
                        download_root=config.get(
                            "talk", "faster_whisper", "download_root"
                        ),
                    )
                    logger.info("faster_whisper 模型加载完毕，可以开始说话了喵~")
            elif "sensevoice" == config.get("talk", "type"):
                from funasr import AutoModel

                logger.info("sensevoice 模型加载中，请稍后...")
                asr_model_path = config.get("talk", "sensevoice", "asr_model_path")
                vad_model_path = config.get("talk", "sensevoice", "vad_model_path")
                if sense_voice_model is None:
                    sense_voice_model = AutoModel(
                        model=asr_model_path,
                        vad_model=vad_model_path,
                        vad_kwargs={
                            "max_single_segment_time": int(
                                config.get(
                                    "talk", "sensevoice", "vad_max_single_segment_time"
                                )
                            )
                        },
                        trust_remote_code=True,
                        device=config.get("talk", "sensevoice", "device"),
                        remote_code="./sensevoice/model.py",
                    )

                    logger.info("sensevoice 模型加载完毕，可以开始说话了喵~")

            while True:
                try:
                    # 检查是否收到停止事件
                    if stop_do_listen_and_comment_thread_event.is_set():
                        logger.info("停止录音~")
                        is_recording = False
                        break

                    config = Config(config_path)

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
                        WAVE_OUTPUT_FILENAME = common.get_new_audio_path(
                            audio_out_path, file_name
                        )
                        # WAVE_OUTPUT_FILENAME = './out/asr_' + common.get_bj_time(4) + '.wav'

                        frames = audio_listen(
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

                                talk_handle(content)
                            else:
                                logger.error(f"百度接口报错：{res}")
                        elif config.get("talk", "type") == "faster_whisper":
                            logger.debug("faster_whisper模型加载中...")

                            language = config.get("talk", "faster_whisper", "language")
                            if language == "自动识别":
                                language = None

                            segments, info = faster_whisper_model.transcribe(
                                WAVE_OUTPUT_FILENAME,
                                language=language,
                                beam_size=config.get(
                                    "talk", "faster_whisper", "beam_size"
                                ),
                            )

                            logger.debug(
                                "识别语言为：'%s'，概率：%f"
                                % (info.language, info.language_probability)
                            )

                            content = ""
                            for segment in segments:
                                logger.info(
                                    "[%.2fs -> %.2fs] %s"
                                    % (segment.start, segment.end, segment.text)
                                )
                                content += segment.text + "。"

                            if content == "":
                                # 恢复录音标志位
                                is_recording = False
                                return

                            talk_handle(content)
                        elif config.get("talk", "type") == "sensevoice":
                            res = sense_voice_model.generate(
                                input=WAVE_OUTPUT_FILENAME,
                                cache={},
                                language=config.get("talk", "sensevoice", "language"),
                                text_norm=config.get("talk", "sensevoice", "text_norm"),
                                batch_size_s=int(
                                    config.get("talk", "sensevoice", "batch_size_s")
                                ),
                                batch_size=int(
                                    config.get("talk", "sensevoice", "batch_size")
                                ),
                            )

                            def remove_angle_brackets_content(input_string: str):
                                # 使用正则表达式来匹配并删除 <> 之间的内容
                                return re.sub(r"<.*?>", "", input_string)

                            content = remove_angle_brackets_content(res[0]["text"])

                            talk_handle(content)
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

                                talk_handle(content)
                        except sr.UnknownValueError:
                            logger.warning("无法识别输入的语音")
                        except sr.RequestError as e:
                            logger.error("请求出错：" + str(e))

                    is_recording = False

                    if not status:
                        return
                except Exception as e:
                    logger.error(traceback.format_exc())
                    is_recording = False
                    return
        except Exception as e:
            logger.error(traceback.format_exc())
            is_recording = False
            return

    def on_key_press(event):
        global \
            do_listen_and_comment_thread, \
            stop_do_listen_and_comment_thread_event, \
            is_recording

        # 是否启用按键监听，不启用的话就不用执行了
        if not config.get("talk", "key_listener_enable"):
            return

        # if event.name in ['z', 'Z', 'c', 'C'] and keyboard.is_pressed('ctrl'):
        # logger.info("退出程序")

        # os._exit(0)

        # 按键CD
        current_time = time.time()
        if current_time - last_pressed < cooldown:
            return

        """
        触发按键部分的判断
        """
        trigger_key_lower = None
        stop_trigger_key_lower = None

        # trigger_key是字母, 整个小写
        if trigger_key.isalpha():
            trigger_key_lower = trigger_key.lower()

        # stop_trigger_key是字母, 整个小写
        if stop_trigger_key.isalpha():
            stop_trigger_key_lower = stop_trigger_key.lower()

        if trigger_key_lower:
            if event.name == trigger_key or event.name == trigger_key_lower:
                logger.info(f"检测到单击键盘 {event.name}，即将开始录音~")
            elif event.name == stop_trigger_key or event.name == stop_trigger_key_lower:
                logger.info(f"检测到单击键盘 {event.name}，即将停止录音~")
                stop_do_listen_and_comment_thread_event.set()
                return
            else:
                return
        else:
            if event.name == trigger_key:
                logger.info(f"检测到单击键盘 {event.name}，即将开始录音~")
            elif event.name == stop_trigger_key:
                logger.info(f"检测到单击键盘 {event.name}，即将停止录音~")
                stop_do_listen_and_comment_thread_event.set()
                return
            else:
                return

        if not is_recording:
            # 是否启用连续对话模式
            if config.get("talk", "continuous_talk"):
                stop_do_listen_and_comment_thread_event.clear()
                do_listen_and_comment_thread = threading.Thread(
                    target=do_listen_and_comment, args=(True,)
                )
                do_listen_and_comment_thread.start()
            else:
                stop_do_listen_and_comment_thread_event.clear()
                do_listen_and_comment_thread = threading.Thread(
                    target=do_listen_and_comment, args=(False,)
                )
                do_listen_and_comment_thread.start()
        else:
            logger.warning("正在录音中...请勿重复点击录音捏！")

    # 按键监听
    def key_listener():
        # 注册按键按下事件的回调函数
        keyboard.on_press(on_key_press)

        try:
            # 进入监听状态，等待按键按下
            keyboard.wait()
        except KeyboardInterrupt:
            os._exit(0)

    # 直接运行语音对话
    def direct_run_talk():
        global \
            do_listen_and_comment_thread, \
            stop_do_listen_and_comment_thread_event, \
            is_recording

        if not is_recording:
            # 是否启用连续对话模式
            if config.get("talk", "continuous_talk"):
                stop_do_listen_and_comment_thread_event.clear()
                do_listen_and_comment_thread = threading.Thread(
                    target=do_listen_and_comment, args=(True,)
                )
                do_listen_and_comment_thread.start()
            else:
                stop_do_listen_and_comment_thread_event.clear()
                do_listen_and_comment_thread = threading.Thread(
                    target=do_listen_and_comment, args=(False,)
                )
                do_listen_and_comment_thread.start()

    # 从配置文件中读取触发键的字符串配置
    trigger_key = config.get("talk", "trigger_key")
    stop_trigger_key = config.get("talk", "stop_trigger_key")

    # 是否启用了 按键监听
    if config.get("talk", "key_listener_enable"):
        logger.info(
            f"单击键盘 {trigger_key} 按键进行录音喵~ 由于其他任务还要启动，如果按键没有反应，请等待一段时间（如果使用本地ASR，请等待模型加载完成后使用）"
        )

    # 是否启用了直接运行对话，如果启用了，将在首次运行时直接进行语音识别，而不需手动点击开始按键。针对有些系统按键无法触发的情况下，配合连续对话和唤醒词使用
    if config.get("talk", "direct_run_talk"):
        logger.info("直接运行对话模式，首次运行时将直接进行语音识别，而不需手动点击开始按键（如果使用本地ASR，请等待模型加载完成后使用）")
        direct_run_talk()

    # 创建并启动按键监听线程，放着也是在聊天模式下，让程序一直阻塞用的
    thread = threading.Thread(target=key_listener)
    thread.start()

    # 定时任务
    def schedule_task(index):
        global config, common, my_handle

        logger.debug("定时任务执行中...")
        hour, min = common.get_bj_time(6)

        if 0 <= hour and hour < 6:
            time = f"凌晨{hour}点{min}分"
        elif 6 <= hour and hour < 9:
            time = f"早晨{hour}点{min}分"
        elif 9 <= hour and hour < 12:
            time = f"上午{hour}点{min}分"
        elif hour == 12:
            time = f"中午{hour}点{min}分"
        elif 13 <= hour and hour < 18:
            time = f"下午{hour - 12}点{min}分"
        elif 18 <= hour and hour < 20:
            time = f"傍晚{hour - 12}点{min}分"
        elif 20 <= hour and hour < 24:
            time = f"晚上{hour - 12}点{min}分"

        # 根据对应索引从列表中随机获取一个值
        if len(config.get("schedule")[index]["copy"]) <= 0:
            return None

        random_copy = random.choice(config.get("schedule")[index]["copy"])

        # 假设有多个未知变量，用户可以在此处定义动态变量
        variables = {
            "time": time,
            "user_num": "N",
            "last_username": my_global.last_username_list[-1],
        }

        # 有用户数据情况的平台特殊处理
        if platform in ["dy", "tiktok"]:
            variables["user_num"] = my_global.last_liveroom_data["OnlineUserCount"]

        # 使用字典进行字符串替换
        if any(var in random_copy for var in variables):
            content = random_copy.format(
                **{var: value for var, value in variables.items() if var in random_copy}
            )
        else:
            content = random_copy

        content = common.brackets_text_randomize(content)

        data = {"platform": platform, "username": "定时任务", "content": content}

        logger.info(f"定时任务：{content}")

        my_handle.process_data(data, "schedule")

        # schedule.clear(index)

    # 启动定时任务
    def run_schedule():
        global config

        try:
            for index, task in enumerate(config.get("schedule")):
                if task["enable"]:
                    # logger.info(task)
                    min_seconds = int(task["time_min"])
                    max_seconds = int(task["time_max"])

                    def schedule_random_task(index, min_seconds, max_seconds):
                        schedule.clear(index)
                        # 在min_seconds和max_seconds之间随机选择下一次任务执行的时间
                        next_time = random.randint(min_seconds, max_seconds)
                        # logger.info(f"Next task {index} scheduled in {next_time} seconds at {time.ctime()}")

                        schedule_task(index)

                        schedule.every(next_time).seconds.do(
                            schedule_random_task, index, min_seconds, max_seconds
                        ).tag(index)

                    schedule_random_task(index, min_seconds, max_seconds)
        except Exception as e:
            logger.error(traceback.format_exc())

        while True:
            schedule.run_pending()
            # time.sleep(1)  # 控制每次循环的间隔时间，避免过多占用 CPU 资源

    # 创建定时任务子线程并启动 在平台是 dy的情况下，默认启动定时任务用于阻塞
    schedule_thread = None
    if any(item["enable"] for item in config.get("schedule")) or platform == "dy":
        # 创建定时任务子线程并启动
        schedule_thread = threading.Thread(target=run_schedule)
        schedule_thread.start()

    # 启动动态文案
    async def run_trends_copywriting():
        global config

        try:
            if not config.get("trends_copywriting", "enable"):
                return

            logger.info("动态文案任务线程运行中...")

            while True:
                # 文案文件路径列表
                copywriting_file_path_list = []

                # 获取动态文案列表
                for copywriting in config.get("trends_copywriting", "copywriting"):
                    # 获取文件夹内所有文件的文件绝对路径，包括文件扩展名
                    for tmp in common.get_all_file_paths(copywriting["folder_path"]):
                        copywriting_file_path_list.append(tmp)

                    # 是否开启随机播放
                    if config.get("trends_copywriting", "random_play"):
                        random.shuffle(copywriting_file_path_list)

                    logger.debug(
                        f"copywriting_file_path_list={copywriting_file_path_list}"
                    )

                    # 遍历文案文件路径列表
                    for copywriting_file_path in copywriting_file_path_list:
                        # 获取文案文件内容
                        copywriting_file_content = common.read_file_return_content(
                            copywriting_file_path
                        )
                        # 是否启用提示词对文案内容进行转换
                        if copywriting["prompt_change_enable"]:
                            data_json = {
                                "username": "trends_copywriting",
                                "content": copywriting["prompt_change_content"]
                                + copywriting_file_content,
                            }

                            # 调用函数进行LLM处理，以及生成回复内容，进行音频合成，需要好好考虑考虑实现
                            data_json["content"] = my_handle.llm_handle(
                                config.get("trends_copywriting", "llm_type"), data_json
                            )
                        else:
                            copywriting_file_content = common.brackets_text_randomize(
                                copywriting_file_content
                            )

                            data_json = {
                                "username": "trends_copywriting",
                                "content": copywriting_file_content,
                            }

                        logger.debug(
                            f'copywriting_file_content={copywriting_file_content},content={data_json["content"]}'
                        )

                        # 空数据判断
                        if (
                            data_json["content"] is not None
                            and data_json["content"] != ""
                        ):
                            # 发给直接复读进行处理
                            my_handle.reread_handle(
                                data_json, filter=True, type="trends_copywriting"
                            )

                            await asyncio.sleep(
                                config.get("trends_copywriting", "play_interval")
                            )
        except Exception as e:
            logger.error(traceback.format_exc())

    if config.get("trends_copywriting", "enable"):
        # 创建动态文案子线程并启动
        threading.Thread(target=lambda: asyncio.run(run_trends_copywriting())).start()

    # 闲时任务
    async def idle_time_task():
        global config, common

        try:
            if not config.get("idle_time_task", "enable"):
                return

            logger.info("闲时任务线程运行中...")

            # 记录上一次触发的任务类型
            last_mode = 0
            copywriting_copy_list = None
            comment_copy_list = None
            local_audio_path_list = None

            overflow_time_min = int(config.get("idle_time_task", "idle_time_min"))
            overflow_time_max = int(config.get("idle_time_task", "idle_time_max"))
            overflow_time = random.randint(overflow_time_min, overflow_time_max)

            logger.info(f"下一个闲时任务将在{overflow_time}秒后执行")

            def load_data_list(type):
                if type == "copywriting":
                    tmp = config.get("idle_time_task", "copywriting", "copy")
                elif type == "comment":
                    tmp = config.get("idle_time_task", "comment", "copy")
                elif type == "local_audio":
                    tmp = config.get("idle_time_task", "local_audio", "path")

                logger.debug(f"type={type}, tmp={tmp}")
                tmp2 = copy.copy(tmp)
                return tmp2

            # 加载数据到list
            copywriting_copy_list = load_data_list("copywriting")
            comment_copy_list = load_data_list("comment")
            local_audio_path_list = load_data_list("local_audio")

            logger.debug(f"copywriting_copy_list={copywriting_copy_list}")
            logger.debug(f"comment_copy_list={comment_copy_list}")
            logger.debug(f"local_audio_path_list={local_audio_path_list}")

            def do_task(
                last_mode,
                copywriting_copy_list,
                comment_copy_list,
                local_audio_path_list,
            ):
                # 闲时计数清零
                my_global.global_idle_time = 0

                # 闲时任务处理
                if config.get("idle_time_task", "copywriting", "enable"):
                    if last_mode == 0:
                        # 是否开启了随机触发
                        if config.get("idle_time_task", "copywriting", "random"):
                            logger.debug("切换到文案触发模式")
                            if copywriting_copy_list != []:
                                # 随机打乱列表中的元素
                                random.shuffle(copywriting_copy_list)
                                copywriting_copy = copywriting_copy_list.pop(0)
                            else:
                                # 刷新list数据
                                copywriting_copy_list = load_data_list("copywriting")
                                # 随机打乱列表中的元素
                                random.shuffle(copywriting_copy_list)
                                if copywriting_copy_list != []:
                                    copywriting_copy = copywriting_copy_list.pop(0)
                                else:
                                    return (
                                        last_mode,
                                        copywriting_copy_list,
                                        comment_copy_list,
                                        local_audio_path_list,
                                    )
                        else:
                            logger.debug(copywriting_copy_list)
                            if copywriting_copy_list != []:
                                copywriting_copy = copywriting_copy_list.pop(0)
                            else:
                                # 刷新list数据
                                copywriting_copy_list = load_data_list("copywriting")
                                if copywriting_copy_list != []:
                                    copywriting_copy = copywriting_copy_list.pop(0)
                                else:
                                    return (
                                        last_mode,
                                        copywriting_copy_list,
                                        comment_copy_list,
                                        local_audio_path_list,
                                    )

                        hour, min = common.get_bj_time(6)

                        if 0 <= hour and hour < 6:
                            time = f"凌晨{hour}点{min}分"
                        elif 6 <= hour and hour < 9:
                            time = f"早晨{hour}点{min}分"
                        elif 9 <= hour and hour < 12:
                            time = f"上午{hour}点{min}分"
                        elif hour == 12:
                            time = f"中午{hour}点{min}分"
                        elif 13 <= hour and hour < 18:
                            time = f"下午{hour - 12}点{min}分"
                        elif 18 <= hour and hour < 20:
                            time = f"傍晚{hour - 12}点{min}分"
                        elif 20 <= hour and hour < 24:
                            time = f"晚上{hour - 12}点{min}分"

                        # 动态变量替换
                        # 假设有多个未知变量，用户可以在此处定义动态变量
                        variables = {
                            "time": time,
                            "user_num": "N",
                            "last_username": my_global.last_username_list[-1],
                        }

                        # 有用户数据情况的平台特殊处理
                        if platform in ["dy", "tiktok"]:
                            variables["user_num"] = my_global.last_liveroom_data[
                                "OnlineUserCount"
                            ]

                        # 使用字典进行字符串替换
                        if any(var in copywriting_copy for var in variables):
                            copywriting_copy = copywriting_copy.format(
                                **{
                                    var: value
                                    for var, value in variables.items()
                                    if var in copywriting_copy
                                }
                            )

                        # [1|2]括号语法随机获取一个值，返回取值完成后的字符串
                        copywriting_copy = common.brackets_text_randomize(
                            copywriting_copy
                        )

                        # 发送给处理函数
                        data = {
                            "platform": platform,
                            "username": "闲时任务-文案模式",
                            "type": "reread",
                            "content": copywriting_copy,
                        }

                        my_handle.process_data(data, "idle_time_task")

                        # 模式切换
                        last_mode = 1

                        overflow_time = random.randint(
                            overflow_time_min, overflow_time_max
                        )
                        logger.info(f"下一个闲时任务将在{overflow_time}秒后执行")

                        return (
                            last_mode,
                            copywriting_copy_list,
                            comment_copy_list,
                            local_audio_path_list,
                        )
                else:
                    last_mode = 1

                if config.get("idle_time_task", "comment", "enable"):
                    if last_mode == 1:
                        # 是否开启了随机触发
                        if config.get("idle_time_task", "comment", "random"):
                            logger.debug("切换到弹幕触发LLM模式")
                            if comment_copy_list != []:
                                # 随机打乱列表中的元素
                                random.shuffle(comment_copy_list)
                                comment_copy = comment_copy_list.pop(0)
                            else:
                                # 刷新list数据
                                comment_copy_list = load_data_list("comment")
                                # 随机打乱列表中的元素
                                random.shuffle(comment_copy_list)
                                comment_copy = comment_copy_list.pop(0)
                        else:
                            if comment_copy_list != []:
                                comment_copy = comment_copy_list.pop(0)
                            else:
                                # 刷新list数据
                                comment_copy_list = load_data_list("comment")
                                comment_copy = comment_copy_list.pop(0)

                        hour, min = common.get_bj_time(6)

                        if 0 <= hour and hour < 6:
                            time = f"凌晨{hour}点{min}分"
                        elif 6 <= hour and hour < 9:
                            time = f"早晨{hour}点{min}分"
                        elif 9 <= hour and hour < 12:
                            time = f"上午{hour}点{min}分"
                        elif hour == 12:
                            time = f"中午{hour}点{min}分"
                        elif 13 <= hour and hour < 18:
                            time = f"下午{hour - 12}点{min}分"
                        elif 18 <= hour and hour < 20:
                            time = f"傍晚{hour - 12}点{min}分"
                        elif 20 <= hour and hour < 24:
                            time = f"晚上{hour - 12}点{min}分"

                        # 动态变量替换
                        # 假设有多个未知变量，用户可以在此处定义动态变量
                        variables = {
                            "time": time,
                            "user_num": "N",
                            "last_username": my_global.last_username_list[-1],
                        }

                        # 有用户数据情况的平台特殊处理
                        if platform in ["dy", "tiktok"]:
                            variables["user_num"] = my_global.last_liveroom_data[
                                "OnlineUserCount"
                            ]

                        # 使用字典进行字符串替换
                        if any(var in comment_copy for var in variables):
                            comment_copy = comment_copy.format(
                                **{
                                    var: value
                                    for var, value in variables.items()
                                    if var in comment_copy
                                }
                            )

                        # [1|2]括号语法随机获取一个值，返回取值完成后的字符串
                        comment_copy = common.brackets_text_randomize(comment_copy)

                        # 发送给处理函数
                        data = {
                            "platform": platform,
                            "username": "闲时任务-弹幕触发LLM模式",
                            "type": "comment",
                            "content": comment_copy,
                        }

                        my_handle.process_data(data, "idle_time_task")

                        # 模式切换
                        last_mode = 2

                        overflow_time = random.randint(
                            overflow_time_min, overflow_time_max
                        )
                        logger.info(f"下一个闲时任务将在{overflow_time}秒后执行")

                        return (
                            last_mode,
                            copywriting_copy_list,
                            comment_copy_list,
                            local_audio_path_list,
                        )
                else:
                    last_mode = 2

                if config.get("idle_time_task", "local_audio", "enable"):
                    if last_mode == 2:
                        logger.debug("切换到本地音频模式")

                        # 是否开启了随机触发
                        if config.get("idle_time_task", "local_audio", "random"):
                            if local_audio_path_list != []:
                                # 随机打乱列表中的元素
                                random.shuffle(local_audio_path_list)
                                local_audio_path = local_audio_path_list.pop(0)
                            else:
                                # 刷新list数据
                                local_audio_path_list = load_data_list("local_audio")
                                # 随机打乱列表中的元素
                                random.shuffle(local_audio_path_list)
                                local_audio_path = local_audio_path_list.pop(0)
                        else:
                            if local_audio_path_list != []:
                                local_audio_path = local_audio_path_list.pop(0)
                            else:
                                # 刷新list数据
                                local_audio_path_list = load_data_list("local_audio")
                                local_audio_path = local_audio_path_list.pop(0)

                        # [1|2]括号语法随机获取一个值，返回取值完成后的字符串
                        local_audio_path = common.brackets_text_randomize(
                            local_audio_path
                        )

                        logger.debug(f"local_audio_path={local_audio_path}")

                        # 发送给处理函数
                        data = {
                            "platform": platform,
                            "username": "闲时任务-本地音频模式",
                            "type": "local_audio",
                            "content": common.extract_filename(local_audio_path, False),
                            "file_path": local_audio_path,
                        }

                        my_handle.process_data(data, "idle_time_task")

                        # 模式切换
                        last_mode = 0

                        overflow_time = random.randint(
                            overflow_time_min, overflow_time_max
                        )
                        logger.info(f"下一个闲时任务将在{overflow_time}秒后执行")

                        return (
                            last_mode,
                            copywriting_copy_list,
                            comment_copy_list,
                            local_audio_path_list,
                        )
                else:
                    last_mode = 0

                return (
                    last_mode,
                    copywriting_copy_list,
                    comment_copy_list,
                    local_audio_path_list,
                )

            while True:
                # 如果闲时时间范围为0，就睡眠100ms 意思意思
                if overflow_time_min > 0 and overflow_time_max > 0:
                    # 每隔一秒的睡眠进行闲时计数
                    await asyncio.sleep(1)
                else:
                    await asyncio.sleep(0.1)
                my_global.global_idle_time = my_global.global_idle_time + 1

                if config.get("idle_time_task", "type") == "直播间无消息更新闲时":
                    # 闲时计数达到指定值，进行闲时任务处理
                    if my_global.global_idle_time >= overflow_time:
                        (
                            last_mode,
                            copywriting_copy_list,
                            comment_copy_list,
                            local_audio_path_list,
                        ) = do_task(
                            last_mode,
                            copywriting_copy_list,
                            comment_copy_list,
                            local_audio_path_list,
                        )
                elif config.get("idle_time_task", "type") == "待合成消息队列更新闲时":
                    if my_handle.is_queue_less_or_greater_than(
                        type="message_queue",
                        less=int(
                            config.get("idle_time_task", "min_msg_queue_len_to_trigger")
                        ),
                    ):
                        (
                            last_mode,
                            copywriting_copy_list,
                            comment_copy_list,
                            local_audio_path_list,
                        ) = do_task(
                            last_mode,
                            copywriting_copy_list,
                            comment_copy_list,
                            local_audio_path_list,
                        )
                elif config.get("idle_time_task", "type") == "待播放音频队列更新闲时":
                    logger.debug(f"待播放音频数：{my_global.wait_play_audio_num}")
                    # 特殊处理：metahuman_stream平台，判断wait_play_audio_num
                    if config.get("visual_body") == "metahuman_stream":
                        if my_global.wait_play_audio_num < config.get("idle_time_task", "min_audio_queue_len_to_trigger"):
                            (
                                last_mode,
                                copywriting_copy_list,
                                comment_copy_list,
                                local_audio_path_list,
                            ) = do_task(
                                last_mode,
                                copywriting_copy_list,
                                comment_copy_list,
                                local_audio_path_list,
                            )
                    else:
                        if my_handle.is_queue_less_or_greater_than(
                            type="voice_tmp_path_queue",
                            less=int(
                                config.get(
                                    "idle_time_task", "min_audio_queue_len_to_trigger"
                                )
                            ),
                        ):
                            (
                                last_mode,
                                copywriting_copy_list,
                                comment_copy_list,
                                local_audio_path_list,
                            ) = do_task(
                                last_mode,
                                copywriting_copy_list,
                                comment_copy_list,
                                local_audio_path_list,
                            )

        except Exception as e:
            logger.error(traceback.format_exc())

    if config.get("idle_time_task", "enable"):
        # 创建闲时任务子线程并启动
        threading.Thread(target=lambda: asyncio.run(idle_time_task())).start()

    

    # 图像识别 定时任务
    def image_recognition_schedule_task(type: str):
        global config, common, my_handle

        logger.debug(f"图像识别-{type} 定时任务执行中...")

        data = {"platform": platform, "username": None, "content": "", "type": type}

        logger.info(f"图像识别-{type} 定时任务触发")

        my_handle.process_data(data, "image_recognition_schedule")

    # 启动图像识别 定时任务
    def run_image_recognition_schedule(interval: int, type: str):
        global config

        try:
            schedule.every(interval).seconds.do(
                partial(image_recognition_schedule_task, type)
            )
        except Exception as e:
            logger.error(traceback.format_exc())

        while True:
            schedule.run_pending()
            # time.sleep(1)  # 控制每次循环的间隔时间，避免过多占用 CPU 资源

    if config.get("image_recognition", "loop_screenshot_enable"):
        # 创建定时任务子线程并启动
        image_recognition_schedule_thread = threading.Thread(
            target=lambda: run_image_recognition_schedule(
                config.get("image_recognition", "loop_screenshot_delay"), "窗口截图"
            )
        )
        image_recognition_schedule_thread.start()

    if config.get("image_recognition", "loop_cam_screenshot_enable"):
        # 创建定时任务子线程并启动
        image_recognition_cam_schedule_thread = threading.Thread(
            target=lambda: run_image_recognition_schedule(
                config.get("image_recognition", "loop_cam_screenshot_delay"),
                "摄像头截图",
            )
        )
        image_recognition_cam_schedule_thread.start()

    # 针对对接LiveTalking(metahuman-stream)特殊处理
    if config.get("visual_body") == "metahuman_stream":
        def metahuman_stream_is_speaking():

            try:
                from urllib.parse import urljoin
                url = urljoin(
                    config.get("metahuman_stream", "api_ip_port"), "is_speaking"
                )
                resp_json = common.send_request(url, 'POST', {"sessionid": 0}, timeout=5)
                if resp_json and resp_json["code"] == 0:
                    if resp_json["data"]:
                        logger.debug("LiveTalking有音频在播放")
                        my_global.wait_play_audio_num = 1
                    else:
                        logger.debug("LiveTalking没有音频在播放")
                        my_global.wait_play_audio_num = 0
                        
            except Exception as e:
                logger.error(traceback.format_exc())
                logger.error("请求LiveTalking is_speaking接口失败")

        # 创建线程定时请求LiveTalking的is_speaking接口，判断是否有音频在播放
        def run_metahuman_stream_is_speaking_schedule():
            interval = 3
            try:
                schedule.every(interval).seconds.do(
                    partial(metahuman_stream_is_speaking)
                )
            except Exception as e:
                logger.error(traceback.format_exc())

            while True:
                schedule.run_pending()    

        run_metahuman_stream_is_speaking_schedule_thread = threading.Thread(
            target=lambda: run_metahuman_stream_is_speaking_schedule()
        )
        run_metahuman_stream_is_speaking_schedule_thread.start()
    
    logger.info(f"当前平台：{platform}")

    # 聊天模式下靠按键监听线程阻塞主线程
    if platform == "talk":
        thread.join()
        return

    # 平台监听模块按需导入（注册表见 utils/platforms/__init__.py）
    started, message = start_platform_listen(
        platform, config, common, my_handle, schedule_thread
    )
    if not started:
        logger.error(message)


# 退出程序
def exit_handler(signum, frame):
    logger.info("收到信号:", signum)


if __name__ == "__main__":
    common = Common()
    config = Config(config_path)
    # 日志文件路径
    log_path = "./log/log-" + common.get_bj_time(1) + ".txt"
    # Configure_logger(log_path)

    platform = config.get("platform")


    # 按键监听相关
    do_listen_and_comment_thread = None
    stop_do_listen_and_comment_thread_event = None
    # 存储加载的模型对象
    faster_whisper_model = None
    sense_voice_model = None
    # 正在录音中 标志位
    is_recording = False
    # 聊天是否唤醒
    is_talk_awake = False


    # 信号特殊处理
    signal.signal(signal.SIGINT, exit_handler)
    signal.signal(signal.SIGTERM, exit_handler)

    start_server()
