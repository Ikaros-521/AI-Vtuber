import json
import os
import logging

from utils.config import Config
from utils.common import Common
from utils.audio import Audio


class My_handle():
    common = None
    config = None
    audio = None

    room_id = None
    proxy = None
    # proxy = {
    #     "http": "http://127.0.0.1:10809",
    #     "https": "http://127.0.0.1:10809"
    # }
    session_config = None
    sessions = {}
    current_key_index = 0

    # 直播间号
    room_id = None

    before_promet = None
    after_promet = None

    # 敏感词数据路径
    badwords_path = None

    # 最大阅读单词数
    max_len = None
    # 最大阅读字符数
    max_char_len = None

    chat_type = None

    need_lang = None

    # openai
    openai_config = None
    # chatgpt
    chatgpt_config = None
    # claude
    claude_config = None
    # chatterbot
    chatterbot_config = None
    # langchain_pdf
    langchain_pdf_config = None

    # 音频合成使用技术
    audio_synthesis_type = None

    log_file_path = None


    def __init__(self, config_path, userConfig):
        LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
        # logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
        # 不想看那么多日志信息，可以把日志等级提一提
        logging.basicConfig(level=logging.WARNING, format=LOG_FORMAT)

        
        self.common = Common()
        self.config = Config(config_path)

        # 如果存在用户自定义config, 更新配置
        if len(userConfig) > 0:
            self.config.update(userConfig)

        self.audio = Audio()

        self.proxy = None

        try:
            
            # 设置会话初始值
            self.session_config = {'msg': [{"role": "system", "content": self.config.get('chatgpt', 'preset')}]}
            self.sessions = {}
            self.current_key_index = 0

            # 直播间号
            self.room_id = self.config.get("room_display_id")

            self.before_promet = self.config.get("before_promet")
            self.after_promet = self.config.get("after_promet")

            # 敏感词数据路径
            self.badwords_path = self.config.get("badwords_path")

            # 最大阅读单词数
            self.max_len = int(self.config.get("max_len"))
            # 最大阅读字符数
            self.max_char_len = int(self.config.get("max_char_len"))

            self.chat_type = self.config.get("chat_type")

            self.need_lang = self.config.get("need_lang")

            # openai
            self.openai_config = self.config.get("openai")
            # chatgpt
            self.chatgpt_config = self.config.get("chatgpt")
            # claude
            self.claude_config = self.config.get("claude")
            # chatterbot
            self.chatterbot_config = self.config.get("chatterbot")
            # langchain_pdf
            self.langchain_pdf_config = self.config.get("langchain_pdf")

            # 音频合成使用技术
            self.audio_synthesis_type = self.config.get("audio_synthesis_type")

            print("配置文件加载成功。")
        except Exception as e:
            print(e)
            return None


        # 聊天相关类实例化
        if self.chat_type == "gpt":
            from utils.chatgpt import Chatgpt

            self.chatgpt = Chatgpt(self.openai_config, self.chatgpt_config)
        elif self.chat_type == "claude":
            from utils.claude import Claude

            self.claude = Claude(self.claude_config)
        elif self.chat_type == "chatterbot":
            from chatterbot import ChatBot  # 导入聊天机器人库

            try:
                self.bot = ChatBot(
                    self.chatterbot_config["name"],  # 聊天机器人名字
                    database_uri='sqlite:///' + self.chatterbot_config["db_path"]  # 数据库URI，数据库用于存储对话历史
                )
            except Exception as e:
                print(e)
                exit(0)
        elif self.chat_type == "langchain_pdf" or self.chat_type == "langchain_pdf+gpt":
            from utils.langchain_pdf import Langchain_pdf

            self.langchain_pdf = Langchain_pdf(self.langchain_pdf_config, self.chat_type)
        elif self.chat_type == "game":
            exit(0)


        # 日志文件路径
        self.log_file_path = "./log/log-" + self.common.get_bj_time(1) + ".txt"
        if os.path.isfile(self.log_file_path):
            print(f'{self.log_file_path} 日志文件已存在，跳过')
        else:
            with open(self.log_file_path, 'w') as f:
                f.write('')
                print(f'{self.log_file_path} 日志文件已创建')


    def get_room_id(self):
        return self.room_id
    

    def commit_handle(self, user_name, content):
        # 判断弹幕是否以句号或问号结尾，如果是则进行回复
        if content.endswith("。") or content.endswith("？") or content.endswith("?"):
            # 输出当前用户发送的弹幕消息
            print(f"[{user_name}]: {content}")

            # 全为标点符号
            if self.common.is_punctuation_string(content):
                return

            # 换行转为,
            content = content.replace('\n', ',')

            # 含有违禁词/链接
            if self.common.profanity_content(content) or self.common.check_sensitive_words(self.badwords_path, content) or \
                self.common.is_url_check(content):
                print(f"违禁词/链接：{content}")
                return

            # 语言检测
            if self.common.lang_check(content, self.need_lang) is None:
                return

            # 根据聊天类型执行不同逻辑
            if self.chat_type == "gpt":
                content = self.before_promet + content + self.after_promet
                # 调用gpt接口，获取返回内容
                resp_content = self.chatgpt.get_gpt_resp(user_name, content)
                if resp_content is not None:
                    # 输出 ChatGPT 返回的回复消息
                    print(f"[AI回复{user_name}]：{resp_content}")
                else:
                    resp_content = ""
                    print("警告：gpt无返回")
            elif self.chat_type == "claude":
                content = self.before_promet + content + self.after_promet
                resp_content = self.claude.get_claude_resp(content)
                if resp_content is not None:
                    # 输出 返回的回复消息
                    print(f"[AI回复{user_name}]：{resp_content}")
                else:
                    resp_content = ""
                    print("警告：claude无返回")
            elif self.chat_type == "chatterbot":
                # 生成回复
                resp_content = self.bot.get_response(content).text
                print(f"[AI回复{user_name}]：{resp_content}")
            elif self.chat_type == "langchain_pdf" or self.chat_type == "langchain_pdf+gpt":
                # 只用langchain，不做gpt的调用，可以节省token，做个简单的本地数据搜索
                resp_content = self.langchain_pdf.get_langchain_pdf_resp(self.chat_type, content)

                print(f"[AI回复{user_name}]：{resp_content}")
            elif self.chat_type == "game":
                return
                g1 = game1()
                g1.parse_keys_and_simulate_key_press(content.split(), 2)

                return
            else:
                # 复读机
                resp_content = content

            # print("resp_content=" + resp_content)

            # 将 AI 回复记录到日志文件中
            with open(self.log_file_path, "r+", encoding="utf-8") as f:
                content = f.read()
                # 将指针移到文件头部位置（此目的是为了让直播中读取日志文件时，可以一直让最新内容显示在顶部）
                f.seek(0, 0)
                # 不过这个实现方式，感觉有点低效
                f.write(f"[AI回复{user_name}]：{resp_content}\n" + content)

            tmp_config = {
                "max_len": self.max_len,
                "max_char_len" : self.max_char_len
            }

            # 音频合成（edge-tts / vits）并播放
            self.audio.audio_synthesis(self.audio_synthesis_type, self.config.get(self.audio_synthesis_type), tmp_config, resp_content)

