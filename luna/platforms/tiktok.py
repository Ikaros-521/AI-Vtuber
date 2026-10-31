"""
tiktok
"""

import time
import traceback
import json

from TikTokLive import TikTokLiveClient
from TikTokLive.events import (
    CommentEvent,
    ConnectEvent,
    DisconnectEvent,
    JoinEvent,
    GiftEvent,
    FollowEvent,
)
# from TikTokLive.client.errors import LiveNotFound

from luna.infra.my_log import logger
import luna.infra.my_global as my_global


def start_listen(config, common, my_handle, platform: str):
    # 比如直播间是 https://www.tiktok.com/@username/live 那么room_id就是 username，其实就是用户唯一ID
    room_id = my_handle.get_room_id()

    proxys = {
        "http://": "http://127.0.0.1:10809",
        "https://": "http://127.0.0.1:10809",
    }

    proxys = None

    # 代理软件开启TUN模式进行代理，由于库的ws不走传入的代理参数，只能靠代理软件全代理了
    client: TikTokLiveClient = TikTokLiveClient(unique_id=f"@{room_id}", web_proxy=proxys, ws_proxy=proxys)

    def register_events():
        # Define how you want to handle specific events via decorator
        @client.on(ConnectEvent)
        async def on_connect(_: ConnectEvent):
            logger.info(f"连接到 房间ID:{client.room_id}")

        @client.on(DisconnectEvent)
        async def on_disconnect(event: DisconnectEvent):
            # 只记日志：重连交给 start_client() 的外层循环。以前这里直接调 start_client()，
            # 等于在事件循环里再跑一次阻塞的 client.run()
            logger.info("断开连接，等待重连")

        @client.on(JoinEvent)
        async def on_join(event: JoinEvent):
            my_global.idle_time_auto_clear(config, "entrance")

            username = event.user.nickname

            logger.info(f"[🚹🚺直播间成员加入消息] 欢迎 {username} 进入直播间")

            data = {
                "platform": platform,
                "username": username,
                "content": "进入直播间",
            }

            # 添加用户名到最新的用户名列表
            my_global.add_username_to_last_username_list(username)

            my_handle.process_data(data, "entrance")

        # Notice no decorator?
        @client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            # 闲时计数清零
            my_global.idle_time_auto_clear(config, "comment")

            username = event.user.nickname
            content = event.comment

            logger.info(f"[📧直播间弹幕消息] [{username}]：{content}")

            data = {"platform": platform, "username": username, "content": content}

            my_handle.process_data(data, "comment")

        @client.on(GiftEvent)
        async def on_gift(event: GiftEvent):
            """
            This is an example for the "gift" event to show you how to read gift data properly.

            Important Note:

            Gifts of type 1 can have streaks, so we need to check that the streak has ended
            If the gift type isn't 1, it can't repeat. Therefore, we can go straight to logger.infoing

            """
            my_global.idle_time_auto_clear(config, "gift")

            # Streakable gift & streak is over
            if event.gift.streakable and not event.gift.streaking:
                # 礼物重复数量
                repeat_count = event.gift.count

            # Non-streakable gift
            elif not event.gift.streakable:
                # 礼物重复数量
                repeat_count = 1

            # 连击还在进行中：这一下不播报，等 streaking 变 False 的那条事件带总个数，
            # 否则 repeat_count 根本没被赋值，下面一用就是 UnboundLocalError，礼物整条丢掉
            else:
                return

            gift_name = event.gift.info.name
            username = event.user.nickname
            # 礼物数量
            num = 1

            try:
                # 暂时是写死的
                data_path = "data/tiktok礼物价格表.json"

                # 读取JSON文件
                with open(data_path, encoding="utf-8") as file:
                    # 解析JSON数据
                    data_json = json.load(file)

                if gift_name in data_json:
                    # 单个礼物金额 需要自己维护礼物价值表
                    discount_price = data_json[gift_name]
                else:
                    logger.warning(f"数据文件：{data_path} 中，没有 {gift_name} 对应的价值，请手动补充数据")
                    discount_price = 1
            except Exception:
                logger.error(traceback.format_exc())
                discount_price = 1

            # 总金额
            combo_total_coin = repeat_count * discount_price

            logger.info(
                f"[🎁直播间礼物消息] 用户：{username} 赠送 {num} 个 {gift_name}，单价 {discount_price}抖币，总计 {combo_total_coin}抖币"
            )

            data = {
                "platform": platform,
                "gift_name": gift_name,
                "username": username,
                "num": num,
                "unit_price": discount_price / 10,
                "total_price": combo_total_coin / 10,
            }

            my_handle.process_data(data, "gift")

        @client.on(FollowEvent)
        async def on_follow(event: FollowEvent):
            my_global.idle_time_auto_clear(config, "follow")

            username = event.user.nickname

            logger.info(f"[➕直播间关注消息] 感谢 {username} 的关注")

            data = {"platform": platform, "username": username}

            my_handle.process_data(data, "follow")

    def start_client():
        # 原来这里 except 里直接再调一次 start_client()：既会把六个 handler 重新注册一遍
        # （之后每条弹幕都被处理多次），又会一层层递归下去。改成注册一次、连接失败就地重试。
        while True:
            try:
                client.stop()
                logger.info(f"连接{room_id}中...")
                client.run()
            except Exception:
                logger.info(f"用户ID: @{client.unique_id} 好像不在线捏, 1分钟后重试...")
                time.sleep(60)
                continue
            # run() 正常返回一般是直播断开/结束，按原语义继续等下一次
            logger.info("连接已关闭，10秒后重连")
            time.sleep(10)

    register_events()
    start_client()
