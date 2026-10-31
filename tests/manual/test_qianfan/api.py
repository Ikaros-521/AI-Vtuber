import os
import qianfan
import requests, copy
import json, logging
import traceback

class My_QianFan():
    def __init__(self, data):
        self.config_data = data
        self.history = []
        
        try:
            os.environ["QIANFAN_ACCESS_KEY"] = data["access_key"]
            os.environ["QIANFAN_SECRET_KEY"] = data["secret_key"]
            # 通过 App Id 选择使用的应用
            # 该参数可选，若不提供 SDK 会自动选择最新创建的应用
            # os.environ["QIANFAN_APPID"]="44916356"
        except Exception as e:
            logging.error("千帆大模型，配置出错，请检查config配置是否有格式问题！")
            logging.error(traceback.format_exc())

    def get_resp(self, prompt):
        """请求对应接口，获取返回值

        Args:
            prompt (str): 你的提问

        Returns:
            str: 返回的文本回答
        """
        try:
            chat_comp = qianfan.ChatCompletion(model=self.config_data["model"])
            tmp_history = copy.copy(self.history)
            tmp_history.append({
                "role": "user",
                "content": prompt
            })
            logging.debug(f"历史={tmp_history}")
            resp = chat_comp.do(messages=tmp_history, top_p=self.config_data["top_p"], temperature=self.config_data["temperature"], penalty_score=self.config_data["penalty_score"])

            logging.debug(resp)
            logging.info(f'token总消耗：{resp["usage"]["total_tokens"]}')

            resp_content = resp["result"]
        
            # 启用历史就给我记住！
            if self.config_data["history_enable"]:
                while True:
                    # 获取嵌套列表中所有字符串的字符数
                    total_chars = sum(len(string) for sublist in self.history for string in sublist)
                    # 如果大于限定最大历史数，就剔除第一个元素
                    if total_chars > self.config_data["history_max_len"]:
                        self.history.pop(0)
                    else:
                        self.history.append({"role": "user", "content": prompt})
                        self.history.append({"role": "assistant", "content": resp_content})
                        break

            return resp_content
        except Exception as e:
            logging.error(traceback.format_exc())

            return None


if __name__ == '__main__':
    # 配置日志输出格式
    logging.basicConfig(
        level=logging.DEBUG,  # 设置日志级别，可以根据需求调整
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    '''
    support model:
        - ERNIE-Bot-turbo
        - ERNIE-Bot
        - ERNIE-Bot-4
        - BLOOMZ-7B
        - Llama-2-7b-chat
        - Llama-2-13b-chat
        - Llama-2-70b-chat
        - Qianfan-BLOOMZ-7B-compressed
        - Qianfan-Chinese-Llama-2-7B
        - ChatGLM2-6B-32K
        - AquilaChat-7B
    '''

    data = {
        "model": "Llama-2-7b-chat",
        "access_key": "",
        "secret_key": "",
        "top_p": 0.8,
        "temperature": 0.9,
        "penalty_score": 1.0,
        "history_enable": True,
        "history_max_len": 300
    }

    my_qian_fan = My_QianFan(data)
    logging.info(f'{my_qian_fan.get_resp("你可以扮演猫娘吗，每句话后面加个喵")}')
    logging.info(f'{my_qian_fan.get_resp("早上好")}')
