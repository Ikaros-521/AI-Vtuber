import _thread
import binascii
import gzip
import json
import logging
import re
import time
import requests
import websocket
import urllib
from protobuf_inspector.types import StandardParser
from google.protobuf import json_format
from dy_pb2 import PushFrame
from dy_pb2 import Response
from dy_pb2 import MatchAgainstScoreMessage
from dy_pb2 import LikeMessage
from dy_pb2 import MemberMessage
from dy_pb2 import GiftMessage
from dy_pb2 import ChatMessage
from dy_pb2 import SocialMessage
from dy_pb2 import RoomUserSeqMessage
from dy_pb2 import UpdateFanTicketMessage
from dy_pb2 import CommonTextMessage

# 导入所需的库
import json, re

from utils.my_handle import My_handle


my_handle = My_handle("config.json", None)
if my_handle is None:
    print("程序初始化失败！")
    exit(0)


liveRoomId = None
ttwid = None
roomStore = None
liveRoomTitle = None
proxy = None


def onMessage(ws: websocket.WebSocketApp, message: bytes):
    wssPackage = PushFrame()
    wssPackage.ParseFromString(message)
    logId = wssPackage.logId
    decompressed = gzip.decompress(wssPackage.payload)
    payloadPackage = Response()
    payloadPackage.ParseFromString(decompressed)
    # 发送ack包
    if payloadPackage.needAck:
        sendAck(ws, logId, payloadPackage.internalExt)
    for msg in payloadPackage.messagesList:
        if msg.method == 'WebcastMatchAgainstScoreMessage':
            unPackMatchAgainstScoreMessage(msg.payload)
            continue

        if msg.method == 'WebcastLikeMessage':
            unPackWebcastLikeMessage(msg.payload)
            continue

        if msg.method == 'WebcastMemberMessage':
            unPackWebcastMemberMessage(msg.payload)
            continue
        if msg.method == 'WebcastGiftMessage':
            unPackWebcastGiftMessage(msg.payload)
            continue
        if msg.method == 'WebcastChatMessage':
            data = unPackWebcastChatMessage(msg.payload)

            # print(data)

            content = data['content']
            user_name = data['user']['nickName']

            my_handle.commit_handle(user_name, content)

            continue

        if msg.method == 'WebcastSocialMessage':
            unPackWebcastSocialMessage(msg.payload)
            continue

        if msg.method == 'WebcastRoomUserSeqMessage':
            unPackWebcastRoomUserSeqMessage(msg.payload)
            continue

        if msg.method == 'WebcastUpdateFanTicketMessage':
            unPackWebcastUpdateFanTicketMessage(msg.payload)
            continue

        if msg.method == 'WebcastCommonTextMessage':
            unPackWebcastCommonTextMessage(msg.payload)
            continue

        logging.info('[onMessage] [⌛️方法' + msg.method + '等待解析～] [房间Id：' + liveRoomId + ']')


def unPackWebcastCommonTextMessage(data):
    commonTextMessage = CommonTextMessage()
    commonTextMessage.ParseFromString(data)
    data = json_format.MessageToDict(commonTextMessage, preserving_proto_field_name=True)
    log = json.dumps(data, ensure_ascii=False)
    # logging.info('[unPackWebcastCommonTextMessage] [] [房间Id：' + liveRoomId + '] ｜ ' + log)
    return data


def unPackWebcastUpdateFanTicketMessage(data):
    updateFanTicketMessage = UpdateFanTicketMessage()
    updateFanTicketMessage.ParseFromString(data)
    data = json_format.MessageToDict(updateFanTicketMessage, preserving_proto_field_name=True)
    log = json.dumps(data, ensure_ascii=False)
    # logging.info('[unPackWebcastUpdateFanTicketMessage] [] [房间Id：' + liveRoomId + '] ｜ ' + log)
    return data


def unPackWebcastRoomUserSeqMessage(data):
    roomUserSeqMessage = RoomUserSeqMessage()
    roomUserSeqMessage.ParseFromString(data)
    data = json_format.MessageToDict(roomUserSeqMessage, preserving_proto_field_name=True)
    log = json.dumps(data, ensure_ascii=False)
    logging.info('[unPackWebcastRoomUserSeqMessage] [] [房间Id：' + liveRoomId + '] ｜ ' + log)
    return data


def unPackWebcastSocialMessage(data):
    socialMessage = SocialMessage()
    socialMessage.ParseFromString(data)
    data = json_format.MessageToDict(socialMessage, preserving_proto_field_name=True)
    log = json.dumps(data, ensure_ascii=False)
    # logging.info('[unPackWebcastSocialMessage] [➕直播间关注消息] [房间Id：' + liveRoomId + '] ｜ ' + log)
    return data


# 普通消息
def unPackWebcastChatMessage(data):
    chatMessage = ChatMessage()
    chatMessage.ParseFromString(data)
    data = json_format.MessageToDict(chatMessage, preserving_proto_field_name=True)
    logging.info('[unPackWebcastChatMessage] [📧直播间弹幕消息] [房间Id：' + liveRoomId + '] ｜ ' + data['content'])
    # logging.info('[unPackWebcastChatMessage] [📧直播间弹幕消息] [房间Id：' + liveRoomId + '] ｜ ' + json.dumps(data))
    return data


# 礼物消息
def unPackWebcastGiftMessage(data):
    giftMessage = GiftMessage()
    giftMessage.ParseFromString(data)
    data = json_format.MessageToDict(giftMessage, preserving_proto_field_name=True)
    log = json.dumps(data, ensure_ascii=False)
    # logging.info('[unPackWebcastGiftMessage] [🎁直播间礼物消息] [房间Id：' + liveRoomId + '] ｜ ' + log)
    return data


# xx成员进入直播间消息
def unPackWebcastMemberMessage(data):
    memberMessage = MemberMessage()
    memberMessage.ParseFromString(data)
    data = json_format.MessageToDict(memberMessage, preserving_proto_field_name=True)
    log = json.dumps(data, ensure_ascii=False)
    # logging.info('[unPackWebcastMemberMessage] [🚹🚺直播间成员加入消息] [房间Id：' + liveRoomId + '] ｜ ' + log)
    return data


# 点赞
def unPackWebcastLikeMessage(data):
    likeMessage = LikeMessage()
    likeMessage.ParseFromString(data)
    data = json_format.MessageToDict(likeMessage, preserving_proto_field_name=True)
    log = json.dumps(data, ensure_ascii=False)
    # logging.info('[unPackWebcastLikeMessage] [👍直播间点赞消息] [房间Id：' + liveRoomId + '] ｜ ' + log)
    return data


# 解析WebcastMatchAgainstScoreMessage消息包体
def unPackMatchAgainstScoreMessage(data):
    matchAgainstScoreMessage = MatchAgainstScoreMessage()
    matchAgainstScoreMessage.ParseFromString(data)
    data = json_format.MessageToDict(matchAgainstScoreMessage, preserving_proto_field_name=True)
    log = json.dumps(data, ensure_ascii=False)
    # logging.info('[unPackMatchAgainstScoreMessage] [🤷不知道是啥的消息] [房间Id：' + liveRoomId + '] ｜ ' + log)
    return data


# 发送Ack请求
def sendAck(ws, logId, internalExt):
    obj = PushFrame()
    obj.payloadType = 'ack'
    obj.logId = logId
    obj.payloadType = internalExt
    data = obj.SerializeToString()
    ws.send(data, websocket.ABNF.OPCODE_BINARY)
    # logging.info('[sendAck] [🌟发送Ack] [房间Id：' + liveRoomId + '] ====> 房间🏖标题【' + liveRoomTitle + '】')


def onError(ws, error):
    logging.error('[onError] [webSocket Error事件] [房间Id：' + liveRoomId + ']')


def onClose(ws, a, b):
    logging.info('[onClose] [webSocket Close事件] [房间Id：' + liveRoomId + ']')


def onOpen(ws):
    _thread.start_new_thread(ping, (ws,))
    logging.info('[onOpen] [webSocket Open事件] [房间Id：' + liveRoomId + ']')


# 发送ping心跳包
def ping(ws):
    while True:
        obj = PushFrame()
        obj.payloadType = 'hb'
        data = obj.SerializeToString()
        ws.send(data, websocket.ABNF.OPCODE_BINARY)
        logging.info('[ping] [💗发送ping心跳] [房间Id：' + liveRoomId + '] ====> 房间🏖标题【' + liveRoomTitle + '】')
        time.sleep(10)


def wssServerStart(roomId):
    global liveRoomId
    liveRoomId = roomId
    websocket.enableTrace(False)
    webSocketUrl = 'wss://webcast3-ws-web-lq.douyin.com/webcast/im/push/v2/?app_name=douyin_web&version_code=180800&webcast_sdk_version=1.3.0&update_version_code=1.3.0&compress=gzip&internal_ext=internal_src:dim|wss_push_room_id:'+liveRoomId+'|wss_push_did:7188358506633528844|dim_log_id:20230521093022204E5B327EF20D5CDFC6|fetch_time:1684632622323|seq:1|wss_info:0-1684632622323-0-0|wrds_kvs:WebcastRoomRankMessage-1684632106402346965_WebcastRoomStatsMessage-1684632616357153318&cursor=t-1684632622323_r-1_d-1_u-1_h-1&host=https://live.douyin.com&aid=6383&live_id=1&did_rule=3&debug=false&maxCacheMessageNumber=20&endpoint=live_pc&support_wrds=1&im_path=/webcast/im/fetch/&user_unique_id=7188358506633528844&device_platform=web&cookie_enabled=true&screen_width=1440&screen_height=900&browser_language=zh&browser_platform=MacIntel&browser_name=Mozilla&browser_version=5.0%20(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20(KHTML,%20like%20Gecko)%20Chrome/113.0.0.0%20Safari/537.36&browser_online=true&tz_name=Asia/Shanghai&identity=audience&room_id='+liveRoomId+'&heartbeatDuration=0&signature=00000000'
    h = {
        'cookie': 'ttwid='+ttwid + \
                "__ac_nonce=063c22e0b00ef2187712a; __ac_signature=_02B4Z6wo00f01UZsilwAAIDC0rrRUTr27elGTI7AADJcqjRe1hQOZ"
                ".K4Q4FmO9daZqxwlf.5k4RomG9GZZgMXO3CvtvKJiy9txGxo4HWdJhcwlVYhBiKSGhWCrULSjQEPlsLZ8LgciLILIZO8f; "
                "%7Cd796439337e51fc553cfb64d79ef412b84b3eef18e9e19ebaa1287a829b90db8; douyin.com; "
                "passport_csrf_token=955106f18f323068c601a6918c27747d; "
                "passport_csrf_token_default=955106f18f323068c601a6918c27747d; "
                "s_v_web_id=verify_lcvfzyv4_BZabwp7p_r58g_4G5z_8KHs_lDuazCJCZ9uB; "
                "passport_assist_user"
                "=Cj2FisA1wsU1M6ZAOUfBxA5tt48uEnnpcfN8dtT3oivxC3hjFxm0iQwLvZkXjoCnZas0ias8qelCHfDmIZJ5GkgKPEal_vGBVAKPt3vk_68vkfwzRBgsf8APM87d_iaEiBj6_B9X0Gj7vjvTHA_1A0fF9m3QYysg3NS7vbf-ihDlxaYNGImv1lQiAQNaHWg4; n_mh=bUxOCHzZv5szT8QIHfxmgnjoVlZQ1kn7aM-ZW6ndDKY; sso_uid_tt=e1e48ca5f945784a59c3174e16176a61; sso_uid_tt_ss=e1e48ca5f945784a59c3174e16176a61; toutiao_sso_user=fba93355178fb80aafc02d05bfcd0a5c; toutiao_sso_user_ss=fba93355178fb80aafc02d05bfcd0a5c; sid_ucp_sso_v1=1.0.0-KDM0OWJmNzI2ZDQ1NjFmODJkMTY4Y2Q2MDAzMTIzY2FkMTc1YWUwYmQKHQik8Iy7gQMQ7tyIngYY7zEgDDCYxPfbBTgGQPQHGgJsZiIgZmJhOTMzNTUxNzhmYjgwYWFmYzAyZDA1YmZjZDBhNWM; ssid_ucp_sso_v1=1.0.0-KDM0OWJmNzI2ZDQ1NjFmODJkMTY4Y2Q2MDAzMTIzY2FkMTc1YWUwYmQKHQik8Iy7gQMQ7tyIngYY7zEgDDCYxPfbBTgGQPQHGgJsZiIgZmJhOTMzNTUxNzhmYjgwYWFmYzAyZDA1YmZjZDBhNWM; odin_tt=8547fef56c59daf11b0c15312d499833a2be72189dd6aad256dc07c950b8880c52ad37e717a99de93cc971ad3d80d88ffc1b4e6a10be0fd4f05d46ba29e91ac5; passport_auth_status=6929cca1c9119873a9d7fa528ccd5f37%2C; passport_auth_status_ss=6929cca1c9119873a9d7fa528ccd5f37%2C; uid_tt=8c0899f7528059e847f7eddad4210e5c; uid_tt_ss=8c0899f7528059e847f7eddad4210e5c; sid_tt=6c5a7be3caf51c935494a12b4f1c5c13; sessionid=6c5a7be3caf51c935494a12b4f1c5c13; sessionid_ss=6c5a7be3caf51c935494a12b4f1c5c13; LOGIN_STATUS=1; store-region=cn-hn; store-region-src=uid; sid_guard=6c5a7be3caf51c935494a12b4f1c5c13%7C1673670258%7C5183996%7CWed%2C+15-Mar-2023+04%3A24%3A14+GMT; sid_ucp_v1=1.0.0-KGZmOThhNTZlMThiOTEzMTI2MWI0MDIxZGM5MDUyNjVmZmVkMzVhMTgKFwik8Iy7gQMQ8tyIngYY7zEgDDgGQPQHGgJsZiIgNmM1YTdiZTNjYWY1MWM5MzU0OTRhMTJiNGYxYzVjMTM; ssid_ucp_v1=1.0.0-KGZmOThhNTZlMThiOTEzMTI2MWI0MDIxZGM5MDUyNjVmZmVkMzVhMTgKFwik8Iy7gQMQ8tyIngYY7zEgDDgGQPQHGgJsZiIgNmM1YTdiZTNjYWY1MWM5MzU0OTRhMTJiNGYxYzVjMTM; csrf_session_id=f8b3bae210355efd72d7b596b8d59786; tt_scid=yrq-tjQaXEaPz4kTP9WpqNwOnqVy13KMI.snGi6wnZp8P1hduQmhbtqsTOyIhz.O0bd1; download_guide=%223%2F20230114%22; VIDEO_FILTER_MEMO_SELECT=%7B%22expireTime%22%3A1674275671220%2C%22type%22%3A1%7D; strategyABtestKey=%221673670871.396%22; FOLLOW_NUMBER_YELLOW_POINT_INFO=%22MS4wLjABAAAAlc42G0Nktrm_CVQMfASabMRnI_6GlL2br1i7a8yqTEI%2F1673712000000%2F0%2F1673670871480%2F0%22; home_can_add_dy_2_desktop=%221%22; passport_fe_beating_status=true; msToken=veZvf1xerEu8qj_1IHeP6Tce5JyHlTLZf_YVSJCj5moDg72Q0821Vcqo4ylUrBP75wlGO2xO22kVG9fEsZvWcx6L6nUPhL6LFf6TtpXznJMEA7riXCgfInQgv70a3Go=; msToken=6j75IbD0uth58uE0p2svIf3-bGlzkqLnJ34RfGkr8Ooxgos99KHfw-4HzlJ26GI6C3uTwDUUIthFI0wUocJy2ZAMkpyPrUgGFgcshHRO3vw_kBc9yiZ-4EbErjwp8FI=",
        "origin": "https://www.douyin.com",
        "referer": "https://www.douyin.com/",
        # "sec-ch-ua": "\"Not_A Brand\";v=\"99\", \"Google Chrome\";v=\"109\", \"Chromium\";v=\"109\"",
        # "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"macOS\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "x-secsdk-csrf-token": "000100000001a4af956d5ea10b016b19ba5c287191937c2093fc6b603acc6ee5bed3a6354333173a12ca9498806f",
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    }
    # 创建一个长连接
    ws = websocket.WebSocketApp(
        webSocketUrl, on_message=onMessage, on_error=onError, on_close=onClose,
        on_open=onOpen,
        header=h
    )
    ws.run_forever()


def parseLiveRoomUrl(url):
    print(f"直播间地址：{url}")

    h = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
        'cookie': '__ac_nonce=0638733a400869171be51',
    }
    res = requests.get(url=url, headers=h, proxies=proxy)
    global ttwid, roomStore, liveRoomId, liveRoomTitle
    data = res.cookies.get_dict()
    # print(f"data={data}")
    ttwid = data['ttwid']
    res = res.text
    res = re.search(r'<script id="RENDER_DATA" type="application/json">(.*?)</script>', res)
    res = res.group(1)
    res = urllib.parse.unquote(res, encoding='utf-8', errors='replace')
    res = json.loads(res)
    # print(f"res={res}")
    roomStore = res['app']['initialState']['roomStore']
    liveRoomId = roomStore['roomInfo']['roomId']
    liveRoomTitle = roomStore['roomInfo']['room']['title']
    liveAnchorNickname = roomStore['roomInfo']['anchor']['nickname']

    print(f"直播间标题：{liveRoomTitle}\n播主：{liveAnchorNickname}\n直播间ID：{liveRoomId}")

    wssServerStart(liveRoomId)


def test():
    url = "https://www.douyin.com/aweme/v1/web/commit/follow/user/?device_platform=webapp&aid=6383&channel=channel_pc_web&pc_client_type=1&version_code=170400&version_name=17.4.0&cookie_enabled=true&screen_width=1440&screen_height=900&browser_language=zh&browser_platform=MacIntel&browser_name=Chrome&browser_version=109.0.0.0&browser_online=true&engine_name=Blink&engine_version=109.0.0.0&os_name=Mac+OS&os_version=10.15.7&cpu_core_num=8&device_memory=8&platform=PC&downlink=10&effective_type=4g&round_trip_time=50&webid=7188358506633528844&msToken=6j75IbD0uth58uE0p2svIf3-bGlzkqLnJ34RfGkr8Ooxgos99KHfw-4HzlJ26GI6C3uTwDUUIthFI0wUocJy2ZAMkpyPrUgGFgcshHRO3vw_kBc9yiZ-4EbErjwp8FI=&X-Bogus=DFSzswVYdOs9-MIISZ-yup7TlqtU"
    h = {
        "accept": "application/json, text/plain, */*",
        # "accept-encoding": "gzip, deflate, br",
        # "accept-language": "zh,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6",
        # "content-length": "26",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "cookie": "__ac_nonce=063c22e0b00ef2187712a; __ac_signature=_02B4Z6wo00f01UZsilwAAIDC0rrRUTr27elGTI7AADJcqjRe1hQOZ"
                ".K4Q4FmO9daZqxwlf.5k4RomG9GZZgMXO3CvtvKJiy9txGxo4HWdJhcwlVYhBiKSGhWCrULSjQEPlsLZ8LgciLILIZO8f; "
                "ttwid=1%7Cw5daZw41FpoZMR-XIJc-J_4yVhjVtBUBWUPO-v6khXo%7C1673670155"
                "%7Cd796439337e51fc553cfb64d79ef412b84b3eef18e9e19ebaa1287a829b90db8; douyin.com; "
                "passport_csrf_token=955106f18f323068c601a6918c27747d; "
                "passport_csrf_token_default=955106f18f323068c601a6918c27747d; "
                "s_v_web_id=verify_lcvfzyv4_BZabwp7p_r58g_4G5z_8KHs_lDuazCJCZ9uB; "
                "passport_assist_user"
                "=Cj2FisA1wsU1M6ZAOUfBxA5tt48uEnnpcfN8dtT3oivxC3hjFxm0iQwLvZkXjoCnZas0ias8qelCHfDmIZJ5GkgKPEal_vGBVAKPt3vk_68vkfwzRBgsf8APM87d_iaEiBj6_B9X0Gj7vjvTHA_1A0fF9m3QYysg3NS7vbf-ihDlxaYNGImv1lQiAQNaHWg4; n_mh=bUxOCHzZv5szT8QIHfxmgnjoVlZQ1kn7aM-ZW6ndDKY; sso_uid_tt=e1e48ca5f945784a59c3174e16176a61; sso_uid_tt_ss=e1e48ca5f945784a59c3174e16176a61; toutiao_sso_user=fba93355178fb80aafc02d05bfcd0a5c; toutiao_sso_user_ss=fba93355178fb80aafc02d05bfcd0a5c; sid_ucp_sso_v1=1.0.0-KDM0OWJmNzI2ZDQ1NjFmODJkMTY4Y2Q2MDAzMTIzY2FkMTc1YWUwYmQKHQik8Iy7gQMQ7tyIngYY7zEgDDCYxPfbBTgGQPQHGgJsZiIgZmJhOTMzNTUxNzhmYjgwYWFmYzAyZDA1YmZjZDBhNWM; ssid_ucp_sso_v1=1.0.0-KDM0OWJmNzI2ZDQ1NjFmODJkMTY4Y2Q2MDAzMTIzY2FkMTc1YWUwYmQKHQik8Iy7gQMQ7tyIngYY7zEgDDCYxPfbBTgGQPQHGgJsZiIgZmJhOTMzNTUxNzhmYjgwYWFmYzAyZDA1YmZjZDBhNWM; odin_tt=8547fef56c59daf11b0c15312d499833a2be72189dd6aad256dc07c950b8880c52ad37e717a99de93cc971ad3d80d88ffc1b4e6a10be0fd4f05d46ba29e91ac5; passport_auth_status=6929cca1c9119873a9d7fa528ccd5f37%2C; passport_auth_status_ss=6929cca1c9119873a9d7fa528ccd5f37%2C; uid_tt=8c0899f7528059e847f7eddad4210e5c; uid_tt_ss=8c0899f7528059e847f7eddad4210e5c; sid_tt=6c5a7be3caf51c935494a12b4f1c5c13; sessionid=6c5a7be3caf51c935494a12b4f1c5c13; sessionid_ss=6c5a7be3caf51c935494a12b4f1c5c13; LOGIN_STATUS=1; store-region=cn-hn; store-region-src=uid; sid_guard=6c5a7be3caf51c935494a12b4f1c5c13%7C1673670258%7C5183996%7CWed%2C+15-Mar-2023+04%3A24%3A14+GMT; sid_ucp_v1=1.0.0-KGZmOThhNTZlMThiOTEzMTI2MWI0MDIxZGM5MDUyNjVmZmVkMzVhMTgKFwik8Iy7gQMQ8tyIngYY7zEgDDgGQPQHGgJsZiIgNmM1YTdiZTNjYWY1MWM5MzU0OTRhMTJiNGYxYzVjMTM; ssid_ucp_v1=1.0.0-KGZmOThhNTZlMThiOTEzMTI2MWI0MDIxZGM5MDUyNjVmZmVkMzVhMTgKFwik8Iy7gQMQ8tyIngYY7zEgDDgGQPQHGgJsZiIgNmM1YTdiZTNjYWY1MWM5MzU0OTRhMTJiNGYxYzVjMTM; csrf_session_id=f8b3bae210355efd72d7b596b8d59786; tt_scid=yrq-tjQaXEaPz4kTP9WpqNwOnqVy13KMI.snGi6wnZp8P1hduQmhbtqsTOyIhz.O0bd1; download_guide=%223%2F20230114%22; VIDEO_FILTER_MEMO_SELECT=%7B%22expireTime%22%3A1674275671220%2C%22type%22%3A1%7D; strategyABtestKey=%221673670871.396%22; FOLLOW_NUMBER_YELLOW_POINT_INFO=%22MS4wLjABAAAAlc42G0Nktrm_CVQMfASabMRnI_6GlL2br1i7a8yqTEI%2F1673712000000%2F0%2F1673670871480%2F0%22; home_can_add_dy_2_desktop=%221%22; passport_fe_beating_status=true; msToken=veZvf1xerEu8qj_1IHeP6Tce5JyHlTLZf_YVSJCj5moDg72Q0821Vcqo4ylUrBP75wlGO2xO22kVG9fEsZvWcx6L6nUPhL6LFf6TtpXznJMEA7riXCgfInQgv70a3Go=; msToken=6j75IbD0uth58uE0p2svIf3-bGlzkqLnJ34RfGkr8Ooxgos99KHfw-4HzlJ26GI6C3uTwDUUIthFI0wUocJy2ZAMkpyPrUgGFgcshHRO3vw_kBc9yiZ-4EbErjwp8FI=",
        "origin": "https://www.douyin.com",
        "referer": "https://www.douyin.com/",
        # "sec-ch-ua": "\"Not_A Brand\";v=\"99\", \"Google Chrome\";v=\"109\", \"Chromium\";v=\"109\"",
        # "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"macOS\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "x-secsdk-csrf-token": "000100000001a4af956d5ea10b016b19ba5c287191937c2093fc6b603acc6ee5bed3a6354333173a12ca9498806f"
    }
    data = "type=1&user_id=93865343726"
    # res = requests.post(url=url, data=data, headers=h, proxies=proxy)
    # print(res)
    res = requests.post(url=url, data=data, headers=h, proxies=proxy).json()
    print(res)


# 十六进制字符串转protobuf格式 （用于快手网页websocket调试分析包体结构）
def hexStrToProtobuf(hexStr):
    # 示例数据
    # hexStr = '08d40210011aeb250a8e010a81010a0b66666731343535323939391206e68595e799bd1a6a68747470733a2f2f70312e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f31322f32312f424d6a41794d6a45784d5449794d5441304d6a68664d6a67784d4445354e7a67344d5638795832686b4d6a6335587a49324d513d3d5f732e6a7067180120012a04323132300aa8010a9e010a0b79697869616f77753636361209e79fa5e5b08fe6ada61a830168747470733a2f2f616c69696d672e612e7978696d67732e636f6d2f75686561642f41422f323032322f31302f30322f31392f424d6a41794d6a45774d4449784f544d304e4442664e6a497a4d4455324d445977587a4a66614751304e444a664d546b335f732e6a70674030655f306f5f306c5f3530685f3530775f3835712e73726318012a033430330ab6010aac010a0c4c31333130373432373635301212e9bb8ee699a8f09f8c8af09f8c8af09f8c8a1a870168747470733a2f2f616c69696d672e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f31392f31332f424d6a41794d6a45784d546b784d7a4d784d5452664d5441344e5467794d5449334d5638795832686b4e444935587a45304d513d3d5f732e6a70674030655f306f5f306c5f3530685f3530775f3835712e73726318012a033335390ac2010ab8010a104757515053414148445244444145775a121ee69492e4b880e58fa3e8a28be6989fe6989fe98081e7bb99e58c97e699a81a830168747470733a2f2f616c69696d672e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f31322f32312f424d6a41794d6a45784d5449794d5445774d6a4e664d5445314d7a59354d4451324e6c38795832686b4e7a46664f5449355f732e6a70674030655f306f5f306c5f3530685f3530775f3835712e73726318012a033130330a91010a88010a0f337870323538746a6d6376337a62751209e58699e7949ce8af971a6a68747470733a2f2f70332e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f32302f31372f424d6a41794d6a45784d6a41784e7a4d784e5442664d7a45784d7a4d784f5445784e6c38795832686b4d545530587a49344d513d3d5f732e6a706718012a0233340aac010aa3010a0979756875616e306b64120ce88a8be594a4e1b587e1b69c1a870168747470733a2f2f616c69696d672e612e7978696d67732e636f6d2f75686561642f41422f323032322f30362f31312f30312f424d6a41794d6a41324d5445774d5451334e5452664d5441774d6a51324f4445344f4638795832686b4e444535587a457a4e773d3d5f732e6a70674030655f306f5f306c5f3530685f3530775f3835712e73726318012a0233330a8a010a81010a0c6868686832303033313032391205e888aac2b71a6a68747470733a2f2f70332e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f30332f32322f424d6a41794d6a45784d444d794d6a41784d546c664d6a4d7a4d7a45794d4455304d3138795832686b4e544133587a4d314d513d3d5f732e6a706718012a0233310aab010aa2010a0f3378686d3568677a6e657963666b6b1209e890a8e5bf853536391a830168747470733a2f2f616c69696d672e612e7978696d67732e636f6d2f75686561642f41422f323032302f30372f32342f30382f424d6a41794d4441334d6a51774f4449774d4442664d5467344e5455314d5449784e6c38795832686b4d6a4d79587a673d5f732e6a70674030655f306f5f306c5f3530685f3530775f3835712e73726318012a0232330a93010a8a010a0f33787569663363746b6e6d38773271120be790aae790aa37313432321a6a68747470733a2f2f70312e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f31382f31322f424d6a41794d6a45784d5467784d6a45784e4446664d7a45794f5441354f446b304e3138795832686b4e7a6730587a49344e773d3d5f732e6a706718012a0232320a94010a8b010a0f337862677a6a627034777570763567120cefbc87e7bbade99b86efbc821a6a68747470733a2f2f70352e612e7978696d67732e636f6d2f75686561642f41422f323032322f30382f33302f31352f424d6a41794d6a41344d7a41784e5451334e4452664d5441324d6a51334d6a41324e3138795832686b4f545533587a63314e413d3d5f732e6a706718012a0232320aa5010a9c010a0979796473696f73313212054c696b652e1a870168747470733a2f2f616c69696d672e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f31382f31322f424d6a41794d6a45784d5467784d6a51324e4456664d6a4d354d4459774d5455344e5638785832686b4d546731587a51354d773d3d5f732e6a70674030655f306f5f306c5f3530685f3530775f3835712e73726318012a0232310a90010a85010a0a48657969676530353230120be4bba5e6ad8c20f09f8e801a6a68747470733a2f2f70312e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f31332f31302f424d6a41794d6a45784d544d784d4455354d6a4e664d544d324e6a41304e7a41774d5638785832686b4d6a6779587a51794f413d3d5f732e6a7067180120012a0231320aa8010a9f010a0f33786b623464793435706a797570711206e684a6e6829f1a830168747470733a2f2f616c69696d672e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f30342f32322f424d6a41794d6a45784d4451794d6a41774d445a664e4445794f446b324d545931587a4a66614751324e4456664f446b355f732e6a70674030655f306f5f306c5f3530685f3530775f3835712e73726318012a0231310aa5010a9c010a08776a353431383830120ae88b8fe791bee699a82f1a830168747470733a2f2f616c69696d672e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f30332f30302f424d6a41794d6a45784d444d774d4449344e546c664d6a41354e6a45794e544d31587a4666614751304d7a6c664e444d785f732e6a70674030655f306f5f306c5f3530685f3530775f3835712e73726318012a0231310abc010ab3010a0f33786334746a7a376e7875636561791216e7a9bfe5b1b1e794b2efbc88696b756ee59ba2efbc891a870168747470733a2f2f616c69696d672e612e7978696d67732e636f6d2f75686561642f41422f323032322f30382f32362f31312f424d6a41794d6a41344d6a59784d5451334d4442664d6a4d314d7a41314d4449774d3138795832686b4e444d79587a4d7a4e673d3d5f732e6a70674030655f306f5f306c5f3530685f3530775f3835712e73726318012a0231300a8c010a84010a0957535162616f353230120fe5b08f20e5a88120e5b09120e380821a6668747470733a2f2f70312e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f31332f31392f424d6a41794d6a45784d544d784f5445354d5446664f5455314e4449304f445578587a4a666147517a4e5452664e4449785f732e6a706718012a01330a8f010a87010a0f337834646178626768746a78716979120ce7a78be8be9ee1b587e1b69c1a6668747470733a2f2f70332e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f31342f31312f424d6a41794d6a45784d5451784d544d7a4d544a664e7a55354d7a63774d446b31587a4a66614751784f544e664e5459315f732e6a706718012a01330a8d010a85010a0f3378723937706975747768326d7a321206e791bee4b8811a6a68747470733a2f2f70312e612e7978696d67732e636f6d2f75686561642f41422f323032312f30342f32332f32312f424d6a41794d5441304d6a4d794d5445304e544a664d5463794d7a55304f4463304d4638795832686b4f546378587a59354e513d3d5f732e6a706718012a01330ab0010aa8010a0d6c713431383835343138386868120de585b3e4ba8ee58a8920e5bcb71a870168747470733a2f2f616c69696d672e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f30352f32332f424d6a41794d6a45784d4455794d7a4d334e544a664d54517a4f44497a4e6a67784d6c38795832686b4d544578587a67324f413d3d5f732e6a70674030655f306f5f306c5f3530685f3530775f3835712e73726318012a01330a8b010a83010a0e4c544431353933313731353337371209e4bba5e6a4bfe383bb1a6668747470733a2f2f70332e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f30372f31392f424d6a41794d6a45784d4463784f544d314d545a664d5441314d5463784e4459334e6c38795832686b4f444579587a55315f732e6a706718012a01330a89010a83010a0b64796c3230303830363130120ce5b08fe5b08fe5a79ce99c961a6668747470733a2f2f70342e612e7978696d67732e636f6d2f75686561642f41422f323032322f31302f31362f31312f424d6a41794d6a45774d5459784d5455354e5442664f4449304e7a517a4e545535587a4a66614751334d7a42664e5445335f732e6a70672a01320ab7010ab1010a0f3378727a33667a69737438717334611218e5bf98e5b79de38088e5b7b2e69c89e58584e5bc9fe380891a830168747470733a2f2f616c69696d672e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f31342f31312f424d6a41794d6a45784d5451784d54557a4d6a42664f4441304e444d794f545579587a4666614751304d7a52664d7a4d785f732e6a70674030655f306f5f306c5f3530685f3530775f3835712e7372632a01320a90010a8a010a0e796f6e6773686974756f7a68616e1210e5b08fe58b87e5a3ab2de99988e8b68a1a6668747470733a2f2f70312e612e7978696d67732e636f6d2f75686561642f41422f323032322f30352f32382f31332f424d6a41794d6a41314d6a67784d7a51354d445a664e7a59304f44517a4d7a6b35587a4a66614751794d6a56664e544d7a5f732e6a70672a01320a8d010a87010a0f3378746d706b6167627536766e7139120ce5ad90e792a9e1b587e1b69c1a6668747470733a2f2f70312e612e7978696d67732e636f6d2f75686561642f41422f323032322f31302f33312f31312f424d6a41794d6a45774d7a45784d544d784e4468664e6a45324d4445304d444d30587a4a66614751314e446c664d54497a5f732e6a70672a01320a89010a83010a0f4c4a483532304c4a31333134656d6f1204f09f88b71a6a68747470733a2f2f70352e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f31342f31382f424d6a41794d6a45784d5451784f4441314d4442664d6a67354d4441774f5455314e6c38795832686b4d6a6730587a63794e513d3d5f732e6a70672a01320aa5010a9d010a0f33786967326675743533373872626b1204456e6d681a830168747470733a2f2f616c69696d672e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f32332f31312f424d6a41794d6a45784d6a4d784d544d784e446c664d6a59324e7a517a4d4455334f5638785832686b4d7a4132587a6b315f732e6a70674030655f306f5f306c5f3530685f3530775f3835712e73726318012a01320ab1010aab010a0f33786d39353268396a393473787a731212e5ad90e792a9efbc88e5b08fe58fb7efbc891a830168747470733a2f2f616c69696d672e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f30372f30302f424d6a41794d6a45784d4463774d4451794e4452664d6a517a4d5463314d6a49354e5638795832686b4e5464664e7a49785f732e6a70674030655f306f5f306c5f3530685f3530775f3835712e7372632a01320aa9010aa3010a0f3378397370326436703272727866391206e585b1e5928c1a870168747470733a2f2f616c69696d672e612e7978696d67732e636f6d2f75686561642f41422f323032322f30372f32382f31322f424d6a41794d6a41334d6a67784d6a55314d7a42664d6a4d354e6a4d774e4455304d3138795832686b4e6a6b35587a45774e413d3d5f732e6a70674030655f306f5f306c5f3530685f3530775f3835712e7372632a01320aa5010a9f010a0b4c5a5032303133313479611206e6b3bde4b8801a870168747470733a2f2f616c69696d672e612e7978696d67732e636f6d2f75686561642f41422f323032322f30372f31332f31362f424d6a41794d6a41334d544d784e6a49304e5456664d546b324e4445794f4463334f5638795832686b4f545179587a597a4d673d3d5f732e6a70674030655f306f5f306c5f3530685f3530775f3835712e7372632a01320a9f010a99010a0f3378326e37793865656573766b6879121ee58c97e699a8e79a84e4bfa1e699baefbc88e5b7b2e7b4abe7a082efbc891a6668747470733a2f2f70312e612e7978696d67732e636f6d2f75686561642f41422f323032322f31312f31332f31312f424d6a41794d6a45784d544d784d5441344d6a68664d5467344d44497a4f5441354e5638785832686b4f446b79587a45795f732e6a70672a013220a699a0ebca30'
    with open('t-proto', 'wb') as w:
        w.write(binascii.unhexlify(hexStr))

    parser = StandardParser()

    print(parser)
    with open('t-proto', 'rb') as fh:
        output = parser.parse_message(fh, 'message')
    print(output)
    return output


try: 
    room_id = my_handle.get_room_id()
    # room_id = "2036164249"
    parseLiveRoomUrl(f"https://live.douyin.com/{room_id}")
except KeyboardInterrupt:
    print('程序被强行退出')
finally:
    print('关闭连接...可能是直播间不存在或下播或网络问题')
    exit(0)
