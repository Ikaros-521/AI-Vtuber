import json, logging
import re, requests
import traceback
from urllib.parse import urljoin
import sys
sys.path.insert(1, "../../utils")
#from utils.common import Common
from loguru import logger


class Dify:
    def __init__(self, data):
        #self.common = Common()
        self.config_data = data

        self.conversation_id = ""

        logger.debug(self.config_data)


    def get_resp(self, data):
        """请求对应接口，获取返回值

        Args:
            data (dict): 含有提问的json数据

        Returns:
            str: 返回的文本回答
        """
        try:
            resp_content = None

            if self.config_data["type"] == "聊天助手":
                API_URL = urljoin(self.config_data["api_ip_port"], '/v1/chat-messages')

                data_json = {
                    "inputs": {},
                    "query": data["prompt"],
                    # 阻塞模式
                    "response_mode": "blocking",
                    # 会话 ID，需要基于之前的聊天记录继续对话，必须传之前消息的 conversation_id。
                    "conversation_id": self.conversation_id,
                    # 用户名是否区分 视情况而定，暂时为了稳定性统一
                    "user": "test"
                }
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.config_data["api_key"]}'
                }
                
                response = requests.request("POST", API_URL, headers=headers, json=data_json)
                resp_json = json.loads(response.content)
                
                logger.debug(f"resp_json={resp_json}")

                if "answer" in resp_json:
                    resp_content = resp_json["answer"]

                    # 是否记录历史
                    if self.config_data["history_enable"]:
                        self.conversation_id = resp_json["conversation_id"]
                else:
                    logger.error(f"获取LLM返回失败。{resp_json}")
                    return None

                return resp_content
            
        except Exception as e:
            logger.error(traceback.format_exc())

        return None

if __name__ == '__main__':


    data = {
        "api_ip_port": "http://172.26.189.21/v1",
        "type": "聊天助手",
        "api_key": "app-64xu0vQjP2kxN4DKR8Ch7ZGY",
        "history_enable": True
    }

    # 实例化并调用
    dify = Dify(data)
    logger.info(dify.get_resp({"prompt": "你可以扮演猫娘吗，每句话后面加个喵"}))
    logger.info(dify.get_resp({"prompt": "早上好"}))
