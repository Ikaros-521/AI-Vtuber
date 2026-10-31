import json
import traceback
import requests
from urllib.parse import urljoin

from luna.common.helpers import Common
from luna.infra.my_log import logger


class AnythingLLM:
    def __init__(self, data):
        self.common = Common()

        self.config_data = data
        self.headers = {"Accept": "application/json", "Authorization": f"Bearer {self.config_data['api_key']}"}
        self.workspaces_list = []

    # 验证密钥
    def verify_auth(self):
        try:
            url = urljoin(self.config_data["api_ip_port"], "/api/v1/auth")

            response = requests.get(url, headers=self.headers, timeout=(10, 300))
            response.raise_for_status()  # 检查响应的状态码

            result = response.content
            ret = json.loads(result)

            logger.debug(ret)
            if "authenticated" in ret:
                return True

            logger.error(f"AnythingLLM API密钥 验证失败: {ret['message']}")
            return False
        except Exception:
            logger.error(traceback.format_exc())
            return False

    # 获取工作区列表
    def get_workspaces_list(self):
        try:
            url = urljoin(self.config_data["api_ip_port"], "/api/v1/workspaces")

            response = requests.get(url, headers=self.headers, timeout=(10, 300))
            response.raise_for_status()  # 检查响应的状态码

            result = response.content
            ret = json.loads(result)

            logger.debug(ret)
            if "workspaces" in ret:
                self.workspaces_list = ret["workspaces"]
                return ret["workspaces"]

            logger.error(f"AnythingLLM 获取工作区列表失败: {ret['message']}")
            return None
        except Exception:
            logger.error(traceback.format_exc())
            return None

    def get_resp(self, data):
        """请求对应接口，获取返回值

        Args:
            data (dict): 你的提问

        Returns:
            str: 返回的文本回答
        """
        try:
            url = urljoin(
                self.config_data["api_ip_port"], f"/api/v1/workspace/{self.config_data['workspace_slug']}/chat"
            )

            if "mode" in data:
                mode = data["mode"]
            else:
                mode = self.config_data["mode"]

            data_json = {"message": data["prompt"], "mode": mode}

            response = requests.post(url=url, json=data_json, headers=self.headers, timeout=(10, 300))
            response.raise_for_status()  # 检查响应的状态码

            result = response.content
            ret = json.loads(result)

            logger.debug(ret)

            if "textResponse" in ret:
                return ret["textResponse"]

            logger.error(f"AnythingLLM 对话失败: {ret['message']}")
            return None
        except Exception:
            logger.error(traceback.format_exc())
            return None
