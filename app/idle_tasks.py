"""动态文案与闲时任务：拆分自 main.py 的 run_trends_copywriting / idle_time_task。"""

import asyncio
import copy
import random
import threading
import traceback

from app.greeting import time_period_text
from utils.my_log import logger
import utils.my_global as my_global


async def run_trends_copywriting(state):
    """动态文案任务：遍历文案文件，可选 LLM 改写后复读播放。"""
    config = state.config
    common = state.common
    my_handle = state.my_handle

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

                logger.debug(f"copywriting_file_path_list={copywriting_file_path_list}")

                # 遍历文案文件路径列表
                for copywriting_file_path in copywriting_file_path_list:
                    # 获取文案文件内容
                    copywriting_file_content = common.read_file_return_content(copywriting_file_path)
                    # 是否启用提示词对文案内容进行转换
                    if copywriting["prompt_change_enable"]:
                        data_json = {
                            "username": "trends_copywriting",
                            "content": copywriting["prompt_change_content"] + copywriting_file_content,
                        }

                        # 调用函数进行LLM处理，以及生成回复内容，进行音频合成，需要好好考虑考虑实现
                        data_json["content"] = my_handle.llm_handle(
                            config.get("trends_copywriting", "llm_type"), data_json
                        )
                    else:
                        copywriting_file_content = common.brackets_text_randomize(copywriting_file_content)

                        data_json = {
                            "username": "trends_copywriting",
                            "content": copywriting_file_content,
                        }

                    logger.debug(f"copywriting_file_content={copywriting_file_content},content={data_json['content']}")

                    # 空数据判断
                    if data_json["content"] is not None and data_json["content"] != "":
                        # 发给直接复读进行处理
                        my_handle.reread_handle(data_json, filter=True, type="trends_copywriting")

                        await asyncio.sleep(config.get("trends_copywriting", "play_interval"))
    except Exception:
        logger.error(traceback.format_exc())


def start_trends_copywriting(state) -> threading.Thread | None:
    if state.config.get("trends_copywriting", "enable"):
        thread = threading.Thread(target=lambda: asyncio.run(run_trends_copywriting(state)), name="trends-copywriting")
        thread.start()
        return thread
    return None


async def idle_time_task(state):
    """闲时任务：按触发模式轮转 文案/弹幕LLM/本地音频 三种模式。"""
    config = state.config
    common = state.common
    my_handle = state.my_handle

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
        # 注意：原实现 do_task 内部重新随机出的 overflow_time 只写入了局部变量，
        # 外层 while 用的始终是这第一次抽到的值；为保持行为一致这里不做"修复"。
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

        def build_dynamic_variables():
            """动态变量替换的公共变量表（时段问候/人气/最近用户名）。"""
            hour, min = common.get_bj_time(6)
            time_text = time_period_text(hour, min)

            # 假设有多个未知变量，用户可以在此处定义动态变量
            variables = {
                "time": time_text,
                "user_num": "N",
                "last_username": my_global.last_username_list[-1],
            }

            # 有用户数据情况的平台特殊处理
            if state.platform in ["dy", "tiktok"]:
                variables["user_num"] = my_global.last_liveroom_data["OnlineUserCount"]

            return variables

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

                    # 动态变量替换
                    variables = build_dynamic_variables()

                    # 使用字典进行字符串替换
                    if any(var in copywriting_copy for var in variables):
                        copywriting_copy = copywriting_copy.format(
                            **{var: value for var, value in variables.items() if var in copywriting_copy}
                        )

                    # [1|2]括号语法随机获取一个值，返回取值完成后的字符串
                    copywriting_copy = common.brackets_text_randomize(copywriting_copy)

                    # 发送给处理函数
                    data = {
                        "platform": state.platform,
                        "username": "闲时任务-文案模式",
                        "type": "reread",
                        "content": copywriting_copy,
                    }

                    my_handle.process_data(data, "idle_time_task")

                    # 模式切换
                    last_mode = 1

                    logger.info(f"下一个闲时任务将在{random.randint(overflow_time_min, overflow_time_max)}秒后执行")

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

                    # 动态变量替换
                    variables = build_dynamic_variables()

                    # 使用字典进行字符串替换
                    if any(var in comment_copy for var in variables):
                        comment_copy = comment_copy.format(
                            **{var: value for var, value in variables.items() if var in comment_copy}
                        )

                    # [1|2]括号语法随机获取一个值，返回取值完成后的字符串
                    comment_copy = common.brackets_text_randomize(comment_copy)

                    # 发送给处理函数
                    data = {
                        "platform": state.platform,
                        "username": "闲时任务-弹幕触发LLM模式",
                        "type": "comment",
                        "content": comment_copy,
                    }

                    my_handle.process_data(data, "idle_time_task")

                    # 模式切换
                    last_mode = 2

                    logger.info(f"下一个闲时任务将在{random.randint(overflow_time_min, overflow_time_max)}秒后执行")

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
                    local_audio_path = common.brackets_text_randomize(local_audio_path)

                    logger.debug(f"local_audio_path={local_audio_path}")

                    # 发送给处理函数
                    data = {
                        "platform": state.platform,
                        "username": "闲时任务-本地音频模式",
                        "type": "local_audio",
                        "content": common.extract_filename(local_audio_path, False),
                        "file_path": local_audio_path,
                    }

                    my_handle.process_data(data, "idle_time_task")

                    # 模式切换
                    last_mode = 0

                    logger.info(f"下一个闲时任务将在{random.randint(overflow_time_min, overflow_time_max)}秒后执行")

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
                    less=int(config.get("idle_time_task", "min_msg_queue_len_to_trigger")),
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
                        less=int(config.get("idle_time_task", "min_audio_queue_len_to_trigger")),
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

    except Exception:
        logger.error(traceback.format_exc())


def start_idle_time_task(state) -> threading.Thread | None:
    if state.config.get("idle_time_task", "enable"):
        thread = threading.Thread(target=lambda: asyncio.run(idle_time_task(state)), name="idle-time-task")
        thread.start()
        return thread
    return None
