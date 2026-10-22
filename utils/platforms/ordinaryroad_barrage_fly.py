from asyncio import Event
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import AsyncGenerator, Tuple

from reactivestreams.subscriber import Subscriber
from reactivestreams.subscription import Subscription
from rsocket.helpers import single_transport_provider
from rsocket.payload import Payload
from rsocket.rsocket_client import RSocketClient
from rsocket.streams.stream_from_async_generator import StreamFromAsyncGenerator
from rsocket.transports.aiohttp_websocket import TransportAioHttpClient

import json
import aiohttp
import asyncio
import traceback

from utils.my_log import logger
import utils.my_global as my_global

def start_listen(config, common, my_handle, platform: str):
    subscribe_payload_json = {
        "data": {
            "taskIds": [],
            "cmd": "SUBSCRIBE"
        }
    }


    class ChannelSubscriber(Subscriber):
        def __init__(self, wait_for_responder_complete: Event) -> None:
            super().__init__()
            self.subscription = None
            self._wait_for_responder_complete = wait_for_responder_complete

        def on_subscribe(self, subscription: Subscription):
            self.subscription = subscription
            self.subscription.request(0x7FFFFFFF)

        # TODO 收到消息回调
        def on_next(self, value: Payload, is_complete=False):
            try:
                msg_dto = json.loads(value.data)
                if type(msg_dto) != dict:
                    return
                msg_type = msg_dto.get('type')
                # 直接输出
                if msg_type == "DANMU":
                    msg = msg_dto['msg']
                    # logger.info(
                    #     f"{msg_dto['roomId']} 收到弹幕 {str(msg['badgeLevel']) + str(msg['badgeName']) if msg['badgeLevel'] != 0 else ''} {msg['username']}({str(msg['uid'])})：{msg['content']}"
                    # )
                    username = msg['username']
                    content = msg['content']
                    logger.info(f"【让弹幕飞-{msg_dto['platform']}-{msg_dto['roomId']}】 [{username}]: {content}")

                    data = {
                        "platform": platform,
                        "username": username,
                        "content": content,
                    }

                    # 闲时计数清零
                    my_global.idle_time_auto_clear(config, "comment")

                    my_handle.process_data(data, "comment")
                elif msg_type == "GIFT":
                    msg = msg_dto['msg']
                    logger.debug(msg)
                    # logger.info(
                    #     f"{msg_dto['roomId']} 收到礼物 {str(msg['badgeLevel']) + str(msg['badgeName']) if msg['badgeLevel'] != 0 else ''} {msg['username']}({str(msg['uid'])}) {str(msg['data']['action']) if msg.get('data') is not None and msg.get('data').get('action') is not None else '赠送'} {msg['giftName']}({str(msg['giftId'])})x{str(msg['giftCount'])}({str(msg['giftPrice'])})"
                    # )
                    username = msg['username']
                    gift_name = msg['giftName']
                    combo_num = msg['giftCount']
                    combo_total_coin = combo_num * msg['giftPrice']
                    logger.info(
                        f"【让弹幕飞-{msg_dto['platform']}-{msg_dto['roomId']}】 [{username}] 赠送 {combo_num} 个 {gift_name}，总计 {combo_total_coin}"
                    )

                    # TODO： 金额换算
                    data = {
                        "platform": platform,
                        "gift_name": gift_name,
                        "username": username,
                        # "user_face": user_face,
                        "num": combo_num,
                        "unit_price": combo_total_coin / combo_num,
                        "total_price": combo_total_coin,
                    }

                    # 闲时计数清零
                    my_global.idle_time_auto_clear(config, "gift")

                    my_handle.process_data(data, "gift")
                elif msg_type == "ENTER_ROOM":
                    msg = msg_dto['msg']
                    username = msg['username']
                    logger.info(f"【让弹幕飞-{msg_dto['platform']}-{msg_dto['roomId']}】 欢迎 {username} 进入直播间")

                    data = {
                        "platform": platform,
                        "username": username,
                        "content": "进入直播间",
                    }

                    # 添加用户名到最新的用户名列表
                    my_global.add_username_to_last_username_list(username)

                    # 闲时计数清零
                    my_global.idle_time_auto_clear(config, "entrance")

                    my_handle.process_data(data, "entrance")
                elif msg_type == "LIKE":
                    msg = msg_dto['msg']
                    logger.debug(msg)
                    username = msg['username']
                    clickCount = msg['clickCount']
                    logger.info(f"【让弹幕飞-{msg_dto['platform']}-{msg_dto['roomId']}】 [{username}] 点赞了 {clickCount} 次")
                # 无用消息丢弃
                elif msg_type in ["inter_h5_game_data_update"]:
                    pass
                else:
                    # 刚连接上ws收到的消息
                    if "status" in msg_dto:
                        pass
                    else:
                        logger.debug(msg_dto)
                        logger.debug(f"【让弹幕飞-{msg_dto['platform']}-{msg_dto['roomId']}】 收到消息 " + json.dumps(msg_dto))
                if is_complete:
                    self._wait_for_responder_complete.set()
            except Exception as e:
                logger.error(traceback.format_exc())

        def on_error(self, exception: Exception):
            logger.error('Error from server on channel' + str(exception))
            self._wait_for_responder_complete.set()

        def on_complete(self):
            logger.info('Completed from server on channel')
            self._wait_for_responder_complete.set()


    @asynccontextmanager
    async def connect(websocket_uri):
        """
        创建一个Client，建立连接并return
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(websocket_uri) as websocket:
                    async with RSocketClient(
                            single_transport_provider(TransportAioHttpClient(websocket=websocket)),
                            keep_alive_period=timedelta(seconds=30),
                            max_lifetime_period=timedelta(days=1)
                    ) as client:
                        yield client
        except Exception as e:
            logger.error(traceback.format_exc())

    async def main(websocket_uri):
        try:
            # 1 建立连接
            async with connect(websocket_uri) as client:
                # 阻塞等待Channel关闭事件
                channel_completion_event = Event()

                # 定义Client向Channel发送消息的Publisher
                # Python没有匿名内部类，这里定义一个方法作为参数，传给StreamFromAsyncGenerator类
                async def generator() -> AsyncGenerator[Tuple[Payload, bool], None]:
                    # 2 发送订阅Task的请求
                    # Payload：Client通过Channel向Server发送的消息，False表示不需要关闭Channel
                    yield Payload(
                        data=json.dumps(subscribe_payload_json["data"]).encode()
                    ), False
                    # 发送了一条订阅消息后直接暂停发送即可
                    await Event().wait()

                stream = StreamFromAsyncGenerator(generator)

                # Client请求一个Channel，Payload留空，turn StreamHandler
                requested = client.request_channel(Payload(), stream)

                # 3 订阅Channel，ChannelSubscriber用于处理Server通过Channel回复的消息
                requested.subscribe(ChannelSubscriber(channel_completion_event))

                await channel_completion_event.wait()
        except Exception as e:
            logger.error(traceback.format_exc())
            my_handle.abnormal_alarm_handle("platform")

    if config.get("ordinaryroad_barrage_fly", "taskIds") == []:
        logger.error("请先配置 让弹幕飞 的监听任务ID列表！")
    else:
        subscribe_payload_json["data"]["taskIds"] = config.get("ordinaryroad_barrage_fly", "taskIds") 
        logger.info(subscribe_payload_json)
        asyncio.run(main(config.get("ordinaryroad_barrage_fly", "ws_ip_port")))