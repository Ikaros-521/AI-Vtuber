# -*- coding: UTF-8 -*-
"""
@Project : AI-Vtuber 
@File    : gpt.py
@Author  : HildaM
@Email   : Hilda_quan@163.com
@Date    : 2023/06/23 下午 7:47 
@Description :  统一模型层抽象
"""
import importlib

from utils.my_log import logger

# 延迟导入的模型注册表：只有配置里真正选中的模型才会导入对应 SDK
PROVIDERS = {
    "chatgpt": ("utils.gpt_model.chatgpt", "Chatgpt"),
    "text_generation_webui": ("utils.gpt_model.text_generation_webui", "TEXT_GENERATION_WEBUI"),
    "sparkdesk": ("utils.gpt_model.sparkdesk", "SPARKDESK"),
    "langchain_chatchat": ("utils.gpt_model.langchain_chatchat", "Langchain_ChatChat"),
    "zhipu": ("utils.gpt_model.zhipu", "Zhipu"),
    "bard": ("utils.gpt_model.bard", "Bard_api"),
    "tongyi": ("utils.gpt_model.tongyi", "TongYi"),
    "tongyixingchen": ("utils.gpt_model.tongyixingchen", "TongYiXingChen"),
    "my_wenxinworkshop": ("utils.gpt_model.my_wenxinworkshop", "My_WenXinWorkShop"),
    "gemini": ("utils.gpt_model.gemini", "Gemini"),
    "koboldcpp": ("utils.gpt_model.koboldcpp", "Koboldcpp"),
    "anythingllm": ("utils.gpt_model.anythingllm", "AnythingLLM"),
    "gpt4free": ("utils.gpt_model.gpt4free", "GPT4Free"),
    "custom_llm": ("utils.gpt_model.custom_llm", "Custom_LLM"),
    "llm_tpu": ("utils.gpt_model.llm_tpu", "LLM_TPU"),
    "dify": ("utils.gpt_model.dify", "Dify"),
    "volcengine": ("utils.gpt_model.volcengine", "VolcEngine"),
}


def load_model_class(model_name):
    provider = PROVIDERS.get(model_name)
    if provider is None:
        return None

    module_name, class_name = provider
    try:
        return getattr(importlib.import_module(module_name), class_name)
    except ImportError as e:
        raise ImportError(
            f"模型 {model_name} 缺少依赖（{module_name}），请按 requirements/ 里的对应分组安装后重试"
        ) from e


class GPT_Model:
    openai = None
    
    def set_model_config(self, model_name, config):
        if model_name == "openai":
            self.openai = config
            return

        model_class = load_model_class(model_name)
        if model_class is None:
            return

        if model_name == "chatgpt":
            if self.openai is None:
                # 这里不能 exit()：config_load 会无条件配 chatgpt，
                # 用 dify/gemini 的用户会因为缺 openai 段而启动即退出。
                logger.error("openai key 为空，跳过 chatgpt 模型配置")
                return
            self.chatgpt = model_class(self.openai, config)
            return

        setattr(self, model_name, model_class(config))

    def set_vision_model_config(self, model_name, config):
        model_class = load_model_class(model_name)
        if model_class is None:
            return

        setattr(self, model_name, model_class(config))

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

    def get_openai_api(self):
        if self.openai is None:
            return None
        return self.openai.get("api")

    def get_openai_model_name(self):
        model = self.openai.get("model") if self.openai else None
        if not model:
            logger.warning("openai的model为空，将设置为默认gpt-3.5")
            return "gpt-3.5-turbo-0301"
        return model


# 全局变量
GPT_MODEL = GPT_Model()
