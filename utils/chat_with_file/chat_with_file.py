# -*- coding: UTF-8 -*-
"""@File    : chat_with_file.py
@Description : 本地资料问答入口，chat_mode 决定是只检索还是检索后再走 LLM 总结
"""
from utils.chat_with_file.chat_mode.openai_model import Openai_mode
from utils.my_log import logger

SUPPORTED_CHAT_MODES = ("openai_gpt", "openai_vector_search")


class Chat_with_file:
    chat_model = None

    def __init__(self, data):
        chat_mode = (data or {}).get("chat_mode")
        if chat_mode not in SUPPORTED_CHAT_MODES:
            logger.error(f"chat_with_file 不支持 chat_mode={chat_mode}，可选：{', '.join(SUPPORTED_CHAT_MODES)}")
            return

        self.chat_model = Openai_mode(data)

    def get_model_resp(self, question):
        if self.chat_model is None:
            return "chat_with_file 未正确配置，请检查 chat_mode。"
        return self.chat_model.get_model_resp(question)
