import threading
import traceback
from collections import OrderedDict
from copy import deepcopy
import openai
from packaging import version

from luna.common.helpers import Common
from luna.infra.my_log import logger


class Chatgpt:
    # 设置会话初始值
    # session_config = {'msg': [{"role": "system", "content": config_data['chatgpt']['preset']}]}
    session_config: dict = {}
    # sessionid 用的是观众名，一场直播下来会有几万个不同的 key，每个 key 还挂着
    # 一条只会变长的 msg 历史。装不下时按「最久没开口」丢一条，不掉线的观众不受影响。
    MAX_SESSIONS = 10000
    sessions: OrderedDict = OrderedDict()
    sessions_lock = threading.Lock()
    current_key_index = 0
    data_openai: dict = {}
    data_chatgpt: dict = {}

    def __init__(self, data_openai, data_chatgpt):
        self.common = Common()
        # 设置会话初始值
        self.session_config = {"msg": [{"role": "system", "content": data_chatgpt["preset"]}]}
        self.data_openai = data_openai
        self.data_chatgpt = data_chatgpt

    # chatgpt相关
    def chat(self, msg, sessionid):
        """
        ChatGPT 对话函数
        :param msg: 用户输入的消息
        :param sessionid: 当前会话 ID
        :return: ChatGPT 返回的回复内容
        """
        try:
            # 获取当前会话
            session = self.get_chat_session(sessionid)

            # 将用户输入的消息添加到会话中
            session["msg"].append({"role": "user", "content": msg})

            # 添加当前时间到会话中
            session["msg"][1] = {"role": "system", "content": "current time is:" + self.common.get_bj_time()}

            # 调用 ChatGPT 接口生成回复消息
            message = self.chat_with_gpt(session["msg"])

            if message is None:
                return None

            # 如果返回的消息包含最大上下文长度限制，则删除超长上下文并重试
            if message.__contains__("This model's maximum context length is 409"):
                # 只丢对话轮次，留着开头两条 system（预设人设 + 当前时间）。
                # 原来删的是 [0:3]，把两条 system 和刚加的 user 全删了，重试那次
                # 给只有 1 个元素的列表做 msg[1] = ... 直接 IndexError，
                # 撞上上下文超长就永远只会返回 None
                del session["msg"][2:]
                # 重试那一次自己会把 assistant 回复写回会话，所以这里必须直接返回，
                # 再往下走会又 append 一遍，历史里留下两条一模一样的回复
                return self.chat(msg, sessionid)

            # 将 ChatGPT 返回的回复消息添加到会话中
            session["msg"].append({"role": "assistant", "content": message})

            # 输出会话 ID 和 ChatGPT 返回的回复消息
            logger.info("会话ID: " + str(sessionid))
            logger.debug("ChatGPT返回内容: ")
            logger.debug(message)

            # 返回 ChatGPT 返回的回复消息
            return message

        # 捕获异常并打印堆栈跟踪信息
        except Exception:
            logger.error(traceback.format_exc())
            return None

    def get_chat_session(self, sessionid):
        """
        获取指定 ID 的会话，如果不存在则创建一个新的会话
        :param sessionid: 会话 ID
        :return: 指定 ID 的会话
        """
        sessionid = str(sessionid)
        # sessions 是类属性、跨实例共享，聊天页和弹幕处理会同时碰它
        with Chatgpt.sessions_lock:
            session = Chatgpt.sessions.get(sessionid)
            if session is not None:
                # 用过就挪到末尾，淘汰时丢的是最久没开口的观众，不是最早进直播间的那个
                Chatgpt.sessions.move_to_end(sessionid)
                return session

            config = deepcopy(self.session_config)
            config["id"] = sessionid
            config["msg"].append({"role": "system", "content": "current time is:" + self.common.get_bj_time()})
            Chatgpt.sessions[sessionid] = config

            while len(Chatgpt.sessions) > self.MAX_SESSIONS:
                Chatgpt.sessions.popitem(last=False)

            return Chatgpt.sessions[sessionid]

    def chat_with_gpt(self, messages):
        """
        使用 ChatGPT 接口生成回复消息
        :param messages: 上下文消息列表
        :return: ChatGPT 返回的回复消息
        """
        max_length = len(self.data_openai["api_key"]) - 1

        try:
            openai.api_base = self.data_openai["api"]

            if not self.data_openai["api_key"]:
                logger.error("请设置openai Api Key")
                return None
            else:
                # 判断是否所有 API key 均已达到速率限制
                if self.current_key_index > max_length:
                    self.current_key_index = 0
                    logger.warning("全部Key均已达到速率限制,请等待一分钟后再尝试")
                    return None
                openai.api_key = self.data_openai["api_key"][self.current_key_index]

            logger.debug(f"openai.__version__={openai.__version__}")

            # 判断openai库版本，1.x.x和0.x.x有破坏性更新
            if version.parse(openai.__version__) < version.parse("1.0.0"):
                # 调用 ChatGPT 接口生成回复消息
                resp = openai.ChatCompletion.create(model=self.data_chatgpt["model"], messages=messages, timeout=30)

                resp = resp["choices"][0]["message"]["content"]
            else:
                logger.debug(f"base_url={openai.api_base}, api_key={openai.api_key}")

                client = openai.OpenAI(base_url=openai.api_base, api_key=openai.api_key)
                # 调用 ChatGPT 接口生成回复消息
                resp = client.chat.completions.create(model=self.data_chatgpt["model"], messages=messages, timeout=30)

                resp = resp.choices[0].message.content
        # 处理 OpenAIError 异常
        except openai.OpenAIError as e:
            if (
                str(e).__contains__("Rate limit reached for default-gpt-3.5-turbo")
                and self.current_key_index <= max_length
            ):
                self.current_key_index = self.current_key_index + 1
                logger.warning("速率限制，尝试切换key")
                msg = self.chat_with_gpt(messages)
                return msg
            elif (
                str(e).__contains__("Your access was terminated due to violation of our policies")
                and self.current_key_index <= max_length
            ):
                logger.warning("请及时确认该Key: " + str(openai.api_key) + " 是否正常，若异常，请移除")

                # 判断是否所有 API key 均已尝试
                if self.current_key_index + 1 > max_length:
                    return str(e)
                else:
                    logger.warning("访问被阻止，尝试切换Key")
                    self.current_key_index = self.current_key_index + 1
                    msg = self.chat_with_gpt(messages)
                    return msg
            else:
                logger.error("openai 接口报错: " + str(e))
                return None

        return resp

    def chat_stream(self, msg, sessionid):
        """
        ChatGPT 流式对话函数
        :param msg: 用户输入的消息
        :param sessionid: 当前会话 ID
        :return: resp - 响应消息
        """
        try:
            # 获取当前会话
            session = self.get_chat_session(sessionid)

            # 将用户输入的消息添加到会话中
            session["msg"].append({"role": "user", "content": msg})

            # 添加当前时间到会话中
            session["msg"][1] = {"role": "system", "content": "current time is:" + self.common.get_bj_time()}

            # logger.warning(sessionid)
            # logger.warning(session)

            messages = session["msg"]

            max_length = len(self.data_openai["api_key"]) - 1

            openai.api_base = self.data_openai["api"]

            if not self.data_openai["api_key"]:
                logger.error("请设置openai Api Key")
                return None
            else:
                # 判断是否所有 API key 均已达到速率限制
                if self.current_key_index > max_length:
                    self.current_key_index = 0
                    logger.warning("全部Key均已达到速率限制,请等待一分钟后再尝试")
                    return None
                openai.api_key = self.data_openai["api_key"][self.current_key_index]

            logger.debug(f"openai.__version__={openai.__version__}")

            # 判断openai库版本，1.x.x和0.x.x有破坏性更新
            if version.parse(openai.__version__) < version.parse("1.0.0"):
                # 调用 ChatGPT 接口生成回复消息
                resp = openai.ChatCompletion.create(
                    model=self.data_chatgpt["model"],
                    messages=messages,
                    timeout=30,
                    stream=True,
                )

            else:
                logger.debug(f"base_url={openai.api_base}, api_key={openai.api_key}")

                client = openai.OpenAI(base_url=openai.api_base, api_key=openai.api_key)
                # 调用 ChatGPT 接口生成回复消息
                resp = client.chat.completions.create(
                    model=self.data_chatgpt["model"],
                    messages=messages,
                    timeout=30,
                    stream=True,
                )

            return resp

        except Exception:
            logger.error(traceback.format_exc())
            return None

    # 调用gpt接口，获取返回内容
    def get_gpt_resp(self, username, prompt, stream=False):
        try:
            if not stream:
                # 调用 ChatGPT 接口生成回复消息
                resp_content = self.chat(prompt, username)
            else:
                resp_content = self.chat_stream(prompt, username)

            return resp_content
        except Exception:
            logger.error(traceback.format_exc())
            return None

    # 添加AI返回消息到会话，用于提供上下文记忆
    def add_assistant_msg_to_session(self, username, message):
        try:
            # 获取当前用户的会话
            session = self.get_chat_session(str(username))
            # 将 ChatGPT 返回的回复消息添加到会话中
            session["msg"].append({"role": "assistant", "content": message})

            # logger.warning(str(username))
            # logger.warning(session)

            return {"ret": True}
        except Exception:
            logger.error(traceback.format_exc())
            return {"ret": False}
