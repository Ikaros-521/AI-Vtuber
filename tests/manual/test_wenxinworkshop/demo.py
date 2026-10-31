import json, logging, traceback
from wenxinworkshop import LLMAPI, EmbeddingAPI, PromptTemplateAPI
from wenxinworkshop import Message, Messages, Texts

# 前往官网：https://cloud.baidu.com/product/wenxinworkshop 申请服务获取

class My_WenXinWorkShop:
    def __init__(self, data):
        # self.common = Common()
        # # 日志文件路径
        # file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        # Configure_logger(file_path)

        self.config_data = data
        self.history = []

        try:
            model_url_map = {
                "ERNIEBot": LLMAPI.ERNIEBot,
                "ERNIEBot_turbo": LLMAPI.ERNIEBot_turbo,
                "ERNIEBot_4_0": LLMAPI.ERNIEBot_4_0,
                "BLOOMZ_7B": LLMAPI.BLOOMZ_7B,
                "LLAMA_2_7B": LLMAPI.LLAMA_2_7B,
                "LLAMA_2_13B": LLMAPI.LLAMA_2_13B,
                "LLAMA_2_70B": LLMAPI.LLAMA_2_70B,
                "ERNIEBot_4_0": LLMAPI.ERNIEBot_4_0,
                "QIANFAN_BLOOMZ_7B_COMPRESSED": LLMAPI.QIANFAN_BLOOMZ_7B_COMPRESSED,
                "QIANFAN_CHINESE_LLAMA_2_7B": LLMAPI.QIANFAN_CHINESE_LLAMA_2_7B,
                "CHATGLM2_6B_32K": LLMAPI.CHATGLM2_6B_32K,
                "AQUILACHAT_7B": LLMAPI.AQUILACHAT_7B,
                "ERNIE_BOT_8K": LLMAPI.ERNIE_BOT_8K,
                "CODELLAMA_7B_INSTRUCT": LLMAPI.CODELLAMA_7B_INSTRUCT,
                "XUANYUAN_70B_CHAT": LLMAPI.XUANYUAN_70B_CHAT,
                "CHATLAW": LLMAPI.QIANFAN_BLOOMZ_7B_COMPRESSED,
                "QIANFAN_BLOOMZ_7B_COMPRESSED": LLMAPI.CHATLAW,
            }

            selected_model = self.config_data["model"]
            if selected_model in model_url_map:
                self.my_bot = LLMAPI(
                    api_key=self.config_data["api_key"],
                    secret_key=self.config_data["secret_key"],
                    url=model_url_map[selected_model]
                )
        except Exception as e:
            logging.error(traceback.format_exc())



    def get_resp(self, prompt):
        """请求对应接口，获取返回值

        Args:
            prompt (str): 你的提问

        Returns:
            str: 返回的文本回答
        """
        try:
            # create messages
            messages: Messages = []
            
            for history in self.history:
                messages.append(Message(
                    role=history["role"],
                    content=history["content"]
                ))

            messages.append(Message(
                role='user',
                content=prompt
            ))

            logging.info(f"self.history={self.history}")

            # get response from LLM API
            resp_content = self.my_bot(
                messages=messages,
                temperature=self.config_data["temperature"],
                top_p=self.config_data["top_p"],
                penalty_score=self.config_data["penalty_score"],
                stream=None,
                user_id=None,
                chunk_size=512
            )

            # 启用历史就给我记住！
            if self.config_data["history_enable"]:
                while True:
                    # 获取嵌套列表中所有字符串的字符数
                    total_chars = sum(len(item['content']) for item in self.history if 'content' in item)
                    # 如果大于限定最大历史数，就剔除第一个元素
                    if total_chars > self.config_data["history_max_len"]:
                        self.history.pop(0)
                        self.history.pop(0)
                    else:
                        # self.history.pop()
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
        "model": "ERNIEBot",
        "api_key": "",
        "secret_key": "",
        "top_p": 0.8,
        "temperature": 0.9,
        "penalty_score": 1.0,
        "history_enable": True,
        "history_max_len": 300
    }

    # 实例化并调用
    my_wenxinworkshop = My_WenXinWorkShop(data)
    logging.info(my_wenxinworkshop.get_resp("你可以扮演猫娘吗，每句话后面加个喵"))
    logging.info(my_wenxinworkshop.get_resp("早上好"))
