import json
import copy
import traceback

from utils.common import Common
from utils.my_log import logger


def convert_cookies(cookies: list) -> dict:
    """转换cookies"""
    cookies_dict = {}
    for cookie in cookies:
        cookies_dict[cookie["name"]] = cookie["value"]
    return cookies_dict


class TongYi:
    def __init__(self, data):
        self.common = Common()

        self.config_data = data
        self.cookie_path = data["cookie_path"]
        self.parentId = None
        self.chatbot = None

        self.history = []

        self.cookies_dict = {}

        try:
            if self.config_data["type"] == "web":
                # 非流式模式
                import revTongYi.qianwen as qwen

                with open(self.cookie_path) as f:
                    self.cookies_dict = convert_cookies(json.load(f))
                self.chatbot = qwen.Chatbot(
                    cookies=self.cookies_dict  # 以dict形式提供cookies
                )

            elif self.config_data["type"] == "api":
                import dashscope

                dashscope.api_key = self.config_data["api_key"]
        except Exception:
            logger.error(traceback.format_exc())

    def get_resp(self, prompt, stream=False):
        """请求对应接口，获取返回值

        Args:
            prompt (str): 你的提问
            stream (bool, optional): 是否流式返回. Defaults to False.

        Returns:
            str: 返回的文本回答
        """
        try:
            if self.config_data["type"] == "web":
                if self.parentId:
                    ret = self.chatbot.ask(prompt=prompt, parentId=self.parentId)
                else:
                    ret = self.chatbot.ask(prompt=prompt)

                # logger.info(ret)

                # 是否启用上下文记忆
                if self.config_data["history_enable"]:
                    self.parentId = ret["msgId"]
                resp_content = ret["content"][0]

                return resp_content
            elif self.config_data["type"] == "api":
                from http import HTTPStatus
                from dashscope import Generation
                from dashscope.api_entities.dashscope_response import Role

                if self.config_data["history_enable"] is False:
                    # 预设不能为空
                    if self.config_data["preset"] == "":
                        self.config_data["preset"] = "请做为一个人工智能，回答我的问题"
                    messages = [
                        {"role": Role.SYSTEM, "content": self.config_data["preset"]},
                        {"role": Role.USER, "content": prompt},
                    ]
                else:
                    messages = copy.copy(self.history)
                    messages.append({"role": Role.USER, "content": prompt})
                    messages.insert(0, {"role": Role.SYSTEM, "content": self.config_data["preset"]})

                logger.debug(f"messages={messages}")

                response = Generation.call(
                    self.config_data["model"],
                    messages=messages,
                    result_format="message",  # set the result to be "message" format.
                    temperature=self.config_data["temperature"],
                    top_p=self.config_data["top_p"],
                    top_k=self.config_data["top_k"],
                    enable_search=self.config_data["enable_search"],
                    max_tokens=self.config_data["max_tokens"],
                    stream=stream,
                )

                if response is None:
                    return None

                if stream:
                    # 返回响应
                    return response

                if response.status_code == HTTPStatus.OK:
                    logger.debug(response)

                    resp_content = response.output.choices[0]["message"]["content"]

                    if self.config_data["history_enable"]:
                        self.history.append({"role": Role.USER, "content": prompt})
                        self.history.append(
                            {"role": response.output.choices[0]["message"]["role"], "content": resp_content}
                        )
                        while True:
                            # 获取嵌套列表中所有字符串的字符数
                            total_chars = sum(len(item["content"]) for item in self.history if "content" in item)
                            # 如果大于限定最大历史数，就剔除第一个元素
                            if total_chars > int(self.config_data["history_max_len"]):
                                self.history.pop(0)
                                self.history.pop(0)
                            else:
                                break

                    return resp_content
                else:
                    logger.error(
                        f"出错，请查看message信息排查问题，已知问题有：输入数据可能包含不适当的内容\nRequest id: {response.request_id}, Status code: {response.status_code}, error code: {response.code}, error message: {response.message}"
                    )
                    return None
        except Exception:
            logger.error(traceback.format_exc())
            return None

    # 添加AI返回消息到会话，用于提供上下文记忆
    def add_assistant_msg_to_session(self, prompt: str, message: str):
        try:
            if self.config_data["type"] == "api":
                from dashscope.api_entities.dashscope_response import Role

                # 启用历史就给我记住！
                if self.config_data["history_enable"]:
                    self.history.append({"role": Role.USER, "content": prompt})
                    self.history.append({"role": Role.ASSISTANT, "content": message})
                    while True:
                        # 获取嵌套列表中所有字符串的字符数
                        total_chars = sum(len(item["content"]) for item in self.history if "content" in item)
                        # 如果大于限定最大历史数，就剔除第一个元素
                        if total_chars > int(self.config_data["history_max_len"]):
                            self.history.pop(0)
                            self.history.pop(0)
                        else:
                            break

                logger.debug(f"history={self.history}")

                return {"ret": True}

            return {"ret": False}
        except Exception:
            logger.error(traceback.format_exc())
            return {"ret": False}


if __name__ == "__main__":
    # 配置日志输出格式
    logger.basicConfig(
        level=logger.INFO,  # 设置日志级别，可以根据需求调整
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    data = {
        "cookie_path": "cookies.json",
        "type": "api",
        "model": "qwen-max",
        "preset": "你是一个专业的虚拟主播",
        "api_key": "sk-",
        "temperature": 0.9,
        "top_p": 0.9,
        "top_k": 3,
        "enable_search": True,
        "max_tokens": 1024,
        "history_enable": True,
        "history_max_len": 20,
    }

    tongyi = TongYi(data)

    logger.info(tongyi.get_resp("你现在叫小伊，是个猫娘，每句话后面加个喵"))
    logger.info(tongyi.get_resp("早上好，你叫什么"))
