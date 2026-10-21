import os, sys, threading, json, random
import difflib
from datetime import datetime
import traceback
import importlib
import asyncio

import copy
import re
from functools import partial


from .config import Config
from .common import Common
from .audio import Audio
from .gpt_model.gpt import GPT_MODEL
from .my_log import logger
from .db import SQLiteDB
from .my_translate import My_Translate

from .luoxi_project.live_comment_assistant import send_msg_to_live_comment_assistant


"""
	___ _                       
	|_ _| | ____ _ _ __ ___  ___ 
	 | || |/ / _` | '__/ _ \/ __|
	 | ||   < (_| | | | (_) \__ \
	|___|_|\_\__,_|_|  \___/|___/

"""
class SingletonMeta(type):
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
            return cls._instances[cls]


class My_handle(metaclass=SingletonMeta):
    common = None
    config = None
    audio = None
    my_translate = None
    
    # 是否在数据处理中
    is_handleing = 0

    # 异常报警数据
    abnormal_alarm_data = {
        "platform": {
            "error_count": 0
        },
        "llm": {
            "error_count": 0
        },
        "tts": {
            "error_count": 0
        },
        "svc": {
            "error_count": 0
        },
        "visual_body": {
            "error_count": 0
        },
        "other": {
            "error_count": 0
        }
    }

    # 直播消息存储(入场、礼物、弹幕)，用于限定时间内的去重
    live_data = {
        "comment": [],
        "gift": [],
        "entrance": [],
    }

    # 各个任务运行数据缓存 暂时用于 限定任务周期性触发
    task_data = {
        "read_comment": {
            "data": [],
            "time": 0
        },
        "local_qa": {
            "data": [],
            "time": 0
        },
        "thanks": {
            "gift": {
                "data": [],
                "time": 0
            },
            "entrance": {
                "data": [],
                "time": 0
            },
            "follow": {
                "data": [],
                "time": 0
            },
        }
    }

    # 答谢板块文案数据临时存储
    thanks_entrance_copy = []
    thanks_gift_copy = []
    thanks_follow_copy = []

    def __init__(self, config_path):
        logger.info("初始化My_handle...")

        try:
            if My_handle.common is None:
                My_handle.common = Common()
            if My_handle.config is None:
                My_handle.config = Config(config_path)
            if My_handle.audio is None:
                My_handle.audio = Audio(config_path)
            if My_handle.my_translate is None:
                My_handle.my_translate = My_Translate(config_path)

            self.proxy = None
            # self.proxy = {
            #     "http": "http://127.0.0.1:10809",
            #     "https": "http://127.0.0.1:10809"
            # }
            
            # 数据丢弃部分相关的实现
            self.data_lock = threading.Lock()
            self.timers = {}

            self.db = None

            # 设置会话初始值
            self.session_config = None
            self.sessions = {}
            self.current_key_index = 0

            # 点歌模块
            self.choose_song_song_lists = None

            """
            新增LLM后，这边先定义下各个变量，下面会用到
            """
            self.chatgpt = None
            self.chat_with_file = None
            self.text_generation_webui = None
            self.sparkdesk = None
            self.langchain_chatchat = None
            self.zhipu = None
            self.bard_api = None
            self.tongyi = None
            self.tongyixingchen = None
            self.my_wenxinworkshop = None
            self.gemini = None
            self.koboldcpp = None
            self.anythingllm = None
            self.gpt4free = None
            self.custom_llm = None
            self.llm_tpu = None
            self.dify = None
            self.volcengine = None

            self.image_recognition_model = None

            self.chat_type_list = ["chatgpt", "chat_with_file", "text_generation_webui", \
                    "sparkdesk",  "langchain_chatchat", "zhipu", "bard", "tongyi", \
                    "tongyixingchen", "my_wenxinworkshop", "gemini", "koboldcpp", "anythingllm", "gpt4free", \
                    "custom_llm", "llm_tpu", "dify", "volcengine"]

            # 配置加载
            self.config_load()

            logger.info(f"配置数据加载成功。")

            # 启动定时器
            self.start_timers()
        except Exception as e:
            logger.error(traceback.format_exc())     

    # 清空 待合成消息队列|待播放音频队列
    def clear_queue(self, type: str="message_queue"):
        """清空 待合成消息队列|待播放音频队列

        Args:
            type (str, optional): 队列类型. Defaults to "message_queue".

        Returns:
            bool: 清空结果
        """
        try:
            return My_handle.audio.clear_queue(type)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f"清空{type}队列失败：{e}")
            return False
        
    # 停止音频播放
    def stop_audio(self, type: str="pygame", mixer_normal: bool=True, mixer_copywriting: bool=True):
        try:
            return My_handle.audio.stop_audio(type, mixer_normal, mixer_copywriting)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f"停止音频播放失败：{e}")
            return False

    # 周期性触发数据处理，每秒执行一次，进行计时
    def periodic_trigger_data_handle(self):
        def get_last_n_items(data_list: list, num: int):
            # 返回最后的 n 个元素，如果不足 n 个则返回实际元素个数
            return data_list[-num:] if num > 0 else []
        
        
        if My_handle.config.get("read_comment", "periodic_trigger", "enable"):
            type = "read_comment"
            # 计时+1
            My_handle.task_data[type]["time"] += 1
            
            periodic_time_min = int(My_handle.config.get(type, "periodic_trigger", "periodic_time_min"))
            periodic_time_max = int(My_handle.config.get(type, "periodic_trigger", "periodic_time_max"))
            # 生成触发周期值
            periodic_time = random.randint(periodic_time_min, periodic_time_max)
            logger.debug(f"type={type}, periodic_time={periodic_time}, My_handle.task_data={My_handle.task_data}")

            # 计时时间是否超过限定的触发周期
            if My_handle.task_data[type]["time"] >= periodic_time:
                # 计时清零
                My_handle.task_data[type]["time"] = 0

                trigger_num_min = int(My_handle.config.get(type, "periodic_trigger", "trigger_num_min"))
                trigger_num_max = int(My_handle.config.get(type, "periodic_trigger", "trigger_num_max"))
                # 生成触发个数
                trigger_num = random.randint(trigger_num_min, trigger_num_max)
                # 获取数据
                data_list = get_last_n_items(My_handle.task_data[type]["data"], trigger_num)
                logger.debug(f"type={type}, trigger_num={trigger_num}")

                if data_list != []:
                    # 遍历数据 进行webui数据回传 和 音频合成播放
                    for data in data_list:
                        self.audio_synthesis_handle(data)

                # 数据清空
                My_handle.task_data[type]["data"] = []
        

        if My_handle.config.get("local_qa", "periodic_trigger", "enable"):
            type = "local_qa"
            # 计时+1
            My_handle.task_data[type]["time"] += 1
            
            periodic_time_min = int(My_handle.config.get(type, "periodic_trigger", "periodic_time_min"))
            periodic_time_max = int(My_handle.config.get(type, "periodic_trigger", "periodic_time_max"))
            # 生成触发周期值
            periodic_time = random.randint(periodic_time_min, periodic_time_max)
            logger.debug(f"type={type}, periodic_time={periodic_time}, My_handle.task_data={My_handle.task_data}")

            # 计时时间是否超过限定的触发周期
            if My_handle.task_data[type]["time"] >= periodic_time:
                # 计时清零
                My_handle.task_data[type]["time"] = 0

                trigger_num_min = int(My_handle.config.get(type, "periodic_trigger", "trigger_num_min"))
                trigger_num_max = int(My_handle.config.get(type, "periodic_trigger", "trigger_num_max"))
                # 生成触发个数
                trigger_num = random.randint(trigger_num_min, trigger_num_max)
                # 获取数据
                data_list = get_last_n_items(My_handle.task_data[type]["data"], trigger_num)
                logger.debug(f"type={type}, trigger_num={trigger_num}")

                if data_list != []:
                    # 遍历数据 进行webui数据回传 和 音频合成播放
                    for data in data_list:
                        if data["type"] == "local_qa_audio":
                            self.webui_show_chat_log_callback("本地问答-音频", data, data["file_path"])
                        else:
                            self.webui_show_chat_log_callback("本地问答-文本", data, data["content"])

                        self.audio_synthesis_handle(data)

                # 数据清空
                My_handle.task_data[type]["data"] = []
        
        if My_handle.config.get("thanks", "gift", "periodic_trigger", "enable"):
            type = "thanks"
            type2 = "gift"

            # 计时+1
            My_handle.task_data[type][type2]["time"] += 1

            periodic_time_min = int(My_handle.config.get(type, type2, "periodic_trigger", "periodic_time_min"))
            periodic_time_max = int(My_handle.config.get(type, type2, "periodic_trigger", "periodic_time_max"))
            # 生成触发周期值
            periodic_time = random.randint(periodic_time_min, periodic_time_max)
            logger.debug(f"type={type}, periodic_time={periodic_time}, My_handle.task_data={My_handle.task_data}")

            # 计时时间是否超过限定的触发周期
            if My_handle.task_data[type][type2]["time"] >= periodic_time:
                # 计时清零
                My_handle.task_data[type][type2]["time"] = 0

                trigger_num_min = int(My_handle.config.get(type, type2, "periodic_trigger", "trigger_num_min"))
                trigger_num_max = int(My_handle.config.get(type, type2, "periodic_trigger", "trigger_num_max"))
                # 生成触发个数
                trigger_num = random.randint(trigger_num_min, trigger_num_max)
                # 获取数据
                data_list = get_last_n_items(My_handle.task_data[type][type2]["data"], trigger_num)
                logger.debug(f"type={type}, trigger_num={trigger_num}")

                if data_list != []:
                    # 遍历数据 进行webui数据回传 和 音频合成播放
                    for data in data_list:
                        self.audio_synthesis_handle(data)

                # 数据清空
                My_handle.task_data[type][type2]["data"] = []
        
        if My_handle.config.get("thanks", "entrance", "periodic_trigger", "enable"):
            type = "thanks"
            type2 = "entrance"

            # 计时+1
            My_handle.task_data[type][type2]["time"] += 1

            periodic_time_min = int(My_handle.config.get(type, type2, "periodic_trigger", "periodic_time_min"))
            periodic_time_max = int(My_handle.config.get(type, type2, "periodic_trigger", "periodic_time_max"))
            # 生成触发周期值
            periodic_time = random.randint(periodic_time_min, periodic_time_max)
            logger.debug(f"type={type}, periodic_time={periodic_time}, My_handle.task_data={My_handle.task_data}")

            # 计时时间是否超过限定的触发周期
            if My_handle.task_data[type][type2]["time"] >= periodic_time:
                # 计时清零
                My_handle.task_data[type][type2]["time"] = 0

                trigger_num_min = int(My_handle.config.get(type, type2, "periodic_trigger", "trigger_num_min"))
                trigger_num_max = int(My_handle.config.get(type, type2, "periodic_trigger", "trigger_num_max"))
                # 生成触发个数
                trigger_num = random.randint(trigger_num_min, trigger_num_max)
                # 获取数据
                data_list = get_last_n_items(My_handle.task_data[type][type2]["data"], trigger_num)
                logger.debug(f"type={type}, trigger_num={trigger_num}")

                if data_list != []:
                    # 遍历数据 进行webui数据回传 和 音频合成播放
                    for data in data_list:
                        self.audio_synthesis_handle(data)

                # 数据清空
                My_handle.task_data[type][type2]["data"] = []

        if My_handle.config.get("thanks", "follow", "periodic_trigger", "enable"):
            type = "thanks"
            type2 = "follow"

            # 计时+1
            My_handle.task_data[type][type2]["time"] += 1

            periodic_time_min = int(My_handle.config.get(type, type2, "periodic_trigger", "periodic_time_min"))
            periodic_time_max = int(My_handle.config.get(type, type2, "periodic_trigger", "periodic_time_max"))
            # 生成触发周期值
            periodic_time = random.randint(periodic_time_min, periodic_time_max)
            logger.debug(f"type={type}, periodic_time={periodic_time}, My_handle.task_data={My_handle.task_data}")

            # 计时时间是否超过限定的触发周期
            if My_handle.task_data[type][type2]["time"] >= periodic_time:
                # 计时清零
                My_handle.task_data[type][type2]["time"] = 0

                trigger_num_min = int(My_handle.config.get(type, type2, "periodic_trigger", "trigger_num_min"))
                trigger_num_max = int(My_handle.config.get(type, type2, "periodic_trigger", "trigger_num_max"))
                # 生成触发个数
                trigger_num = random.randint(trigger_num_min, trigger_num_max)
                # 获取数据
                data_list = get_last_n_items(My_handle.task_data[type][type2]["data"], trigger_num)
                logger.debug(f"type={type}, trigger_num={trigger_num}")

                if data_list != []:
                    # 遍历数据 进行webui数据回传 和 音频合成播放
                    for data in data_list:
                        self.audio_synthesis_handle(data)

                # 数据清空
                My_handle.task_data[type][type2]["data"] = []


        self.periodic_trigger_timer = threading.Timer(1, partial(self.periodic_trigger_data_handle))
        self.periodic_trigger_timer.start()

    # 清空live_data直播数据
    def clear_live_data(self, type: str=""):
        if type != "" and type is not None:
            My_handle.live_data[type] = []

        if type == "comment":
            self.comment_check_timer = threading.Timer(int(My_handle.config.get("filter", "limited_time_deduplication", "comment")), partial(self.clear_live_data, "comment"))
            self.comment_check_timer.start()
        elif type == "gift":
            self.gift_check_timer = threading.Timer(int(My_handle.config.get("filter", "limited_time_deduplication", "gift")), partial(self.clear_live_data, "gift"))
            self.gift_check_timer.start()
        elif type == "entrance":
            self.entrance_check_timer = threading.Timer(int(My_handle.config.get("filter", "limited_time_deduplication", "entrance")), partial(self.clear_live_data, "entrance"))
            self.entrance_check_timer.start()

    # 启动定时器
    def start_timers(self):
        
        if My_handle.config.get("filter", "limited_time_deduplication", "enable"):

            # 设置定时器，每隔n秒执行一次
            self.comment_check_timer = threading.Timer(int(My_handle.config.get("filter", "limited_time_deduplication", "comment")), partial(self.clear_live_data, "comment"))
            self.comment_check_timer.start()

            self.gift_check_timer = threading.Timer(int(My_handle.config.get("filter", "limited_time_deduplication", "gift")), partial(self.clear_live_data, "gift"))
            self.gift_check_timer.start()

            self.entrance_check_timer = threading.Timer(int(My_handle.config.get("filter", "limited_time_deduplication", "entrance")), partial(self.clear_live_data, "entrance"))
            self.entrance_check_timer.start()

            logger.info("启动 限定时间直播数据去重 定时器")

        self.periodic_trigger_timer = threading.Timer(1, partial(self.periodic_trigger_data_handle))
        self.periodic_trigger_timer.start()
        logger.info("启动 周期性触发 定时器")


    # 是否位于数据处理状态
    def is_handle_empty(self):
        return My_handle.is_handleing


    # 音频队列、播放相关情况
    def is_audio_queue_empty(self):
        return My_handle.audio.is_audio_queue_empty()

    # 判断 等待合成消息队列|待播放音频队列 数是否小于或大于某个值，就返回True
    def is_queue_less_or_greater_than(self, type: str="message_queue", less: int=None, greater: int=None):
        """判断 等待合成消息队列|待播放音频队列 数是否小于或大于某个值

        Args:
            type (str, optional): _description_. Defaults to "message_queue" | voice_tmp_path_queue.
            less (int, optional): _description_. Defaults to None.
            greater (int, optional): _description_. Defaults to None.

        Returns:
            bool: 是否小于或大于某个值
        """
        return My_handle.audio.is_queue_less_or_greater_than(type, less, greater)

    # 获取音频类信息
    def get_audio_info(self):
        return My_handle.audio.get_audio_info()

    def get_chat_model(self, chat_type, config):
        if chat_type in ["chatterbot", "chat_with_file"]:
            # 对这些类型做特殊处理
            pass
        else:
            GPT_MODEL.set_model_config(chat_type, config.get(chat_type))
        self.__dict__[chat_type] = GPT_MODEL.get(chat_type)

    def get_vision_model(self, chat_type, config):
        GPT_MODEL.set_vision_model_config(chat_type, config)
        self.image_recognition_model = GPT_MODEL.get(chat_type)

    def handle_chat_type(self):
        chat_type = My_handle.config.get("chat_type")
        self.get_chat_model(chat_type, My_handle.config)

        if chat_type == "chatterbot":
            from chatterbot import ChatBot
            self.chatterbot_config = My_handle.config.get("chatterbot")
            try:
                self.bot = ChatBot(
                    self.chatterbot_config["name"],
                    database_uri='sqlite:///' + self.chatterbot_config["db_path"]
                )
            except Exception as e:
                logger.info(e)
                exit(0)
        elif chat_type == "chat_with_file":
            from utils.chat_with_file.chat_with_file import Chat_with_file
            self.chat_with_file = Chat_with_file(My_handle.config.get("chat_with_file"))
        elif chat_type == "game":
            self.game = importlib.import_module("game." + My_handle.config.get("game", "module_name"))

    # 配置加载
    def config_load(self):
        self.session_config = {'msg': [{"role": "system", "content": My_handle.config.get('chatgpt', 'preset')}]}

        # 设置GPT_Model全局模型列表
        GPT_MODEL.set_model_config("openai", My_handle.config.get("openai"))
        GPT_MODEL.set_model_config("chatgpt", My_handle.config.get("chatgpt"))

        # 聊天相关类实例化
        self.handle_chat_type()

        # 判断是否使能了SD
        if My_handle.config.get("sd")["enable"]:
            from utils.sd import SD

            self.sd = SD(My_handle.config.get("sd"))
        # 特殊：在SD没有使能情况下，判断图片映射是否使能
        elif My_handle.config.get("key_mapping", "img_path_trigger_type") != "不启用":
            # 沿用SD的虚拟摄像头来展示图片
            from utils.sd import SD

            self.sd = SD({"enable": False, "visual_camera": My_handle.config.get("sd", "visual_camera")})

        # 日志文件路径
        self.log_file_path = "./log/log-" + My_handle.common.get_bj_time(1) + ".txt"
        if os.path.isfile(self.log_file_path):
            logger.info(f'{self.log_file_path} 日志文件已存在，跳过')
        else:
            with open(self.log_file_path, 'w') as f:
                f.write('')
                logger.info(f'{self.log_file_path} 日志文件已创建')

        # 生成弹幕文件
        self.comment_file_path = "./log/comment-" + My_handle.common.get_bj_time(1) + ".txt"
        if os.path.isfile(self.comment_file_path):
            logger.info(f'{self.comment_file_path} 弹幕文件已存在，跳过')
        else:
            with open(self.comment_file_path, 'w') as f:
                f.write('')
                logger.info(f'{self.comment_file_path} 弹幕文件已创建')

        """                                                                                                                
                                                                                                                                        
            .............  '>)xcn)I                                                                                 
            }}}}}}}}}}}}](v0kaaakad\..                                                                              
            ++++++~~++<_xpahhhZ0phah>                                                                               
            _________+(OhhkamuCbkkkh+                                                                               
            ?????????nbhkhkn|makkkhQ^                                                                               
            [[[[[[[}UhkbhZ]fbhkkkhb<                                                                                
            1{1{1{1ChkkaXicohkkkhk]                                                                                 
            ))))))JhkkhrICakkkkap-                                                                                  
            \\\\|ckkkat;0akkkka0>                                                                                   
            ttt/fpkka/;Oakhhaku"                                                                                    
            jjjjUmkau^QabwQX\< '!<++~>iI       .;>++++<>I'     :+}}{?;                                              
            xxxcpdkO"capmmZ/^ +Y-;,,;-Lf     ItX/+l:",;>1cx>  .`"x#d>`        .`.                                   
            uuvqwkh+1ahaaL_  'Zq;     ;~   '/bQ!         "uhc: . 1oZ'         "vj.     ^'                           
            ccc0kaz!kawX}'   .\hbv?:      .jop;           .C*L^  )oO`        .':I^. ."_L!^^.    ':;,'               
            XXXXph_cU_"        >rZhbC\!   "qaC...          faa~  )oO`        ;-jqj .l[mb1]_'  ^(|}\Ow{              
            XXXz00i+             '!1Ukkc, 'JoZ` .          uop;  )oO'          >ou   .Lp"  . ,0j^^>Yvi              
            XXXzLn. .        ^>      lC#(  lLot.          _kq- . 1o0'          >on   .Qp,    }*|><i^  .             
            YYYXQ|           ,O]^.   "XQI . `10c~^.    '!t0f:   .t*q;....'l1. ._#c.. .Qkl`I_"Iw0~"`,<|i.            
            (|((f1           ^t1]++-}(?`      '>}}}/rrx1]~^    ^?jvv/]--]{r) .i{x/+;  ]Xr1_;. :(vnrj\i.             
                '1..             .''.   .         .Itq*Z}`             ..                                           
                 +; .                                "}XmQf-i!;.                                                    
                  .                                     ';><iI"                                                     
                                                                                                                                        
                                                                                                                                                                                                                                                     
        """
        try:
            # 数据库
            self.db = SQLiteDB(My_handle.config.get("database", "path"))
            logger.info(f'创建数据库:{My_handle.config.get("database", "path")}')

            # 创建弹幕表
            create_table_sql = '''
            CREATE TABLE IF NOT EXISTS danmu (
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                ts DATETIME NOT NULL
            )
            '''
            self.db.execute(create_table_sql)
            logger.debug('创建danmu（弹幕）表')

            create_table_sql = '''
            CREATE TABLE IF NOT EXISTS entrance (
                username TEXT NOT NULL,
                ts DATETIME NOT NULL
            )
            '''
            self.db.execute(create_table_sql)
            logger.debug('创建entrance（入场）表')

            create_table_sql = '''
            CREATE TABLE IF NOT EXISTS gift (
                username TEXT NOT NULL,
                gift_name TEXT NOT NULL,
                gift_num INT NOT NULL,
                unit_price REAL NOT NULL,
                total_price REAL NOT NULL,
                ts DATETIME NOT NULL
            )
            '''
            self.db.execute(create_table_sql)
            logger.debug('创建gift（礼物）表')

            create_table_sql = '''
            CREATE TABLE IF NOT EXISTS integral (
                platform TEXT NOT NULL,
                username TEXT NOT NULL,
                uid TEXT NOT NULL,
                integral INT NOT NULL,
                view_num INT NOT NULL,
                sign_num INT NOT NULL,
                last_sign_ts DATETIME NOT NULL,
                total_price INT NOT NULL,
                last_ts DATETIME NOT NULL
            )
            '''
            self.db.execute(create_table_sql)
            logger.debug('创建integral（积分）表')
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f'数据库 {My_handle.config.get("database", "path")} 创建失败，请查看日志排查问题！！！')


    # 重载config
    def reload_config(self, config_path):
        My_handle.config = Config(config_path)
        My_handle.audio.reload_config(config_path)
        My_handle.my_translate.reload_config(config_path)

        self.config_load()


    # 回传给webui，用于聊天内容显示
    def webui_show_chat_log_callback(self, data_type: str, data: dict, resp_content: str):
        """回传给webui，用于聊天内容显示

        Args:
            data_type (str): 数据内容的类型（多指LLM）
            data (dict): 数据JSON
            resp_content (str): 显示的聊天内容的文本
        """
        try:
            if My_handle.config.get("talk", "show_chat_log") == True: 
                if "ori_username" not in data:
                    data["ori_username"] = data["username"]
                if "ori_content" not in data:
                    data["ori_content"] = data["content"]
                    
                # 返回给webui的数据
                return_webui_json = {
                    "type": "llm",
                    "data": {
                        "type": data_type,
                        "username": data["ori_username"], 
                        "content_type": "answer",
                        "content": f"错误：{data_type}无返回，请查看日志" if resp_content is None else resp_content,
                        "timestamp": My_handle.common.get_bj_time(0)
                    }
                }

                webui_ip = "127.0.0.1" if My_handle.config.get("webui", "ip") == "0.0.0.0" else My_handle.config.get("webui", "ip")
                tmp_json = My_handle.common.send_request(f'http://{webui_ip}:{My_handle.config.get("webui", "port")}/callback', "POST", return_webui_json, timeout=30)
        except Exception as e:
            logger.error(traceback.format_exc())

    # 获取房间号
    def get_room_id(self):
        return My_handle.config.get("room_display_id")


    # 音频合成处理
    def audio_synthesis_handle(self, data_json):
        """音频合成处理

        Args:
            data_json (dict): 传递的json数据

            核心参数:
            type目前有
                reread_top_priority 最高优先级-复读
                talk 聊天（语音输入）
                comment 弹幕
                local_qa_text 本地问答文本
                local_qa_audio 本地问答音频
                song 歌曲
                reread 复读
                key_mapping 按键映射
                key_mapping_copywriting 按键映射-文案
                integral 积分
                read_comment 念弹幕
                gift 礼物
                entrance 用户入场
                follow 用户关注
                schedule 定时任务
                idle_time_task 闲时任务
                abnormal_alarm 异常报警
                image_recognition_schedule 图像识别定时任务

        """

        if "content" in data_json:
            if data_json['content']:
                # 替换文本内容中\n为空
                data_json['content'] = data_json['content'].replace('\n', '')

        # 如果虚拟身体-Unity，则发送数据到中转站
        if My_handle.config.get("visual_body") == "unity":
            # 判断 'config' 是否存在于字典中
            if 'config' in data_json:
                # 删除 'config' 对应的键值对
                data_json.pop('config')

            data_json["password"] = My_handle.config.get("unity", "password")

            resp_json = My_handle.common.send_request(My_handle.config.get("unity", "api_ip_port"), "POST", data_json)
            if resp_json:
                if resp_json["code"] == 200:
                    logger.info("请求unity中转站成功")
                else:
                    logger.info(f"请求unity中转站出错，{resp_json['message']}")
            else:
                logger.error("请求unity中转站失败")
        else:
            # 音频合成（edge-tts / vits_fast）并播放
            My_handle.audio.audio_synthesis(data_json)

            logger.debug(f'data_json={data_json}')

            # 数据类型不在需要触发助播条件的范围内，则直接返回
            if data_json["type"] not in My_handle.config.get("assistant_anchor", "type"):
                return

            # 1、匹配助播本地问答库 触发后不执行后面的其他功能
            if My_handle.config.get("assistant_anchor", "local_qa", "text", "enable"):
                # 根据类型，执行不同的问答匹配算法
                if My_handle.config.get("assistant_anchor", "local_qa", "text", "format") == "text":
                    tmp = self.find_answer(data_json["content"], My_handle.config.get("assistant_anchor", "local_qa", "text", "file_path"), My_handle.config.get("assistant_anchor", "local_qa", "text", "similarity"))
                else:
                    tmp = self.find_similar_answer(data_json["content"], My_handle.config.get("assistant_anchor", "local_qa", "text", "file_path"), My_handle.config.get("assistant_anchor", "local_qa", "text", "similarity"))

                if tmp is not None:
                    logger.info(f'触发助播 本地问答库-文本 [{My_handle.config.get("assistant_anchor", "username")}]: {data_json["content"]}')
                    # 将问答库中设定的参数替换为指定内容，开发者可以自定义替换内容
                    # 假设有多个未知变量，用户可以在此处定义动态变量
                    variables = {
                        'cur_time': My_handle.common.get_bj_time(5),
                        'username': My_handle.config.get("assistant_anchor", "username")
                    }

                    # 使用字典进行字符串替换
                    if any(var in tmp for var in variables):
                        tmp = tmp.format(**{var: value for var, value in variables.items() if var in tmp})

                    # [1|2]括号语法随机获取一个值，返回取值完成后的字符串
                    tmp = My_handle.common.brackets_text_randomize(tmp)
                    
                    logger.info(f"助播 本地问答库-文本回答为: {tmp}")

                    resp_content = tmp
                    # 将 AI 回复记录到日志文件中
                    self.write_to_comment_log(resp_content, {"username": My_handle.config.get("assistant_anchor", "username"), "content": data_json["content"]})
                    
                    message = {
                        "type": "assistant_anchor_text",
                        "tts_type": My_handle.config.get("assistant_anchor", "audio_synthesis_type"),
                        "data": My_handle.config.get(My_handle.config.get("assistant_anchor", "audio_synthesis_type")),
                        "config": My_handle.config.get("filter"),
                        "username": My_handle.config.get("assistant_anchor", "username"),
                        "content": resp_content
                    }

                    if "insert_index" in message:
                        message["insert_index"] = data_json["insert_index"]

                    
                    My_handle.audio.audio_synthesis(message)

                    return True
                
            # 如果开启了助播功能，则根据当前播放内容的文本信息，进行助播音频的播放
            if My_handle.config.get("assistant_anchor", "enable"):
                # 2、匹配本地问答音频库 触发后不执行后面的其他功能
                if My_handle.config.get("assistant_anchor", "local_qa", "audio", "enable"):
                    # 输出当前用户发送的弹幕消息
                    # logger.info(f"[{username}]: {content}")
                    # 获取本地问答音频库文件夹内所有的音频文件名
                    local_qa_audio_filename_list = My_handle.audio.get_dir_audios_filename(My_handle.config.get("assistant_anchor", "local_qa", "audio", "file_path"), type=1)
                    local_qa_audio_list = My_handle.audio.get_dir_audios_filename(My_handle.config.get("assistant_anchor", "local_qa", "audio", "file_path"), type=0)

                    if My_handle.config.get("assistant_anchor", "local_qa", "audio", "type") == "相似度匹配":
                        # 不含拓展名，在本地音频名列表中做查找
                        local_qv_audio_filename = My_handle.common.find_best_match(data_json["content"], local_qa_audio_filename_list, My_handle.config.get("assistant_anchor", "local_qa", "audio", "similarity"))
                    elif My_handle.config.get("assistant_anchor", "local_qa", "audio", "type") == "包含关系":
                        # 在本地音频名列表中查找是否包含于当前这个传入的文本内容
                        local_qv_audio_filename = My_handle.common.find_substring_in_list(data_json["content"], local_qa_audio_filename_list)

                    # print(f"local_qv_audio_filename={local_qv_audio_filename}")

                    # 找到了匹配的结果
                    if local_qv_audio_filename is not None:
                        logger.info(f'触发 助播 本地问答库-语音 [{My_handle.config.get("assistant_anchor", "username")}]: {data_json["content"]}')
                        # 把结果从原文件名列表中在查找一遍，补上拓展名。相似度设置为0，就能必定有返回的结果
                        local_qv_audio_filename = My_handle.common.find_best_match(local_qv_audio_filename, local_qa_audio_list, 0)

                        # 寻找对应的文件
                        resp_content = My_handle.audio.search_files(My_handle.config.get("assistant_anchor", "local_qa", "audio", "file_path"), local_qv_audio_filename)
                        if resp_content != []:
                            logger.debug(f"匹配到的音频原相对路径：{resp_content[0]}")

                            # 拼接音频文件路径
                            resp_content = f'{My_handle.config.get("assistant_anchor", "local_qa", "audio", "file_path")}/{resp_content[0]}'
                            logger.info(f"匹配到的音频路径：{resp_content}")
                            message = {
                                "type": "assistant_anchor_audio",
                                "tts_type": My_handle.config.get("assistant_anchor", "audio_synthesis_type"),
                                "data": My_handle.config.get(My_handle.config.get("assistant_anchor", "audio_synthesis_type")),
                                "config": My_handle.config.get("filter"),
                                "username": My_handle.config.get("assistant_anchor", "username"),
                                "content": data_json["content"],
                                "file_path": resp_content
                            }

                            if "insert_index" in message:
                                message["insert_index"] = data_json["insert_index"]

                            My_handle.audio.audio_synthesis(message)

                            return True


    # 从本地问答库中搜索问题的答案(文本数据是一问一答的单行格式)
    def find_answer(self, question, qa_file_path, similarity=1):
        """从本地问答库中搜索问题的答案(文本数据是一问一答的单行格式)

        Args:
            question (str): 问题文本
            qa_file_path (str): 问答库的路径
            similarity (float): 相似度

        Returns:
            str: 答案文本 或 None
        """

        with open(qa_file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        q_list = [lines[i].strip() for i in range(0, len(lines), 2)]
        q_to_answer_index = {q: i + 1 for i, q in enumerate(q_list)}

        q = My_handle.common.find_best_match(question, q_list, similarity)
        # print(f"q={q}")

        if q is not None:
            answer_index = q_to_answer_index.get(q)
            # print(f"answer_index={answer_index}")
            if answer_index is not None and answer_index < len(lines):
                return lines[answer_index * 2 - 1].strip()

        return None


    # 本地问答库 文本模式  根据相似度查找答案(文本数据是json格式)
    def find_similar_answer(self, input_str, qa_file_path, min_similarity=0.8):
        """本地问答库 文本模式  根据相似度查找答案(文本数据是json格式)

        Args:
            input_str (str): 输入的待查找字符串
            qa_file_path (str): 问答库的路径
            min_similarity (float, optional): 最低匹配相似度. 默认 0.8.

        Returns:
            response (str): 匹配到的结果，如果匹配不到则返回None
        """
        def load_data_from_file(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    return data
            except json.JSONDecodeError:
                logger.error(traceback.format_exc())
                logger.error(f"本地问答库 文本模式，JSON文件：{file_path}，加载失败，文件JSON格式出错，请进行修改匹配格式！")
                return None
            except FileNotFoundError:
                logger.error(traceback.format_exc())
                logger.error(f"本地问答库 文本模式，JSON文件：{file_path}不存在！")
                return None
            
        # 从文件加载数据
        data = load_data_from_file(qa_file_path)
        if data is None:
            return None

        # 存储相似度与回答的元组列表
        similarity_responses = []
        
        # 遍历json中的每个条目，找到与输入字符串相似的关键词
        for entry in data:
            for keyword in entry.get("关键词", []):
                similarity = difflib.SequenceMatcher(None, input_str, keyword).ratio()
                similarity_responses.append((similarity, entry.get("回答", [])))
        
        # 过滤相似度低于设定阈值的回答
        similarity_responses = [(similarity, response) for similarity, response in similarity_responses if similarity >= min_similarity]
        
        # 如果没有符合条件的回答，返回None
        if not similarity_responses:
            return None
        
        # 按相似度降序排序
        similarity_responses.sort(reverse=True, key=lambda x: x[0])
        
        # 获取相似度最高的回答列表
        top_response = similarity_responses[0][1]
        
        # 随机选择一个回答
        response = random.choice(top_response)
        
        return response


    # 本地问答库 处理
    def local_qa_handle(self, data):
        """本地问答库 处理

        Args:
            data (dict): 用户名 弹幕数据

        Returns:
            bool: 是否触发并处理
        """
        username = data["username"]
        content = data["content"]

        # 合并字符串末尾连续的*  主要针对获取不到用户名的情况
        username = My_handle.common.merge_consecutive_asterisks(username)

        # 最大保留的用户名长度
        username = username[:self.config.get("local_qa", "text", "username_max_len")]

        # 1、匹配本地问答库 触发后不执行后面的其他功能
        if My_handle.config.get("local_qa", "text", "enable"):
            # 根据类型，执行不同的问答匹配算法
            if My_handle.config.get("local_qa", "text", "type") == "text":
                tmp = self.find_answer(content, My_handle.config.get("local_qa", "text", "file_path"), My_handle.config.get("local_qa", "text", "similarity"))
            else:
                tmp = self.find_similar_answer(content, My_handle.config.get("local_qa", "text", "file_path"), My_handle.config.get("local_qa", "text", "similarity"))

            if tmp is not None:
                logger.info(f"触发本地问答库-文本 [{username}]: {content}")
                # 将问答库中设定的参数替换为指定内容，开发者可以自定义替换内容
                # 假设有多个未知变量，用户可以在此处定义动态变量
                variables = {
                    'cur_time': My_handle.common.get_bj_time(5),
                    'username': username
                }

                # 使用字典进行字符串替换
                if any(var in tmp for var in variables):
                    tmp = tmp.format(**{var: value for var, value in variables.items() if var in tmp})
                
                # [1|2]括号语法随机获取一个值，返回取值完成后的字符串
                tmp = My_handle.common.brackets_text_randomize(tmp)

                logger.info(f"本地问答库-文本回答为: {tmp}")

                """
                # 判断 回复模板 是否启用
                if My_handle.config.get("reply_template", "enable"):
                    # 根据模板变量关系进行回复内容的替换
                    # 假设有多个未知变量，用户可以在此处定义动态变量
                    variables = {
                        'username': data["username"][:self.config.get("reply_template", "username_max_len")],
                        'data': tmp,
                        'cur_time': My_handle.common.get_bj_time(5),
                    }

                    reply_template_copywriting = My_handle.common.get_list_random_or_default(self.config.get("reply_template", "copywriting"), "{data}")
                    # 使用字典进行字符串替换
                    if any(var in reply_template_copywriting for var in variables):
                        tmp = reply_template_copywriting.format(**{var: value for var, value in variables.items() if var in reply_template_copywriting})

                logger.debug(f"回复模板转换后: {tmp}")
                """

                resp_content = tmp
                # 将 AI 回复记录到日志文件中
                self.write_to_comment_log(resp_content, {"username": username, "content": content})
                
                message = {
                    "type": "comment",
                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                    "config": My_handle.config.get("filter"),
                    "username": username,
                    "content": resp_content
                }

                # 洛曦 直播弹幕助手
                if My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable") and \
                    "comment_reply" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "type") and \
                    "消息产生时" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                    asyncio.run(send_msg_to_live_comment_assistant(My_handle.config.get("luoxi_project", "Live_Comment_Assistant"), resp_content))

                # 是否启用了周期性触发功能，启用此功能后，数据会被缓存，之后周期到了才会触发
                if My_handle.config.get("local_qa", "periodic_trigger", "enable"):
                    My_handle.task_data["local_qa"]["data"].append(message)
                else:
                    self.webui_show_chat_log_callback("本地问答-文本", data, resp_content)
                    
                    self.audio_synthesis_handle(message)

                return True

        # 2、匹配本地问答音频库 触发后不执行后面的其他功能
        if My_handle.config.get("local_qa")["audio"]["enable"]:
            # 输出当前用户发送的弹幕消息
            # logger.info(f"[{username}]: {content}")
            # 获取本地问答音频库文件夹内所有的音频文件名
            local_qa_audio_filename_list = My_handle.audio.get_dir_audios_filename(My_handle.config.get("local_qa", "audio", "file_path"), type=1)
            local_qa_audio_list = My_handle.audio.get_dir_audios_filename(My_handle.config.get("local_qa", "audio", "file_path"), type=0)

            # 不含拓展名做查找
            local_qv_audio_filename = My_handle.common.find_best_match(content, local_qa_audio_filename_list, My_handle.config.get("local_qa", "audio", "similarity"))
            
            # print(f"local_qv_audio_filename={local_qv_audio_filename}")

            # 找到了匹配的结果
            if local_qv_audio_filename is not None:
                logger.info(f"触发本地问答库-语音 [{username}]: {content}")
                # 把结果从原文件名列表中在查找一遍，补上拓展名
                local_qv_audio_filename = My_handle.common.find_best_match(local_qv_audio_filename, local_qa_audio_list, 0)

                # 寻找对应的文件
                resp_content = My_handle.audio.search_files(My_handle.config.get("local_qa", "audio", "file_path"), local_qv_audio_filename)
                if resp_content != []:
                    logger.debug(f"匹配到的音频原相对路径：{resp_content[0]}")

                    # 拼接音频文件路径
                    resp_content = f'{My_handle.config.get("local_qa", "audio", "file_path")}/{resp_content[0]}'
                    logger.info(f"匹配到的音频路径：{resp_content}")
                    message = {
                        "type": "local_qa_audio",
                        "tts_type": My_handle.config.get("audio_synthesis_type"),
                        "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                        "config": My_handle.config.get("filter"),
                        "username": username,
                        "content": content,
                        "file_path": resp_content
                    }

                    # 是否启用了周期性触发功能，启用此功能后，数据会被缓存，之后周期到了才会触发
                    if My_handle.config.get("local_qa", "periodic_trigger", "enable"):
                        My_handle.task_data["local_qa"]["data"].append(message)
                    else:
                        self.webui_show_chat_log_callback("本地问答-音频", data, resp_content)

                        self.audio_synthesis_handle(message)

                    return True
            
        return False


    # 点歌模式 处理
    def choose_song_handle(self, data):
        """点歌模式 处理

        Args:
            data (dict): 用户名 弹幕数据

        Returns:
            bool: 是否触发并处理
        """
        username = data["username"]
        content = data["content"]

        

        # 合并字符串末尾连续的*  主要针对获取不到用户名的情况
        username = My_handle.common.merge_consecutive_asterisks(username)

        if My_handle.config.get("choose_song")["enable"] == True:
            start_cmd = My_handle.common.starts_with_any(content, My_handle.config.get("choose_song", "start_cmd"))
            stop_cmd = My_handle.common.starts_with_any(content, My_handle.config.get("choose_song", "stop_cmd"))
            random_cmd = My_handle.common.starts_with_any(content, My_handle.config.get("choose_song", "random_cmd"))

            
            # 判断随机点歌命令是否正确
            if random_cmd:
                resp_content = My_handle.common.random_search_a_audio_file(My_handle.config.get("choose_song", "song_path"))
                if resp_content is None:
                    return True
                
                logger.info(f"随机到的音频路径：{resp_content}")

                message = {
                    "type": "song",
                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                    "config": My_handle.config.get("filter"),
                    "username": username,
                    "content": resp_content
                }

                
                self.audio_synthesis_handle(message)

                self.webui_show_chat_log_callback("点歌", data, resp_content)

                return True
            # 判断点歌命令是否正确
            elif start_cmd:
                logger.info(f"[{username}]: {content}")

                # 获取本地音频文件夹内所有的音频文件名（不含拓展名）
                choose_song_song_lists = My_handle.audio.get_dir_audios_filename(My_handle.config.get("choose_song", "song_path"), 1)

                # 去除命令前缀
                content = content[len(start_cmd):]

                # 说明用户仅发送命令，没有发送歌名，说明用户不会用
                if content == "":
                    resp_content = f'点歌命令错误，命令为 {My_handle.config.get("choose_song", "start_cmd")}+歌名'
                    message = {
                        "type": "comment",
                        "tts_type": My_handle.config.get("audio_synthesis_type"),
                        "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                        "config": My_handle.config.get("filter"),
                        "username": username,
                        "content": resp_content
                    }

                    self.audio_synthesis_handle(message)

                    self.webui_show_chat_log_callback("点歌", data, resp_content)

                    return True

                # 判断是否有此歌曲
                song_filename = My_handle.common.find_best_match(content, choose_song_song_lists, similarity=My_handle.config.get("choose_song", "similarity"))
                if song_filename is None:
                    # resp_content = f"抱歉，我还没学会唱{content}"
                    # 根据配置的 匹配失败回复文案来进行合成
                    resp_content = My_handle.config.get("choose_song", "match_fail_copy").format(content=content)
                    logger.info(f"[AI回复{username}]：{resp_content}")

                    message = {
                        "type": "comment",
                        "tts_type": My_handle.config.get("audio_synthesis_type"),
                        "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                        "config": My_handle.config.get("filter"),
                        "username": username,
                        "content": resp_content
                    }

                    
                    self.audio_synthesis_handle(message)

                    self.webui_show_chat_log_callback("点歌", data, resp_content)

                    return True
                
                resp_content = My_handle.audio.search_files(My_handle.config.get('choose_song', 'song_path'), song_filename, True)
                if resp_content == []:
                    return True
                
                logger.debug(f"匹配到的音频原相对路径：{resp_content[0]}")

                # 拼接音频文件路径
                resp_content = f"{My_handle.config.get('choose_song', 'song_path')}/{resp_content[0]}"
                resp_content = os.path.abspath(resp_content)
                logger.info(f"点歌成功！匹配到的音频路径：{resp_content}")
                
                message = {
                    "type": "song",
                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                    "config": My_handle.config.get("filter"),
                    "username": username,
                    "content": resp_content
                }

                self.webui_show_chat_log_callback("点歌", data, resp_content)
                
                self.audio_synthesis_handle(message)

                return True
            # 判断取消点歌命令是否正确
            elif stop_cmd:
                My_handle.audio.stop_current_audio()

                return True
            

        return False


    """
    
         ]@@@@@               =@@       @@^              =@@@@@@].  .@@` ./@@@ ,@@@^                /@^                     
        @@^      @@*          =@@       @@^              =@@   ,@@\      =@@   @@^                                          
        \@@].  =@@@@@.=@@@@@` =@@@@@@@. @@^ ./@@@@\.     =@@    .@@^.@@.@@@@@@@@@@@.@@   @@^ /@@@@^ @@^ ./@@@@@]  @@/@@@@.  
          ,\@@\  @@*   .]]/@@ =@@.  =@\ @@^ @@\]]/@^     =@@     @@^.@@. =@@   @@^ .@@   @@^ @@\`   @@^ @@^   \@^ @@`  \@^  
             @@^ @@* ,@@` =@@ =@@   =@/ @@^ @@`          =@@   ./@/ .@@. =@@   @@^ .@@.  @@^   ,\@@ @@^ @@^   /@^ @@*  =@^  
       .@@@@@@/  \@@@.@@@@@@@ =@@@@@@/  @@^ .\@@@@@.     =@@@@@@/`  .@@. =@@   @@^  =@@@@@@^.@@@@@^ @@^ .\@@@@@`  @@*  =@^ 
    
    """

    # 画图模式 SD 处理
    def sd_handle(self, data):
        """画图模式 SD 处理

        Args:
            data (dict): 用户名 弹幕数据

        Returns:
            bool: 是否触发并处理
        """
        username = data["username"]
        content = data["content"]

        # 合并字符串末尾连续的*  主要针对获取不到用户名的情况
        username = My_handle.common.merge_consecutive_asterisks(username)

        if content.startswith(My_handle.config.get("sd", "trigger")):
            # 违禁检测
            content = self.prohibitions_handle(content)
            if content is None:
                return
        
            if My_handle.config.get("sd", "enable") == False:
                logger.info("您还未启用SD模式，无法使用画画功能")
                return True
            else:
                # 输出当前用户发送的弹幕消息
                logger.info(f"[{username}]: {content}")

                # 删除文本中的命令前缀
                content = content[len(My_handle.config.get("sd", "trigger")):]

                if My_handle.config.get("sd", "translate_type") != "none":
                    # 判断翻译类型 进行翻译工作
                    tmp = My_handle.my_translate.trans(content, My_handle.config.get("sd", "translate_type"))
                    if tmp:
                        content = tmp

                """
                根据聊天类型执行不同逻辑
                """ 
                chat_type = My_handle.config.get("sd", "prompt_llm", "type")
                if chat_type in self.chat_type_list:
                    content = My_handle.config.get("sd", "prompt_llm", "before_prompt") + \
                        content + My_handle.config.get("after_prompt")
                    
                    data_json = {
                        "username": username,
                        "content": content,
                        "ori_username": data["username"],
                        "ori_content": data["content"]
                    }
                    resp_content = self.llm_handle(chat_type, data_json)
                    if resp_content is not None:
                        logger.info(f"[AI回复{username}]：{resp_content}")
                    else:
                        resp_content = ""
                        logger.warning(f"警告：{chat_type}无返回")
                elif chat_type == "none" or chat_type == "reread" or chat_type == "game":
                    resp_content = content
                else:
                    resp_content = content

                logger.info(f"传给SD接口的内容：{resp_content}")

                self.sd.process_input(resp_content)
                return True
            
        return False


    # 弹幕格式检查和特殊字符替换和指定语言过滤
    def comment_check_and_replace(self, content):
        """弹幕格式检查和特殊字符替换和指定语言过滤

        Args:
            content (str): 待处理的弹幕内容

        Returns:
            str: 处理完毕后的弹幕内容/None
        """
        # 判断弹幕是否以xx起始，如果是则返回None
        if My_handle.config.get("filter", "before_filter_str") and any(
                content.startswith(prefix) for prefix in My_handle.config.get("filter", "before_filter_str")):
            return None

        # 判断弹幕是否以xx结尾，如果是则返回None
        if My_handle.config.get("filter", "after_filter_str") and any(
                content.endswith(prefix) for prefix in My_handle.config.get("filter", "after_filter_str")):
            return None

        # 判断弹幕是否以xx起始，如果不是则返回None
        if My_handle.config.get("filter", "before_must_str") and not any(
                content.startswith(prefix) for prefix in My_handle.config.get("filter", "before_must_str")):
            return None
        else:
            for prefix in My_handle.config.get("filter", "before_must_str"):
                if content.startswith(prefix):
                    content = content[len(prefix):]  # 删除匹配的开头
                    break

        # 判断弹幕是否以xx结尾，如果不是则返回None
        if My_handle.config.get("filter", "after_must_str") and not any(
                content.endswith(prefix) for prefix in My_handle.config.get("filter", "after_must_str")):
            return None
        else:
            for prefix in My_handle.config.get("filter", "after_must_str"):
                if content.endswith(prefix):
                    content = content[:-len(prefix)]  # 删除匹配的结尾
                    break

        # 全为标点符号
        if My_handle.common.is_punctuation_string(content):
            return None

        # 换行转为,
        content = content.replace('\n', ',')

        # 表情弹幕过滤
        if My_handle.config.get("filter", "emoji"):
            # 如b站的表情弹幕就是[表情名]的这种格式，采用正则表达式进行过滤
            content = re.sub(r'\[.*?\]', '', content)
            logger.info(f"表情弹幕过滤后：{content}")

        # 语言检测
        if My_handle.common.lang_check(content, My_handle.config.get("need_lang")) is None:
            logger.warning("语言检测不通过，已过滤")
            return None

        return content


    # 违禁处理
    def prohibitions_handle(self, content):
        """违禁处理

        Args:
            content (str): 带判断的字符串内容

        Returns:
            str: 是：None 否返回：content
        """
        # 含有链接
        if My_handle.common.is_url_check(content):
            logger.warning(f"链接：{content}")
            return None
        
        # 违禁词检测
        if My_handle.config.get("filter", "badwords", "enable"):
            if My_handle.common.profanity_content(content):
                logger.warning(f"违禁词：{content}")
                return None
            
            bad_word = My_handle.common.check_sensitive_words2(My_handle.config.get("filter", "badwords", "path"), content)
            if bad_word is not None:
                logger.warning(f"命中本地违禁词：{bad_word}")

                # 是否丢弃
                if My_handle.config.get("filter", "badwords", "discard"):
                    return None
                
                # 进行违禁词替换
                content = content.replace(bad_word, My_handle.config.get("filter", "badwords", "replace"))

                logger.info(f"违禁词替换后：{content}")

                # 回调，多次进行违禁词过滤替换
                return self.prohibitions_handle(content)


            # 同拼音违禁词过滤
            if My_handle.config.get("filter", "badwords", "bad_pinyin_path") != "":
                if My_handle.common.check_sensitive_words3(My_handle.config.get("filter", "badwords", "bad_pinyin_path"), content):
                    logger.warning(f"同音违禁词：{content}")
                    return None

        return content


    # 直接复读
    def reread_handle(self, data, filter=False, type="reread"):
        """复读处理

        Args:
            data (dict): 包含用户名,弹幕内容
            filter (bool): 是否开启复读内容的过滤
            type (str): 复读数据的类型（reread | trends_copywriting）

        Returns:
            _type_: 寂寞
        """
        try:
            username = data["username"]
            content = data["content"]

            logger.info(f"复读内容：{content}")

            if filter:
                # 违禁处理
                content = self.prohibitions_handle(content)
                if content is None:
                    return
                
                # 弹幕格式检查和特殊字符替换和指定语言过滤
                content = self.comment_check_and_replace(content)
                if content is None:
                    return
                
                # 判断字符串是否全为标点符号，是的话就过滤
                if My_handle.common.is_punctuation_string(content):
                    logger.debug(f"用户:{username}]，发送纯符号的弹幕，已过滤")
                    return
            
            # 音频合成时需要用到的重要数据
            message = {
                "type": type,
                "tts_type": My_handle.config.get("audio_synthesis_type"),
                "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                "config": My_handle.config.get("filter"),
                "username": username,
                "content": content
            }

            # 音频插入的索引（适用于audio_player_v2）
            if "insert_index" in data:
                message["insert_index"] = data["insert_index"]

            logger.debug(message)

            # 洛曦 直播弹幕助手
            if My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable") and \
                "reread" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "type") and \
                "消息产生时" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                asyncio.run(send_msg_to_live_comment_assistant(My_handle.config.get("luoxi_project", "Live_Comment_Assistant"), content))

            self.audio_synthesis_handle(message)
        except Exception as e:
            logger.error(traceback.format_exc())

    # 调教
    def tuning_handle(self, data_json):
        """调教LLM处理

        Args:
            data_json (dict): 包含用户名,弹幕内容

        Returns:
            _type_: 寂寞
        """
        try:
            logger.info(f"调教命令：{data_json['content']}")

            """
            根据聊天类型执行不同逻辑
            """ 
            chat_type = My_handle.config.get("chat_type")
            if chat_type in self.chat_type_list:
                data_json["ori_username"] = data_json["username"]
                data_json["ori_content"] = data_json["content"]
                resp_content = self.llm_handle(chat_type, data_json)
                if resp_content is not None:
                    logger.info(f"[AI回复{My_handle.config.get('talk', 'username')}]：{resp_content}")
                else:
                    logger.warning(f"警告：{chat_type}无返回")
        except Exception as e:
            logger.error(traceback.format_exc())

    # 弹幕日志记录
    def write_to_comment_log(self, resp_content: str, data: dict):
        try:
            # 将 AI 回复记录到日志文件中
            with open(self.comment_file_path, "r+", encoding="utf-8") as f:
                tmp_content = f.read()
                # 将指针移到文件头部位置（此目的是为了让直播中读取日志文件时，可以一直让最新内容显示在顶部）
                f.seek(0, 0)
                # 不过这个实现方式，感觉有点低效
                # 设置单行最大字符数，主要目的用于接入直播弹幕显示时，弹幕过长导致的显示溢出问题
                max_length = 20
                resp_content_substrings = [resp_content[i:i + max_length] for i in range(0, len(resp_content), max_length)]
                resp_content_joined = '\n'.join(resp_content_substrings)

                # 根据 弹幕日志类型进行各类日志写入
                if My_handle.config.get("comment_log_type") == "问答":
                    f.write(f"[{data['username']} 提问]:\n{data['content']}\n[AI回复{data['username']}]:{resp_content_joined}\n" + tmp_content)
                elif My_handle.config.get("comment_log_type") == "问题":
                    f.write(f"[{data['username']} 提问]:\n{data['content']}\n" + tmp_content)
                elif My_handle.config.get("comment_log_type") == "回答":
                    f.write(f"[AI回复{data['username']}]:\n{resp_content_joined}\n" + tmp_content)
        except Exception as e:
            logger.error(traceback.format_exc())

    """

                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@@@@@@^         /@@@@@@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@@@@@@@        ,@@@@@@@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@@@@@@@^       /@@@@@@@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@@@@@@@@.     ,@@@@@@@@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@@@@@@@@^     /@@@@@@@@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@=@@@@@@@.   ,@@@@@@@^@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@.@@@@@@@^   @@@@@@@@.@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@ =@@@@@@@. =@@@@@@@^.@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@ .@@@@@@@^ @@@@@@@@ .@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@  =@@@@@@@=@@@@@@@^ .@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@  .@@@@@@@@@@@@@@@  .@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@   =@@@@@@@@@@@@@^  .@@@@@@@@@              
                 .@@@@@@@@@@@                    .@@@@@@@@@@@                    .@@@@@@@@@   .@@@@@@@@@@@@/   .@@@@@@@@@              
                 .@@@@@@@@@@@@@@@@@@@@@@@@@@@^   .@@@@@@@@@@@@@@@@@@@@@@@@@@@^   .@@@@@@@@@    =@@@@@@@@@@@`   .@@@@@@@@@              
                 .@@@@@@@@@@@@@@@@@@@@@@@@@@@^   .@@@@@@@@@@@@@@@@@@@@@@@@@@@^   .@@@@@@@@@    .@@@@@@@@@@/    .@@@@@@@@@              
                 .@@@@@@@@@@@@@@@@@@@@@@@@@@@^   .@@@@@@@@@@@@@@@@@@@@@@@@@@@^   .@@@@@@@@@     =@@@@@@@@@`    .@@@@@@@@@              
                 .@@@@@@@@@@@@@@@@@@@@@@@@@@@^   .@@@@@@@@@@@@@@@@@@@@@@@@@@@^   .@@@@@@@@@     .@@@@@@@@/     .@@@@@@@@@  

    """


    # LLM处理
    def llm_handle(self, chat_type, data, type="chat", webui_show=True):
        """LLM统一处理

        Args:
            chat_type (str): 聊天类型
            data (str): dict，含用户名和内容
            type (str): 调用的类型（chat / vision）
            webui_show (bool): 是否在webui上显示

        Returns:
            str: LLM返回的结果
        """
        try:
            # 判断弹幕是否以xx起始，如果不是则返回None 不触发LLM
            if My_handle.config.get("filter", "before_must_str_for_llm") != []:
                if any(data["ori_content"].startswith(prefix) for prefix in My_handle.config.get("filter", "before_must_str_for_llm")):
                    pass
                else:
                    return None
            
            # 判断弹幕是否以xx结尾，如果不是则返回None
            if My_handle.config.get("filter", "after_must_str_for_llm") != []:
                if any(data["ori_content"].endswith(prefix) for prefix in My_handle.config.get("filter", "after_must_str_for_llm")):
                    pass
                else:
                    return None

            resp_content = None
            
            logger.debug(f"chat_type={chat_type}, data={data}")

            if type == "chat":
                # 使用 getattr 来动态获取属性
                if getattr(self, chat_type, None) is None:
                    self.get_chat_model(chat_type, My_handle.config)
                    # setattr(self, chat_type, GPT_MODEL.get(chat_type))
            
                # 新增LLM需要在这里追加
                chat_model_methods = {
                    "chatgpt": lambda: self.chatgpt.get_gpt_resp(data["username"], data["content"]),
                    "chatterbot": lambda: self.bot.get_response(data["content"]).text,
                    "chat_with_file": lambda: self.chat_with_file.get_model_resp(data["content"]),
                    "text_generation_webui": lambda: self.text_generation_webui.get_resp(data["content"]),
                    "sparkdesk": lambda: self.sparkdesk.get_resp(data["content"]),
                    "langchain_chatchat": lambda: self.langchain_chatchat.get_resp(data["content"]),
                    "zhipu": lambda: self.zhipu.get_resp(data["content"]),
                    "bard": lambda: self.bard_api.get_resp(data["content"]),
                    "tongyi": lambda: self.tongyi.get_resp(data["content"]),
                    "tongyixingchen": lambda: self.tongyixingchen.get_resp(data["content"]),
                    "my_wenxinworkshop": lambda: self.my_wenxinworkshop.get_resp(data["content"]),
                    "gemini": lambda: self.gemini.get_resp(data["content"]),
                    "koboldcpp": lambda: self.koboldcpp.get_resp({"prompt": data["content"]}),
                    "anythingllm": lambda: self.anythingllm.get_resp({"prompt": data["content"]}),
                    "gpt4free": lambda: self.gpt4free.get_resp({"prompt": data["content"]}),
                    "custom_llm": lambda: self.custom_llm.get_resp({"prompt": data["content"]}),
                    "llm_tpu": lambda: self.llm_tpu.get_resp({"prompt": data["content"]}),
                    "dify": lambda: self.dify.get_resp({"prompt": data["content"]}),
                    "volcengine": lambda: self.volcengine.get_resp({"prompt": data["content"]}),
                    "reread": lambda: data["content"]
                }
            elif type == "vision":
                # 使用 getattr 来动态获取属性
                if getattr(self, chat_type, None) is None:
                    self.get_vision_model(chat_type, My_handle.config.get("image_recognition", chat_type))
                
                # 新增LLM需要在这里追加
                chat_model_methods = {
                    "gemini": lambda: self.image_recognition_model.get_resp_with_img(data["content"], data["img_data"]),
                    "zhipu": lambda: self.image_recognition_model.get_resp_with_img(data["content"], data["img_data"]),
                }

            # 使用字典映射的方式来获取响应内容
            resp_content = chat_model_methods.get(chat_type, lambda: data["content"])()

            if resp_content is not None:
                resp_content = resp_content.strip()
                # 替换 \n换行符 \n字符串为空
                resp_content = re.sub(r'\\n|\n', '', resp_content)

                # 初始化过滤状态
                filter_state = {
                    'is_filtering': False,
                    'current_tag': None,
                    'buffer': ''
                }
                # 过滤<></>标签内容 主要针对deepseek返回
                resp_content = My_handle.common.llm_resp_content_filter_tags(resp_content, filter_state)

            # 判断 回复模板 是否启用
            if My_handle.config.get("reply_template", "enable"):
                # 根据模板变量关系进行回复内容的替换
                # 假设有多个未知变量，用户可以在此处定义动态变量
                variables = {
                    'username': data["username"][:self.config.get("reply_template", "username_max_len")],
                    'data': resp_content,
                    'cur_time': My_handle.common.get_bj_time(5),
                }

                reply_template_copywriting = My_handle.common.get_list_random_or_default(self.config.get("reply_template", "copywriting"), "{data}")
                # 使用字典进行字符串替换
                if any(var in reply_template_copywriting for var in variables):
                    resp_content = reply_template_copywriting.format(**{var: value for var, value in variables.items() if var in reply_template_copywriting})


            logger.debug(f"resp_content={resp_content}")

            # 返回为空，触发异常报警
            if resp_content is None:
                self.abnormal_alarm_handle("llm")
                logger.warning("LLM没有正确返回数据，请排查配置、网络等是否正常。如果排查后都没有问题，可能是接口改动导致的兼容性问题，可以前往官方仓库提交issue，传送门：https://github.com/Ikaros-521/AI-Vtuber/issues")
            
            # 是否启用webui回显
            if webui_show and resp_content:
                self.webui_show_chat_log_callback(chat_type, data, resp_content)

            return resp_content
        except Exception as e:
            logger.error(traceback.format_exc())

        return None

    # 流式LLM处理 + 音频合成
    def llm_stream_handle_and_audio_synthesis(self, chat_type, data, type="chat", webui_show=True):
        """LLM统一处理

        Args:
            chat_type (str): 聊天类型
            data (str): dict，含用户名和内容
            type (str): 调用的类型（chat / vision）
            webui_show (bool): 是否在webui上显示

        Returns:
            str: LLM返回的结果
        """
        try:
            # 判断弹幕是否以xx起始，如果不是则返回None 不触发LLM
            if My_handle.config.get("filter", "before_must_str_for_llm") != []:
                if any(data["ori_content"].startswith(prefix) for prefix in My_handle.config.get("filter", "before_must_str_for_llm")):
                    pass
                else:
                    return None
            
            # 判断弹幕是否以xx结尾，如果不是则返回None
            if My_handle.config.get("filter", "after_must_str_for_llm") != []:
                if any(data["ori_content"].endswith(prefix) for prefix in My_handle.config.get("filter", "after_must_str_for_llm")):
                    pass
                else:
                    return None

            # 最终返回的整个llm响应内容
            resp_content = ""

            # 备份一下传给LLM的内容，用于上下文记忆
            content_bak = data["content"]
            
            logger.debug(f"chat_type={chat_type}, data={data}")

            if type == "chat":
                # 使用 getattr 来动态获取属性
                if getattr(self, chat_type, None) is None:
                    self.get_chat_model(chat_type, My_handle.config)
                    # setattr(self, chat_type, GPT_MODEL.get(chat_type))
            
                # 新增LLM需要在这里追加
                chat_model_methods = {
                    "chatgpt": lambda: self.chatgpt.get_gpt_resp(data["username"], data["content"], stream=True),
                    "zhipu": lambda: self.zhipu.get_resp(data["content"], stream=True),
                    "tongyi": lambda: self.tongyi.get_resp(data["content"], stream=True),
                    "tongyixingchen": lambda: self.tongyixingchen.get_resp(data["content"], stream=True),
                    "my_wenxinworkshop": lambda: self.my_wenxinworkshop.get_resp(data["content"], stream=True),
                    "volcengine": lambda: self.volcengine.get_resp({"prompt": data["content"]}, stream=True),
                    "dify": lambda: self.dify.get_resp({"prompt": data["content"]}, stream=True),
                }
            elif type == "vision":
                pass

            # 使用字典映射的方式来获取响应内容
            resp = chat_model_methods.get(chat_type, lambda: data["content"])()
            
            def split_by_chinese_punctuation(s):
                # 定义中文标点符号集合
                chinese_punctuation = "。、，；！？"
                
                # 遍历字符串中的每一个字符
                for i, char in enumerate(s):
                    if char in chinese_punctuation:
                        # 找到第一个中文标点符号，进行切分
                        return {"ret": True, "content1": s[:i+1], "content2": s[i+1:].lstrip()}
                
                # 如果没有找到中文标点符号，返回原字符串和空字符串
                return {"ret": False, "content1": s, "content2": ""}

            if resp is not None:
                # 流式开始拼接文本内容时，初始的临时文本存储变量
                tmp = ""

                # 判断 回复模板 是否启用
                if My_handle.config.get("reply_template", "enable"):
                    # 根据模板变量关系进行回复内容的替换
                    # 假设有多个未知变量，用户可以在此处定义动态变量
                    variables = {
                        'username': data["username"][:self.config.get("reply_template", "username_max_len")],
                        'data': "",
                        'cur_time': My_handle.common.get_bj_time(5),
                    }

                    reply_template_copywriting = My_handle.common.get_list_random_or_default(self.config.get("reply_template", "copywriting"), "")
                    # 使用字典进行字符串替换
                    if any(var in reply_template_copywriting for var in variables):
                        tmp = reply_template_copywriting.format(**{var: value for var, value in variables.items() if var in reply_template_copywriting})


                # 已经切掉的字符长度，针对一些特殊llm的流式输出，需要去掉前面的字符
                cut_len = 0

                # 智谱 智能体情况特殊处理
                if chat_type == "zhipu" and My_handle.config.get("zhipu", "model") == "智能体":
                    resp = resp.iter_lines()

                # 初始化过滤状态
                filter_state = {
                    'is_filtering': False,
                    'current_tag': None,
                    'buffer': ''
                }

                buffer = b""

                def tmp_handle(resp_json: dict, tmp: str, cut_len: int=0):
                    if resp_json["ret"]:
                        # 切出来的句子
                        tmp_content = resp_json["content1"]
                        
                        #logger.warning(f"句子生成：{tmp_content}")

                        if chat_type in ["chatgpt", "zhipu", "tongyixingchen", "my_wenxinworkshop", "volcengine", "dify"]:
                            # 智谱 智能体情况特殊处理
                            if chat_type == "zhipu" and My_handle.config.get("zhipu", "model") == "智能体":
                                # 记录 并追加切出的文本长度
                                cut_len += len(tmp_content)
                            else:
                                # 标点符号后的内容包留，用于之后继续追加内容
                                tmp = resp_json["content2"]
                        elif chat_type in ["tongyi"]:
                            # 记录 并追加切出的文本长度
                            cut_len += len(tmp_content)
                            
                        """
                        双重过滤，为您保驾护航
                        """
                        tmp_content = tmp_content.strip()

                        tmp_content = tmp_content.replace('\n', '。')

                        # 替换 \n换行符 \n字符串为空
                        tmp_content = re.sub(r'\\n|\n', '', tmp_content)
                        
                        # LLM回复的内容进行违禁判断
                        tmp_content = self.prohibitions_handle(tmp_content)
                        if tmp_content is None:
                            return tmp, cut_len

                        # logger.info("tmp_content=" + tmp_content)

                        # 回复内容是否进行翻译
                        if My_handle.config.get("translate", "enable") and (My_handle.config.get("translate", "trans_type") == "回复" or \
                            My_handle.config.get("translate", "trans_type") == "弹幕+回复"):
                            tmp = My_handle.my_translate.trans(tmp_content)
                            if tmp:
                                tmp_content = tmp

                        self.write_to_comment_log(tmp_content, data)

                        # 判断按键映射触发类型
                        if My_handle.config.get("key_mapping", "type") == "回复" or My_handle.config.get("key_mapping", "type") == "弹幕+回复":
                            # 替换内容
                            data["content"] = tmp_content
                            # 按键映射 触发后不执行后面的其他功能
                            if self.key_mapping_handle("回复", data):
                                pass

                        # 判断自定义命令触发类型
                        if My_handle.config.get("custom_cmd", "type") == "回复" or My_handle.config.get("custom_cmd", "type") == "弹幕+回复":
                            # 替换内容
                            data["content"] = tmp_content
                            # 自定义命令 触发后不执行后面的其他功能
                            if self.custom_cmd_handle("回复", data):
                                pass
                            

                        # 音频合成时需要用到的重要数据
                        message = {
                            "type": "comment",
                            "tts_type": My_handle.config.get("audio_synthesis_type"),
                            "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                            "config": My_handle.config.get("filter"),
                            "username": data['username'],
                            "content": tmp_content
                        }

                        # 洛曦 直播弹幕助手
                        if My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable") and \
                            "comment_reply" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "type") and \
                            "消息产生时" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                            asyncio.run(send_msg_to_live_comment_assistant(My_handle.config.get("luoxi_project", "Live_Comment_Assistant"), tmp_content))

                        self.audio_synthesis_handle(message)

                        return tmp, cut_len

                    return tmp, cut_len


                for chunk in resp:
                    # logger.warning(chunk)
                    if chunk is None:
                        continue

                    if chat_type in ["chatgpt", "zhipu"]:
                        # 智谱 智能体情况特殊处理
                        if chat_type == "zhipu" and My_handle.config.get("zhipu", "model") == "智能体":
                            decoded_line = chunk.decode('utf-8')
                            if decoded_line.startswith('data:'):
                                data_dict = json.loads(decoded_line[5:])
                                message = data_dict.get("message")
                                if len(message) > 0:
                                    content = message.get("content")
                                    if len(content) > 0:
                                        response_type = content.get("type")
                                        if response_type == "text":
                                            text = content.get("text", "")
                                            #logger.warning(f"cut_len={cut_len},智谱返回内容：{text}")
                                            # 这个是一直输出全部的内容，所以要切分掉已经处理的文本长度
                                            tmp = text[cut_len:]
                                            resp_content = text
                                        else:
                                            continue
                                    else:
                                        continue
                                else:
                                    continue
                            else:
                                continue
                        else:
                            if chunk.choices[0].delta.content:
                                # 过滤<></>标签内容 主要针对deepseek返回
                                chunk.choices[0].delta.content = My_handle.common.llm_resp_content_filter_tags(chunk.choices[0].delta.content, filter_state)

                                # 流式的内容是追加形式的
                                tmp += chunk.choices[0].delta.content
                                resp_content += chunk.choices[0].delta.content
                    elif chat_type in ["tongyi"]:
                        # 这个是一直输出全部的内容，所以要切分掉已经处理的文本长度
                        tmp = chunk.output.choices[0].message.content[cut_len:]
                        resp_content = chunk.output.choices[0].message.content
                    elif chat_type in ["tongyixingchen"]:
                        # 流式的内容是追加形式的
                        tmp += chunk.data.choices[0].messages[0].content
                        resp_content += chunk.data.choices[0].messages[0].content
                    elif chat_type in ["volcengine"]:
                        tmp += chunk.choices[0].delta.content
                        resp_content += chunk.choices[0].delta.content
                    elif chat_type in ["my_wenxinworkshop"]:
                        tmp += chunk
                        resp_content += chunk
                    elif chat_type in ["dify"]:
                        # 将新的数据添加到缓冲区
                        buffer += chunk
                        
                        # 初始化resp_json
                        resp_json = {"ret": False, "content1": "", "content2": ""}
                        
                        # 尝试按行分割数据
                        while b"\n" in buffer:
                            # 获取一个完整的行
                            line, buffer = buffer.split(b"\n", 1)
                            line = line.strip()
                            
                            # 跳过空行
                            if not line:
                                continue
                                
                            # 处理data:前缀
                            if line.startswith(b"data: "):
                                try:
                                    # 解析JSON数据
                                    data_chunk = json.loads(line[6:].decode('utf-8'))
                                    
                                    # 处理不同类型的事件
                                    if "event" in data_chunk:
                                        if data_chunk["event"] == "message":
                                            answer = data_chunk.get("answer", "")

                                            # 过滤<></>标签内容 主要针对deepseek返回
                                            answer = My_handle.common.llm_resp_content_filter_tags(answer, filter_state)

                                            tmp += answer
                                            resp_content += answer

                                            resp_json = split_by_chinese_punctuation(tmp)
                                            #logger.warning(f"resp_json={resp_json}")
                                            tmp, cut_len = tmp_handle(resp_json, tmp, cut_len)
                                        elif data_chunk["event"] == "message_end":
                                            self.dify.add_assistant_msg_to_session(data_chunk["conversation_id"])
                                            resp_json = split_by_chinese_punctuation(tmp)
                                            if not resp_json['ret']:
                                                resp_json['ret'] = True
                                                logger.warning(f"resp_json={resp_json}")
                                                tmp, cut_len = tmp_handle(resp_json, tmp, cut_len)
                                            logger.info(f"[{chat_type}] 流式接收完毕")
                                            break
                                        elif data_chunk["event"] == "error":
                                            logger.error(f"Dify返回错误: {data_chunk}")
                                            break
                                except json.JSONDecodeError as e:
                                    logger.error(f"JSON解析错误: {e}. 原始数据: {line}")
                                    continue
                            else:
                                logger.debug(f"跳过非data:开头的行: {line}")
                                continue

                    if chat_type not in ["dify"]:
                        # 用于切分，根据中文标点符号切分语句
                        resp_json = split_by_chinese_punctuation(tmp)
                        #logger.warning(f"resp_json={resp_json}")
                        tmp, cut_len = tmp_handle(resp_json, tmp, cut_len)
                        #logger.warning(f"cut_len={cut_len}, tmp={tmp}")

                    if chat_type in ["chatgpt", "zhipu"]:
                        # logger.info(chunk)
                        # 智谱 智能体情况特殊处理
                        if chat_type == "zhipu" and My_handle.config.get("zhipu", "model") == "智能体":
                            decoded_line = chunk.decode('utf-8')
                            if decoded_line.startswith('data:'):
                                data_dict = json.loads(decoded_line[5:])
                                status = data_dict.get("status")
                                if len(status) > 0 and status == "finish":
                                    resp_json['ret'] = True
                                    tmp, cut_len = tmp_handle(resp_json, tmp, cut_len)

                                    logger.info(f"[{chat_type}] 流式接收完毕")
                                    break
                        else:
                            if chunk.choices[0].finish_reason == "stop":
                                if not resp_json['ret']:
                                    resp_json['ret'] = True
                                    tmp, cut_len = tmp_handle(resp_json, tmp, cut_len)

                                logger.info(f"[{chat_type}] 流式接收完毕")
                                break
                    elif chat_type in ["tongyi"]:
                        if chunk.output.choices[0].finish_reason == "stop":
                            if not resp_json['ret']:
                                resp_json['ret'] = True
                                tmp, cut_len = tmp_handle(resp_json, tmp, cut_len)

                            logger.info(f"[{chat_type}] 流式接收完毕")
                            break


            # 返回为空，触发异常报警
            else:
                self.abnormal_alarm_handle("llm")
                logger.warning("LLM没有正确返回数据，请排查配置、网络等是否正常。如果排查后都没有问题，可能是接口改动导致的兼容性问题，可以前往官方仓库提交issue，传送门：https://github.com/Ikaros-521/AI-Vtuber/issues")
            
            # 是否启用webui回显
            if webui_show:
                # 去除resp_content字符串最开始无用的空格和换行
                resp_content = resp_content.lstrip()

                self.webui_show_chat_log_callback(chat_type, data, resp_content)

            # 添加返回到上下文记忆
            if type == "chat":
                # TODO：兼容更多流式LLM
                # 新增流式LLM需要在这里追加
                chat_model_methods = {
                    "chatgpt": lambda: self.chatgpt.add_assistant_msg_to_session(data["username"], resp_content),
                    "zhipu": lambda: self.zhipu.add_assistant_msg_to_session(content_bak, resp_content),
                    "tongyi": lambda: self.tongyi.add_assistant_msg_to_session(content_bak, resp_content),
                    "tongyixingchen": lambda: self.tongyixingchen.add_assistant_msg_to_session(content_bak, resp_content),
                    "my_wenxinworkshop": lambda: self.my_wenxinworkshop.add_assistant_msg_to_session(content_bak, resp_content),
                    "volcengine": lambda: self.volcengine.add_assistant_msg_to_session(content_bak, resp_content),
                }
            elif type == "vision":
                pass

            # 使用字典映射的方式来获取响应内容
            func = chat_model_methods.get(chat_type, resp_content)

            if callable(func):
                # 如果 func 是一个可调用对象（函数），则执行它
                resp = func()
            elif isinstance(func, str):
                # 如果 func 是字符串，跳过执行
                pass
            else:
                # 如果 func 既不是函数也不是字符串，处理其他情况
                pass

            return resp_content
        except Exception as e:
            logger.error(traceback.format_exc())

        return None

    # 积分处理
    def integral_handle(self, type, data):
        """积分处理

        Args:
            type (str): 消息数据类型（comment/gift/entrance）
            data (dict): 平台侧传入的data数据，直接拿来做解析

        Returns:
            bool: 是否正常触发了积分事件，是True 否False
        """
        username = data["username"]
        
        if My_handle.config.get("integral", "enable"):
            # 根据消息类型进行对应处理
            if "comment" == type:
                content = data["content"]

                # 是否开启了签到功能
                if My_handle.config.get("integral", "sign", "enable"):
                    # 判断弹幕内容是否是命令
                    if content in My_handle.config.get("integral", "sign", "cmd"):
                        # 查询数据库中是否有当前用户的积分记录（缺个UID）
                        common_sql = '''
                        SELECT * FROM integral WHERE username =?
                        '''
                        integral_data = self.db.fetch_all(common_sql, (username,))

                        logger.debug(f"integral_data={integral_data}")

                        # 获取文案并合成语音，传入签到天数自动检索
                        def get_copywriting_and_audio_synthesis(sign_num):
                            # 判断当前签到天数在哪个签到数区间内，根据不同的区间提供不同的文案回复
                            for integral_sign_copywriting in My_handle.config.get("integral", "sign", "copywriting"):
                                # 在此区间范围内，所以你的配置一定要对，不然这里就崩溃了！！！
                                if int(integral_sign_copywriting["sign_num_interval"].split("-")[0]) <= \
                                    sign_num <= \
                                    int(integral_sign_copywriting["sign_num_interval"].split("-")[1]):
                                    # 匹配文案
                                    resp_content = random.choice(integral_sign_copywriting["copywriting"])
                                    
                                    logger.debug(f"resp_content={resp_content}")

                                    data_json = {
                                        "username": data["username"],
                                        "get_integral": int(My_handle.config.get("integral", "sign", "get_integral")),
                                        "sign_num": sign_num + 1
                                    } 

                                    resp_content = My_handle.common.dynamic_variable_replacement(resp_content, data_json)
                                    
                                    # 括号语法替换
                                    resp_content = My_handle.common.brackets_text_randomize(resp_content)
                                    
                                    # 生成回复内容
                                    message = {
                                        "type": "integral",
                                        "tts_type": My_handle.config.get("audio_synthesis_type"),
                                        "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                                        "config": My_handle.config.get("filter"),
                                        "username": username,
                                        "content": resp_content
                                    }

                                    # 洛曦 直播弹幕助手
                                    if My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable") and \
                                        "integral" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "type") and \
                                        "消息产生时" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                                        asyncio.run(send_msg_to_live_comment_assistant(My_handle.config.get("luoxi_project", "Live_Comment_Assistant"), resp_content))
                                    
                                    self.audio_synthesis_handle(message)

                        if integral_data == []:
                            # 积分表中没有该用户，插入数据
                            insert_data_sql = '''
                            INSERT INTO integral (platform, username, uid, integral, view_num, sign_num, last_sign_ts, total_price, last_ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            '''
                            self.db.execute(insert_data_sql, (
                                data["platform"], 
                                username, 
                                username, 
                                My_handle.config.get("integral", "sign", "get_integral"), 
                                1,
                                1,
                                datetime.now(),
                                0,
                                datetime.now())
                            )

                            logger.info(f"integral积分表 新增 用户：{username}")

                            get_copywriting_and_audio_synthesis(0)

                            return True
                        else:
                            integral_data = integral_data[0]
                            # 积分表中有该用户，更新数据

                            # 先判断last_sign_ts是否是今天，如果是，则说明已经打卡过了，不能重复打卡
                            # 获取日期时间字符串字段，此处是个坑点，一旦数据库结构发生改变或者select语句改了，就会关联影响！！！
                            date_string = integral_data[6]

                            # 获取日期部分（前10个字符），并与当前日期字符串比较
                            if date_string[:10] == datetime.now().date().strftime("%Y-%m-%d"):
                                resp_content = f"{username}您今天已经签到过了，不能重复打卡哦~"
                                message = {
                                    "type": "integral",
                                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                                    "config": My_handle.config.get("filter"),
                                    "username": username,
                                    "content": resp_content
                                }

                                # 洛曦 直播弹幕助手
                                if My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable") and \
                                    "integral" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "type") and \
                                    "消息产生时" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                                    asyncio.run(send_msg_to_live_comment_assistant(My_handle.config.get("luoxi_project", "Live_Comment_Assistant"), resp_content))
                                
                                self.audio_synthesis_handle(message)

                                return True

                            # 更新下用户数据
                            update_data_sql = '''
                            UPDATE integral SET integral=?, view_num=?, sign_num=?, last_sign_ts=?, last_ts=? WHERE username =?
                            '''
                            self.db.execute(update_data_sql, (
                                # 此处是个坑点，一旦数据库结构发生改变或者select语句改了，就会关联影响！！！
                                integral_data[3] + My_handle.config.get("integral", "sign", "get_integral"), 
                                integral_data[4] + 1,
                                integral_data[5] + 1,
                                datetime.now(),
                                datetime.now(),
                                username
                                )
                            )

                            logger.info(f"integral积分表 更新 用户：{username}")

                            get_copywriting_and_audio_synthesis(integral_data[5] + 1)

                            return True
            elif "gift" == type:
                # 是否开启了礼物功能
                if My_handle.config.get("integral", "gift", "enable"):
                    # 查询数据库中是否有当前用户的积分记录（缺个UID）
                    common_sql = '''
                    SELECT * FROM integral WHERE username =?
                    '''
                    integral_data = self.db.fetch_all(common_sql, (username,))

                    logger.debug(f"integral_data={integral_data}")

                    get_integral = int(float(My_handle.config.get("integral", "gift", "get_integral_proportion")) * data["total_price"])

                    # 获取文案并合成语音，传入总礼物金额自动检索
                    def get_copywriting_and_audio_synthesis(total_price):
                        # 判断当前礼物金额在哪个礼物金额区间内，根据不同的区间提供不同的文案回复
                        for integral_gift_copywriting in My_handle.config.get("integral", "gift", "copywriting"):
                            # 在此区间范围内，所以你的配置一定要对，不然这里就崩溃了！！！
                            if float(integral_gift_copywriting["gift_price_interval"].split("-")[0]) <= \
                                total_price <= \
                                float(integral_gift_copywriting["gift_price_interval"].split("-")[1]):
                                # 匹配文案
                                resp_content = random.choice(integral_gift_copywriting["copywriting"])
                                
                                logger.debug(f"resp_content={resp_content}")

                                data_json = {
                                    "username": data["username"],
                                    "gift_name": data["gift_name"],
                                    "get_integral": get_integral,
                                    'gift_num': data["num"],
                                    'unit_price': data["unit_price"],
                                    'total_price': data["total_price"],
                                    'cur_time': My_handle.common.get_bj_time(5),
                                } 

                                # 括号语法替换
                                resp_content = My_handle.common.brackets_text_randomize(resp_content)

                                # 动态变量替换
                                resp_content = My_handle.common.dynamic_variable_replacement(resp_content, data_json)
                                
                                # 生成回复内容
                                message = {
                                    "type": "integral",
                                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                                    "config": My_handle.config.get("filter"),
                                    "username": username,
                                    "content": resp_content
                                }

                                # 洛曦 直播弹幕助手
                                if My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable") and \
                                    "integral" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "type") and \
                                    "消息产生时" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                                    asyncio.run(send_msg_to_live_comment_assistant(My_handle.config.get("luoxi_project", "Live_Comment_Assistant"), resp_content))
                                

                                self.audio_synthesis_handle(message)

                    # TODO：此处有计算bug！！！ 总礼物价值计算不对，后期待优化
                    if integral_data == []:
                        # 积分表中没有该用户，插入数据
                        insert_data_sql = '''
                        INSERT INTO integral (platform, username, uid, integral, view_num, sign_num, last_sign_ts, total_price, last_ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        '''
                        self.db.execute(insert_data_sql, (
                            data["platform"], 
                            username, 
                            username, 
                            get_integral, 
                            1,
                            1,
                            datetime.now(),
                            data["total_price"],
                            datetime.now())
                        )

                        logger.info(f"integral积分表 新增 用户：{username}")

                        get_copywriting_and_audio_synthesis(data["total_price"])

                        return True
                    else:
                        integral_data = integral_data[0]
                        # 积分表中有该用户，更新数据

                        # 更新下用户数据
                        update_data_sql = '''
                        UPDATE integral SET integral=?, total_price=?, last_ts=? WHERE username =?
                        '''
                        self.db.execute(update_data_sql, (
                            # 此处是个坑点，一旦数据库结构发生改变或者select语句改了，就会关联影响！！！
                            integral_data[3] + get_integral, 
                            integral_data[7] + data["total_price"],
                            datetime.now(),
                            username
                            )
                        )

                        logger.info(f"integral积分表 更新 用户：{username}")

                        get_copywriting_and_audio_synthesis(data["total_price"])

                        return True
            elif "entrance" == type:
                # 是否开启了入场功能
                if My_handle.config.get("integral", "entrance", "enable"):
                    # 查询数据库中是否有当前用户的积分记录（缺个UID）
                    common_sql = '''
                    SELECT * FROM integral WHERE username =?
                    '''
                    integral_data = self.db.fetch_all(common_sql, (username,))

                    logger.debug(f"integral_data={integral_data}")

                    # 获取文案并合成语音，传入观看天数自动检索
                    def get_copywriting_and_audio_synthesis(view_num):
                        # 判断当前签到天数在哪个签到数区间内，根据不同的区间提供不同的文案回复
                        for integral_entrance_copywriting in My_handle.config.get("integral", "entrance", "copywriting"):
                            # 在此区间范围内，所以你的配置一定要对，不然这里就崩溃了！！！
                            if int(integral_entrance_copywriting["entrance_num_interval"].split("-")[0]) <= \
                                view_num <= \
                                int(integral_entrance_copywriting["entrance_num_interval"].split("-")[1]):

                                if len(integral_entrance_copywriting["copywriting"]) <= 0:
                                    return False

                                # 匹配文案
                                resp_content = random.choice(integral_entrance_copywriting["copywriting"])
                                
                                logger.debug(f"resp_content={resp_content}")

                                data_json = {
                                    "username": data["username"],
                                    "get_integral": int(My_handle.config.get("integral", "entrance", "get_integral")),
                                    "entrance_num": view_num + 1
                                } 

                                resp_content = My_handle.common.dynamic_variable_replacement(resp_content, data_json)
                                
                                # 括号语法替换
                                resp_content = My_handle.common.brackets_text_randomize(resp_content)

                                # 生成回复内容
                                message = {
                                    "type": "integral",
                                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                                    "config": My_handle.config.get("filter"),
                                    "username": username,
                                    "content": resp_content
                                }

                                # 洛曦 直播弹幕助手
                                if My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable") and \
                                    "integral" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "type") and \
                                    "消息产生时" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                                    asyncio.run(send_msg_to_live_comment_assistant(My_handle.config.get("luoxi_project", "Live_Comment_Assistant"), resp_content))
                                
                                
                                self.audio_synthesis_handle(message)

                    if integral_data == []:
                        # 积分表中没有该用户，插入数据
                        insert_data_sql = '''
                        INSERT INTO integral (platform, username, uid, integral, view_num, sign_num, last_sign_ts, total_price, last_ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        '''
                        self.db.execute(insert_data_sql, (
                            data["platform"], 
                            username, 
                            username, 
                            My_handle.config.get("integral", "entrance", "get_integral"), 
                            1,
                            0,
                            datetime.now(),
                            0,
                            datetime.now())
                        )

                        logger.info(f"integral积分表 新增 用户：{username}")

                        get_copywriting_and_audio_synthesis(1)

                        return True
                    else:
                        integral_data = integral_data[0]
                        # 积分表中有该用户，更新数据

                        # 先判断last_ts是否是今天，如果是，则说明已经观看过了，不能重复记录
                        # 获取日期时间字符串字段，此处是个坑点，一旦数据库结构发生改变或者select语句改了，就会关联影响！！！
                        date_string = integral_data[8]

                        # 获取日期部分（前10个字符），并与当前日期字符串比较
                        if date_string[:10] == datetime.now().date().strftime("%Y-%m-%d"):
                            return False

                        # 更新下用户数据
                        update_data_sql = '''
                        UPDATE integral SET integral=?, view_num=?, last_ts=? WHERE username =?
                        '''
                        self.db.execute(update_data_sql, (
                            # 此处是个坑点，一旦数据库结构发生改变或者select语句改了，就会关联影响！！！
                            integral_data[3] + My_handle.config.get("integral", "entrance", "get_integral"), 
                            integral_data[4] + 1,
                            datetime.now(),
                            username
                            )
                        )

                        logger.info(f"integral积分表 更新 用户：{username}")

                        get_copywriting_and_audio_synthesis(integral_data[4] + 1)

                        return True
            elif "crud" == type:
                content = data["content"]
                
                # 是否开启了查询功能
                if My_handle.config.get("integral", "crud", "query", "enable"):
                    # 判断弹幕内容是否是命令
                    if content in My_handle.config.get("integral", "crud", "query", "cmd"):
                        # 查询数据库中是否有当前用户的积分记录（缺个UID）
                        common_sql = '''
                        SELECT * FROM integral WHERE username =?
                        '''
                        integral_data = self.db.fetch_all(common_sql, (username,))

                        logger.debug(f"integral_data={integral_data}")

                        # 获取文案并合成语音，传入积分总数自动检索
                        def get_copywriting_and_audio_synthesis(total_integral):
                            # 匹配文案
                            resp_content = random.choice(My_handle.config.get("integral", "crud", "query", "copywriting"))
                            
                            logger.debug(f"resp_content={resp_content}")

                            data_json = {
                                "username": data["username"],
                                "integral": total_integral
                            }

                            resp_content = My_handle.common.dynamic_variable_replacement(resp_content, data_json)

                            # 如果积分为0，则返回个没积分的回复。不过这个基本没可能，除非有bug
                            if total_integral == 0:
                                resp_content = data["username"] + "，查询到您无积分。"
                            
                            # 括号语法替换
                            resp_content = My_handle.common.brackets_text_randomize(resp_content)

                            # 生成回复内容
                            message = {
                                "type": "integral",
                                "tts_type": My_handle.config.get("audio_synthesis_type"),
                                "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                                "config": My_handle.config.get("filter"),
                                "username": username,
                                "content": resp_content
                            }

                            # 洛曦 直播弹幕助手
                            if My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable") and \
                                "integral" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "type") and \
                                "消息产生时" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                                asyncio.run(send_msg_to_live_comment_assistant(My_handle.config.get("luoxi_project", "Live_Comment_Assistant"), resp_content))
                            
                            
                            self.audio_synthesis_handle(message)

                        if integral_data == []:
                            logger.info(f"integral积分表 查询不到 用户：{username}")

                            get_copywriting_and_audio_synthesis(0)

                            return True
                        else:
                            integral_data = integral_data[0]
                            # 积分表中有该用户

                            # 获取日期时间字符串字段，此处是个坑点，一旦数据库结构发生改变或者select语句改了，就会关联影响！！！
                            date_string = integral_data[3]

                            logger.info(f"integral积分表 用户：{username}，总积分：{date_string}")

                            get_copywriting_and_audio_synthesis(int(date_string))

                            return True
        return False


    # 按键映射处理
    def key_mapping_handle(self, type, data):
        """按键映射处理

        Args:
            type (str): 数据来源类型（弹幕/回复）
            data (dict): 平台侧传入的data数据，直接拿来做解析

        Returns:
            bool: 是否正常触发了按键映射事件，是True 否False
        """
        flag = False

        # 获取一个文案并传递给音频合成函数进行音频合成
        def get_a_copywriting_and_audio_synthesis(key_mapping_config, data):
            try:
                # 随机获取一个文案
                tmp = random.choice(key_mapping_config["copywriting"])

                # 括号语法替换
                tmp = My_handle.common.brackets_text_randomize(tmp)
                
                # 动态变量替换
                data_json = {
                    "username": data["username"],
                    "gift_name": data["gift_name"],
                    'gift_num': data["num"],
                    'unit_price': data["unit_price"],
                    'total_price': data["total_price"],
                    'cur_time': My_handle.common.get_bj_time(5),
                } 
                tmp = My_handle.common.dynamic_variable_replacement(tmp, data_json)

                # 音频合成时需要用到的重要数据
                message = {
                    "type": "key_mapping",
                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                    "config": My_handle.config.get("filter"),
                    "username": data["username"],
                    "content": tmp
                }

                logger.info(f'【触发按键映射】触发文案：{tmp}')

                # 洛曦 直播弹幕助手
                if My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable") and \
                    "key_mapping_copywriting" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "type") and \
                    "消息产生时" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                    asyncio.run(send_msg_to_live_comment_assistant(My_handle.config.get("luoxi_project", "Live_Comment_Assistant"), tmp))

                # TODO: 播放时的转发没有实现，因为类型定义没有这么细化
                self.audio_synthesis_handle(message)
            except Exception as e:
                logger.error(traceback.format_exc())

        # 获取一个本地音频并传递给音频合成函数进行音频播放
        def get_a_local_audio_and_audio_play(key_mapping_config, data):
            try:
                # 随机获取一个文案
                if len(key_mapping_config["local_audio"]) <= 0:
                    return
                
                tmp = random.choice(key_mapping_config["local_audio"])

                # 音频合成时需要用到的重要数据
                message = {
                    "type": "key_mapping",
                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                    "config": My_handle.config.get("filter"),
                    "username": data["username"],
                    "content": tmp,
                    "file_path": tmp
                }

                logger.info(f'【触发映射】播放本地音频：{tmp}')

                self.audio_synthesis_handle(message)
            except Exception as e:
                logger.error(traceback.format_exc())

        # 随机获取一个串口发送数据 内容
        def get_a_serial_send_data_and_send(key_mapping_config, data):
            try:
                async def connect_serial_and_send_data(serial_name, baudrate, serial_data_type, data):
                    from utils.serial_manager_instance import get_serial_manager

                    serial_manager = get_serial_manager()
                    # 关闭串口 单例没啥用啊，醉了
                    # resp_json = await serial_manager.disconnect(serial_name)
                    # 打开串口
                    resp_json = await serial_manager.connect(serial_name, int(baudrate))
                
                    # 发送数据到串口
                    resp_json = await serial_manager.send_data(serial_name, tmp, serial_data_type)

                    return resp_json
                    
                # 随机获取一个文案
                tmp = random.choice(key_mapping_config["serial_send_data"])

                # 括号语法替换
                tmp = My_handle.common.brackets_text_randomize(tmp)
                
                # 动态变量替换
                data_json = {
                    "username": data.get("username", ""),
                    "gift_name": data.get("gift_name", ""),
                    "gift_num": data.get("num", ""),
                    "unit_price": data.get("unit_price", ""),
                    "total_price": data.get("total_price", ""),
                    "cur_time": My_handle.common.get_bj_time(5),
                }
                tmp = My_handle.common.dynamic_variable_replacement(tmp, data_json)

                # 定义一个函数，通过 serial_name 获取 对应的config配置
                def get_serial_config(serial_name: str):
                    for config in My_handle.config.get("serial", "config"):
                        if config["serial_name"] == serial_name:
                            return config
                    return None  # 如果未找到匹配的 serial_name，返回 None

                serial_name = key_mapping_config["serial_name"]
                tmp_config = get_serial_config(serial_name)
                if tmp_config:
                    baudrate = tmp_config["baudrate"]
                    resp_json = asyncio.run(connect_serial_and_send_data(serial_name, baudrate, tmp_config["serial_data_type"], data))
                    
                    logger.info(f'【触发按键映射】触发串口：{tmp}，{resp_json["msg"]}')

                    return tmp
                
                logger.error(f"获取串口名：{serial_name} 的配置信息失败，请到 串口 页面检查配置是否正确！")
            
                return None
            except Exception as e:
                logger.error(traceback.format_exc())
                return None

        # 获取一个本地图片路径并传递给虚拟摄像头显示
        def get_a_img_path_and_send(key_mapping_config, data):
            try:
                # 随机获取一个图片路径
                if len(key_mapping_config["img_path"]) <= 0:
                    return
                
                tmp = random.choice(key_mapping_config["img_path"])

                self.sd.set_new_img(tmp)
            except Exception as e:
                logger.error(traceback.format_exc())


        try:
            import pyautogui

            # 关键词触发的内容统一到此函数进行处理
            def keyword_handle_trigger(trigger_type, keyword, key_mapping_config, data, flag):
                try:
                    if My_handle.config.get("key_mapping", trigger_type) in ["关键词", "关键词+礼物"]:
                        if trigger_type == "key_trigger_type":
                            logger.info(f'【触发按键映射】关键词：{keyword} 按键：{key_mapping_config["keys"]}')
                            for key in key_mapping_config["keys"]:
                                pyautogui.keyDown(key)
                            for key in key_mapping_config["keys"]:
                                pyautogui.keyUp(key)
                        elif trigger_type == "copywriting_trigger_type":
                            logger.info(f'【触发按键映射】关键词：{keyword} ，触发文案')
                            get_a_copywriting_and_audio_synthesis(key_mapping_config, data)
                        elif trigger_type == "local_audio_trigger_type":
                            logger.info(f'【触发按键映射】关键词：{keyword} ，触发本地音频')
                            get_a_local_audio_and_audio_play(key_mapping_config, data)
                        elif trigger_type == "serial_trigger_type":
                            logger.info(f'【触发按键映射】关键词：{keyword} ，触发串口')
                            get_a_serial_send_data_and_send(key_mapping_config, data)
                        elif trigger_type == "img_path_trigger_type":
                            logger.info(f'【触发按键映射】关键词：{keyword} ，触发图片')
                            get_a_img_path_and_send(key_mapping_config, data)
                        
                        flag = True
                        
                    single_sentence_trigger_once_enable = My_handle.config.get("key_mapping", f"{trigger_type.split('_')[0]}_single_sentence_trigger_once_enable")
                    return {"trigger_once_enable": single_sentence_trigger_once_enable, "flag": flag}
                except Exception as e:
                    logger.error(f"【触发按键映射】异常：{e}")
                    return {"trigger_once_enable": False, "flag": False}
                
            
            # 礼物触发的内容统一到此函数进行处理
            def gift_handle_trigger(trigger_type, gift_name, key_mapping_config, data, flag):
                try:
                    if My_handle.config.get("key_mapping", trigger_type) in ["礼物", "关键词+礼物"]:
                        if trigger_type == "key_trigger_type":
                            logger.info(f'【触发按键映射】礼物：{gift_name} 按键：{key_mapping_config["keys"]}')
                            for key in key_mapping_config["keys"]:
                                pyautogui.keyDown(key)
                            for key in key_mapping_config["keys"]:
                                pyautogui.keyUp(key)
                        elif trigger_type == "copywriting_trigger_type":
                            logger.info(f'【触发按键映射】礼物：{gift_name} ，触发文案')
                            get_a_copywriting_and_audio_synthesis(key_mapping_config, data)
                        elif trigger_type == "local_audio_trigger_type":
                            logger.info(f'【触发按键映射】礼物：{gift_name} ，触发本地音频')
                            get_a_local_audio_and_audio_play(key_mapping_config, data)
                        elif trigger_type == "serial_trigger_type":
                            logger.info(f'【触发按键映射】礼物：{gift_name} ，触发串口')
                            get_a_serial_send_data_and_send(key_mapping_config, data)
                        elif trigger_type == "img_path_trigger_type":
                            logger.info(f'【触发按键映射】礼物：{gift_name} ，触发图片')
                            get_a_img_path_and_send(key_mapping_config, data)

                        flag = True
                        
                    single_sentence_trigger_once_enable = My_handle.config.get("key_mapping", f"{trigger_type.split('_')[0]}_single_sentence_trigger_once_enable")
                    return {"trigger_once_enable": single_sentence_trigger_once_enable, "flag": flag}
                except Exception as e:
                    logger.error(f"【触发按键映射】异常：{e}")
                    return {"trigger_once_enable": False, "flag": False}
            
            # 官方文档：https://pyautogui.readthedocs.io/en/latest/keyboard.html#keyboard-keys
            if My_handle.config.get("key_mapping", "enable"):
                # 判断传入的数据是否包含gift_name键值，有的话则是礼物数据
                if "gift_name" in data:
                    # 获取key_mapping 所有 config数据
                    key_mapping_configs = My_handle.config.get("key_mapping", "config")

                    # 遍历key_mapping_configs
                    for key_mapping_config in key_mapping_configs:
                        # 遍历单个配置中所有礼物名
                        for gift in key_mapping_config["gift"]:
                            # 判断礼物名是否相同
                            if gift == data["gift_name"]:
                                """
                                不同的触发类型 都会进行独立的执行判断
                                """

                                for trigger in ["key_trigger_type", "copywriting_trigger_type", "local_audio_trigger_type", "serial_trigger_type"]:
                                    resp_json = gift_handle_trigger(trigger, gift, key_mapping_config, data, flag)
                                    if resp_json["trigger_once_enable"]:
                                        return resp_json["flag"]  
                else:
                    content = data["content"]
                    # 判断命令头是否匹配
                    start_cmd = My_handle.config.get("key_mapping", "start_cmd")
                    if start_cmd != "" and content.startswith(start_cmd):
                        # 删除命令头部
                        content = content[len(start_cmd):]

                    key_mapping_configs = My_handle.config.get("key_mapping", "config")
                    
                    for key_mapping_config in key_mapping_configs:
                        similarity = float(key_mapping_config["similarity"])
                        for keyword in key_mapping_config["keywords"]:
                            if type == "弹幕":
                                # 判断相似度
                                ratio = difflib.SequenceMatcher(None, content, keyword).ratio()
                                if ratio >= similarity:
                                    """
                                    不同的触发类型 都会进行独立的执行判断
                                    """
                                    
                                    for trigger in ["key_trigger_type", "copywriting_trigger_type", "local_audio_trigger_type", "serial_trigger_type", \
                                                    "img_path_trigger_type"]:
                                        resp_json = keyword_handle_trigger(trigger, keyword, key_mapping_config, data, flag)
                                        if resp_json["trigger_once_enable"]:
                                            return resp_json["flag"]  
                                        
                            elif type == "回复":
                                logger.debug(f"keyword={keyword}, content={content}")
                                if keyword in content:
                                    for trigger in ["key_trigger_type", "copywriting_trigger_type", "local_audio_trigger_type", "serial_trigger_type", \
                                                    "img_path_trigger_type"]:
                                        resp_json = keyword_handle_trigger(trigger, keyword, key_mapping_config, data, flag)
                                        if resp_json["trigger_once_enable"]:
                                            return resp_json["flag"]
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f'【触发按键映射】错误：{e}')

        return flag


    # 自定义命令处理
    def custom_cmd_handle(self, type, data):
        """自定义命令处理

        Args:
            type (str): 数据来源类型（弹幕/回复）
            data (dict): 平台侧传入的data数据，直接拿来做解析

        Returns:
            bool: 是否正常触发了自定义命令事件，是True 否False
        """
        flag = False


        try:
            if My_handle.config.get("custom_cmd", "enable"):
                # 判断传入的数据是否包含gift_name键值，有的话则是礼物数据
                if "gift_name" in data:
                    pass
                else:
                    username = data["username"]
                    content = data["content"]
                    custom_cmd_configs = My_handle.config.get("custom_cmd", "config")

                    for custom_cmd_config in custom_cmd_configs:
                        similarity = float(custom_cmd_config["similarity"])
                        for keyword in custom_cmd_config["keywords"]:
                            if type == "弹幕":
                                # 判断相似度
                                ratio = difflib.SequenceMatcher(None, content, keyword).ratio()
                                if ratio >= similarity:
                                    resp = My_handle.common.send_request(
                                        custom_cmd_config["api_url"], 
                                        custom_cmd_config["api_type"],
                                        resp_data_type=custom_cmd_config["resp_data_type"]
                                    )

                                    # 使用 eval() 执行字符串表达式并获取结果
                                    resp_content = eval(custom_cmd_config["data_analysis"])

                                    # 将字符串中的换行符替换为句号
                                    resp_content = resp_content.replace('\n', '。')

                                    logger.debug(f"resp_content={resp_content}")

                                    # 违禁词处理
                                    resp_content = self.prohibitions_handle(resp_content)
                                    if resp_content is None:
                                        return flag

                                    variables = {
                                        'keyword': keyword,
                                        'cur_time': My_handle.common.get_bj_time(5),
                                        'username': username,
                                        'data': resp_content
                                    }

                                    tmp = custom_cmd_config["resp_template"]

                                    # 使用字典进行字符串替换
                                    if any(var in tmp for var in variables):
                                        resp_content = tmp.format(**{var: value for var, value in variables.items() if var in tmp})
                                    
                                    # 音频合成时需要用到的重要数据
                                    message = {
                                        "type": "reread",
                                        "tts_type": My_handle.config.get("audio_synthesis_type"),
                                        "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                                        "config": My_handle.config.get("filter"),
                                        "username": username,
                                        "content": resp_content
                                    }

                                    logger.debug(message)
                                    
                                    logger.info(f'【触发 自定义命令】关键词：{keyword} 返回内容：{resp_content}')

                                    self.audio_synthesis_handle(message)

                                    self.webui_show_chat_log_callback("自定义命令", data, resp_content)

                                    flag = True
                                    
                            
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f'【触发自定义命令】错误：{e}')

        return flag


    # 黑名单处理
    def blacklist_handle(self, data):
        """黑名单处理

        Args:
            data (dict): 包含用户名,弹幕内容

        Returns:
            bool: True是黑名单用户，False不是黑名单用户
        """
        try:
            if My_handle.config.get("filter", "blacklist", "enable"):
                username_blacklist = My_handle.config.get("filter", "blacklist", "username")
                if len(username_blacklist) == 0:
                    return False
                
                if data["username"] in username_blacklist:
                    logger.info(f'弹幕黑名单 过滤 用户名：{data["username"]}')
                    return True
                
            return False
        except Exception as e:
            logger.error(traceback.format_exc())
            return False

    

    # 判断限定时间段内数据是否重复
    def is_data_repeat_in_limited_time(self, type: str=None, data: dict=None):
        """判断限定时间段内数据是否重复

        Args:
            type (str): 判断的数据类型（comment|gift|entrance)
            data (dict): 包含用户名,弹幕内容

        Returns:
            dict: 传递给音频合成的JSON数据
        """
        if My_handle.config.get("filter", "limited_time_deduplication", "enable"):
            logger.debug(f"限定时间段内数据重复 My_handle.live_data={My_handle.live_data}")
                        
            if type is not None and type != "" and data is not None:
                if type == "comment":
                    # 如果存在重复数据，返回True
                    for tmp in My_handle.live_data[type]:
                        if tmp['username'] == data['username'] and tmp['content'] == data['content']:
                            logger.debug(f"限定时间段内数据重复 type={type},data={data}")
                            return True
                elif type == "gift":
                    # 如果存在重复数据，返回True
                    for tmp in My_handle.live_data[type]:
                        if tmp['username'] == data['username']:
                            logger.debug(f"限定时间段内数据重复 type={type},data={data}")
                            return True
                elif type == "entrance":   
                    # 如果存在重复数据，返回True
                    for tmp in My_handle.live_data[type]:
                        if tmp['username'] == data['username']:
                            logger.debug(f"限定时间段内数据重复 type={type},data={data}")
                            return True
                
                # 不存在则插入，返回False
                My_handle.live_data[type].append(data)
        return False

    # 判断是否进行联网搜索，返回处理后的结果
    def search_online_handle(self, content: str):
        try:
            if My_handle.config.get("search_online", "enable"):
                # 是否启用了关键词命令
                if My_handle.config.get("search_online", "keyword_enable"):
                    # 没有命中关键词 直接返回
                    if My_handle.config.get("search_online", "before_keyword") and not any(content.startswith(prefix) for prefix in \
                        My_handle.config.get("search_online", "before_keyword")):
                        return content
                    else:
                        for prefix in My_handle.config.get("search_online", "before_keyword"):
                            if content.startswith(prefix):
                                content = content[len(prefix):]  # 删除匹配的开头
                                break
            
                from .search_engine import search_online

                if My_handle.config.get("search_online", "http_proxy") == "" and My_handle.config.get("search_online", "https_proxy") == "":
                    proxies = None
                else:
                    proxies = {
                        "http": My_handle.config.get("search_online", "http_proxy"),
                        "https": My_handle.config.get("search_online", "https_proxy")
                    }
                summaries = search_online(
                    content, 
                    engine=My_handle.config.get("search_online", "engine"), 
                    engine_id=int(My_handle.config.get("search_online", "engine_id")), 
                    count=int(My_handle.config.get("search_online", "count")), 
                    proxies=proxies
                )
                if summaries != []:
                    # 追加索引编号
                    indexed_summaries = [f"参考资料{i+1}. {summary}" for i, summary in enumerate(summaries)]
                    
                    # 替换掉内容中的多余换行符
                    cleaned_summaries = [summary.replace('\n', ' ') for summary in indexed_summaries]

                    variables = {
                        'summary': cleaned_summaries,
                        'cur_time': My_handle.common.get_bj_time(5),
                        'data': content
                    }

                    tmp = My_handle.config.get("search_online", "resp_template")

                    # 使用字典进行字符串替换
                    if any(var in tmp for var in variables):
                        content = tmp.format(**{var: value for var, value in variables.items() if var in tmp})

            return content
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f"联网搜索报错: {e}")
            return content

    """                                                              
                                                                           
                                                         ,`                
                             @@@@`               =@@\`   /@@/              
                ,/@@] =@@@`  @@@/                 =@@\/@@@@@@@@@[          
           .\@@/[@@@@` ,@@@ =@/.             ,[[[[.=@^ ,@@@@\`             
                *@@^,`  .]]]@@@@@@\`          ,@@@@@@[[[. =@@@@.           
           .]]]]/@@`\@@/ *@@^  =@@@/           ,@@@@@@@@/`@@@`             
            =@@*    .@@@@@@@@/`@@@^             ,@@\]]/@@@@@.              
            =@@      =@@*.@@\]/@@^               ,\@@\   ,]]@@@@]          
          ,/@@@@@@@^  \@/[@@^               .@@@@@@@@@[[[\@\.              
          ,@/. .@@@      .@@\]/@@@@@@`          ,@@@,@@@.,]@@@`            
               .@@/@@@@@/[@@/                  /@@\]@@@@@@@@@@@@@]         
               =@@^      .@@^                ]@@@@@^ @@@  @@@ ,@@@@@@\].   
           ,]]/@@@`      .@@^             ./@/` .@@^.@@@/@@@/              
             \@@@`       .@@^                       .@@@ .[[               
                         .@@`                        @@^                   
                                                                                                                                          

    """

    # 弹幕处理 直播间的弹幕消息会统一到此函数进行处理
    def comment_handle(self, data):
        """弹幕处理 直播间的弹幕消息会统一到此函数进行处理

        Args:
            data (dict): 包含用户名,弹幕内容

        Returns:
            dict: 传递给音频合成的JSON数据
        """

        try:
            username = data["username"]
            content = data["content"]

            # 输出当前用户发送的弹幕消息
            logger.debug(f"[{username}]: {content}")

            # 限定时间数据去重
            if self.is_data_repeat_in_limited_time("comment", data):
                return None

            # 黑名单过滤
            if self.blacklist_handle(data):
                return None
            
            # 弹幕数据经过基本初步筛选后，通过 洛曦直播弹幕助手，可以进行转发。
            # 洛曦 直播弹幕助手
            if My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable") and \
                "comment" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "type") and \
                "消息产生时" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                asyncio.run(send_msg_to_live_comment_assistant(My_handle.config.get("luoxi_project", "Live_Comment_Assistant"), content))


            # 返回给webui的聊天记录
            if My_handle.config.get("talk", "show_chat_log"):
                if "ori_username" not in data:
                    data["ori_username"] = data["username"]
                if "ori_content" not in data:
                    data["ori_content"] = data["content"]
                if "user_face" not in data:
                    data["user_face"] = 'https://robohash.org/ui'

                # 返回给webui的数据
                return_webui_json = {
                    "type": "llm",
                    "data": {
                        "type": "弹幕信息",
                        "username": data["ori_username"],
                        "user_face": data["user_face"],
                        "content_type": "question",
                        "content": data["ori_content"],
                        "timestamp": My_handle.common.get_bj_time(0)
                    }
                }
                webui_ip = "127.0.0.1" if My_handle.config.get("webui", "ip") == "0.0.0.0" else My_handle.config.get("webui", "ip")
                tmp_json = My_handle.common.send_request(f'http://{webui_ip}:{My_handle.config.get("webui", "port")}/callback', "POST", return_webui_json, timeout=10)
            

            # 记录数据库
            if My_handle.config.get("database", "comment_enable"):
                insert_data_sql = '''
                INSERT INTO danmu (username, content, ts) VALUES (?, ?, ?)
                '''
                self.db.execute(insert_data_sql, (username, content, datetime.now()))



            # 合并字符串末尾连续的*  主要针对获取不到用户名的情况
            username = My_handle.common.merge_consecutive_asterisks(username)

            # 0、积分机制运转
            if self.integral_handle("comment", data):
                return
            if self.integral_handle("crud", data):
                return

            """
            用户名也得过滤一下，防止炸弹人
            """
            # 用户名以及弹幕违禁判断
            username = self.prohibitions_handle(username)
            if username is None:
                return
            
            content = self.prohibitions_handle(content)
            if content is None:
                return
            
            # 弹幕格式检查和特殊字符替换和指定语言过滤
            content = self.comment_check_and_replace(content)
            if content is None:
                return
            
            # 判断字符串是否全为标点符号，是的话就过滤
            if My_handle.common.is_punctuation_string(content):
                logger.debug(f"用户:{username}]，发送纯符号的弹幕，已过滤")
                return
            
            # 判断按键映射触发类型
            if My_handle.config.get("key_mapping", "type") == "弹幕" or My_handle.config.get("key_mapping", "type") == "弹幕+回复":
                # 按键映射 触发后不执行后面的其他功能
                if self.key_mapping_handle("弹幕", data):
                    return
                
            # 判断自定义命令触发类型
            if My_handle.config.get("custom_cmd", "type") == "弹幕" or My_handle.config.get("custom_cmd", "type") == "弹幕+回复":
                # 自定义命令 触发后不执行后面的其他功能
                if self.custom_cmd_handle("弹幕", data):
                    return
            
            try:
                # 念弹幕
                if My_handle.config.get("read_comment", "enable"):
                    logger.debug(f"念弹幕 content:{content}")

                    # 音频合成时需要用到的重要数据
                    message = {
                        "type": "read_comment",
                        "tts_type": My_handle.config.get("audio_synthesis_type"),
                        "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                        "config": My_handle.config.get("filter"),
                        "username": username,
                        "content": content
                    }

                    # 判断是否需要念用户名
                    if My_handle.config.get("read_comment", "read_username_enable"):
                        # 将用户名中特殊字符替换为空
                        message['username'] = My_handle.common.replace_special_characters(message['username'], "！!@#￥$%^&*_-+/——=()（）【】}|{:;<>~`\\")
                        message['username'] = message['username'][:self.config.get("read_comment", "username_max_len")]

                        # 将用户名字符串中的数字转换成中文
                        if My_handle.config.get("filter", "username_convert_digits_to_chinese"):
                            message["username"] = My_handle.common.convert_digits_to_chinese(message["username"])
                            logger.debug(f"用户名字符串中的数字转换成中文：{message['username']}")

                        if len(self.config.get("read_comment", "read_username_copywriting")) > 0:
                            tmp_content = random.choice(self.config.get("read_comment", "read_username_copywriting"))
                            if "{username}" in tmp_content:
                                message['content'] = tmp_content.format(username=message['username']) + message['content']

                    # 是否启用了周期性触发功能，启用此功能后，数据会被缓存，之后周期到了才会触发
                    if My_handle.config.get("read_comment", "periodic_trigger", "enable"):
                        My_handle.task_data["read_comment"]["data"].append(message)
                    else:
                        self.audio_synthesis_handle(message)
            except Exception as e:
                logger.error(traceback.format_exc())

            # 1、本地问答库 处理
            if self.local_qa_handle(data):
                return

            # 2、点歌模式 触发后不执行后面的其他功能
            if self.choose_song_handle(data):
                return

            # 3、画图模式 触发后不执行后面的其他功能
            if self.sd_handle(data):
                return
            
            # 4、弹幕内容是否进行翻译
            if My_handle.config.get("translate", "enable") and (My_handle.config.get("translate", "trans_type") == "弹幕" or \
                My_handle.config.get("translate", "trans_type") == "弹幕+回复"):
                tmp = My_handle.my_translate.trans(content)
                if tmp:
                    content = tmp
                    # logger.info(f"翻译后：{content}")

            # 5、联网搜索
            content = self.search_online_handle(content)

            data_json = {
                "username": username,
                "content": content,
                "ori_username": data["username"],
                "ori_content": data["content"]
            }

            """
            根据聊天类型执行不同逻辑
            """ 
            chat_type = My_handle.config.get("chat_type")
            if chat_type in self.chat_type_list:
                data_json["content"] = My_handle.config.get("before_prompt")
                # 是否启用弹幕模板
                if self.config.get("comment_template", "enable"):
                    # 假设有多个未知变量，用户可以在此处定义动态变量
                    variables = {
                        'username': username,
                        'comment': content,
                        'cur_time': My_handle.common.get_bj_time(5),
                    }

                    comment_template_copywriting = self.config.get("comment_template", "copywriting")
                    # 使用字典进行字符串替换
                    if any(var in comment_template_copywriting for var in variables):
                        content = comment_template_copywriting.format(**{var: value for var, value in variables.items() if var in comment_template_copywriting})

                data_json["content"] += content + My_handle.config.get("after_prompt")

                logger.debug(f"data_json={data_json}")
                
                # 当前选用的LLM类型是否支持stream，并且启用stream
                if "stream" in self.config.get(chat_type) and self.config.get(chat_type, "stream"):
                    logger.warning("使用流式推理LLM")
                    resp_content = self.llm_stream_handle_and_audio_synthesis(chat_type, data_json)
                    return resp_content
                else:
                    resp_content = self.llm_handle(chat_type, data_json)
                    if resp_content is not None:
                        logger.info(f"[AI回复{username}]：{resp_content}")
                    else:
                        resp_content = ""
                        logger.warning(f"警告：{chat_type}无返回")
            elif chat_type == "game":
                if My_handle.config.get("game", "enable"):
                    self.game.parse_keys_and_simulate_keys_press(content.split(), 2)
                return
            elif chat_type == "none":
                return
            elif chat_type == "reread":
                resp_content = self.llm_handle(chat_type, data_json)
            else:
                resp_content = content

            # 空数据结束
            if resp_content == "" or resp_content is None:
                return

            """
            双重过滤，为您保驾护航
            """
            resp_content = resp_content.strip()

            resp_content = resp_content.replace('\n', '。')
            
            # LLM回复的内容进行违禁判断
            resp_content = self.prohibitions_handle(resp_content)
            if resp_content is None:
                return

            # logger.info("resp_content=" + resp_content)

            # 回复内容是否进行翻译
            if My_handle.config.get("translate", "enable") and (My_handle.config.get("translate", "trans_type") == "回复" or \
                My_handle.config.get("translate", "trans_type") == "弹幕+回复"):
                tmp = My_handle.my_translate.trans(resp_content)
                if tmp:
                    resp_content = tmp

            self.write_to_comment_log(resp_content, {"username": username, "content": content})

            # 判断按键映射触发类型
            if My_handle.config.get("key_mapping", "type") == "回复" or My_handle.config.get("key_mapping", "type") == "弹幕+回复":
                # 替换内容
                data["content"] = resp_content
                # 按键映射 触发后不执行后面的其他功能
                if self.key_mapping_handle("回复", data):
                    pass

            # 判断自定义命令触发类型
            if My_handle.config.get("custom_cmd", "type") == "回复" or My_handle.config.get("custom_cmd", "type") == "弹幕+回复":
                # 替换内容
                data["content"] = resp_content
                # 自定义命令 触发后不执行后面的其他功能
                if self.custom_cmd_handle("回复", data):
                    pass
                

            # 音频合成时需要用到的重要数据
            message = {
                "type": "comment",
                "tts_type": My_handle.config.get("audio_synthesis_type"),
                "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                "config": My_handle.config.get("filter"),
                "username": username,
                "content": resp_content
            }

            # 洛曦 直播弹幕助手
            if My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable") and \
                "comment_reply" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "type") and \
                "消息产生时" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                asyncio.run(send_msg_to_live_comment_assistant(My_handle.config.get("luoxi_project", "Live_Comment_Assistant"), resp_content))

            # 合成音频
            self.audio_synthesis_handle(message)

            return message
        except Exception as e:
            logger.error(traceback.format_exc())
            return None


    # 礼物处理
    def gift_handle(self, data):
        try:
            # 限定时间数据去重
            if self.is_data_repeat_in_limited_time("gift", data):
                return None
            
            # 记录数据库
            if My_handle.config.get("database", "gift_enable"):
                insert_data_sql = '''
                INSERT INTO gift (username, gift_name, gift_num, unit_price, total_price, ts) VALUES (?, ?, ?, ?, ?, ?)
                '''
                self.db.execute(insert_data_sql, (
                    data['username'], 
                    data['gift_name'], 
                    data['num'], 
                    data['unit_price'], 
                    data['total_price'],
                    datetime.now())
                )

            # 按键映射 触发后仍然执行后面的其他功能
            self.key_mapping_handle("弹幕", data)
            # 自定义命令触发
            self.custom_cmd_handle("弹幕", data)
            
            # 违禁处理
            data['username'] = self.prohibitions_handle(data['username'])
            if data['username'] is None:
                return None
            
            # 积分处理
            if self.integral_handle("gift", data):
                return None

            # 合并字符串末尾连续的*  主要针对获取不到用户名的情况
            data['username'] = My_handle.common.merge_consecutive_asterisks(data['username'])
            # 删除用户名中的特殊字符
            data['username'] = My_handle.common.replace_special_characters(data['username'], "！!@#￥$%^&*_-+/——=()（）【】}|{:;<>~`\\")  

            data['username'] = data['username'][:self.config.get("thanks", "username_max_len")]

            # 将用户名字符串中的数字转换成中文
            if My_handle.config.get("filter", "username_convert_digits_to_chinese"):
                data["username"] = My_handle.common.convert_digits_to_chinese(data["username"])

            # logger.debug(f"[{data['username']}]: {data}")
        
            if not My_handle.config.get("thanks")["gift_enable"]:
                return None

            # 如果礼物总价低于设置的礼物感谢最低值
            if data["total_price"] < My_handle.config.get("thanks")["lowest_price"]:
                return None

            if My_handle.config.get("thanks", "gift_random"):
                resp_content = random.choice(My_handle.config.get("thanks", "gift_copy"))
            else:
                # 类变量list中是否有数据，没有就拷贝下数据再顺序取出首个数据
                if len(My_handle.thanks_gift_copy) == 0:
                    if len(My_handle.config.get("thanks", "gift_copy")) == 0:
                        logger.warning("你把礼物的文案删了，还触发个der礼物感谢？不用别启用不就得了，删了搞啥")
                        return None
                resp_content = My_handle.thanks_gift_copy.pop(0)

            
            # 括号语法替换
            resp_content = My_handle.common.brackets_text_randomize(resp_content)
            
            # 动态变量替换
            data_json = {
                "username": data["username"],
                "gift_name": data["gift_name"],
                'gift_num': data["num"],
                'unit_price': data["unit_price"],
                'total_price': data["total_price"],
                'cur_time': My_handle.common.get_bj_time(5),
            } 
            resp_content = My_handle.common.dynamic_variable_replacement(resp_content, data_json)


            message = {
                "type": "gift",
                "tts_type": My_handle.config.get("audio_synthesis_type"),
                "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                "config": My_handle.config.get("filter"),
                "username": data["username"],
                "content": resp_content,
                "gift_info": data
            }

            # 洛曦 直播弹幕助手
            if My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable") and \
                "gift_reply" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "type") and \
                "消息产生时" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                asyncio.run(send_msg_to_live_comment_assistant(My_handle.config.get("luoxi_project", "Live_Comment_Assistant"), resp_content))
            

            # 是否启用了周期性触发功能，启用此功能后，数据会被缓存，之后周期到了才会触发
            if My_handle.config.get("thanks", "gift", "periodic_trigger", "enable"):
                My_handle.task_data["thanks"]["gift"]["data"].append(message)
            else:
                self.audio_synthesis_handle(message)

            return message
        except Exception as e:
            logger.error(traceback.format_exc())
            return None


    # 入场处理
    def entrance_handle(self, data):
        try:
            # 限定时间数据去重
            if self.is_data_repeat_in_limited_time("entrance", data):
                return None
            
            # 记录数据库
            if My_handle.config.get("database", "entrance_enable"):
                insert_data_sql = '''
                INSERT INTO entrance (username, ts) VALUES (?, ?)
                '''
                self.db.execute(insert_data_sql, (data['username'], datetime.now()))

            # 违禁处理
            data['username'] = self.prohibitions_handle(data['username'])
            if data['username'] is None:
                return None
            
            if self.integral_handle("entrance", data):
                return None

            # 合并字符串末尾连续的*  主要针对获取不到用户名的情况
            data['username'] = My_handle.common.merge_consecutive_asterisks(data['username'])
            # 删除用户名中的特殊字符
            data['username'] = My_handle.common.replace_special_characters(data['username'], "！!@#￥$%^&*_-+/——=()（）【】}|{:;<>~`\\")

            data['username'] = data['username'][:self.config.get("thanks", "username_max_len")]

            # 将用户名字符串中的数字转换成中文
            if My_handle.config.get("filter", "username_convert_digits_to_chinese"):
                data["username"] = My_handle.common.convert_digits_to_chinese(data["username"])

            # logger.debug(f"[{data['username']}]: {data['content']}")
        
            if not My_handle.config.get("thanks")["entrance_enable"]:
                return None

            if My_handle.config.get("thanks", "entrance_random"):
                resp_content = random.choice(My_handle.config.get("thanks", "entrance_copy")).format(username=data["username"])
            else:
                # 类变量list中是否有数据，没有就拷贝下数据再顺序取出首个数据
                if len(My_handle.thanks_entrance_copy) == 0:
                    if len(My_handle.config.get("thanks", "entrance_copy")) == 0:
                        logger.warning("你把入场的文案删了，还触发个der入场感谢？不用别启用不就得了，删了搞啥")
                        return None
                    My_handle.thanks_entrance_copy = copy.copy(My_handle.config.get("thanks", "entrance_copy"))
                resp_content = My_handle.thanks_entrance_copy.pop(0).format(username=data["username"])

            # 括号语法替换
            resp_content = My_handle.common.brackets_text_randomize(resp_content)

            message = {
                "type": "entrance",
                "tts_type": My_handle.config.get("audio_synthesis_type"),
                "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                "config": My_handle.config.get("filter"),
                "username": data['username'],
                "content": resp_content
            }

            # 洛曦 直播弹幕助手
            if My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable") and \
                "entrance_reply" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "type") and \
                "消息产生时" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                asyncio.run(send_msg_to_live_comment_assistant(My_handle.config.get("luoxi_project", "Live_Comment_Assistant"), resp_content))
            
            # 是否启用了周期性触发功能，启用此功能后，数据会被缓存，之后周期到了才会触发
            if My_handle.config.get("thanks", "entrance", "periodic_trigger", "enable"):
                My_handle.task_data["thanks"]["entrance"]["data"].append(message)
            else:
                self.audio_synthesis_handle(message)

            return message
        except Exception as e:
            logger.error(traceback.format_exc())
            return None


    # 关注处理
    def follow_handle(self, data):
        try:
            # 合并字符串末尾连续的*  主要针对获取不到用户名的情况
            data['username'] = My_handle.common.merge_consecutive_asterisks(data['username'])
            # 删除用户名中的特殊字符
            data['username'] = My_handle.common.replace_special_characters(data['username'], "！!@#￥$%^&*_-+/——=()（）【】}|{:;<>~`\\")

            data['username'] = data['username'][:self.config.get("thanks", "username_max_len")]

            # 违禁处理
            data['username'] = self.prohibitions_handle(data['username'])
            if data['username'] is None:
                return None

            # 将用户名字符串中的数字转换成中文
            if My_handle.config.get("filter", "username_convert_digits_to_chinese"):
                data["username"] = My_handle.common.convert_digits_to_chinese(data["username"])

            # logger.debug(f"[{data['username']}]: {data['content']}")
        
            if not My_handle.config.get("thanks")["follow_enable"]:
                return None

            if My_handle.config.get("thanks", "follow_random"):
                resp_content = random.choice(My_handle.config.get("thanks", "follow_copy")).format(username=data["username"])
            else:
                # 类变量list中是否有数据，没有就拷贝下数据再顺序取出首个数据
                if len(My_handle.thanks_follow_copy) == 0:
                    if len(My_handle.config.get("thanks", "follow_copy")) == 0:
                        logger.warning("你把关注的文案删了，还触发个der关注感谢？不用别启用不就得了，删了搞啥")
                        return None
                    My_handle.thanks_follow_copy = copy.copy(My_handle.config.get("thanks", "follow_copy"))
                resp_content = My_handle.thanks_follow_copy.pop(0).format(username=data["username"])
            
            # 括号语法替换
            resp_content = My_handle.common.brackets_text_randomize(resp_content)

            message = {
                "type": "follow",
                "tts_type": My_handle.config.get("audio_synthesis_type"),
                "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                "config": My_handle.config.get("filter"),
                "username": data['username'],
                "content": resp_content
            }

            # 洛曦 直播弹幕助手
            if My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable") and \
                "follow_reply" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "type") and \
                "消息产生时" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                asyncio.run(send_msg_to_live_comment_assistant(My_handle.config.get("luoxi_project", "Live_Comment_Assistant"), resp_content))
            

            # 是否启用了周期性触发功能，启用此功能后，数据会被缓存，之后周期到了才会触发
            if My_handle.config.get("thanks", "follow", "periodic_trigger", "enable"):
                My_handle.task_data["thanks"]["follow"]["data"].append(message)
            else:
                self.audio_synthesis_handle(message)

            return message
        except Exception as e:
            logger.error(traceback.format_exc())
            return None

    # 定时处理
    def schedule_handle(self, data):
        try:
            content = data["content"]

            message = {
                "type": "schedule",
                "tts_type": My_handle.config.get("audio_synthesis_type"),
                "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                "config": My_handle.config.get("filter"),
                "username": data['username'],
                "content": content
            }

            # 洛曦 直播弹幕助手
            if My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable") and \
                "schedule" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "type") and \
                "消息产生时" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                asyncio.run(send_msg_to_live_comment_assistant(My_handle.config.get("luoxi_project", "Live_Comment_Assistant"), content))
            
            
            self.audio_synthesis_handle(message)

            return message
        except Exception as e:
            logger.error(traceback.format_exc())
            return None

    """
.....................................................................................................................
..............:*.....................................-*=........:+-......................-*+.........................
..............:*%+.:#%%%%%%%%%%%%*..:+++++++-........=@+........+%=-++++++***##%%=......=%@*+++++++++++:.............
.............--.-+:............-@*..=%#+++*@*........=@+.......+%+.:=+++=+%#-:........-#%%%+-------=#%#:.............
.............%#.......+#.......-@*..=%+...-@*+@@@@@@@@@@@@+...=%*:.......-#*:.......:*%*:.+%*-...-*%*-...............
.............%#..::::-*#-:::::.-@*..=%+...-@*........=@+.....+%@+........-#*:.......+*:.....*%@%%%*..................
.............%#.-****#@%*****+.-%*..=%*:::=@*.-*=....=@+....+%%%+........-##:..........:-*%%%%+-*%%%%#+-::...........
.............%#.....:@@#:......-%*..=%*---+@*.:*%=...=@+...+@==#+.+%@@@@@@@@@@@@@@**%@@#=...#@:.......=*%%...........
.............%#....+%+*%#%*:...-%*..=%+...-@*..-#%=..=@+......=#+........-##:........+******%%#********:.............
.............%#..-%#:.*#:.=%#=.-%*..=%+...-@*...:-:..=@+......=#+........-#*:........::::::*%=-::::::#%:.............
.............%#-#%-...*#....=+:-%*..=%*---+@*........=@+......=#+........-#*:.............=%*:.......#@..............
.............%#.:.....+#.......-%*..=%#+++*@*........=@+......=#+........-#*:...........-#%+.........#@..............
.............%#.......::..:====*%+..-*=...:*=...-*++*%#-......=#+..+##############-.-=*%#+:...=++==+%%-..............
.............*+...........:****+:...............:----:........-*=...................=*=........--==-:................
.....................................................................................................................
    """
    # 闲时任务处理
    def idle_time_task_handle(self, data):
        try:
            type = data["type"]
            content = data["content"]
            username = data["username"]

            # 将用户名字符串中的数字转换成中文
            if My_handle.config.get("filter", "username_convert_digits_to_chinese"):
                username = My_handle.common.convert_digits_to_chinese(username)

            if type == "reread":
                # 输出当前用户发送的弹幕消息
                logger.info(f"[{username}]: {content}")

                # 弹幕格式检查和特殊字符替换和指定语言过滤
                content = self.comment_check_and_replace(content)
                if content is None:
                    return None
                
                # 判断按键映射触发类型
                if My_handle.config.get("key_mapping", "type") == "弹幕" or My_handle.config.get("key_mapping", "type") == "弹幕+回复":
                    # 按键映射 触发后不执行后面的其他功能
                    if self.key_mapping_handle("弹幕", data):
                        return None
                    
                # 判断自定义命令触发类型
                if My_handle.config.get("custom_cmd", "type") == "弹幕" or My_handle.config.get("custom_cmd", "type") == "弹幕+回复":
                    # 自定义命令 触发后不执行后面的其他功能
                    if self.custom_cmd_handle("弹幕", data):
                        return None

                # 音频合成时需要用到的重要数据
                message = {
                    "type": "idle_time_task",
                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                    "config": My_handle.config.get("filter"),
                    "username": username,
                    "content": content,
                    "content_type": type
                }

                # 洛曦 直播弹幕助手
                if My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable") and \
                    "idle_time_task" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "type") and \
                    "消息产生时" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                    asyncio.run(send_msg_to_live_comment_assistant(My_handle.config.get("luoxi_project", "Live_Comment_Assistant"), content))

                
                self.audio_synthesis_handle(message)

                return message
            elif type == "comment":
                # 记录数据库
                if My_handle.config.get("database", "comment_enable"):
                    insert_data_sql = '''
                    INSERT INTO danmu (username, content, ts) VALUES (?, ?, ?)
                    '''
                    self.db.execute(insert_data_sql, (username, content, datetime.now()))

                # 输出当前用户发送的弹幕消息
                logger.info(f"[{username}]: {content}")

                # 弹幕格式检查和特殊字符替换和指定语言过滤
                content = self.comment_check_and_replace(content)
                if content is None:
                    return None
                
                # 判断按键映射触发类型
                if My_handle.config.get("key_mapping", "type") == "弹幕" or My_handle.config.get("key_mapping", "type") == "弹幕+回复":
                    # 按键映射 触发后不执行后面的其他功能
                    if self.key_mapping_handle("弹幕", data):
                        return None
                    
                # 判断自定义命令触发类型
                if My_handle.config.get("custom_cmd", "type") == "弹幕" or My_handle.config.get("custom_cmd", "type") == "弹幕+回复":
                    # 自定义命令 触发后不执行后面的其他功能
                    if self.custom_cmd_handle("弹幕", data):
                        return None
                
                # 1、本地问答库 处理
                if self.local_qa_handle(data):
                    return None

                # 2、点歌模式 触发后不执行后面的其他功能
                if self.choose_song_handle(data):
                    return None

                # 3、画图模式 触发后不执行后面的其他功能
                if self.sd_handle(data):
                    return None

                """
                根据聊天类型执行不同逻辑
                """ 
                chat_type = My_handle.config.get("chat_type")
                if chat_type == "game":
                    if My_handle.config.get("game", "enable"):
                        self.game.parse_keys_and_simulate_keys_press(content.split(), 2)
                    return None
                elif chat_type == "none":
                    return None
                else:
                    # 通用的data_json构造
                    data_json = {
                        "username": username,
                        "content": My_handle.config.get("before_prompt") + content + My_handle.config.get("after_prompt") if chat_type != "reread" else content,
                        "ori_username": data["username"],
                        "ori_content": data["content"]
                    }

                    logger.debug("data_json={data_json}")
                    
                    # 调用LLM统一接口，获取返回内容
                    resp_content = self.llm_handle(chat_type, data_json) if chat_type != "game" else ""

                    if resp_content:
                        logger.info(f"[AI回复{username}]：{resp_content}")
                    else:
                        logger.warning(f"警告：{chat_type}无返回")
                        resp_content = ""

                """
                双重过滤，为您保驾护航
                """
                resp_content = resp_content.replace('\n', '。')
                
                # LLM回复的内容进行违禁判断
                resp_content = self.prohibitions_handle(resp_content)
                if resp_content is None:
                    return None

                # logger.info("resp_content=" + resp_content)

                self.write_to_comment_log(resp_content, {"username": username, "content": content})

                # 判断按键映射触发类型
                if My_handle.config.get("key_mapping", "type") == "回复" or My_handle.config.get("key_mapping", "type") == "弹幕+回复":
                    # 替换内容
                    data["content"] = resp_content
                    # 按键映射 触发后不执行后面的其他功能
                    if self.key_mapping_handle("回复", data):
                        pass

                # 判断自定义命令射触发类型
                if My_handle.config.get("custom_cmd", "type") == "回复" or My_handle.config.get("custom_cmd", "type") == "弹幕+回复":
                    # 替换内容
                    data["content"] = resp_content
                    # 自定义命令 触发后不执行后面的其他功能
                    if self.custom_cmd_handle("回复", data):
                        pass
                    

                # 音频合成时需要用到的重要数据
                message = {
                    "type": "idle_time_task",
                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                    "config": My_handle.config.get("filter"),
                    "username": username,
                    "content": resp_content,
                    "content_type": type
                }

                # 洛曦 直播弹幕助手
                if My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "enable") and \
                    "idle_time_task" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "type") and \
                    "消息产生时" in My_handle.config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                    asyncio.run(send_msg_to_live_comment_assistant(My_handle.config.get("luoxi_project", "Live_Comment_Assistant"), resp_content))

                
                self.audio_synthesis_handle(message)

                return message
            elif type == "local_audio":
                logger.info(f'[{username}]: {data["file_path"]}')

                message = {
                    "type": "idle_time_task",
                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                    "config": My_handle.config.get("filter"),
                    "username": username,
                    "content": content,
                    "content_type": type,
                    "file_path": os.path.abspath(data["file_path"])
                }

                self.audio_synthesis_handle(message)

                return message
        except Exception as e:
            logger.error(traceback.format_exc())
            return None


    # 图像识别 定时任务
    def image_recognition_schedule_handle(self, data):
        try:
            username = data["username"]
            content = My_handle.config.get("image_recognition", "prompt")
            # 区分图片源类型
            type = data["type"]

            # 将用户名字符串中的数字转换成中文
            if My_handle.config.get("filter", "username_convert_digits_to_chinese"):
                username = My_handle.common.convert_digits_to_chinese(username)

            if type == "窗口截图":
                # 根据窗口名截图
                screenshot_path = My_handle.common.capture_window_by_title(My_handle.config.get("image_recognition", "img_save_path"), My_handle.config.get("image_recognition", "screenshot_window_title"))
            elif type == "摄像头截图":
                # 根据摄像头索引截图
                screenshot_path = My_handle.common.capture_image(My_handle.config.get("image_recognition", "img_save_path"), int(My_handle.config.get("image_recognition", "cam_index")))

            # 通用的data_json构造
            data_json = {
                "username": username,
                "content": content,
                "img_data": screenshot_path,
                "ori_username": data["username"],
                "ori_content": content
            }
            
            # 调用LLM统一接口，获取返回内容
            resp_content = self.llm_handle(My_handle.config.get("image_recognition", "model"), data_json, type="vision")

            if resp_content:
                logger.info(f"[AI回复{username}]：{resp_content}")
            else:
                logger.warning(f'警告：{My_handle.config.get("image_recognition", "model")}无返回')
                resp_content = ""

            """
            双重过滤，为您保驾护航
            """
            resp_content = resp_content.replace('\n', '。')
            
            # LLM回复的内容进行违禁判断
            resp_content = self.prohibitions_handle(resp_content)
            if resp_content is None:
                return

            # logger.info("resp_content=" + resp_content)

            self.write_to_comment_log(resp_content, {"username": username, "content": content})

            # 判断按键映射触发类型
            if My_handle.config.get("key_mapping", "type") == "回复" or My_handle.config.get("key_mapping", "type") == "弹幕+回复":
                # 替换内容
                data["content"] = resp_content
                # 按键映射 触发后不执行后面的其他功能
                if self.key_mapping_handle("回复", data):
                    pass

            # 判断自定义命令触发类型
            if My_handle.config.get("custom_cmd", "type") == "回复" or My_handle.config.get("custom_cmd", "type") == "弹幕+回复":
                # 替换内容
                data["content"] = resp_content
                # 自定义命令 触发后不执行后面的其他功能
                if self.custom_cmd_handle("回复", data):
                    pass
                

            # 音频合成时需要用到的重要数据
            message = {
                "type": "image_recognition_schedule",
                "tts_type": My_handle.config.get("audio_synthesis_type"),
                "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                "config": My_handle.config.get("filter"),
                "username": username,
                "content": resp_content
            }

            
            self.audio_synthesis_handle(message)
        except Exception as e:
            logger.error(traceback.format_exc())


    # 聊天处理（语音输入）
    def talk_handle(self, data):
        """聊天处理（语音输入）

        Args:
            data (dict): 包含用户名,弹幕内容

        Returns:
            dict: 传递给音频合成的JSON数据
        """

        try:
            username = data["username"]
            content = data["content"]

            # 输出当前用户发送的弹幕消息
            logger.debug(f"[{username}]: {content}")

            if My_handle.config.get("talk", "show_chat_log"):
                if "ori_username" not in data:
                    data["ori_username"] = data["username"]
                if "ori_content" not in data:
                    data["ori_content"] = data["content"]
                if "user_face" not in data:
                    data["user_face"] = 'https://robohash.org/ui'

                # 返回给webui的数据
                return_webui_json = {
                    "type": "llm",
                    "data": {
                        "type": "弹幕信息",
                        "username": data["ori_username"],
                        "user_face": data["user_face"],
                        "content_type": "question",
                        "content": data["ori_content"],
                        "timestamp": My_handle.common.get_bj_time(0)
                    }
                }
                webui_ip = "127.0.0.1" if My_handle.config.get("webui", "ip") == "0.0.0.0" else My_handle.config.get("webui", "ip")
                tmp_json = My_handle.common.send_request(f'http://{webui_ip}:{My_handle.config.get("webui", "port")}/callback', "POST", return_webui_json, timeout=10)
            

            # 记录数据库
            if My_handle.config.get("database", "comment_enable"):
                insert_data_sql = '''
                INSERT INTO danmu (username, content, ts) VALUES (?, ?, ?)
                '''
                self.db.execute(insert_data_sql, (username, content, datetime.now()))

            # 0、积分机制运转
            if self.integral_handle("comment", data):
                return
            if self.integral_handle("crud", data):
                return

            """
            用户名也得过滤一下，防止炸弹人
            """
            # 用户名以及弹幕违禁判断
            username = self.prohibitions_handle(username)
            if username is None:
                return
            
            content = self.prohibitions_handle(content)
            if content is None:
                return
            
            # 弹幕格式检查和特殊字符替换和指定语言过滤
            content = self.comment_check_and_replace(content)
            if content is None:
                return
            
            # 判断字符串是否全为标点符号，是的话就过滤
            if My_handle.common.is_punctuation_string(content):
                logger.debug(f"用户:{username}]，发送纯符号的弹幕，已过滤")
                return
            
            # 判断按键映射触发类型
            if My_handle.config.get("key_mapping", "type") == "弹幕" or My_handle.config.get("key_mapping", "type") == "弹幕+回复":
                # 按键映射 触发后不执行后面的其他功能
                if self.key_mapping_handle("弹幕", data):
                    return
                
            # 判断自定义命令触发类型
            if My_handle.config.get("custom_cmd", "type") == "弹幕" or My_handle.config.get("custom_cmd", "type") == "弹幕+回复":
                # 自定义命令 触发后不执行后面的其他功能
                if self.custom_cmd_handle("弹幕", data):
                    return
            
            try:
                # 念弹幕
                if My_handle.config.get("read_comment", "enable") and False:
                    logger.debug(f"念弹幕 content:{content}")

                    # 音频合成时需要用到的重要数据
                    message = {
                        "type": "read_comment",
                        "tts_type": My_handle.config.get("audio_synthesis_type"),
                        "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                        "config": My_handle.config.get("filter"),
                        "username": username,
                        "content": content
                    }

                    # 判断是否需要念用户名
                    if My_handle.config.get("read_comment", "read_username_enable"):
                        # 将用户名中特殊字符替换为空
                        message['username'] = My_handle.common.replace_special_characters(message['username'], "！!@#￥$%^&*_-+/——=()（）【】}|{:;<>~`\\")
                        message['username'] = message['username'][:self.config.get("read_comment", "username_max_len")]

                        if len(self.config.get("read_comment", "read_username_copywriting")) > 0:
                            tmp_content = random.choice(self.config.get("read_comment", "read_username_copywriting"))
                            if "{username}" in tmp_content:
                                message['content'] = tmp_content.format(username=message['username']) + message['content']

                    
                    self.audio_synthesis_handle(message)
            except Exception as e:
                logger.error(traceback.format_exc())

            # 1、本地问答库 处理
            if self.local_qa_handle(data):
                return

            # 2、点歌模式 触发后不执行后面的其他功能
            if self.choose_song_handle(data):
                return

            # 3、画图模式 触发后不执行后面的其他功能
            if self.sd_handle(data):
                return
            
            # 4、弹幕内容是否进行翻译
            if My_handle.config.get("translate", "enable") and (My_handle.config.get("translate", "trans_type") == "弹幕" or \
                My_handle.config.get("translate", "trans_type") == "弹幕+回复"):
                tmp = My_handle.my_translate.trans(content)
                if tmp:
                    content = tmp
                    # logger.info(f"翻译后：{content}")

            # 5、联网搜索
            content = self.search_online_handle(content)

            data_json = {
                "username": username,
                "content": content,
                "ori_username": data["username"],
                "ori_content": data["content"]
            }

            """
            根据聊天类型执行不同逻辑
            """ 
            chat_type = My_handle.config.get("chat_type")
            if chat_type in self.chat_type_list:
                

                data_json["content"] = My_handle.config.get("before_prompt")
                # 是否启用弹幕模板
                if self.config.get("comment_template", "enable"):
                    # 假设有多个未知变量，用户可以在此处定义动态变量
                    variables = {
                        'username': username,
                        'comment': content,
                        'cur_time': My_handle.common.get_bj_time(5),
                    }

                    comment_template_copywriting = self.config.get("comment_template", "copywriting")
                    # 使用字典进行字符串替换
                    if any(var in comment_template_copywriting for var in variables):
                        content = comment_template_copywriting.format(**{var: value for var, value in variables.items() if var in comment_template_copywriting})

                data_json["content"] += content + My_handle.config.get("after_prompt")

                logger.debug(f"data_json={data_json}")
                
                # 当前选用的LLM类型是否支持stream，并且启用stream
                if "stream" in self.config.get(chat_type) and self.config.get(chat_type, "stream"):
                    logger.warning("使用流式推理LLM")
                    resp_content = self.llm_stream_handle_and_audio_synthesis(chat_type, data_json)
                    return resp_content
                else:
                    resp_content = self.llm_handle(chat_type, data_json)
                    if resp_content is not None:
                        logger.info(f"[AI回复{username}]：{resp_content}")
                    else:
                        resp_content = ""
                        logger.warning(f"警告：{chat_type}无返回")
            elif chat_type == "game":
                if My_handle.config.get("game", "enable"):
                    self.game.parse_keys_and_simulate_keys_press(content.split(), 2)
                return
            elif chat_type == "none":
                return
            elif chat_type == "reread":
                resp_content = self.llm_handle(chat_type, data_json)
            else:
                resp_content = content

            # 空数据结束
            if resp_content == "" or resp_content is None:
                return

            """
            双重过滤，为您保驾护航
            """
            resp_content = resp_content.strip()

            resp_content = resp_content.replace('\n', '。')
            
            # LLM回复的内容进行违禁判断
            resp_content = self.prohibitions_handle(resp_content)
            if resp_content is None:
                return

            # logger.info("resp_content=" + resp_content)

            # 回复内容是否进行翻译
            if My_handle.config.get("translate", "enable") and (My_handle.config.get("translate", "trans_type") == "回复" or \
                My_handle.config.get("translate", "trans_type") == "弹幕+回复"):
                tmp = My_handle.my_translate.trans(resp_content)
                if tmp:
                    resp_content = tmp

            self.write_to_comment_log(resp_content, {"username": username, "content": content})

            # 判断按键映射触发类型
            if My_handle.config.get("key_mapping", "type") == "回复" or My_handle.config.get("key_mapping", "type") == "弹幕+回复":
                # 替换内容
                data["content"] = resp_content
                # 按键映射 触发后不执行后面的其他功能
                if self.key_mapping_handle("回复", data):
                    pass

            # 判断自定义命令触发类型
            if My_handle.config.get("custom_cmd", "type") == "回复" or My_handle.config.get("custom_cmd", "type") == "弹幕+回复":
                # 替换内容
                data["content"] = resp_content
                # 自定义命令 触发后不执行后面的其他功能
                if self.custom_cmd_handle("回复", data):
                    pass
                

            # 音频合成时需要用到的重要数据
            message = {
                "type": "talk",
                "tts_type": My_handle.config.get("audio_synthesis_type"),
                "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                "config": My_handle.config.get("filter"),
                "username": username,
                "content": resp_content
            }

            self.audio_synthesis_handle(message)

            return message
        except Exception as e:
            logger.error(traceback.format_exc())
            return None


    """
    数据丢弃部分
    增加新的处理事件时，需要进行这块部分的内容追加
    """
    def process_data(self, data, timer_flag):
        with self.data_lock:
            if timer_flag not in self.timers or not self.timers[timer_flag].is_alive():
                self.timers[timer_flag] = threading.Timer(self.get_interval(timer_flag), self.process_last_data, args=(timer_flag,))
                self.timers[timer_flag].start()

            # self.timers[timer_flag].last_data = data
            if hasattr(self.timers[timer_flag], 'last_data'):
                self.timers[timer_flag].last_data.append(data)
                # 这里需要注意配置命名!!!
                # 保留数据数量
                if len(self.timers[timer_flag].last_data) > int(My_handle.config.get("filter", timer_flag + "_forget_reserve_num")):
                    self.timers[timer_flag].last_data.pop(0)
            else:
                self.timers[timer_flag].last_data = [data]

    def process_last_data(self, timer_flag):
        with self.data_lock:
            timer = self.timers.get(timer_flag)
            if timer and timer.last_data is not None and timer.last_data != []:
                logger.debug(f"预处理定时器触发 type={timer_flag}，data={timer.last_data}")

                My_handle.is_handleing = 1

                if timer_flag == "comment":
                    for data in timer.last_data:
                        self.comment_handle(data)
                elif timer_flag == "gift":
                    for data in timer.last_data:
                        self.gift_handle(data)
                    #self.gift_handle(timer.last_data)
                elif timer_flag == "entrance":
                    for data in timer.last_data:
                        self.entrance_handle(data)
                    #self.entrance_handle(timer.last_data)
                elif timer_flag == "follow":
                    for data in timer.last_data:
                        self.follow_handle(data)
                elif timer_flag == "talk":
                    # 聊天暂时共用弹幕处理逻辑
                    for data in timer.last_data:
                        self.talk_handle(data)
                    #self.comment_handle(timer.last_data)
                elif timer_flag == "schedule":
                    # 定时任务处理
                    for data in timer.last_data:
                        self.schedule_handle(data)
                    #self.schedule_handle(timer.last_data)
                elif timer_flag == "idle_time_task":
                    # 定时任务处理
                    for data in timer.last_data:
                        self.idle_time_task_handle(data)
                    #self.idle_time_task_handle(timer.last_data)
                elif timer_flag == "image_recognition_schedule":
                    # 定时任务处理
                    for data in timer.last_data:
                        self.image_recognition_schedule_handle(data)

                My_handle.is_handleing = 0

                # 清空数据
                timer.last_data = []

    def get_interval(self, timer_flag):
        # 根据标志定义不同计时器的间隔
        intervals = {
            "comment": My_handle.config.get("filter", "comment_forget_duration"),
            "gift": My_handle.config.get("filter", "gift_forget_duration"),
            "entrance": My_handle.config.get("filter", "entrance_forget_duration"),
            "follow": My_handle.config.get("filter", "follow_forget_duration"),
            "talk": My_handle.config.get("filter", "talk_forget_duration"),
            "schedule": My_handle.config.get("filter", "schedule_forget_duration"),
            "idle_time_task": My_handle.config.get("filter", "idle_time_task_forget_duration")
            # 根据需要添加更多计时器及其间隔，记得添加config.json中的配置项
        }

        # 默认间隔为0.1秒
        return intervals.get(timer_flag, 0.1)


    """
    异常报警
    """ 
    def abnormal_alarm_handle(self, type):
        """异常报警

        Args:
            type (str): 报警类型

        Returns:
            bool: True/False
        """

        try:
            if not My_handle.config.get("abnormal_alarm", type, "enable"):
                # 关掉时连错都不记，避免攒下的计数在打开后被第一个偶发错误直接顶过重启阈值
                return True

            My_handle.abnormal_alarm_data[type]["error_count"] += 1
            
            if My_handle.config.get("abnormal_alarm", type, "type") == "local_audio":
                # 是否错误数大于 自动重启错误数
                if My_handle.abnormal_alarm_data[type]["error_count"] >= My_handle.config.get("abnormal_alarm", type, "auto_restart_error_num"):
                    data = {
                        "type": "restart",
                        "api_type": "api",
                        "data": {
                            "config_path": "config.json"
                        }
                    }

                    webui_ip = "127.0.0.1" if My_handle.config.get("webui", "ip") == "0.0.0.0" else My_handle.config.get("webui", "ip")
                    My_handle.common.send_request(f'http://{webui_ip}:{My_handle.config.get("webui", "port")}/sys_cmd', "POST", data)

                # 是否错误数小于 开始报警错误数，是则不触发报警
                if My_handle.abnormal_alarm_data[type]["error_count"] < My_handle.config.get("abnormal_alarm", type, "start_alarm_error_num"):
                    return

                path_list = My_handle.common.get_all_file_paths(My_handle.config.get("abnormal_alarm", type, "local_audio_path"))

                # 随机选择列表中的一个元素
                audio_path = random.choice(path_list)

                message = {
                    "type": "abnormal_alarm",
                    "tts_type": My_handle.config.get("audio_synthesis_type"),
                    "data": My_handle.config.get(My_handle.config.get("audio_synthesis_type")),
                    "config": My_handle.config.get("filter"),
                    "username": "系统",
                    "content": os.path.join(My_handle.config.get("abnormal_alarm", type, "local_audio_path"), My_handle.common.extract_filename(audio_path, True))
                }

                logger.warning(f"【异常报警-{type}】 {My_handle.common.extract_filename(audio_path, False)}")

                self.audio_synthesis_handle(message)

        except Exception as e:
            logger.error(traceback.format_exc())

            return False

        return True

