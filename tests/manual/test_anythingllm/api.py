import json, logging, traceback
import requests
from urllib.parse import urljoin

# from utils.common import Common
# from utils.logger import Configure_logger


class AnythingLLM:
    def __init__(self, data):
        # self.common = Common()
        # 日志文件路径
        # file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        # Configure_logger(file_path)

        self.config_data = data
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.config_data['api_key']}"
        }
        self.workspaces_list = []

    # 验证密钥
    def verify_auth(self):
        try:
            url = urljoin(self.config_data["api_ip_port"], "/api/v1/auth")
        

            response = requests.get(url, headers=self.headers)
            response.raise_for_status()  # 检查响应的状态码

            result = response.content
            ret = json.loads(result)

            logging.debug(ret)
            if "authenticated" in ret:
                return True

            logging.error(f"AnythingLLM API密钥 验证失败: {ret['message']}")
            return False
        except Exception as e:
            logging.error(traceback.format_exc())
            return False

    # 获取工作区列表
    def get_workspaces_list(self):
        try:
            url = urljoin(self.config_data["api_ip_port"], "/api/v1/workspaces")
        

            response = requests.get(url, headers=self.headers)
            response.raise_for_status()  # 检查响应的状态码

            result = response.content
            ret = json.loads(result)

            logging.debug(ret)
            if "workspaces" in ret:
                self.workspaces_list = ret["workspaces"]
                return ret["workspaces"]

            logging.error(f"AnythingLLM 获取工作区列表失败: {ret['message']}")
            return None
        except Exception as e:
            logging.error(traceback.format_exc())
            return None

    def get_resp(self, data):
        """请求对应接口，获取返回值

        Args:
            data (dict): 你的提问

        Returns:
            str: 返回的文本回答
        """
        try:
            url = urljoin(self.config_data["api_ip_port"], f"/api/v1/workspace/{self.config_data['workspace_slug']}/chat")

            if "mode" in data:
                mode = data["mode"]
            else:
                mode = self.config_data["mode"]

            data_json = {
                "message": data["prompt"],
                "mode": mode
            }

            response = requests.post(url=url, json=data_json, headers=self.headers)
            response.raise_for_status()  # 检查响应的状态码

            result = response.content
            ret = json.loads(result)

            logging.debug(ret)

            if "textResponse" in ret:
                return ret["textResponse"]

            logging.error(f"AnythingLLM 对话失败: {ret['message']}")
            return None
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

    data = {
        "api_ip_port": "http://127.0.0.1:3001",
        "api_key": "S1PPG9B-YP2M8NX-Q64ZBF1-Y4K5DCS",
        "mode": "chat",
        "workspace_slug": "test"
    }
    anythingllm = AnythingLLM(data)

    # 验证密钥
    if anythingllm.verify_auth():
        # 获取返回值
        
        anythingllm.get_workspaces_list()

        logging.info(anythingllm.get_resp({"prompt": "你可以扮演猫娘吗，每句话后面加个喵"}))
        logging.info(anythingllm.get_resp({"prompt": "早上好"}))
    
        logging.info(anythingllm.get_resp({"prompt": "伊卡洛斯和妮姆芙的关系", "mode": "chat"}))
        #logging.info(anythingllm.get_resp({"prompt": "伊卡洛斯的英文名", "mode": "chat"}))