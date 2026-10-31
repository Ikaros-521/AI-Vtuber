"""schedule 定时任务：定时文案、图像识别循环、LiveTalking 轮询。

原实现有三处独立的 `while True: schedule.run_pending()` 线程（定时任务、
窗口截图、摄像头截图、metahuman 轮询），且循环里的 time.sleep(1) 被注释
成了忙等空转；schedule 库本身非线程安全，多线程共跑一个默认调度器还可能
重复执行同一任务。现收拢为单一调度线程：
- 所有任务在该线程启动时注册（schedule.clear/tag 语义不变）
- 只有一处调用 run_pending，循环间隔 1 秒
"""

import random
import threading
import time
import traceback
from functools import partial

import schedule

from app.greeting import time_period_text
from luna.infra.my_log import logger
import luna.infra.my_global as my_global


def schedule_task(state, index):
    """定时文案任务：按索引取随机文案，做变量替换后交给 my_handle。"""
    logger.debug("定时任务执行中...")
    hour, min = state.common.get_bj_time(6)
    time_text = time_period_text(hour, min)

    # 根据对应索引从列表中随机获取一个值
    if len(state.config.get("schedule")[index]["copy"]) <= 0:
        return None

    random_copy = random.choice(state.config.get("schedule")[index]["copy"])

    # 假设有多个未知变量，用户可以在此处定义动态变量
    variables = {
        "time": time_text,
        "user_num": "N",
        "last_username": my_global.last_username_list[-1],
    }

    # 有用户数据情况的平台特殊处理
    if state.platform in ["dy", "tiktok"]:
        variables["user_num"] = my_global.last_liveroom_data["OnlineUserCount"]

    # 使用字典进行字符串替换
    if any(var in random_copy for var in variables):
        content = random_copy.format(**{var: value for var, value in variables.items() if var in random_copy})
    else:
        content = random_copy

    content = state.common.brackets_text_randomize(content)

    data = {"platform": state.platform, "username": "定时任务", "content": content}

    logger.info(f"定时任务：{content}")

    state.my_handle.process_data(data, "schedule")


def image_recognition_schedule_task(state, type: str):
    """图像识别定时任务：截图后交给 my_handle 处理。"""
    logger.debug(f"图像识别-{type} 定时任务执行中...")

    data = {"platform": state.platform, "username": None, "content": "", "type": type}

    logger.info(f"图像识别-{type} 定时任务触发")

    state.my_handle.process_data(data, "image_recognition_schedule")


def metahuman_stream_is_speaking(state):
    """轮询 LiveTalking(metahuman-stream) 的 is_speaking 接口，维护待播放计数。"""
    try:
        from urllib.parse import urljoin

        url = urljoin(state.config.get("metahuman_stream", "api_ip_port"), "is_speaking")
        resp_json = state.common.send_request(url, "POST", {"sessionid": 0}, timeout=5)
        if resp_json and resp_json["code"] == 0:
            if resp_json["data"]:
                logger.debug("LiveTalking有音频在播放")
                my_global.wait_play_audio_num = 1
            else:
                logger.debug("LiveTalking没有音频在播放")
                my_global.wait_play_audio_num = 0

    except Exception:
        logger.error(traceback.format_exc())
        logger.error("请求LiveTalking is_speaking接口失败")


def _register_jobs(state):
    """把全部定时任务注册进 schedule 默认调度器（仅调度线程启动时调用一次）。"""
    # 定时文案任务（随机间隔自重新调度）
    try:
        for index, task in enumerate(state.config.get("schedule")):
            if task["enable"]:
                min_seconds = int(task["time_min"])
                max_seconds = int(task["time_max"])

                def schedule_random_task(index, min_seconds, max_seconds):
                    schedule.clear(index)
                    # 在min_seconds和max_seconds之间随机选择下一次任务执行的时间
                    next_time = random.randint(min_seconds, max_seconds)

                    schedule_task(state, index)

                    schedule.every(next_time).seconds.do(schedule_random_task, index, min_seconds, max_seconds).tag(
                        index
                    )

                schedule_random_task(index, min_seconds, max_seconds)
    except Exception:
        logger.error(traceback.format_exc())

    # 图像识别循环：窗口截图 / 摄像头截图
    if state.config.get("image_recognition", "loop_screenshot_enable"):
        try:
            schedule.every(state.config.get("image_recognition", "loop_screenshot_delay")).seconds.do(
                partial(image_recognition_schedule_task, state, "窗口截图")
            )
        except Exception:
            logger.error(traceback.format_exc())

    if state.config.get("image_recognition", "loop_cam_screenshot_enable"):
        try:
            schedule.every(state.config.get("image_recognition", "loop_cam_screenshot_delay")).seconds.do(
                partial(image_recognition_schedule_task, state, "摄像头截图")
            )
        except Exception:
            logger.error(traceback.format_exc())

    # 针对对接LiveTalking(metahuman-stream)特殊处理：定时请求 is_speaking 接口
    if state.config.get("visual_body") == "metahuman_stream":
        try:
            schedule.every(3).seconds.do(partial(metahuman_stream_is_speaking, state))
        except Exception:
            logger.error(traceback.format_exc())


def run_scheduler(state):
    """调度线程主体：注册任务后循环触发（唯一的 run_pending 调用点）。"""
    _register_jobs(state)

    while True:
        schedule.run_pending()
        # 控制每次循环的间隔时间，避免过多占用 CPU 资源
        # （原实现此行被注释导致忙等空转，现恢复）
        time.sleep(1)


def start_scheduler(state):
    """按需启动调度线程；没有可调度任务时返回 None。

    dy 平台即使没有启用的定时任务也需要该线程存在（监听器会 join 它阻塞）。
    """
    schedule_enabled = any(item["enable"] for item in state.config.get("schedule") or [])
    image_loop_enabled = bool(
        state.config.get("image_recognition", "loop_screenshot_enable")
        or state.config.get("image_recognition", "loop_cam_screenshot_enable")
    )
    metahuman_enabled = state.config.get("visual_body") == "metahuman_stream"

    if not (schedule_enabled or image_loop_enabled or metahuman_enabled or state.platform == "dy"):
        return None

    thread = threading.Thread(target=run_scheduler, args=(state,), name="scheduler")
    thread.start()
    return thread
