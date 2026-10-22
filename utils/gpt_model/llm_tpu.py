from utils.history import total_chars as history_chars
import traceback
from gradio_client import Client
import re

from utils.common import Common
from utils.my_log import logger


class LLM_TPU:
    def __init__(self, data):
        self.common = Common()

        self.config_data = data
        self.history = []

        self.history_enable = data["history_enable"]
        self.history_max_len = data["history_max_len"]


    def get_resp(self, data):
        """请求对应接口，获取返回值

        Args:
            data (dict): 你的提问等

        Returns:
            str: 返回的文本回答
        """
        try:
            client = Client(self.config_data["api_ip_port"])

            result = client.predict(
                input=data["prompt"],
                chatbot=self.history,
                max_length=self.config_data["max_length"],
                top_p=self.config_data["top_p"],
                temperature=self.config_data["temperature"],
                api_name="/predict"
            )
            
            response_text = result[-1][1]
            # Remove <p> and </p> tags using regex
            resp_content = re.sub(r'</?p>', '', response_text)

            self.history = result

            # 启用历史就给我记住！
            if self.history_enable:
                while True:
                    # 按条目里真正的内容算长度：历史存的是字典，直接遍历字典拿到的是键名
                    total_chars = history_chars(self.history)
                    # 如果大于限定最大历史数，就剔除第一个元素
                    if total_chars > self.history_max_len:
                        self.history.pop(0)
                    else:
                        break

            return resp_content
        except Exception as e:
            logger.error(traceback.format_exc())
            return None

if __name__ == '__main__':
    # 配置日志输出格式
    logger.basicConfig(
        level=logger.DEBUG,  # 设置日志级别，可以根据需求调整
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    data = {
        "api_ip_port": "http://127.0.0.1:8003/",
        "max_length": 1,
        "top_p": 0.8,
        "temperature": 0.95,
        "history_enable": True,
        "history_max_len": 300
    }

    llm_tpu = LLM_TPU(data)
    logger.info(f'{llm_tpu.get_resp("你可以扮演猫娘吗，每句话后面加个喵")}')
    logger.info(f'{llm_tpu.get_resp("早上好")}')

