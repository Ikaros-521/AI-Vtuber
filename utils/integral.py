"""积分系统：签到 / 观看 / 礼物积分的入库、查询与播报。

自 utils/my_handle.py 拆分（原先 ~470 行内联在 God Object 里）；
My_handle.integral_handle 保留一行委托门面，流水线与礼物/入场处理等
调用方零改动。

依赖通过 handle（My_handle 实例）注入：config / common / db /
audio_synthesis_handle——积分模块不反向 import my_handle，避免环。
"""

import asyncio
import random
from datetime import datetime

from .luoxi_project.live_comment_assistant import send_msg_to_live_comment_assistant
from .message import build as build_message
from .my_log import logger


def integral_handle(handle, type, data):
    """积分处理

    Args:
        type (str): 消息数据类型（comment/gift/entrance）
        data (dict): 平台侧传入的data数据，直接拿来做解析

    Returns:
        bool: 是否正常触发了积分事件，是True 否False
    """
    username = data["username"]

    if handle.config.get("integral", "enable"):
        # 根据消息类型进行对应处理
        if "comment" == type:
            content = data["content"]

            # 是否开启了签到功能
            if handle.config.get("integral", "sign", "enable"):
                # 判断弹幕内容是否是命令
                if content in handle.config.get("integral", "sign", "cmd"):
                    # 查询数据库中是否有当前用户的积分记录（缺个UID）
                    common_sql = """
                    SELECT * FROM integral WHERE username =?
                    """
                    integral_data = handle.db.fetch_all(common_sql, (username,))

                    logger.debug(f"integral_data={integral_data}")

                    # 获取文案并合成语音，传入签到天数自动检索
                    def get_copywriting_and_audio_synthesis(sign_num):
                        # 判断当前签到天数在哪个签到数区间内，根据不同的区间提供不同的文案回复
                        for integral_sign_copywriting in handle.config.get("integral", "sign", "copywriting"):
                            # 在此区间范围内，所以你的配置一定要对，不然这里就崩溃了！！！
                            if (
                                int(integral_sign_copywriting["sign_num_interval"].split("-")[0])
                                <= sign_num
                                <= int(integral_sign_copywriting["sign_num_interval"].split("-")[1])
                            ):
                                # 匹配文案
                                resp_content = random.choice(integral_sign_copywriting["copywriting"])

                                logger.debug(f"resp_content={resp_content}")

                                data_json = {
                                    "username": data["username"],
                                    "get_integral": int(handle.config.get("integral", "sign", "get_integral")),
                                    "sign_num": sign_num + 1,
                                }

                                resp_content = handle.common.dynamic_variable_replacement(resp_content, data_json)

                                # 括号语法替换
                                resp_content = handle.common.brackets_text_randomize(resp_content)

                                # 生成回复内容
                                message = build_message(handle.config, "integral", username, resp_content)

                                # 洛曦 直播弹幕助手
                                if (
                                    handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable")
                                    and "integral"
                                    in handle.config.get("luoxi_project", "Live_Comment_Assistant", "type")
                                    and "消息产生时"
                                    in handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position")
                                ):
                                    asyncio.run(
                                        send_msg_to_live_comment_assistant(
                                            handle.config.get("luoxi_project", "Live_Comment_Assistant"),
                                            resp_content,
                                        )
                                    )

                                handle.audio_synthesis_handle(message)

                    if integral_data == []:
                        # 积分表中没有该用户，插入数据
                        insert_data_sql = """
                        INSERT INTO integral (platform, username, uid, integral, view_num, sign_num, last_sign_ts, total_price, last_ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """
                        handle.db.execute(
                            insert_data_sql,
                            (
                                data["platform"],
                                username,
                                username,
                                handle.config.get("integral", "sign", "get_integral"),
                                1,
                                1,
                                datetime.now(),
                                0,
                                datetime.now(),
                            ),
                        )

                        logger.info(f"integral积分表 新增 用户：{username}")

                        get_copywriting_and_audio_synthesis(0)

                        return True
                    else:
                        integral_data = integral_data[0]
                        # 积分表中有该用户，更新数据

                        # 先判断last_sign_ts是否是今天，如果是，则说明已经打卡过了，不能重复打卡
                        # 获取日期时间字符串字段，此处是个坑点，一旦数据库结构发生改变或者select语句改了，就会关联影响！！！
                        date_string = integral_data[6]

                        # 获取日期部分（前10个字符），并与当前日期字符串比较
                        if date_string[:10] == datetime.now().date().strftime("%Y-%m-%d"):
                            resp_content = f"{username}您今天已经签到过了，不能重复打卡哦~"
                            message = build_message(handle.config, "integral", username, resp_content)

                            # 洛曦 直播弹幕助手
                            if (
                                handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable")
                                and "integral" in handle.config.get("luoxi_project", "Live_Comment_Assistant", "type")
                                and "消息产生时"
                                in handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position")
                            ):
                                asyncio.run(
                                    send_msg_to_live_comment_assistant(
                                        handle.config.get("luoxi_project", "Live_Comment_Assistant"),
                                        resp_content,
                                    )
                                )

                            handle.audio_synthesis_handle(message)

                            return True

                        # 更新下用户数据
                        update_data_sql = """
                        UPDATE integral SET integral=?, view_num=?, sign_num=?, last_sign_ts=?, last_ts=? WHERE username =?
                        """
                        handle.db.execute(
                            update_data_sql,
                            (
                                # 此处是个坑点，一旦数据库结构发生改变或者select语句改了，就会关联影响！！！
                                integral_data[3] + handle.config.get("integral", "sign", "get_integral"),
                                integral_data[4] + 1,
                                integral_data[5] + 1,
                                datetime.now(),
                                datetime.now(),
                                username,
                            ),
                        )

                        logger.info(f"integral积分表 更新 用户：{username}")

                        get_copywriting_and_audio_synthesis(integral_data[5] + 1)

                        return True
        elif "gift" == type:
            # 是否开启了礼物功能
            if handle.config.get("integral", "gift", "enable"):
                # 查询数据库中是否有当前用户的积分记录（缺个UID）
                common_sql = """
                SELECT * FROM integral WHERE username =?
                """
                integral_data = handle.db.fetch_all(common_sql, (username,))

                logger.debug(f"integral_data={integral_data}")

                get_integral = int(
                    float(handle.config.get("integral", "gift", "get_integral_proportion")) * data["total_price"]
                )

                # 获取文案并合成语音，传入总礼物金额自动检索
                def get_copywriting_and_audio_synthesis(total_price):
                    # 判断当前礼物金额在哪个礼物金额区间内，根据不同的区间提供不同的文案回复
                    for integral_gift_copywriting in handle.config.get("integral", "gift", "copywriting"):
                        # 在此区间范围内，所以你的配置一定要对，不然这里就崩溃了！！！
                        if (
                            float(integral_gift_copywriting["gift_price_interval"].split("-")[0])
                            <= total_price
                            <= float(integral_gift_copywriting["gift_price_interval"].split("-")[1])
                        ):
                            # 匹配文案
                            resp_content = random.choice(integral_gift_copywriting["copywriting"])

                            logger.debug(f"resp_content={resp_content}")

                            data_json = {
                                "username": data["username"],
                                "gift_name": data["gift_name"],
                                "get_integral": get_integral,
                                "gift_num": data["num"],
                                "unit_price": data["unit_price"],
                                "total_price": data["total_price"],
                                "cur_time": handle.common.get_bj_time(5),
                            }

                            # 括号语法替换
                            resp_content = handle.common.brackets_text_randomize(resp_content)

                            # 动态变量替换
                            resp_content = handle.common.dynamic_variable_replacement(resp_content, data_json)

                            # 生成回复内容
                            message = build_message(handle.config, "integral", username, resp_content)

                            # 洛曦 直播弹幕助手
                            if (
                                handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable")
                                and "integral" in handle.config.get("luoxi_project", "Live_Comment_Assistant", "type")
                                and "消息产生时"
                                in handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position")
                            ):
                                asyncio.run(
                                    send_msg_to_live_comment_assistant(
                                        handle.config.get("luoxi_project", "Live_Comment_Assistant"),
                                        resp_content,
                                    )
                                )

                            handle.audio_synthesis_handle(message)

                # TODO：此处有计算bug！！！ 总礼物价值计算不对，后期待优化
                if integral_data == []:
                    # 积分表中没有该用户，插入数据
                    insert_data_sql = """
                    INSERT INTO integral (platform, username, uid, integral, view_num, sign_num, last_sign_ts, total_price, last_ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    handle.db.execute(
                        insert_data_sql,
                        (
                            data["platform"],
                            username,
                            username,
                            get_integral,
                            1,
                            1,
                            datetime.now(),
                            data["total_price"],
                            datetime.now(),
                        ),
                    )

                    logger.info(f"integral积分表 新增 用户：{username}")

                    get_copywriting_and_audio_synthesis(data["total_price"])

                    return True
                else:
                    integral_data = integral_data[0]
                    # 积分表中有该用户，更新数据

                    # 更新下用户数据
                    update_data_sql = """
                    UPDATE integral SET integral=?, total_price=?, last_ts=? WHERE username =?
                    """
                    handle.db.execute(
                        update_data_sql,
                        (
                            # 此处是个坑点，一旦数据库结构发生改变或者select语句改了，就会关联影响！！！
                            integral_data[3] + get_integral,
                            integral_data[7] + data["total_price"],
                            datetime.now(),
                            username,
                        ),
                    )

                    logger.info(f"integral积分表 更新 用户：{username}")

                    get_copywriting_and_audio_synthesis(data["total_price"])

                    return True
        elif "entrance" == type:
            # 是否开启了入场功能
            if handle.config.get("integral", "entrance", "enable"):
                # 查询数据库中是否有当前用户的积分记录（缺个UID）
                common_sql = """
                SELECT * FROM integral WHERE username =?
                """
                integral_data = handle.db.fetch_all(common_sql, (username,))

                logger.debug(f"integral_data={integral_data}")

                # 获取文案并合成语音，传入观看天数自动检索
                def get_copywriting_and_audio_synthesis(view_num):
                    # 判断当前签到天数在哪个签到数区间内，根据不同的区间提供不同的文案回复
                    for integral_entrance_copywriting in handle.config.get("integral", "entrance", "copywriting"):
                        # 在此区间范围内，所以你的配置一定要对，不然这里就崩溃了！！！
                        if (
                            int(integral_entrance_copywriting["entrance_num_interval"].split("-")[0])
                            <= view_num
                            <= int(integral_entrance_copywriting["entrance_num_interval"].split("-")[1])
                        ):
                            if len(integral_entrance_copywriting["copywriting"]) <= 0:
                                return False

                            # 匹配文案
                            resp_content = random.choice(integral_entrance_copywriting["copywriting"])

                            logger.debug(f"resp_content={resp_content}")

                            data_json = {
                                "username": data["username"],
                                "get_integral": int(handle.config.get("integral", "entrance", "get_integral")),
                                "entrance_num": view_num + 1,
                            }

                            resp_content = handle.common.dynamic_variable_replacement(resp_content, data_json)

                            # 括号语法替换
                            resp_content = handle.common.brackets_text_randomize(resp_content)

                            # 生成回复内容
                            message = build_message(handle.config, "integral", username, resp_content)

                            # 洛曦 直播弹幕助手
                            if (
                                handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable")
                                and "integral" in handle.config.get("luoxi_project", "Live_Comment_Assistant", "type")
                                and "消息产生时"
                                in handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position")
                            ):
                                asyncio.run(
                                    send_msg_to_live_comment_assistant(
                                        handle.config.get("luoxi_project", "Live_Comment_Assistant"),
                                        resp_content,
                                    )
                                )

                            handle.audio_synthesis_handle(message)

                if integral_data == []:
                    # 积分表中没有该用户，插入数据
                    insert_data_sql = """
                    INSERT INTO integral (platform, username, uid, integral, view_num, sign_num, last_sign_ts, total_price, last_ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    handle.db.execute(
                        insert_data_sql,
                        (
                            data["platform"],
                            username,
                            username,
                            handle.config.get("integral", "entrance", "get_integral"),
                            1,
                            0,
                            datetime.now(),
                            0,
                            datetime.now(),
                        ),
                    )

                    logger.info(f"integral积分表 新增 用户：{username}")

                    get_copywriting_and_audio_synthesis(1)

                    return True
                else:
                    integral_data = integral_data[0]
                    # 积分表中有该用户，更新数据

                    # 先判断last_ts是否是今天，如果是，则说明已经观看过了，不能重复记录
                    # 获取日期时间字符串字段，此处是个坑点，一旦数据库结构发生改变或者select语句改了，就会关联影响！！！
                    date_string = integral_data[8]

                    # 获取日期部分（前10个字符），并与当前日期字符串比较
                    if date_string[:10] == datetime.now().date().strftime("%Y-%m-%d"):
                        return False

                    # 更新下用户数据
                    update_data_sql = """
                    UPDATE integral SET integral=?, view_num=?, last_ts=? WHERE username =?
                    """
                    handle.db.execute(
                        update_data_sql,
                        (
                            # 此处是个坑点，一旦数据库结构发生改变或者select语句改了，就会关联影响！！！
                            integral_data[3] + handle.config.get("integral", "entrance", "get_integral"),
                            integral_data[4] + 1,
                            datetime.now(),
                            username,
                        ),
                    )

                    logger.info(f"integral积分表 更新 用户：{username}")

                    get_copywriting_and_audio_synthesis(integral_data[4] + 1)

                    return True
        elif "crud" == type:
            content = data["content"]

            # 是否开启了查询功能
            if handle.config.get("integral", "crud", "query", "enable"):
                # 判断弹幕内容是否是命令
                if content in handle.config.get("integral", "crud", "query", "cmd"):
                    # 查询数据库中是否有当前用户的积分记录（缺个UID）
                    common_sql = """
                    SELECT * FROM integral WHERE username =?
                    """
                    integral_data = handle.db.fetch_all(common_sql, (username,))

                    logger.debug(f"integral_data={integral_data}")

                    # 获取文案并合成语音，传入积分总数自动检索
                    def get_copywriting_and_audio_synthesis(total_integral):
                        # 匹配文案
                        resp_content = random.choice(handle.config.get("integral", "crud", "query", "copywriting"))

                        logger.debug(f"resp_content={resp_content}")

                        data_json = {"username": data["username"], "integral": total_integral}

                        resp_content = handle.common.dynamic_variable_replacement(resp_content, data_json)

                        # 如果积分为0，则返回个没积分的回复。不过这个基本没可能，除非有bug
                        if total_integral == 0:
                            resp_content = data["username"] + "，查询到您无积分。"

                        # 括号语法替换
                        resp_content = handle.common.brackets_text_randomize(resp_content)

                        # 生成回复内容
                        message = build_message(handle.config, "integral", username, resp_content)

                        # 洛曦 直播弹幕助手
                        if (
                            handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable")
                            and "integral" in handle.config.get("luoxi_project", "Live_Comment_Assistant", "type")
                            and "消息产生时"
                            in handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position")
                        ):
                            asyncio.run(
                                send_msg_to_live_comment_assistant(
                                    handle.config.get("luoxi_project", "Live_Comment_Assistant"), resp_content
                                )
                            )

                        handle.audio_synthesis_handle(message)

                    if integral_data == []:
                        logger.info(f"integral积分表 查询不到 用户：{username}")

                        get_copywriting_and_audio_synthesis(0)

                        return True
                    else:
                        integral_data = integral_data[0]
                        # 积分表中有该用户

                        # 获取日期时间字符串字段，此处是个坑点，一旦数据库结构发生改变或者select语句改了，就会关联影响！！！
                        date_string = integral_data[3]

                        logger.info(f"integral积分表 用户：{username}，总积分：{date_string}")

                        get_copywriting_and_audio_synthesis(int(date_string))

                        return True
    return False
