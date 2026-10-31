import json, logging
import requests
from urllib.parse import urljoin

# from utils.common import Common
# from utils.logger import Configure_logger


class Koboldcpp:
    def __init__(self, data):
        # self.common = Common()
        # 日志文件路径
        # file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        # Configure_logger(file_path)

        self.config_data = data

        self.history = "[The following is an interesting chat message log between You and AI.]"


    def get_resp(self, data):
        """请求对应接口，获取返回值

        Args:
            data (dict): 数据

        Returns:
            str: 返回的文本回答
        """
        try:
            prompt = data["prompt"]

            data_json = self.config_data
            url = urljoin(self.config_data["api_ip_port"], "/api/v1/generate")

            data_json["prompt"] = f"{self.history}\nYou: {prompt}"

            logging.info(f"data_json={data_json}")

            response = requests.post(url=url, json=data_json)
            response.raise_for_status()  # 检查响应的状态码

            result = response.content
            ret = json.loads(result)

            logging.info(ret)

            resp_content = ret["results"][0]["text"]

            # 启用历史就给我记住！
            if self.config_data["history_enable"]:
                self.history += f'\nYou: {prompt}\nAI: {resp_content}'
                while True:
                    total_chars = len(self.history)
                    # 如果大于限定最大历史数，就剔除第一个元素
                    if total_chars > self.config_data["history_max_len"]:
                        # 假设 self.history 是原始字符串
                        split_list = self.history.split("\n")  # 分割字符串成列表

                        # 保留第一个元素，跳过第二和第三个元素，然后保留剩下的所有元素
                        # 注意，列表索引从0开始，所以第二个元素的索引是1，第三个元素的索引是2
                        processed_list = split_list[:1] + split_list[3:]

                        # 将处理后的列表元素合并回字符串
                        self.history = "\n".join(processed_list)
                    else:
                        break

            return resp_content
        except Exception as e:
            logging.error(e)
            return None


if __name__ == '__main__':
    # 配置日志输出格式
    logging.basicConfig(
        level=logging.INFO,  # 设置日志级别，可以根据需求调整
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    data = {
        "api_ip_port": "http://127.0.0.1:5001",
        "max_context_length": 2048,
        "max_length": 100,
        "quiet": False,
        "rep_pen": 1.1,
        "rep_pen_range": 256,
        "rep_pen_slope": 1,
        "temperature": 0.5,
        "tfs": 1,
        "top_a": 0,
        "top_k": 3,
        "top_p": 0.9,
        "typical": 1,
        "history_enable": True,
        "history_max_len": 600
    }
    koboldcpp = Koboldcpp(data)

    logging.info(koboldcpp.get_resp({"prompt": "what is your name"}))
    logging.info(koboldcpp.get_resp({"prompt": "what can your do"}))
    