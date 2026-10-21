# -*- coding: UTF-8 -*-
"""@File : chat_model.py — chat_with_file 的公共配置层"""
from utils.gpt_model.gpt import GPT_MODEL


class Chat_model:
    def __init__(self, data):
        self.chat_mode = data.get("chat_mode", "openai_gpt")
        self.data_path = data.get("data_path")

        # 文本切分：分隔符、块大小、块之间的重叠字符数
        self.separator = data.get("separator", "\n")
        self.chunk_size = int(data.get("chunk_size", 1000))
        self.chunk_overlap = int(data.get("chunk_overlap", 100))

        api_key = GPT_MODEL.get_openai_key()
        self.openai_api_key = api_key[0] if isinstance(api_key, (list, tuple)) else api_key
        self.openai_api = GPT_MODEL.get_openai_api()
        self.openai_model_name = GPT_MODEL.get_openai_model_name()

        self.chain_type = data.get("chain_type", "stuff")
        self.show_token_cost = bool(data.get("show_token_cost", False))
        self.local_max_query = max(1, int(data.get("local_max_query", 3)))
        self.question_prompt = data.get("question_prompt", "")

    def get_model_resp(self, question=""):
        raise NotImplementedError
