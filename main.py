"""程序入口：组装配置、核心处理器与各后台任务线程。

历史说明：本文件原本是一个 1500+ 行的 start_server() 巨型函数，
现已按职责拆分到 app/ 包（api / voice_chat / scheduler / idle_tasks /
static_server），本文件只保留启动编排。各子模块共享的运行上下文
见 app.state.AppState。
"""

import os
import signal
import traceback

from app.api import start_api_server
from app.idle_tasks import start_idle_time_task, start_trends_copywriting
from app.scheduler import start_scheduler
from app.static_server import start_static_server
from app.state import AppState
from app.voice_chat import VoiceChat
from luna.core.my_handle import My_handle
from luna.infra.my_log import logger
from luna.platforms import start_platform_listen
import luna.infra.my_global as my_global

# 配置文件路径：LUNA_CONFIG_PATH 供多实例与自动化测试覆盖（与 webui/webui_server 一致）
config_path = os.environ.get("LUNA_CONFIG_PATH") or "config.json"


def start_server(state: AppState):
    """按固定顺序拉起全部后台任务，最后按平台进入监听/阻塞。"""
    my_handle = state.my_handle

    # 待播放音频数量（在使用 音频播放器 或者 metahuman-stream 等不通过 AI Vtuber
    # 播放音频的对接项目时，用此变量记录是否还有音频没有播放完）
    my_global.wait_play_audio_num = 0
    my_global.wait_synthesis_msg_num = 0

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

    # Live2D 静态页线程
    try:
        if state.config.get("live2d", "enable"):
            start_static_server(int(state.config.get("live2d", "port")))
    except Exception:
        logger.error(traceback.format_exc())
        os._exit(0)

    # HTTP API 线程（wxlive 平台不需要）
    if state.platform != "wxlive":
        start_api_server(state)

    # 按键/语音聊天链路（各平台下都会启动，内部按配置判断是否响应）
    voice_chat = VoiceChat(state)
    voice_chat.start()

    # 定时任务统一调度线程（定时文案 / 图像识别循环 / LiveTalking 轮询）
    state.schedule_thread = start_scheduler(state)

    # 动态文案 & 闲时任务
    start_trends_copywriting(state)
    start_idle_time_task(state)

    logger.info(f"当前平台：{state.platform}")

    # 聊天模式下靠按键监听线程阻塞主线程
    if state.platform == "talk":
        voice_chat.join()
        return

    # 平台监听模块按需导入（注册表见 utils/platforms/__init__.py）
    started, message = start_platform_listen(
        state.platform, state.config, state.common, my_handle, state.schedule_thread
    )
    if not started:
        logger.error(message)


# 退出程序
def exit_handler(signum, frame):
    logger.info("收到信号:", signum)


if __name__ == "__main__":
    state = AppState(config_path)

    signal.signal(signal.SIGINT, exit_handler)
    signal.signal(signal.SIGTERM, exit_handler)

    # 核心处理器（单例；内部完成 配置加载/聊天模型注册/数据库初始化）
    state.my_handle = My_handle(config_path)
    if state.my_handle is None:
        logger.error("程序初始化失败！")
        os._exit(0)

    start_server(state)
