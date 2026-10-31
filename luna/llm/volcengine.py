import traceback
from volcenginesdkarkruntime import Ark

from luna.common.helpers import Common
from luna.infra.my_log import logger

# 官方文档：https://www.volcengine.com/docs/82379/1302008


class VolcEngine:
    def __init__(self, data):
        self.common = Common()

        self.config_data = data

        self.history = []

        try:
            self.client = Ark(api_key=self.config_data["api_key"])
        except Exception:
            logger.error(traceback.format_exc())

    def get_resp(self, data: dict, stream: bool = False):
        """请求对应接口，获取返回值

        Args:
            data (dict): json数据
            stream (bool, optional): 是否流式返回. Defaults to False.

        Returns:
            str: 返回的文本回答
        """
        try:
            prompt = data["prompt"]

            # 准备消息
            if not self.config_data["history_enable"]:
                preset = self.config_data["preset"] or "请作为一个人工智能，回答我的问题"
                messages = [{"role": "system", "content": preset}, {"role": "user", "content": prompt}]
            else:
                messages = self.history.copy()
                messages.append({"role": "user", "content": prompt})
                messages.insert(0, {"role": "system", "content": self.config_data["preset"]})

            logger.debug(f"messages={messages}")

            # 创建聊天完成
            response = self.client.chat.completions.create(
                model=self.config_data["model"], messages=messages, stream=stream
            )

            if response is None:
                return None

            if stream:
                return response

            logger.debug(response)
            resp_content = response.choices[0].message.content

            # 更新历史记录
            if self.config_data["history_enable"]:
                self.history.append({"role": "user", "content": prompt})
                self.history.append({"role": "assistant", "content": resp_content})

                # 修剪历史记录
                while sum(len(item["content"]) for item in self.history if "content" in item) > int(
                    self.config_data["history_max_len"]
                ):
                    self.history = self.history[2:]  # 移除最旧的消息对

            return resp_content

        except Exception as e:
            logger.error(f"Error in get_resp: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    # 添加AI返回消息到会话，用于提供上下文记忆
    def add_assistant_msg_to_session(self, prompt: str, message: str):
        try:
            # 启用历史就给我记住！
            if self.config_data["history_enable"]:
                self.history.append({"role": "user", "content": prompt})
                self.history.append({"role": "assistant", "content": message})
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
        except Exception:
            logger.error(traceback.format_exc())
            return {"ret": False}
