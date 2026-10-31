import json, logging
import re, requests
import traceback

from utils.common import Common
from utils.logger import Configure_logger


class Custom_LLM:
    def __init__(self, data):
        self.config_data = data
        self.common = Common()
        # 日志文件路径
        # file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        # Configure_logger(file_path)

        self.history = []

    def parse_headers(self, headers_text):
        headers = {}
        for line in headers_text.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()
        return headers

    def replace_variables(self, text, variables):
        for key, value in variables.items():
            text = re.sub(f'{{{{{key}}}}}', value, text)
        return text

    def send_request(self, url="", method='GET', headers=None, body_type="json", body=None, resp_data_type="json", proxies=None, timeout=60):
        """
        发送 HTTP 请求并返回结果

        Parameters:
            url (str): 请求的 URL
            method (str): 请求方法，'GET' 或 'POST'
            headers (str): 请求头（每行一个键值对，如：Content-Type: application/json）
            body (str): 请求体
            resp_data_type (str): 返回数据的类型（json | content）
            proxies (dict): 代理配置
            timeout (int): 请求超时时间

        Returns:
            dict|str: 包含响应的 JSON数据 | 字符串数据
        """

        try:
            if body_type == "json":
                body = json.loads(body)
                response = requests.request(method=method, url=url, headers=headers, json=body, proxies=proxies, timeout=timeout)
            else:
                body = body.encode('utf-8')
                response = requests.request(method=method, url=url, headers=headers, data=body, proxies=proxies, timeout=timeout)
            logging.info(f'response.content={response.content}')

            if resp_data_type == "json":
                # 解析响应的 JSON 数据
                result = response.json()
            else:
                result = response.content
                # 使用 'utf-8' 编码来解码字节串
                result = result.decode('utf-8')

            return result

        except requests.exceptions.RequestException as e:
            logging.error(traceback.format_exc())
            logging.error(f"请求出错: {e}")
            return None


    def get_resp(self, data):
        """请求对应接口，获取返回值

        Args:
            data (dcit): 请求参数

        Returns:
            str: 返回的文本回答
        """
        try:
            variables = {
                "cur_time": self.common.get_bj_time(0),
                "prompt": data['prompt'],
            }

            url = self.replace_variables(self.config_data['url'], variables)
            method = self.config_data['method']
            body_type = self.config_data['body_type']
            body = self.replace_variables(self.config_data['body'], variables)
            resp_data_type = self.config_data['resp_data_type']
            headers = self.parse_headers(self.replace_variables(self.config_data['headers'], variables))
            data_analysis = self.config_data['data_analysis']
            resp_template = self.config_data['resp_template']
            if self.config_data['proxies'] == '':
                proxies = None
            else:
                proxies = json.loads(self.config_data['proxies'])

            logging.info(f"url={url}\nheaders={headers}\nbody={body}")

            resp = self.send_request(url=url, method=method, headers=headers, body_type=body_type, body=body, resp_data_type=resp_data_type, proxies=proxies, timeout=60)
            if resp is None:
                return None
                
            # 使用 eval() 执行字符串表达式并获取结果
            resp_content = eval(data_analysis)

            variables = {
                'cur_time': self.common.get_bj_time(5),
                'data': resp_content
            }

            # 使用字典进行字符串替换
            if any(var in resp_template for var in variables):
                resp_content = resp_template.format(**{var: value for var, value in variables.items() if var in resp_template})

            return resp_content
        except Exception as e:
            logging.error(traceback.format_exc())
            return None


# 测试用
if __name__ == '__main__':
    # 配置日志输出格式
    logging.basicConfig(
        level=logging.DEBUG,  # 设置日志级别，可以根据需求调整
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    data = {
        "url": "http://127.0.0.1:11434/v1/chat/completions",
        "headers": "Content-Type:application/json\nAuthorization:Bearer sk",
        "method": "POST",
        "proxies": "{}",
        "body_type": "json",
        "body": "{\"model\":\"qwen:latest\",\"messages\":[{\"role\":\"user\",\"content\":\"{{prompt}}\"}]}",
        "resp_data_type": "json",
        "data_analysis": "resp[\"choices\"][0][\"message\"][\"content\"]",
        "resp_template": "{data}"
    }

    custom_llm = Custom_LLM(data)

    logging.info(custom_llm.get_resp({"prompt": "早上好"}))
    