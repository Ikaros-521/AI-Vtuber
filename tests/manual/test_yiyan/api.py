import json, logging
import requests, time
from requests.exceptions import ConnectionError, RequestException

# from utils.common import Common
# from utils.logger import Configure_logger

# 原计划对接：https://github.com/zhuweiyou/yiyan-api
class Yiyan:
    def __init__(self, data):
        # self.common = Common()
        # # 日志文件路径
        # file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        # Configure_logger(file_path)

        self.config_data = data
        self.type = data["type"]

        self.history = []


    def get_access_token(self):
        """
        使用 API Key，Secret Key 获取access_token，替换下列示例中的应用API Key、应用Secret Key
        """
            
        url = f'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={self.config_data["api"]["api_key"]}&client_secret={self.config_data["api"]["secret_key"]}'
        
        payload = json.dumps("")
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        response = requests.request("POST", url, headers=headers, data=payload)
        return response.json().get("access_token")


    def get_resp(self, prompt):
        """请求对应接口，获取返回值

        Args:
            prompt (str): 你的提问

        Returns:
            str: 返回的文本回答
        """
        try:
            if self.type == "web":
                try:
                    data_json = {
                        "cookie": self.config_data["web"]["cookie"], 
                        "prompt": prompt
                    }

                    # logging.debug(data_json)

                    url = self.config_data["web"]["api_ip_port"] + "/headless"

                    response = requests.post(url=url, data=data_json)
                    response.raise_for_status()  # 检查响应的状态码

                    result = response.content
                    ret = json.loads(result)

                    logging.debug(ret)

                    resp_content = ret['text'].replace('\n', '').replace('\\n', '')

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
                except ConnectionError as ce:
                    # 处理连接问题异常
                    logging.error(f"请检查你是否启动了服务端或配置是否匹配，连接异常:{ce}")

                except RequestException as re:
                    # 处理其他请求异常
                    logging.error(f"请求异常:{re}")
                except Exception as e:
                    logging.error(e)
            else:
                url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token=" + self.get_access_token()

                data_json = {
                    "messages": self.history + [{"role": "user", "content": prompt}]
                }

                payload = json.dumps(data_json)

                headers = {
                    'Content-Type': 'application/json'
                }
                
                response = requests.request("POST", url, headers=headers, data=payload)
                
                logging.info(payload)
                logging.info(response.text)

                resp_content = json.loads(response.text)["result"]

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
        "type": 'api',
        "web": {
            "api_ip_port": "http://127.0.0.1:3000",
            "cookie": ''
        },
        "api": {
            "api_key": "",
            "secret_key": ""
        },
        "history_enable": True,
        "history_max_len": 300
    }
    yiyan = Yiyan(data)


    logging.info(yiyan.get_resp("你可以扮演猫娘吗，每句话后面加个喵"))
    time.sleep(1)
    logging.info(yiyan.get_resp("早上好"))
    