import json
import requests
import traceback
from urllib.parse import urljoin
from loguru import logger

from utils.common import Common

class Dify:
    def __init__(self, data: dict):
        self.config_data = data

        self.conversation_id = ""

        # logger.debug(self.config_data)

        self.common = Common()

    def replace_variables(self, text, variables):
        import re

        for key, value in variables.items():
            # 同 utils/gpt_model/custom_llm.py：替换串来自观众输入，
            # 不能交给 re.sub 当模板解析，否则 \1 这种内容直接抛 re.error
            text = re.sub(r'\{\{' + re.escape(key) + r'\}\}', lambda _match, value=value: value, text)
        return text

    def get_resp(self, data: dict, stream: bool = False):
        """请求对应接口，获取返回值

        Args:
            data (dict): 含有提问的json数据
            stream (bool): 是否流式返回

        Returns:
            str: 返回的文本回答
        """
        try:
            resp_content = None

            if self.config_data["type"] == "聊天助手":
                API_URL = urljoin(self.config_data["api_ip_port"], '/v1/chat-messages')

                if stream:
                    data_json = {
                        "inputs": {},
                        "query": data["prompt"],
                        # 阻塞模式
                        "response_mode": "streaming",
                        # 会话 ID，需要基于之前的聊天记录继续对话，必须传之前消息的 conversation_id。
                        "conversation_id": self.conversation_id,
                        # 用户名是否区分 视情况而定，暂时为了稳定性统一
                        "user": "test"
                    }
                else:
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
                
                response = requests.request("POST", API_URL, headers=headers, json=data_json, timeout=(10, 300))

                if response is None:
                    return None

                # 流式的话 直接返回
                if stream:
                    return response

                resp_json = json.loads(response.content)
                
                logger.debug(f"[dify] resp_json={resp_json}")

                if "answer" in resp_json:
                    resp_content = resp_json["answer"]

                    # 是否记录历史
                    if self.config_data["history_enable"]:
                        self.conversation_id = resp_json["conversation_id"]
                else:
                    logger.error(f"[dify] 获取LLM返回失败。{resp_json}")
                    return None

                return resp_content
            elif self.config_data["type"] == "工作流":
                API_URL = urljoin(self.config_data["api_ip_port"], '/v1/workflows/run')

                variables = {
                    "cur_time": self.common.get_bj_time(0),
                    "comment": data['prompt'],
                }

                custom_params = self.replace_variables(self.config_data['custom_params'], variables)
                custom_params = json.loads(custom_params)

                if stream:
                    data_json = {
                        "inputs": custom_params,
                        # 阻塞模式
                        "response_mode": "streaming",
                        # 用户名是否区分 视情况而定，暂时为了稳定性统一
                        "user": "test"
                    }
                else:
                    data_json = {
                        "inputs": custom_params,
                        # 阻塞模式
                        "response_mode": "blocking",
                        # 用户名是否区分 视情况而定，暂时为了稳定性统一
                        "user": "test"
                    }
                    logger.debug(f"[dify] data_json={data_json}")
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.config_data["api_key"]}'
                }
                
                response = requests.request("POST", API_URL, headers=headers, json=data_json, timeout=(10, 300))

                if response is None:
                    return None

                # 流式的话 直接返回
                if stream:
                    return response
                
                resp_json = json.loads(response.content)
                
                logger.debug(f"[dify] resp_json={resp_json}")

                if "data" in resp_json:
                    if "outputs" in resp_json["data"]:
                        resp_content_dict = resp_json["data"]["outputs"]
                        if "text" in resp_content_dict:
                            resp_content = resp_content_dict["text"]
                else:
                    logger.error(f"[dify] 获取LLM返回失败。{resp_json}")
                    return None

                return resp_content
        except Exception:
            logger.error(traceback.format_exc())

        return None
    
    # 添加AI返回消息到会话，用于提供上下文记忆
    def add_assistant_msg_to_session(self, conversation_id: str):
        try:
            # 启用历史就给我记住！
            if self.config_data['history_enable']:
                self.conversation_id = conversation_id
            return {"ret": True}
        except Exception:
            logger.error(traceback.format_exc())
            return {"ret": False}

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
