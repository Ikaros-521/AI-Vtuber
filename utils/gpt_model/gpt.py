# -*- coding: UTF-8 -*-
"""
@Project : AI-Vtuber 
@File    : gpt.py
@Author  : HildaM
@Email   : Hilda_quan@163.com
@Date    : 2023/06/23 下午 7:47 
@Description :  统一模型层抽象
"""
from utils.my_log import logger

from utils.gpt_model.chatgpt import Chatgpt
from utils.gpt_model.sparkdesk import SPARKDESK
from utils.gpt_model.langchain_chatchat import Langchain_ChatChat
from utils.gpt_model.zhipu import Zhipu
from utils.gpt_model.tongyi import TongYi
from utils.gpt_model.my_wenxinworkshop import My_WenXinWorkShop
from utils.gpt_model.gemini import Gemini
from utils.gpt_model.anythingllm import AnythingLLM
from utils.gpt_model.dify import Dify
from utils.gpt_model.volcengine import VolcEngine

class GPT_Model:
    openai = None
    
    def set_model_config(self, model_name, config):
        model_classes = {
            "sparkdesk": SPARKDESK,
            "langchain_chatchat": Langchain_ChatChat,
            "zhipu": Zhipu,
            "tongyi": TongYi,
            "my_wenxinworkshop": My_WenXinWorkShop,
            "gemini": Gemini,
            "anythingllm": AnythingLLM,
            "dify": Dify,
            "volcengine": VolcEngine,
        }

        if model_name == "openai":
            self.openai = config
        elif model_name == "chatgpt":
            if self.openai is None:
                logger.error("openai key 为空，无法配置chatgpt模型")
                exit(-1)
            self.chatgpt = Chatgpt(self.openai, config)
        elif model_name in model_classes:
            setattr(self, model_name, model_classes[model_name](config))

    def set_vision_model_config(self, model_name, config):
        model_classes = {
            "gemini": Gemini,
            "zhipu": Zhipu,
        }

        setattr(self, model_name, model_classes[model_name](config))

    def get(self, name):
        logger.info("GPT_MODEL: 进入get方法")
        try:
            if name != "reread":
                return getattr(self, name)
        except AttributeError:
            logger.warning(f"{name} 该模型不支持，如果不是LLM的类型，那就只是个警告，可以正常使用，请放心")
            return None

    def get_openai_key(self):
        if self.openai is None:
            logger.error("openai_key 为空")
            return None
        return self.openai["api_key"]

    def get_openai_model_name(self):
        if self.openai is None:
            logger.warning("openai的model为空，将设置为默认gpt-3.5")
            return "gpt-3.5-turbo-0301"
        return self.openai["model"]


# 全局变量
GPT_MODEL = GPT_Model()
