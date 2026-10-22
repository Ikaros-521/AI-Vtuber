"""异常报警：Audio 与 My_handle 各持一份计数状态，判定与播报逻辑共用。"""

import os
import random
import threading
import time
import traceback

from .my_log import logger

# 只统计「窗口内的连续错误」。用累计值的话，一次偶发错误会继承几小时前的历史错误，
# 直接顶过 auto_restart_error_num，把好好直播的机器重启掉。
ERROR_COUNT_WINDOW = 600

# 多开平台时，各平台的收消息线程会并发报同一个 type
_state_lock = threading.Lock()

CATEGORIES = ("platform", "llm", "tts", "svc", "visual_body", "other")


def new_state():
    """Audio 与 My_handle 各持一份：报警阈值按类别独立累计。"""
    return {name: {"error_count": 0, "last_error_time": 0.0} for name in CATEGORIES}


def report_error(state, type, config, common, synthesize):
    """记一次错误，达到阈值则播报报警音频、必要时请求重启。

    Args:
        state (dict): 调用方持有的 abnormal_alarm_data
        type (str): 报警类别（platform / llm / tts / svc / visual_body / other）
        config (Config): 配置对象
        common (Common): 工具对象
        synthesize (callable): 报警音频合成入口，接收 message dict

    Returns:
        bool: 处理成功返回 True
    """

    try:
        if not config.get("abnormal_alarm", type, "enable"):
            # 关掉时连错都不记：否则长期直播攒下的计数会在用户某天打开后，
            # 被第一个偶发错误直接顶过重启阈值
            return True

        with _state_lock:
            error_count = _bump_error_count(state, type)

        logger.debug(f"abnormal_alarm_handle type={type}, error_count={error_count}")

        if config.get("abnormal_alarm", type, "type") != "local_audio":
            return True

        # 是否错误数大于 自动重启错误数
        if error_count >= config.get("abnormal_alarm", type, "auto_restart_error_num"):
            logger.warning(f"【异常报警-{type}】 出错数超过自动重启错误数，即将自动重启")
            data = {
                "type": "restart",
                "api_type": "api",
                "data": {
                    "config_path": "config.json"
                }
            }

            webui_ip = "127.0.0.1" if config.get("webui", "ip") == "0.0.0.0" else config.get("webui", "ip")
            common.send_request(f'http://{webui_ip}:{config.get("webui", "port")}/sys_cmd', "POST", data)

        # 是否错误数小于 开始报警错误数，是则不触发报警
        if error_count < config.get("abnormal_alarm", type, "start_alarm_error_num"):
            return True

        local_audio_path = config.get("abnormal_alarm", type, "local_audio_path")
        path_list = common.get_all_file_paths(local_audio_path)
        if not path_list:
            logger.warning(f"【异常报警-{type}】 目录 {local_audio_path} 下没有音频文件，跳过播报")
            return True

        # 随机选择列表中的一个元素
        audio_path = random.choice(path_list)

        message = {
            "type": "abnormal_alarm",
            "tts_type": config.get("audio_synthesis_type"),
            "data": config.get(config.get("audio_synthesis_type")),
            "config": config.get("filter"),
            "username": "系统",
            "content": os.path.join(local_audio_path, common.extract_filename(audio_path, True))
        }

        logger.warning(f"【异常报警-{type}】 {common.extract_filename(audio_path, False)}")

        synthesize(message)

    except Exception:
        logger.error(traceback.format_exc())

        return False

    return True


def _bump_error_count(state, type):
    record = state[type]
    now = time.time()
    if now - record.get("last_error_time", 0) > ERROR_COUNT_WINDOW:
        record["error_count"] = 0
    record["last_error_time"] = now
    record["error_count"] += 1
    return record["error_count"]
