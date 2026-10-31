from urllib.parse import urljoin
from loguru import logger
import traceback

from utils.common import Common

common = Common()


# 发送消息给洛曦 直播弹幕助手
async def send_msg_to_live_comment_assistant(config_data: dict, msg: str):
    try:
        API_URL = urljoin(config_data["api_ip_port"], "/send_text")
        data = {
            "text": msg,
        }
        resp_json = await common.send_async_request(API_URL, "POST", data)
        return resp_json
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"请求 洛曦 直播弹幕助手 API 失败: {e}")
        return None
