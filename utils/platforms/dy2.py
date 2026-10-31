from protobuf.douyin import *
import gzip
import re
import time
import threading
import websocket
import json
import random
import traceback
import string
import requests

from utils.my_log import logger
import utils.my_global as my_global
from utils.config import Config

# 配置文件路径：和 utils/platforms/dy.py 一样用模块级变量，配置模板热切换要靠它记住当前用的是哪份
config_path = "config.json"
config = None


def start_listen(new_config, common, my_handle, platform: str):
    global config
    config = new_config

    # 支持 wss 连接
    if config.get("dy2", {}).get("use_wss", False):
        pass
    else:
        pass

    def generateMsToken(length=107):
        """
        产生请求头部cookie中的msToken字段，其实为随机的107位字符
        :param length:字符位数
        :return:msToken
        """
        random_str = ""
        base_str = string.ascii_letters + string.digits + "=_"
        _len = len(base_str) - 1
        for _ in range(length):
            random_str += base_str[random.randint(0, _len)]
        return random_str

    def generateTtwid():
        """
        产生请求头部cookie中的ttwid字段，访问抖音网页版直播间首页可以获取到响应cookie中的ttwid
        :return: ttwid
        """
        url = "https://live.douyin.com/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        try:
            response = requests.get(url, headers=headers, timeout=(10, 300))
            response.raise_for_status()
        except Exception as err:
            logger.info("【X】request the live url error: ", err)
        else:
            return response.cookies.get("ttwid")

    class DouyinLiveWebFetcher:
        def __init__(self, live_id):
            """
            直播间弹幕抓取对象
            :param live_id: 直播间的直播id，打开直播间web首页的链接如：https://live.douyin.com/261378947940，
                            其中的261378947940即是live_id
            """
            self.__ttwid = None
            self.__room_id = None
            self.is_connected = None
            self.live_id = live_id
            self.live_url = "https://live.douyin.com/"
            self.user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )

        def send_heartbeat(self, ws):

            def heartbeat():
                while True:
                    time.sleep(15)  # 每15秒发送一次心跳
                    if self.is_connected:
                        ws.send("hi")  # 使用实际的心跳消息格式
                    else:
                        logger.info("Connection lost, stopping heartbeat.")
                        return

            threading.Thread(target=heartbeat).start()

        def start(self):
            self._connectWebSocket()

        def stop(self):
            self.ws.close()

        @property
        def ttwid(self):
            """
            产生请求头部cookie中的ttwid字段，访问抖音网页版直播间首页可以获取到响应cookie中的ttwid
            :return: ttwid
            """
            if self.__ttwid:
                return self.__ttwid
            headers = {
                "User-Agent": self.user_agent,
            }
            try:
                response = requests.get(self.live_url, headers=headers, timeout=(10, 300))
                response.raise_for_status()
            except Exception as err:
                logger.info("【X】Request the live url error: ", err)
            else:
                self.__ttwid = response.cookies.get("ttwid")
                return self.__ttwid

        @property
        def room_id(self):
            """
            根据直播间的地址获取到真正的直播间roomId，有时会有错误，可以重试请求解决
            :return:room_id
            """
            if self.__room_id:
                return self.__room_id
            url = self.live_url + self.live_id
            headers = {
                "User-Agent": self.user_agent,
                "cookie": f"ttwid={self.ttwid}&msToken={generateMsToken()}; __ac_nonce=0123407cc00a9e438deb4",
            }
            try:
                response = requests.get(url, headers=headers, timeout=(10, 300))
                response.raise_for_status()
            except Exception as err:
                logger.error("【X】Request the live room url error: ", err)
                return None
            else:
                match = re.search(r'roomId\\":\\"(\d+)\\"', response.text)
                if match is None or len(match.groups()) < 1:
                    logger.error("【X】无法获取 真 roomId，可能是直播间号配置错了，或者被官方拉黑了")
                    return None

                self.__room_id = match.group(1)

                return self.__room_id

        def _connectWebSocket(self):
            """
            连接抖音直播间websocket服务器，请求直播间数据
            """
            wss = (
                f"wss://webcast3-ws-web-lq.douyin.com/webcast/im/push/v2/?"
                f"app_name=douyin_web&version_code=180800&webcast_sdk_version=1.3.0&update_version_code=1.3.0"
                f"&compress=gzip"
                f"&internal_ext=internal_src:dim|wss_push_room_id:{self.room_id}|wss_push_did:{self.room_id}"
                f"|dim_log_id:202302171547011A160A7BAA76660E13ED|fetch_time:1676620021641|seq:1|wss_info:0-1676"
                f"620021641-0-0|wrds_kvs:WebcastRoomStatsMessage-1676620020691146024_WebcastRoomRankMessage-167661"
                f"9972726895075_AudienceGiftSyncData-1676619980834317696_HighlightContainerSyncData-2&cursor=t-1676"
                f"620021641_r-1_d-1_u-1_h-1"
                f"&host=https://live.douyin.com&aid=6383&live_id=1"
                f"&did_rule=3&debug=false&endpoint=live_pc&support_wrds=1&"
                f"im_path=/webcast/im/fetch/&user_unique_id={self.room_id}&"
                f"device_platform=web&cookie_enabled=true&screen_width=1440&screen_height=900&browser_language=zh&"
                f"browser_platform=MacIntel&browser_name=Mozilla&"
                f"browser_version=5.0%20(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20(KHTML,%20"
                f"like%20Gecko)%20Chrome/110.0.0.0%20Safari/537.36&"
                f"browser_online=true&tz_name=Asia/Shanghai&identity=audience&"
                f"room_id={self.room_id}&heartbeatDuration=0&signature=00000000"
            )

            # 直接从直播间抓包ws，赋值url地址填这，在被官方拉黑的情况下用
            # wss = "wss://webcast5-ws-web-lq.douyin.com/webcast/im/push/v2/?app_name=douyin_web&version_code=180800&webcast_sdk_version=1.0.14-beta.0&update_version_code=1.0.14-beta.0&compress=gzip&device_platform=web&cookie_enabled=true&screen_width=2048&screen_height=1152&browser_language=zh-CN&browser_platform=Win32&browser_name=Mozilla&browser_version=5.0%20(Windows%20NT%2010.0;%20Win64;%20x64)%20AppleWebKit/537.36%20(KHTML,%20like%20Gecko)%20Chrome/126.0.0.0%20Safari/537.36%20Edg/126.0.0.0&browser_online=true&tz_name=Etc/GMT-8&cursor=h-7383323426352862262_t-1719063974519_r-1_d-1_u-1&internal_ext=internal_src:dim|wss_push_room_id:7383264938631973686|wss_push_did:7293153952199050788|first_req_ms:1719063974385|fetch_time:1719063974519|seq:1|wss_info:0-1719063974519-0-0|wrds_v:7383323492227230262&host=https://live.douyin.com&aid=6383&live_id=1&did_rule=3&endpoint=live_pc&support_wrds=1&user_unique_id=7293153952199050788&im_path=/webcast/im/fetch/&identity=audience&need_persist_msg_count=15&insert_task_id=&live_reason=&room_id=7383264938631973686&heartbeatDuration=0&signature=6DJMtCOOuubiYZP4"

            headers = {
                "cookie": f"ttwid={self.ttwid}",
                "user-agent": self.user_agent,
            }
            self.ws = websocket.WebSocketApp(
                wss,
                header=headers,
                on_open=self._wsOnOpen,
                on_message=self._wsOnMessage,
                on_error=self._wsOnError,
                on_close=self._wsOnClose,
            )
            try:
                self.ws.run_forever()
            except Exception:
                self.stop()
                raise

        def _wsOnOpen(self, ws):
            """
            连接建立成功
            """
            logger.info("WebSocket connected.")
            self.is_connected = True

        def _wsOnMessage(self, ws, message):
            """
            接收到数据
            :param ws: websocket实例
            :param message: 数据
            """

            # 根据proto结构体解析对象
            package = PushFrame().parse(message)
            response = Response().parse(gzip.decompress(package.payload))

            # 返回直播间服务器链接存活确认消息，便于持续获取数据
            if response.need_ack:
                ack = PushFrame(
                    log_id=package.log_id,
                    payload_type="ack",
                    payload=response.internal_ext.encode("utf-8"),
                ).SerializeToString()
                ws.send(ack, websocket.ABNF.OPCODE_BINARY)

            # 根据消息类别解析消息体
            for msg in response.messages_list:
                method = msg.method
                try:
                    {
                        "WebcastChatMessage": self._parseChatMsg,  # 聊天消息
                        "WebcastGiftMessage": self._parseGiftMsg,  # 礼物消息
                        "WebcastLikeMessage": self._parseLikeMsg,  # 点赞消息
                        "WebcastMemberMessage": self._parseMemberMsg,  # 进入直播间消息
                        "WebcastSocialMessage": self._parseSocialMsg,  # 关注消息
                        "WebcastRoomUserSeqMessage": self._parseRoomUserSeqMsg,  # 直播间统计
                        "WebcastFansclubMessage": self._parseFansclubMsg,  # 粉丝团消息
                        "WebcastControlMessage": self._parseControlMsg,  # 直播间状态消息
                        "WebcastEmojiChatMessage": self._parseEmojiChatMsg,  # 聊天表情包消息
                        "WebcastRoomStatsMessage": self._parseRoomStatsMsg,  # 直播间统计信息
                        "WebcastRoomMessage": self._parseRoomMsg,  # 直播间信息
                        "WebcastRoomRankMessage": self._parseRankMsg,  # 直播间排行榜信息
                    }.get(method)(msg.payload)
                except Exception:
                    pass

        def _wsOnError(self, ws, error):
            logger.info("WebSocket error: ", error)
            self.is_connected = False

        def _wsOnClose(self, ws):
            logger.info("WebSocket connection closed.")
            self.is_connected = False

        def _parseChatMsg(self, payload):
            """聊天消息"""
            message = ChatMessage().parse(payload)
            username = message.user.nick_name
            user_id = message.user.id
            content = message.content
            logger.info(f"【聊天msg】[{user_id}]{username}: {content}")

            data = {"platform": platform, "username": username, "content": content}

            # 闲时计数清零
            my_global.idle_time_auto_clear(config, "comment")

            my_handle.process_data(data, "comment")

        def _parseGiftMsg(self, payload):
            """礼物消息"""
            message = GiftMessage().parse(payload)
            username = message.user.nick_name
            gift_name = message.gift.name
            num = message.combo_count
            logger.info(f"【礼物msg】{username} 送出了 {gift_name}x{num}")

            try:
                # 暂时是写死的
                data_path = "data/抖音礼物价格表.json"

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
            combo_total_coin = num * discount_price

            data = {
                "platform": platform,
                "gift_name": gift_name,
                "username": username,
                "num": num,
                "unit_price": discount_price / 10,
                "total_price": combo_total_coin / 10,
            }

            # 闲时计数清零
            my_global.idle_time_auto_clear(config, "gift")

            my_handle.process_data(data, "gift")

        def _parseLikeMsg(self, payload):
            """点赞消息"""
            message = LikeMessage().parse(payload)
            user_name = message.user.nick_name
            count = message.count
            logger.info(f"【点赞msg】{user_name} 点了{count}个赞")

        def _parseMemberMsg(self, payload):
            """进入直播间消息"""
            message = MemberMessage().parse(payload)
            username = message.user.nick_name
            user_id = message.user.id
            gender = ["女", "男"][message.user.gender]
            logger.info(f"【进场msg】[{user_id}][{gender}]{username} 进入了直播间")

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

        def _parseSocialMsg(self, payload):
            """关注消息"""
            message = SocialMessage().parse(payload)
            username = message.user.nick_name
            user_id = message.user.id
            logger.info(f"【关注msg】[{user_id}]{username} 关注了主播")

            data = {"platform": platform, "username": username}

            # 闲时计数清零
            my_global.idle_time_auto_clear(config, "follow")

            my_handle.process_data(data, "follow")

        def _parseRoomUserSeqMsg(self, payload):
            """直播间统计"""
            global config, config_path
            message = RoomUserSeqMessage().parse(payload)
            OnlineUserCount = message.total
            total = message.total_pv_for_anchor
            logger.info(f"【统计msg】当前观看人数: {OnlineUserCount}, 累计观看人数: {total}")

            try:
                # {'OnlineUserCount': 50, 'TotalUserCount': 22003, 'TotalUserCountStr': '2.2万', 'OnlineUserCountStr': '50',
                # 'MsgId': 7260517442466662207, 'User': None, 'Content': '当前直播间人数 50，累计直播间人数 2.2万', 'RoomId': 7260415920948906807}
                # logger.info(f"data_json={data_json}")

                my_global.last_liveroom_data = {
                    "OnlineUserCount": OnlineUserCount,
                    "TotalUserCountStr": total,
                }

                # 是否开启了动态配置功能
                if config.get("trends_config", "enable"):
                    for path_config in config.get("trends_config", "path"):
                        online_num_min = int(path_config["online_num"].split("-")[0])
                        online_num_max = int(path_config["online_num"].split("-")[1])

                        # 判断在线人数是否在此范围内
                        if OnlineUserCount >= online_num_min and OnlineUserCount <= online_num_max:
                            logger.debug(f"当前配置文件：{path_config['path']}")
                            # 如果配置文件相同，则跳过
                            if config_path == path_config["path"]:
                                break

                            config_path = path_config["path"]
                            config = Config(config_path)

                            my_handle.reload_config(config_path)

                            logger.info(f"切换配置文件：{config_path}")

                            break
            except Exception:
                logger.error(traceback.format_exc())

            pass

        def _parseFansclubMsg(self, payload):
            """粉丝团消息"""
            message = FansclubMessage().parse(payload)
            content = message.content
            logger.info(f"【粉丝团msg】 {content}")

        def _parseEmojiChatMsg(self, payload):
            """聊天表情包消息"""
            message = EmojiChatMessage().parse(payload)
            emoji_id = message.emoji_id
            user = message.user
            common = message.common
            default_content = message.default_content
            logger.info(f"【聊天表情包id】 {emoji_id},user：{user},common:{common},default_content:{default_content}")

        def _parseRoomMsg(self, payload):
            message = RoomMessage().parse(payload)
            common = message.common
            room_id = common.room_id
            logger.info(f"【直播间msg】直播间id:{room_id}")

        def _parseRoomStatsMsg(self, payload):
            message = RoomStatsMessage().parse(payload)
            display_long = message.display_long
            logger.info(f"【直播间统计msg】{display_long}")

        def _parseRankMsg(self, payload):
            message = RoomRankMessage().parse(payload)
            ranks_list = message.ranks_list
            logger.info(f"【直播间排行榜msg】{ranks_list}")

        def _parseControlMsg(self, payload):
            """直播间状态消息"""
            message = ControlMessage().parse(payload)

            if message.status == 3:
                logger.info("直播间已结束")
                self.stop()

    config_room_id = my_handle.get_room_id()
    DouyinLiveWebFetcher(config_room_id).start()
