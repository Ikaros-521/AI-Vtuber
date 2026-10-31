import json, logging

from xingchen import Configuration, ApiClient, ChatApiSub, ChatReqParams, CharacterKey, Message, UserProfile, \
    ModelParameters, ChatHistoryQueryDTO, ChatHistoryQueryWhere

# 官方文档：https://xingchen.aliyun.com/xingchen/document

class TongYiXingChen:
    def __init__(self, data):
        # self.common = Common()
        # # 日志文件路径
        # file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        # Configure_logger(file_path)

        self.config_data = data
        self.timeout = 60

        self.history = []

        self.api_instance = self.init_client()

    def init_client(self):
        configuration = Configuration(
            host="https://nlp.aliyuncs.com"
        )
        configuration.access_token = self.config_data["access_token"]
        with ApiClient(configuration) as api_client:
            api_instance = ChatApiSub(api_client)
        return api_instance

    def build_chat_param(self, prompt):
        # 是否启用历史记忆
        if self.config_data["history_enable"]:
            messages_list = []
            for data in self.history:
                messages_list.append(
                    Message(
                        name=data['name'],
                        role=data['role'],
                        content=data['content']
                    )
                )
            
            messages_list.append(
                Message(
                    name=self.config_data[self.config_data["type"]]["username"],
                    role='user',
                    content=prompt
                )
            )

            # messages_list.append(
            #     Message(
            #         name=self.config_data[self.config_data["type"]]["role_name"],
            #         role='assistant',
            #         content=prompt
            #     )
            # )
        else:
            messages_list = [
                Message(
                    name=self.config_data[self.config_data["type"]]["username"],
                    role='user',
                    content=prompt
                )
            ]

        logging.info(f"messages_list={messages_list}")

        return ChatReqParams(
            bot_profile=CharacterKey(
                character_id=self.config_data[self.config_data["type"]]["character_id"],
                version=1
            ),
            model_parameters=ModelParameters(
                top_p=self.config_data[self.config_data["type"]]["top_p"],    
                temperature=self.config_data[self.config_data["type"]]["temperature"],
                seed=self.config_data[self.config_data["type"]]["seed"]
            ),
            messages=[
                Message(
                    name=self.config_data[self.config_data["type"]]["username"],
                    role='user',
                    content=prompt
                ),
            ],
            user_profile=UserProfile(
                user_id=self.config_data[self.config_data["type"]]["user_id"],
                username=self.config_data[self.config_data["type"]]["username"]
            )
        )
    
    def chat_histories(self):
        api = self.init_client()
        body = ChatHistoryQueryDTO(
            where=ChatHistoryQueryWhere(
                characterId=self.config_data[self.config_data["type"]]["character_id"],
                bizUserId=self.config_data[self.config_data["type"]]["user_id"],
                sessionId="7ed48d9881b54ed49d6967be7be01743"
                # startTime="1970-01-01T00:00:00.00Z",
                # endTime="1970-01-01T00:00:00.00Z",
                # messageIds=[
                #     "e5bfc3c7809e47c5ac17181250adcf2b"
                # ],

            ),
            orderBy=[
                "gmtCreate desc"
            ],
            pageNum=1,
            pageSize=10
        )

        # 对话历史
        result = api.chat_histories(chat_history_query_dto=body)
        logging.info(result.data)

    # 非流式回复
    def chat_sync(self, prompt):
        chat_param = self.build_chat_param(prompt)
        res = self.api_instance.chat(chat_param, _request_timeout=self.timeout)
        # logging.info(res.to_dict())
        # logging.info(res.to_str())

        return res.to_dict()

    # 流式回复
    def chat_async(self, prompt):
        # 用户对话
        chat_param = self.build_chat_param(prompt)
        chat_param.streaming = True
        responses = self.api_instance.chat(chat_param, _request_timeout=self.timeout)
        for res in responses:
            logging.info(res)

    def get_resp(self, prompt):
        """请求对应接口，获取返回值

        Args:
            prompt (str): 你的提问

        Returns:
            str: 返回的文本回答
        """
        try:
            if self.config_data["type"] == "固定角色":
                try:
                    data_json = self.chat_sync(prompt)

                    resp_content = data_json["data"]["choices"][0]["messages"][0]["content"]

                    # 启用历史就给我记住！
                    if self.config_data["history_enable"]:
                        while True:
                            # 获取嵌套列表中所有字符串的字符数
                            total_chars = sum(len(item['content']) for item in self.history if 'content' in item)
                            # 如果大于限定最大历史数，就剔除第一个元素
                            if total_chars > self.config_data["history_max_len"]:
                                self.history.pop(0)
                            else:
                                # self.history.pop()
                                self.history.append({"role": "user", "name": self.config_data[self.config_data["type"]]["username"], "content": prompt})
                                self.history.append({"role": "assistant", "name": self.config_data[self.config_data["type"]]["role_name"], "content": resp_content})
                                break

                    return resp_content
                except Exception as e:
                    logging.error(e)
            
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
        "access_token": "lm-xxx==",
        "type": "固定角色",
        "固定角色": {
            "character_id": "1b34205ee8814acc9e7acf593e7cf759",
            "top_p": 0.95,
            "temperature": 0.92,
            "seed": 1683806810,
            "user_id": "1",
            "username": "主人",
            "role_name": "伊卡洛斯"
        },
        "history_enable": True,
        "history_max_len": 300
    }

    # 实例化并调用 init_client
    tongyixingchen = TongYiXingChen(data)
    logging.info(tongyixingchen.get_resp("请记住我的话"))
    logging.info(tongyixingchen.get_resp("我刚才说了什么"))
    logging.info(tongyixingchen.get_resp("我刚才说了什么!"))