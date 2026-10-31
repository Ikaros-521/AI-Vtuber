import json, logging
import requests

# from utils.common import Common
# from utils.logger import Configure_logger


class Langchain_ChatGLM:
    def __init__(self, data):
        # self.common = Common()
        # 日志文件路径
        # file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        # Configure_logger(file_path)

        self.api_ip_port = data["api_ip_port"]
        self.chat_type = data["chat_type"]
        self.knowledge_base_id = data["knowledge_base_id"]
        self.history_enable = data["history_enable"]
        self.history_max_len = data["history_max_len"]

        self.history = []


    # 获取知识库列表
    def get_list_knowledge_base(self):
        url = self.api_ip_port + "/local_doc_qa/list_knowledge_base"
        try:
            response = requests.get(url)
            response.raise_for_status()  # 检查响应的状态码

            result = response.content
            ret = json.loads(result)

            logging.debug(ret)
            logging.info(f"本地知识库列表：{ret['data']}")

            return ret['data']
        except Exception as e:
            logging.error(e)
            return None


    def get_resp(self, prompt):
        """请求对应接口，获取返回值

        Args:
            prompt (str): 你的提问

        Returns:
            str: 返回的文本回答
        """
        try:
            if self.chat_type == "模型":
                data_json = {
                    "question": prompt, 
                    "streaming": False,
                    "history": self.history
                }
                url = self.api_ip_port + "/chat"
            elif self.chat_type == "知识库":
                data_json = {
                    "knowledge_base_id": self.knowledge_base_id,
                    "question": prompt, 
                    "streaming": False,
                    "history": self.history
                }

                url = self.api_ip_port + "/local_doc_qa/local_doc_chat"
            elif self.chat_type == "必应":
                data_json = {
                    "question": prompt, 
                    "history": self.history
                }

                url = self.api_ip_port + "/local_doc_qa/bing_search_chat"
            else:
                data_json = {
                    "question": prompt, 
                    "streaming": False,
                    "history": self.history
                }
                url = self.api_ip_port + "/chat"

            response = requests.post(url=url, json=data_json)
            response.raise_for_status()  # 检查响应的状态码

            result = response.content
            ret = json.loads(result)

            logging.debug(ret)
            if self.chat_type == "问答库" or self.chat_type == "必应":
                logging.info(f'源自：{ret["source_documents"]}')

            resp_content = ret['response']

            # 启用历史就给我记住！
            if self.history_enable:
                while True:
                    # 获取嵌套列表中所有字符串的字符数
                    total_chars = sum(len(string) for sublist in self.history for string in sublist)
                    # 如果大于限定最大历史数，就剔除第一个元素
                    if total_chars > self.history_max_len:
                        self.history.pop(0)
                    else:
                        self.history.append(ret['history'][-1])
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
        "api_ip_port": "http://127.0.0.1:7861",
        # 模型/知识库/必应
        "chat_type": "必应",
        "knowledge_base_id": "ikaros",
        "history_enable": True,
        "history_max_len": 300
    }
    langchain_chatglm = Langchain_ChatGLM(data)


    if data["chat_type"] == "模型":
        logging.info(langchain_chatglm.get_resp("你可以扮演猫娘吗，每句话后面加个喵"))
        logging.info(langchain_chatglm.get_resp("早上好"))
    elif data["chat_type"] == "知识库":  
        langchain_chatglm.get_list_knowledge_base()
        logging.info(langchain_chatglm.get_resp("伊卡洛斯喜欢谁"))
    # please set BING_SUBSCRIPTION_KEY and BING_SEARCH_URL in os ENV
    elif data["chat_type"] == "必应":  
        logging.info(langchain_chatglm.get_resp("伊卡洛斯是谁"))
    