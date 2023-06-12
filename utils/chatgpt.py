import traceback
from copy import deepcopy
import openai

from .common import Common

common = Common()


class Chatgpt:
    # 设置会话初始值
    # session_config = {'msg': [{"role": "system", "content": config_data['chatgpt']['preset']}]}
    session_config = {}
    sessions = {}
    current_key_index = 0
    data_openai = {}
    data_chatgpt = {}

    def __init__(self, data_openai, data_chatgpt):
        # 设置会话初始值
        self.session_config = {'msg': [{"role": "system", "content": data_chatgpt["preset"]}]}
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
            session['msg'].append({"role": "user", "content": msg})

            # 添加当前时间到会话中
            session['msg'][1] = {"role": "system", "content": "current time is:" + common.get_bj_time()}

            # 调用 ChatGPT 接口生成回复消息
            message = self.chat_with_gpt(session['msg'])

            # 如果返回的消息包含最大上下文长度限制，则删除超长上下文并重试
            if message.__contains__("This model's maximum context length is 4096 token"):
                del session['msg'][2:3]
                del session['msg'][len(session['msg']) - 1:len(session['msg'])]
                message = self.chat(msg, sessionid)

            # 将 ChatGPT 返回的回复消息添加到会话中
            session['msg'].append({"role": "assistant", "content": message})

            # 输出会话 ID 和 ChatGPT 返回的回复消息
            print("会话ID: " + str(sessionid))
            print("ChatGPT返回内容: ")
            print(message)

            # 返回 ChatGPT 返回的回复消息
            return message

        # 捕获异常并打印堆栈跟踪信息
        except Exception as error:
            traceback.print_exc()
            return str('异常: ' + str(error))


    def get_chat_session(self, sessionid):
        """
        获取指定 ID 的会话，如果不存在则创建一个新的会话
        :param sessionid: 会话 ID
        :return: 指定 ID 的会话
        """
        sessionid = str(sessionid)
        if sessionid not in self.sessions:
            config = deepcopy(self.session_config)
            config['id'] = sessionid
            config['msg'].append({"role": "system", "content": "current time is:" + common.get_bj_time()})
            self.sessions[sessionid] = config
        return self.sessions[sessionid]


    def chat_with_gpt(self, messages):
        """
        使用 ChatGPT 接口生成回复消息
        :param messages: 上下文消息列表
        :return: ChatGPT 返回的回复消息
        """
        max_length = len(self.data_openai['api_key']) - 1

        try:
            openai.api_base = self.data_openai['api']

            if not self.data_openai['api_key']:
                return "请设置Api Key"
            else:
                # 判断是否所有 API key 均已达到速率限制
                if self.current_key_index > max_length:
                    self.current_key_index = 0
                    return "全部Key均已达到速率限制,请等待一分钟后再尝试"
                openai.api_key = self.data_openai['api_key'][self.current_key_index]

            # 调用 ChatGPT 接口生成回复消息
            resp = openai.ChatCompletion.create(
                model=self.data_chatgpt['model'],
                messages=messages
            )
            resp = resp['choices'][0]['message']['content']

        # 处理 OpenAIError 异常
        except openai.OpenAIError as e:
            if str(e).__contains__("Rate limit reached for default-gpt-3.5-turbo") and self.current_key_index <= max_length:
                self.current_key_index = self.current_key_index + 1
                print("速率限制，尝试切换key")
                return self.chat_with_gpt(messages)
            elif str(e).__contains__(
                    "Your access was terminated due to violation of our policies") and self.current_key_index <= max_length:
                print("请及时确认该Key: " + str(openai.api_key) + " 是否正常，若异常，请移除")

                # 判断是否所有 API key 均已尝试
                if self.current_key_index + 1 > max_length:
                    return str(e)
                else:
                    print("访问被阻止，尝试切换Key")
                    self.current_key_index = self.current_key_index + 1
                    return self.chat_with_gpt(messages)
            else:
                print('openai 接口报错: ' + str(e))
                resp = "openai 接口报错: " + str(e)

        return resp


    # 调用gpt接口，获取返回内容
    def get_gpt_resp(self, user_name, promet):
        # 获取当前用户的会话
        session = self.get_chat_session(str(user_name))
        # 调用 ChatGPT 接口生成回复消息
        resp_content = self.chat(promet, session)

        return resp_content