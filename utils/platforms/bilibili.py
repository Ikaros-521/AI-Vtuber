import asyncio
import os
import time
import tempfile
import traceback

from bilibili_api import Credential, live, sync
from bilibili_api import login_v2
from bilibili_api.login_v2 import QrCodeLoginEvents

from utils.my_log import logger
import utils.my_global as my_global


def _login_with_qrcode(terminal: bool) -> Credential:
    """扫码登录（bilibili-api 17.x 的 login_v2）

    terminal=True 时在终端打印字符二维码；否则把二维码图片保存到临时目录并在日志中给出路径。
    """

    async def _wait_for_login():
        qr = login_v2.QrCodeLogin()
        await qr.generate_qrcode()

        if terminal:
            logger.info("请使用哔哩哔哩客户端扫描终端中的二维码登录")
            print(qr.get_qrcode_terminal())
        else:
            qrcode_path = os.path.join(tempfile.gettempdir(), "bilibili_login_qrcode.png")
            with open(qrcode_path, "wb") as file:
                file.write(qr.get_qrcode_picture().content)
            logger.info(f"请使用哔哩哔哩客户端扫描二维码登录，二维码已保存至：{qrcode_path}")

        while True:
            state = await qr.check_state()
            if state == QrCodeLoginEvents.DONE:
                return qr.get_credential()
            if state == QrCodeLoginEvents.TIMEOUT:
                logger.warning("二维码已过期，正在重新生成...")
                await qr.generate_qrcode()
                continue
            await asyncio.sleep(1)

    return sync(_wait_for_login())


def start_listen(config, common, my_handle, platform: str):
    platform = "bilibili"

    try:
        if config.get("bilibili", "login_type") == "cookie":
            logger.info(
                "b站登录后F12抓网络包获取cookie，强烈建议使用小号！有封号风险"
            )
            logger.info(
                "b站登录后，F12控制台，输入 window.localStorage.ac_time_value 回车获取(如果没有，请重新登录)"
            )

            bilibili_cookie = config.get("bilibili", "cookie")
            bilibili_ac_time_value = config.get("bilibili", "ac_time_value")
            if bilibili_ac_time_value == "":
                bilibili_ac_time_value = None

            # logger.info(f'SESSDATA={common.parse_cookie_data(bilibili_cookie, "SESSDATA")}')
            # logger.info(f'bili_jct={common.parse_cookie_data(bilibili_cookie, "bili_jct")}')
            # logger.info(f'buvid3={common.parse_cookie_data(bilibili_cookie, "buvid3")}')
            # logger.info(f'DedeUserID={common.parse_cookie_data(bilibili_cookie, "DedeUserID")}')

            # 生成一个 Credential 对象
            credential = Credential(
                sessdata=common.parse_cookie_data(bilibili_cookie, "SESSDATA"),
                bili_jct=common.parse_cookie_data(bilibili_cookie, "bili_jct"),
                buvid3=common.parse_cookie_data(bilibili_cookie, "buvid3"),
                dedeuserid=common.parse_cookie_data(bilibili_cookie, "DedeUserID"),
                ac_time_value=bilibili_ac_time_value,
            )
        elif config.get("bilibili", "login_type") == "手机扫码":
            credential = _login_with_qrcode(terminal=False)
        elif config.get("bilibili", "login_type") == "手机扫码-终端":
            credential = _login_with_qrcode(terminal=True)
        elif config.get("bilibili", "login_type") == "账号密码登录":
            logger.error(
                "账号密码登录需要极验验证码，bilibili-api 17.x 已不再支持，"
                "请改用 cookie 或 手机扫码 登录"
            )
            my_handle.abnormal_alarm_handle("platform")
            return
        elif config.get("bilibili", "login_type") == "不登录":
            credential = None
        else:
            credential = _login_with_qrcode(terminal=True)

        # 初始化 Bilibili 直播间
        room = live.LiveDanmaku(my_handle.get_room_id(), credential=credential)
    except Exception as e:
        logger.error(traceback.format_exc())
        my_handle.abnormal_alarm_handle("platform")
        # 连弹幕客户端对象都建不出来，这条线程没有可做的事：只结束线程，别碰进程
        return

    """
    DANMU_MSG: 用户发送弹幕
    SEND_GIFT: 礼物
    COMBO_SEND：礼物连击
    GUARD_BUY：续费大航海
    SUPER_CHAT_MESSAGE：醒目留言（SC）
    SUPER_CHAT_MESSAGE_JPN：醒目留言（带日语翻译？）
    WELCOME: 老爷进入房间
    WELCOME_GUARD: 房管进入房间
    NOTICE_MSG: 系统通知（全频道广播之类的）
    PREPARING: 直播准备中
    LIVE: 直播开始
    ROOM_REAL_TIME_MESSAGE_UPDATE: 粉丝数等更新
    ENTRY_EFFECT: 进场特效
    ROOM_RANK: 房间排名更新
    INTERACT_WORD: 用户进入直播间
    ACTIVITY_BANNER_UPDATE_V2: 好像是房间名旁边那个xx小时榜
    本模块自定义事件：
    VIEW: 直播间人气更新
    ALL: 所有事件
    DISCONNECT: 断开连接（传入连接状态码参数）
    TIMEOUT: 心跳响应超时
    VERIFICATION_SUCCESSFUL: 认证成功
    """

    @room.on("DANMU_MSG")
    async def _(event):
        """
        处理直播间弹幕事件
        :param event: 弹幕事件数据
        """

        # 闲时计数清零
        my_global.idle_time_auto_clear(config, "comment")

        content = event["data"]["info"][1]  # 获取弹幕内容
        username = event["data"]["info"][2][1]  # 获取发送弹幕的用户昵称

        logger.info(f"[{username}]: {content}")

        data = {"platform": platform, "username": username, "content": content}

        my_handle.process_data(data, "comment")

    @room.on("COMBO_SEND")
    async def _(event):
        """
        处理直播间礼物连击事件
        :param event: 礼物连击事件数据
        """
        my_global.idle_time_auto_clear(config, "gift")

        gift_name = event["data"]["data"]["gift_name"]
        username = event["data"]["data"]["uname"]
        # 礼物数量
        combo_num = event["data"]["data"]["combo_num"]
        # 总金额
        combo_total_coin = event["data"]["data"]["combo_total_coin"]

        logger.info(
            f"用户：{username} 赠送 {combo_num} 个 {gift_name}，总计 {combo_total_coin}电池"
        )

        data = {
            "platform": platform,
            "gift_name": gift_name,
            "username": username,
            "num": combo_num,
            "unit_price": combo_total_coin / combo_num / 1000,
            "total_price": combo_total_coin / 1000,
        }

        my_handle.process_data(data, "gift")

    @room.on("SEND_GIFT")
    async def _(event):
        """
        处理直播间礼物事件
        :param event: 礼物事件数据
        """
        my_global.idle_time_auto_clear(config, "gift")

        # logger.info(event)

        gift_name = event["data"]["data"]["giftName"]
        username = event["data"]["data"]["uname"]
        # 礼物数量
        num = event["data"]["data"]["num"]
        # 总金额
        combo_total_coin = event["data"]["data"]["combo_total_coin"]
        # 单个礼物金额
        discount_price = event["data"]["data"]["discount_price"]

        logger.info(
            f"用户：{username} 赠送 {num} 个 {gift_name}，单价 {discount_price}电池，总计 {combo_total_coin}电池"
        )

        data = {
            "platform": platform,
            "gift_name": gift_name,
            "username": username,
            "num": num,
            "unit_price": discount_price / 1000,
            "total_price": combo_total_coin / 1000,
        }

        my_handle.process_data(data, "gift")

    @room.on("GUARD_BUY")
    async def _(event):
        """
        处理直播间续费大航海事件
        :param event: 续费大航海事件数据
        """

        logger.info(event)

    @room.on("SUPER_CHAT_MESSAGE")
    async def _(event):
        """
        处理直播间醒目留言（SC）事件
        :param event: 醒目留言（SC）事件数据
        """
        my_global.idle_time_auto_clear(config, "gift")

        message = event["data"]["data"]["message"]
        uname = event["data"]["data"]["user_info"]["uname"]
        price = event["data"]["data"]["price"]

        logger.info(f"用户：{uname} 发送 {price}元 SC：{message}")

        data = {
            "platform": platform,
            "gift_name": "SC",
            "username": uname,
            "num": 1,
            "unit_price": price,
            "total_price": price,
            "content": message,
        }

        my_handle.process_data(data, "gift")

        my_handle.process_data(data, "comment")

    @room.on("INTERACT_WORD")
    async def _(event):
        """
        处理直播间用户进入直播间事件
        :param event: 用户进入直播间事件数据
        """

        my_global.idle_time_auto_clear(config, "entrance")

        username = event["data"]["data"]["uname"]

        logger.info(f"用户：{username} 进入直播间")

        # 添加用户名到最新的用户名列表
        my_global.add_username_to_last_username_list(username)

        data = {"platform": platform, "username": username, "content": "进入直播间"}

        my_handle.process_data(data, "entrance")

    # @room.on('WELCOME')
    # async def _(event):
    #     """
    #     处理直播间老爷进入房间事件
    #     :param event: 老爷进入房间事件数据
    #     """

    #     logger.info(event)

    # @room.on('WELCOME_GUARD')
    # async def _(event):
    #     """
    #     处理直播间房管进入房间事件
    #     :param event: 房管进入房间事件数据
    #     """

    #     logger.info(event)

    # 库内部本来就会在多台弹幕服务器之间重试，真的放弃了（主播下播、长时间断网）才回到
    # 这里。以前是 finally + os._exit(0)，等于 B 站一路断开就把音频、webui 和其他平台的
    # 监听一起带走。改成退避重连，只管这条线程。
    # __main__ 跑完时库的 status 已是 CLOSED/ERROR，对同一个 room 再 connect 一次是合法的，
    # 而六个 handler 注册在 room 对象上、这里不会重复注册。
    while True:
        try:
            # 启动 Bilibili 直播间连接
            sync(room.connect())
        except KeyboardInterrupt:
            logger.warning("程序被强行退出")
            return
        except Exception:
            logger.error(traceback.format_exc())
            logger.warning("关闭连接...可能是直播间号配置有误或者其他原因导致的")

        logger.warning("60 秒后重连哔哩哔哩直播间")
        time.sleep(60)