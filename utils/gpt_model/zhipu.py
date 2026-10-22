import zhipuai
import traceback
import json

import time
import jwt  # 确保这是 PyJWT 库
import requests
from urllib.parse import urljoin
from packaging import version

from utils.common import Common
from utils.my_log import logger

class Zhipu:
    def __init__(self, data):
        self.common = Common()

        self.config_data = data

        # zhipuai库版本
        self.zhipuai_ver = "2.0.0"

        try:
            # 判断zhipu库版本，1.x.x和2.x.x有破坏性更新
            if version.parse(zhipuai.__version__) < version.parse('2.0.0'):
                self.zhipuai_ver = "1.0.0"
                zhipuai.api_key = data["api_key"]
            else:
                self.zhipuai_ver = zhipuai.__version__
                from zhipuai import ZhipuAI
                self.client = ZhipuAI(api_key=data["api_key"])
        except Exception as e:
            self.zhipuai_ver = "1.0.0"
            from zhipuai import ZhipuAI
            self.client = ZhipuAI(api_key=data["api_key"])

        self.model = data["model"]

        # 非SDK
        self.base_url = "https://open.bigmodel.cn"
        self.token = None
        self.headers = None
        if self.model == "应用":
            try:
                self.token = self.generate_token(apikey=self.config_data["api_key"], exp_seconds=30 * 24 * 3600)

                self.headers = {
                    "Authorization": f"Bearer {self.token}",
                }

                url = urljoin(self.base_url, "/api/llm-application/open/application")

                data = {
                    "page": 1,
                    "size": 100
                }

                # get请求
                response = requests.get(url=url, data=data, headers=self.headers)

                logger.debug(response.json())

                resp_json = response.json()

                tmp_content = "智谱应用列表："
            
                for data in resp_json["data"]["list"]:
                    tmp_content += f"\n应用名：{data['name']}，应用ID：{data['id']}，知识库：{data['knowledge_ids']}"

                logger.info(tmp_content)
            except Exception as e:
                logger.error(traceback.format_exc())
        elif self.model == "智能体":
            self.assistant_api_conversation_id = None
            self.assistant_api_token = self.get_assistant_api_token(self.config_data["assistant_api"]["api_key"], self.config_data["assistant_api"]["api_secret"])
            if self.assistant_api_token:
                logger.info("智谱AI 智能体 API Token获取成功")

        self.history = []

    # 智能体 获取token
    def get_assistant_api_token(self, api_key, api_secret):
        try:
            url = urljoin("https://chatglm.cn", "/chatglm/assistant-api/v1/get_token")

            data = {
                "api_key": api_key,
                "api_secret": api_secret
            }

            # logger.debug(f"url={url}, data={data}")

            # get请求
            response = requests.post(url=url, json=data)

            # 获取状态码
            status_code = response.status_code
            logger.debug(status_code)

            if status_code == 200:
                logger.debug(response.json())

                resp_json = response.json()

                access_token = resp_json["result"]["access_token"]

                return access_token
            else:
                logger.error(f"获取 智谱AI 智能体 鉴权失败, status_code={status_code}")
                return None
        except Exception as e:
            logger.error(traceback.format_exc())
            return None



    def invoke_example(self, prompt):
        response = zhipuai.model_api.invoke(
            model=self.model,
            prompt=prompt,
            top_p=float(self.config_data["top_p"]),
            temperature=float(self.config_data["temperature"]),
        )
        # logger.info(response)

        return response
    
    def invoke_characterglm(self, prompt):
        response = zhipuai.model_api.invoke(
            model=self.model,
            prompt=prompt,
            meta={
                "user_info": self.config_data["user_info"],
                "bot_info": self.config_data["bot_info"],
                "bot_name": self.config_data["bot_name"],
                "username": self.config_data["username"]
            },
            top_p=float(self.config_data["top_p"]),
            temperature=float(self.config_data["temperature"]),
        )
        # logger.info(response)

        return response

    '''
    说明：
    add: 事件流开启
    error: 平台服务或者模型异常，响应的异常事件
    interrupted: 中断事件，例如：触发敏感词
    finish: 数据接收完毕，关闭事件流
    '''

    # 非SDK鉴权
    def generate_token(self, apikey: str, exp_seconds: int):
        try:
            id, secret = apikey.split(".")
        except Exception as e:
            raise Exception("invalid apikey", e)

        payload = {
            "api_key": id,
            "exp": int(round(time.time())) + exp_seconds,  # PyJWT中exp字段期望的是秒级的时间戳
            "timestamp": int(round(time.time() * 1000)),  # 如果需要毫秒级时间戳，可以保留这一行
        }

        # 使用PyJWT编码payload
        token = jwt.encode(
            payload,
            secret,
            headers={"alg": "HS256", "sign_type": "SIGN"}
        )

        return token

    # 同步调用zhipu api
    def get_zhipu_resp(self, data):
        """请求对应接口，获取返回值

        Args:
            data (dict): zhipu的配置 模型、msg等

        Returns:
            dict: 返回数据
        """
        try:
            response = self.client.chat.completions.create(
                model=data["model"],  # 填写需要调用的模型名称
                messages=data["messages"],
                meta=data.get("meta", None),
                top_p=float(self.config_data["top_p"]),
                temperature=float(self.config_data["temperature"]),
                stream=data["stream"],
            )
        except Exception as e:
            logger.error(traceback.format_exc())
            return None

        return response


    def get_resp(self, prompt, stream=False):
        """请求对应接口，获取返回值

        Args:
            prompt (str): 你的提问
            stream (bool, optional): 是否流式返回. Defaults to False.

        Returns:
            str: 返回的文本回答
        """
        try:
            if version.parse(self.zhipuai_ver) < version.parse('2.0.0'):
                if self.config_data["history_enable"]:
                    self.history.append({"role": "user", "content": prompt})
                    data_json = self.history
                else:
                    data_json = [{"role": "user", "content": prompt}]

                logger.debug(f"data_json={data_json}")
                
                if self.model == "characterglm":
                    ret = self.invoke_characterglm(data_json)
                elif self.model == "应用":
                    url = urljoin(self.base_url, f"/api/llm-application/open/model-api/{self.config_data['app_id']}/invoke")

                    self.history.append({"role": "user", "content": prompt})
                    data = {
                        "prompt": self.history,
                        "returnType": "json_string",
                        # "knowledge_ids": [],
                        # "document_ids": []
                    }

                    response = requests.post(url=url, json=data, headers=self.headers)

                    try:
                        resp_json = response.json()

                        logger.debug(resp_json)

                        resp_content = resp_json["data"]["content"]

                        # 启用历史就给我记住！
                        if self.config_data["history_enable"]:
                            # 把机器人回答添加到历史记录中
                            self.history.append({"role": "assistant", "content": resp_content})

                            while True:
                                # 获取嵌套列表中所有字符串的字符数
                                total_chars = sum(len(string) for sublist in self.history for string in sublist)
                                # 如果大于限定最大历史数，就剔除第1 2个元素
                                if total_chars > int(self.config_data["history_max_len"]):
                                    self.history.pop(0)
                                    self.history.pop(0)
                                else:
                                    break

                        return resp_content
                    except Exception as e:
                        def is_odd(number):
                            # 检查数除以2的余数是否为1
                            return number % 2 != 0
                        
                        # 保持history始终为偶数个
                        if is_odd(len(self.history)):
                            self.history.pop(0)

                        logger.error(traceback.format_exc())
                        return None
                    
                else:
                    ret = self.invoke_example(data_json)

                logger.debug(f"ret={ret}")

                if False == ret['success']:
                    logger.error(f"请求智谱ai失败，错误代码：{ret['code']}，{ret['msg']}")
                    return None

                # 启用历史就给我记住！
                if self.config_data["history_enable"]:
                    while True:
                        # 获取嵌套列表中所有字符串的字符数
                        total_chars = sum(len(string) for sublist in self.history for string in sublist)
                        # 如果大于限定最大历史数，就剔除第一个元素
                        if total_chars > int(self.config_data["history_max_len"]):
                            self.history.pop(0)
                        else:
                            self.history.append(ret['data']['choices'][0])
                            break

                return ret['data']['choices'][0]['content']
            else:
                if self.model == "应用":
                    url = urljoin(self.base_url, f"/api/llm-application/open/model-api/{self.config_data['app_id']}/invoke")

                    self.history.append({"role": "user", "content": prompt})
                    data = {
                        "prompt": self.history,
                        "returnType": "json_string",
                        # "knowledge_ids": [],
                        # "document_ids": []
                    }

                    response = requests.post(url=url, json=data, headers=self.headers)

                    try:
                        resp_json = response.json()

                        logger.debug(resp_json)

                        resp_content = resp_json["data"]["content"]

                        # 启用历史就给我记住！
                        if self.config_data["history_enable"]:
                            # 把机器人回答添加到历史记录中
                            self.history.append({"role": "assistant", "content": resp_content})

                            while True:
                                # 获取嵌套列表中所有字符串的字符数
                                total_chars = sum(len(string) for sublist in self.history for string in sublist)
                                # 如果大于限定最大历史数，就剔除第1 2个元素
                                if total_chars > int(self.config_data["history_max_len"]):
                                    self.history.pop(0)
                                    self.history.pop(0)
                                else:
                                    break

                        return resp_content
                    except Exception as e:
                        def is_odd(number):
                            # 检查数除以2的余数是否为1
                            return number % 2 != 0
                        
                        # 保持history始终为偶数个
                        if is_odd(len(self.history)):
                            self.history.pop(0)

                        logger.error(traceback.format_exc())
                        return None
                elif self.model == "智能体":
                    headers = {
                        "Authorization": f"Bearer {self.assistant_api_token}",
                        "Content-Type": "application/json"
                    }

                    data = {
                        "assistant_id": self.config_data["assistant_api"]["assistant_id"],
                        "conversation_id": self.assistant_api_conversation_id,
                        "prompt": prompt,
                        "meta_data": None
                    }

                    if stream:
                        url = urljoin("https://chatglm.cn", "/chatglm/assistant-api/v1/stream")

                        response = requests.post(url, json=data, headers=headers)

                        if response is None:
                            return None
                        return response
                    else:
                        url = urljoin("https://chatglm.cn", "/chatglm/assistant-api/v1/stream_sync")

                        response = requests.post(url=url, json=data, headers=headers)
                        status_code = response.status_code
                        # print(status_code)

                        if status_code == 200:
                            try:
                                resp_json = response.json()
                                logger.debug(json.dumps(resp_json, ensure_ascii=True, indent=4))

                                # 启用历史就给我记住！
                                if self.config_data["history_enable"]:
                                    # 更新上下文ID
                                    self.assistant_api_conversation_id = resp_json["result"]["conversation_id"]
                                resp_content = resp_json["result"]["output"][-1]["content"][0]["text"]

                                logger.debug(resp_content)

                                return resp_content
                            except Exception as e:
                                logger.error(traceback.format_exc())
                                return None
                        else:
                            logger.error(f"请求智谱AI 智能体 失败, status_code={status_code}")
                            return None
                else:
                    if self.config_data["history_enable"]:
                        import copy 
                        tmp_msg = copy.copy(self.history)
                        tmp_msg.append({"role": "user", "content": prompt})
                        logger.debug(f"tmp_msg={tmp_msg}")

                        if self.model == "charglm-3":
                            response = self.get_zhipu_resp(
                                { 
                                    "model": self.model,  # 填写需要调用的模型名称
                                    "messages": tmp_msg,
                                    "meta": {
                                        "user_info": self.config_data["user_info"],
                                        "bot_info": self.config_data["bot_info"],
                                        "bot_name": self.config_data["bot_name"],
                                        "username": self.config_data["username"]
                                    },
                                    "stream": stream
                                }
                            )
                        else:
                            response = self.get_zhipu_resp(
                                { 
                                    "model": self.model,  # 填写需要调用的模型名称
                                    "messages": tmp_msg,
                                    "stream": stream
                                }
                            )
                    else:
                        if self.model == "charglm-3":
                            response = self.get_zhipu_resp(
                                { 
                                    "model": self.model,  # 填写需要调用的模型名称
                                    "messages": [
                                        {
                                            "role": "user",
                                            "content": prompt
                                        }
                                    ],
                                    "meta": {
                                        "user_info": self.config_data["user_info"],
                                        "bot_info": self.config_data["bot_info"],
                                        "bot_name": self.config_data["bot_name"],
                                        "username": self.config_data["username"]
                                    },
                                    "stream": stream
                                }
                            )
                        else:
                            response = self.get_zhipu_resp(
                                { 
                                    "model": self.model,  # 填写需要调用的模型名称
                                    "messages": [
                                        {
                                            "role": "user",
                                            "content": prompt
                                        }
                                    ],
                                    "stream": stream
                                }
                            )

                    if response is None:
                        return None
                    
                    if stream:
                        # 返回响应
                        return response
            
                    resp_content = response.choices[0].message.content.strip()

                    # 启用历史就给我记住！
                    if self.config_data["history_enable"]:
                        while True:
                            # 获取嵌套列表中所有字符串的字符数
                            total_chars = sum(len(string) for sublist in self.history for string in sublist)
                            # 如果大于限定最大历史数，就剔除第1 2个元素
                            if total_chars > int(self.config_data["history_max_len"]):
                                self.history.pop(0)
                                self.history.pop(0)
                            else:
                                self.history.append({"role": "user", "content": prompt})
                                self.history.append({"role": "assistant", "content": resp_content})
                                break
                    
                    return resp_content
        except Exception as e:
            logger.error(traceback.format_exc())
            return None

    # 图像识别模型调用，需要zhipuai库大于1.x.x
    def get_resp_with_img(self, prompt, img_data):
        try:
            # 检查 img_data 的类型
            if isinstance(img_data, str):  # 如果是字符串，假定为文件路径
                import base64

                # 读取本地图片文件
                with open(img_data, "rb") as image_file:
                    # 将图片内容转换为base64编码
                    img = base64.b64encode(image_file.read()).decode("utf-8")
            else:
                img = img_data

            response = self.client.chat.completions.create(
                model="glm-4v-plus",  # 填写需要调用的模型名称
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url" : img
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )

            if response is None:
                return None

            resp_content = response.choices[0].message.content.strip()
        
            logger.debug(f"resp_content={resp_content}")

            return resp_content
        except Exception as e:
            logger.error(traceback.format_exc())
            return None

    # 添加AI返回消息到会话，用于提供上下文记忆
    def add_assistant_msg_to_session(self, prompt, message):
        try:
            # 启用历史就给我记住！
            if self.config_data["history_enable"]:
                while True:
                    # 获取嵌套列表中所有字符串的字符数
                    total_chars = sum(len(string) for sublist in self.history for string in sublist)
                    # 如果大于限定最大历史数，就剔除第1 2个元素
                    if total_chars > int(self.config_data["history_max_len"]):
                        self.history.pop(0)
                        self.history.pop(0)
                    else:
                        self.history.append({"role": "user", "content": prompt})
                        self.history.append({"role": "assistant", "content": message})
                        break

            logger.debug(f"history={self.history}")

            return {"ret": True}
        except Exception as e:
            logger.error(traceback.format_exc())
            return {"ret": False}

if __name__ == '__main__':
    # 配置日志输出格式
    logger.basicConfig(
        level=logger.DEBUG,  # 设置日志级别，可以根据需求调整
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    data = {
        "api_key": "",
        "app_id": "1761340125461340161",
        # chatglm_pro/chatglm_std/chatglm_lite/characterglm /glm-3-turbo/glm-4/charglm-3
        "model": "chatglm_lite",
        "top_p": 0.7,
        "temperature": 0.9,
        "history_enable": True,
        "history_max_len": 300,
        "user_info": "我是陆星辰，是一个男性，是一位知名导演，也是苏梦远的合作导演。我擅长拍摄音乐题材的电影。苏梦远对我的态度是尊敬的，并视我为良师益友。",
        "bot_info": "苏梦远，本名苏远心，是一位当红的国内女歌手及演员。在参加选秀节目后，凭借独特的嗓音及出众的舞台魅力迅速成名，进入娱乐圈。她外表美丽动人，但真正的魅力在于她的才华和勤奋。苏梦远是音乐学院毕业的优秀生，善于创作，拥有多首热门原创歌曲。除了音乐方面的成就，她还热衷于慈善事业，积极参加公益活动，用实际行动传递正能量。在工作中，她对待工作非常敬业，拍戏时总是全身心投入角色，赢得了业内人士的赞誉和粉丝的喜爱。虽然在娱乐圈，但她始终保持低调、谦逊的态度，深得同行尊重。在表达时，苏梦远喜欢使用“我们”和“一起”，强调团队精神。",
        "bot_name": "苏梦远",
        "username": "陆星辰",
        "remove_useless": True
    }

    zhipu = Zhipu(data)

    # logger.info(zhipu.get_resp("你可以扮演猫娘吗，每句话后面加个喵"))
    # logger.info(zhipu.get_resp("早上好"))
    # logger.info(zhipu.get_resp("你是谁"))

    logger.info(zhipu.get_resp_with_img("判断图片内容", "E:\\GitHub_pro\\AI-Vtuber\\docs\\xmind.png"))
