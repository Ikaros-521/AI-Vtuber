import json, logging
# pip install undetected_chromedriver platformdirs curl_cffi aiohttp_socks g4f 
import g4f
from g4f.client import Client

# from utils.common import Common
# from utils.logger import Configure_logger


class GPT4Free:
    def __init__(self, data):
        # self.common = Common()
        # 日志文件路径
        # file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        # Configure_logger(file_path)

        self.config_data = data
        self.api_key = None if self.config_data["api_key"] == "" else self.config_data["api_key"]

        # 创建映射字典
        provider_mapping = {
            "none": None,
            "g4f.Provider.Bing": g4f.Provider.Bing,
            "g4f.Provider.ChatgptAi": g4f.Provider.ChatgptAi,
        }

        proxy = None if data["proxy"] == "" else {"all": data["proxy"]}

        self.client = Client(provider=provider_mapping.get(data["provider"], None), proxies=proxy)

        self.history = []


    def get_resp(self, data):
        """请求对应接口，获取返回值

        Args:
            data (dict): json数据

        Returns:
            str: 返回的文本回答
        """
        try:
            messages = [
                {"role": "system", "content": self.config_data["preset"]}
            ]

            if self.config_data["history_enable"]:
                for message in self.history:
                    messages.append(message)

                messages.append({"role": "user", "content": data["prompt"]})
            else:
                messages.append({"role": "user", "content": data["prompt"]})

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                max_tokens=self.config_data["max_tokens"],
                api_key=self.api_key,
                messages=messages
            )
            resp_content = response.choices[0].message.content

            if self.config_data["history_enable"]:
                if len(self.history) > self.config_data["history_max_len"]:
                    self.history.pop(0)
                while True:
                    # 获取嵌套列表中所有字符串的字符数
                    total_chars = sum(len(string) for sublist in self.history for string in sublist)
                    # 如果大于限定最大历史数，就剔除第一个元素
                    if total_chars > self.config_data["history_max_len"]:
                        self.history.pop(0)
                    else:
                        self.history.append({"role": "user", "content": data["prompt"]})
                        self.history.append({"role": "assistant", "content": resp_content})
                        break

            return resp_content
        except Exception as e:
            logging.error(e)
            return None


if __name__ == '__main__':
    # 配置日志输出格式
    logging.basicConfig(
        level=logging.DEBUG,  # 设置日志级别，可以根据需求调整
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    data = {
        "provider": "none",
        "api_key": "",
        "model": "gpt-3.5-turbo",
        "max_tokens": 2048,
        "proxy": "http://127.0.0.1:10809",
        "preset": "你是一个虚拟主播",
        "history_enable": True,
        "history_max_len": 300
    }
    gpt4free = GPT4Free(data)


    logging.info(gpt4free.get_resp({"prompt": "你可以扮演猫娘吗，每句话后面加个喵"}))
    logging.info(gpt4free.get_resp({"prompt": "早上好"}))
    