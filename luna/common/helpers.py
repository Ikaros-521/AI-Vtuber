# 导入所需的库
import re
import random
import json
import time
import os
import glob
from datetime import datetime
from datetime import timedelta
from datetime import timezone
import traceback

from urllib.parse import urlparse

import langid

from profanity import profanity
import ahocorasick

import difflib

import shutil

from pypinyin import pinyin, Style

import pyaudio

from luna.common import http_client, screen
from luna.infra.my_log import logger


# 项目认作「可播放音频」的扩展名，全仓唯一来源。
# 之前 Common.is_audio_file 与 Audio.get_dir_audios_filename 各有一份列表且大小写处理不同，
# 导致纯 flac/m4a 曲库走随机点歌时一首都找不到。
SUPPORTED_AUDIO_EXTENSIONS = (".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a")


class Common:
    def __init__(self):
        self.count = 1

    """
    数据校验
    """

    # 检测是否为纯数字
    def is_pure_number(self, text):
        """检测是否为纯数字

        Args:
            text (str): 待检测的文本

        Returns:
            bool: 是否为纯数字
        """
        return text.isdigit()

    # 是否是url
    def is_url_check(self, url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    # 是否是IP地址
    def is_valid_ip(self, ip):
        import ipaddress

        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    # 是否是端口
    def is_valid_port(self, port):
        try:
            port_num = int(port)
            return 0 < port_num <= 65535
        except ValueError:
            return False

    # 判断传入的字符串是否是文件夹路径或文件路径，且此文件夹路径或文件路径是否存在，返回bool
    def is_dir_or_file(self, path: str, type: str = "all"):
        """判断传入的字符串是否是文件夹路径或文件路径，且此文件夹路径或文件路径是否存在，返回bool

        Args:
            path (str): 文件夹路径或文件路径
            type (str, optional): 检测类型. Defaults to "all".

        Returns:
            bool: 结果
        """
        if type == "dir":
            if os.path.isdir(path):
                return True
            return False
        elif type == "file":
            if os.path.isfile(path):
                return True
            return False
        else:
            if os.path.isdir(path) or os.path.isfile(path):
                return True
            return False

    # 识别操作系统
    def detect_os(self):
        """
        识别操作系统
        """
        import platform

        system = platform.system()
        if system == "Linux":
            return "Linux"
        elif system == "Windows":
            return "Windows"
        elif system == "Darwin":
            return "MacOS"

        # 如果platform模块无法识别，则尝试使用os模块
        # system = os.name
        # if system == 'posix':
        #     return '可能是Linux或MacOS'
        # elif system == 'nt':
        #     return 'Windows'

        return "未知系统"

    """
    数字操作
    """

    # 获取北京时间
    def get_bj_time(self, type=0):
        """获取北京时间

        Args:
            type (int, str): 返回时间类型. 默认为 0.
                0 返回数据：年-月-日 时:分:秒
                1 返回数据：年-月-日
                2 返回数据：当前时间的秒
                3 返回数据：自1970年1月1日以来的秒数
                4 返回数据：根据调用次数计数到100循环
                5 返回数据：当前 时点分
                6 返回数据：当前时间的 时, 分
                7 返回数据：年-月-日 时-分-秒 毫秒

        Returns:
            str: 返回指定格式的时间字符串
            int, int
        """
        if type == 0:
            utc_now = datetime.utcnow().replace(tzinfo=timezone.utc)  # 获取当前 UTC 时间
            SHA_TZ = timezone(
                timedelta(hours=8),
                name="Asia/Shanghai",
            )
            beijing_now = utc_now.astimezone(SHA_TZ)  # 将 UTC 时间转换为北京时间
            fmt = "%Y-%m-%d %H:%M:%S"
            now_fmt = beijing_now.strftime(fmt)
            return now_fmt
        elif type == 1:
            now = datetime.now()  # 获取当前时间
            year = now.year  # 获取当前年份
            month = now.month  # 获取当前月份
            day = now.day  # 获取当前日期

            return str(year) + "-" + str(month) + "-" + str(day)
        elif type == 2:
            now = time.localtime()  # 获取当前时间

            # hour = now.tm_hour   # 获取当前小时
            # minute = now.tm_min  # 获取当前分钟
            second = now.tm_sec  # 获取当前秒数

            return str(second)
        elif type == 3:
            current_time = time.time()  # 返回自1970年1月1日以来的秒数

            return str(current_time)
        elif type == 4:
            self.count = (self.count % 100) + 1

            return str(self.count)
        elif type == 5:
            now = time.localtime()  # 获取当前时间

            hour = now.tm_hour  # 获取当前小时
            minute = now.tm_min  # 获取当前分钟

            return str(hour) + "点" + str(minute) + "分"
        elif type == 6:
            now = time.localtime()  # 获取当前时间

            hour = now.tm_hour  # 获取当前小时
            minute = now.tm_min  # 获取当前分钟

            return hour, minute
        elif type == 7:
            utc_now = datetime.utcnow().replace(tzinfo=timezone.utc)  # 获取当前 UTC 时间
            SHA_TZ = timezone(
                timedelta(hours=8),
                name="Asia/Shanghai",
            )
            beijing_now = utc_now.astimezone(SHA_TZ)  # 将 UTC 时间转换为北京时间
            fmt = "%Y-%m-%d %H-%M-%S %f"
            now_fmt = beijing_now.strftime(fmt)
            return now_fmt

    def time_difference_in_seconds(self, specific_time_str: str):
        """计算传入时间和当前时间的时间差

        Args:
            specific_time_str (str): datetime类型字符串

        Returns:
            float: 时间差
        """
        try:
            # 解析时间字符串
            specific_time = datetime.strptime(specific_time_str, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            # 如果时间字符串格式不正确，则返回 None 或者抛出异常，取决于你的需求
            return None  # 或者 raise ValueError("Invalid time format. Please use %Y-%m-%dT%H:%M:%S.")

        # 获取当前时间
        current_time = datetime.now()

        # 计算时间差
        time_difference = specific_time - current_time

        # 返回时间差的总秒数
        return time_difference.total_seconds()

    def get_random_value(self, lower_limit, upper_limit):
        """获得2个数之间的随机值

        Args:
            lower_limit (float): 随机数下限
            upper_limit (float): 随机数上限

        Returns:
            float: 2个数之间的随机值
        """
        if lower_limit == upper_limit:
            return round(lower_limit, 2)

        if lower_limit > upper_limit:
            lower_limit, upper_limit = upper_limit, lower_limit

        random_float = round(random.uniform(lower_limit, upper_limit), 2)
        return random_float

    """
    Dict操作
    """

    def find_keys_by_value(self, dictionary, target_value):
        # 返回一个包含所有具有指定值的键的列表
        return [key for key, value in dictionary.items() if value == target_value]

    def find_key_by_value(self, d: dict, value):
        # 遍历字典项
        for key, val in d.items():
            if val == value:
                return key
        return None

    r"""
                                                                                                              
                   .,]`                    ]]]`            ,]]`                      .`    .]`                
                  ,@@@@                    @@@^            =@@^  .@@@@@@@@@@@@^      /@@@  /@@@               
         =@@@@@@@@@@@@@@@@@@@@@@^ O@@@@@@@@@@@@@@@@@@@@@ ..=@@\...@@@]]]]]]/@@^     =@@@` =@@@@@@@@@@@@@\     
         =@@@@@@@@@@@@@@@@@@@@@@^ O@@@@@@@@@@@@@@@@@@@@@ =@@@@@@^.@@@@@@@@@@@@^    ,@@@^ ,@@@@@@@@@@@@@@@     
             =@@@^      /@@@^            /@@@@@@\          =@@^ .@@@@@@O.@@@@@@@  ,@@@@^=@@@^=@@@.            
              =@@@^    =@@@/           ,@@@@@@@@@@`        =@@^..@@^.@@@.@@^.@@@ ,@@@@@^\@@` =@@@@@@@@@^      
               \@@@\ ./@@@/          ,@@@@`@@@^.@@@@`    /@@@@@@*@@@@@@@.@@@@@@@ =@@@@@^ \.  =@@@@@@@@@^      
                ,@@@@@@@@`         ,@@@@/  @@@^  =@@@@]  =@@@@/`      =@@O       .@.@@@^     =@@@.            
                 ]@@@@@@`        =@@@@@]]]]@@@\]]]]@@@@@^  =@@^ @@@@@@@@@@@@@@@@^   @@@^     =@@@@@@@@@@      
             ,/@@@@@@@@@@@@\`     ,@/.=@@@@@@@@@@@@^ \/.   =@@^    ,@@@@@@@@]       @@@^     =@@@@@@@@@@      
         =@@@@@@@@/.  .\@@@@@@@@`          @@@^          ,]/@@^,/@@@@`=@@@.\@@@@`   @@@^     =@@@.            
          ,@@@/`          ,\@@/.           @@@^          =@@@@` ,@[.  =@@@   ,\`    @@@^     =@@@.            
                                                                                                              

    """

    # 判断文本是否可以转为dict JSON格式
    def is_json_convertible(self, text: str) -> bool:
        """判断文本是否可以转为dict JSON格式

        Args:
            text (str): 待判断内容

        Returns:
            bool: T / F
        """
        try:
            import json

            json.loads(text)
            return True
        except json.JSONDecodeError:
            return False

    # 生成hash字符串 用于gradio请求
    def generate_session_hash(self, length: int = 11):
        import hashlib
        import string

        characters = string.ascii_letters + string.digits
        random_string = "".join(random.choice(characters) for i in range(length))
        hash_object = hashlib.sha1(random_string.encode())
        session_hash = hash_object.hexdigest()[:length]

        return session_hash

    # 将字符串中的数字转换成中文
    def convert_digits_to_chinese(self, input_str: str):
        """将字符串中的数字转换成中文

        Args:
            input_str (str): 待转换的字符串

        Returns:
            str: 转换后的字符串
        """
        try:
            # 定义阿拉伯数字到中文数字的映射
            digit_to_chinese = {
                "0": "零",
                "1": "一",
                "2": "二",
                "3": "三",
                "4": "四",
                "5": "五",
                "6": "六",
                "7": "七",
                "8": "八",
                "9": "九",
            }

            # 遍历输入字符串并替换数字为中文数字
            result = "".join(digit_to_chinese.get(char, char) for char in input_str)

            return result
        except Exception as e:
            logger.error(f"转换数字到中文时出错: {e}")
            return input_str

    # 删除多余单词
    def remove_extra_words(self, text="", max_len=30, max_char_len=50):
        words = text.split()
        if len(words) > max_len:
            words = words[:max_len]  # 列表切片，保留前30个单词
            text = " ".join(words) + "..."  # 使用join()函数将单词列表重新组合为字符串，并在末尾添加省略号
        return text[:max_char_len]

    # 本地敏感词检测 传入敏感词库文件路径和待检查的文本
    def check_sensitive_words(self, file_path, text):
        with open(file_path, encoding="utf-8") as file:
            sensitive_words = [line.strip() for line in file.readlines()]

        for word in sensitive_words:
            if word in text:
                return True

        return False

    # 本地敏感词检测 Aho-Corasick 算法 传入敏感词库文件路径和待检查的文本
    def check_sensitive_words2(self, file_path, text):
        with open(file_path, encoding="utf-8") as file:
            sensitive_words = [line.strip() for line in file.readlines()]

        # 创建 Aho-Corasick 自动机
        automaton = ahocorasick.Automaton()

        # 添加违禁词到自动机中
        for word in sensitive_words:
            automaton.add_word(word, word)

        # 构建自动机的转移函数和失效函数
        automaton.make_automaton()

        # 在文本中搜索违禁词
        for _, found_word in automaton.iter(text):
            logger.warning(f"命中本地违禁词：{found_word}")
            return found_word

        return None

    # 本地敏感词转拼音检测 传入敏感词库文件路径和待检查的文本
    def check_sensitive_words3(self, file_path, text):
        with open(file_path, encoding="utf-8") as file:
            sensitive_words = [line.strip() for line in file.readlines()]

        pinyin_text = self.text2pinyin(text)
        # logger.info(f"pinyin_text={pinyin_text}")

        for word in sensitive_words:
            pinyin_word = self.text2pinyin(word)
            pattern = r"\b" + re.escape(pinyin_word) + r"\b"
            if re.search(pattern, pinyin_text):
                logger.warning(f"同音违禁拼音：{pinyin_word}")
                return True

        return False

    # 语言检测 TODO:有内存泄漏风险
    def lang_check(self, text, need="none"):
        # 语言检测 一个是语言，一个是概率
        language, score = langid.classify(text)

        if need == "none":
            return language
        else:
            if language != need:
                return None
            else:
                return language

    # 判断字符串是否全为标点符号
    def is_punctuation_string(self, string):
        # 使用正则表达式匹配标点符号
        pattern = r"^[^\w\s]+$"
        return re.match(pattern, string) is not None

    # 判断字符串是否全为空格和特殊字符
    def is_all_space_and_punct(self, text):
        pattern = r"^[\s\W]+$"
        return re.match(pattern, text) is not None

    # 违禁词校验
    def profanity_content(self, content):
        return profanity.contains_profanity(content)

    # 判断字符串是否以一个list中任意一个字符串打头
    def starts_with_any(self, string, prefixes):
        """判断字符串是否以一个list中任意一个字符串打头

        Args:
            string (str): 待判断的字符串
            prefixes (list): 匹配的字符串数组

        Returns:
            str: 命中的匹配到的字符串/None
        """
        try:
            for prefix in prefixes:
                if string.startswith(prefix):
                    return prefix
        except AttributeError as e:
            # 处理异常，例如打印错误消息或者返回 False
            logger.error(f"Error: {e}")
            return None

        return None

    # 文本切分算法
    def split_sentences(self, text):
        # 使用正则表达式切分句子
        sentences = re.split(r"(?<=[。！？!?])", text)
        result = []
        current_sentence = ""

        for sentence in sentences:
            # 去除换行和空格
            sentence = sentence.replace("\n", "")

            # 如果句子为空则跳过
            if not sentence:
                continue

            # 如果句子长度小于10个字，则与下一句合并
            if len(current_sentence) < 10:
                current_sentence += sentence
            else:
                # 判断当前句子是否以标点符号结尾
                if current_sentence[-1] in ["。", "！", "？", ".", "!", "?"]:
                    result.append(current_sentence)
                    current_sentence = sentence
                else:
                    # 如果当前句子不以标点符号结尾，则进行二次切分
                    split_sentences = re.split(r"(?<=[,，;；])", current_sentence)
                    if len(split_sentences) > 1:
                        result.extend(split_sentences[:-1])
                        current_sentence = split_sentences[-1] + sentence
                    else:
                        current_sentence += sentence

        # 添加最后一句
        if current_sentence:
            result.append(current_sentence)

        return result

    # 字符串匹配算法来计算字符串之间的相似度，并选择匹配度最高的字符串作为结果
    def find_best_match(self, substring, string_list, similarity=0.5):
        """字符串匹配算法来计算字符串之间的相似度，并选择匹配度最高的字符串作为结果

        Args:
            substring (str): 要搜索的子串
            string_list (list): 字符串列表
            similarity (float): 最低相似度

        Returns:
            _type_: 匹配到的字符串 或 None
        """
        best_match = None
        best_ratio = 0

        for string in string_list:
            ratio = difflib.SequenceMatcher(None, substring, string).ratio()
            # print(f"String: {string}, Ratio: {ratio}")  # 添加调试语句，输出每个字符串的相似度
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = string

        # 如果相似度不到similarity，则认为匹配不成功
        if best_ratio < similarity:
            return None

        return best_match

    # 检查 query_string 是否包含 string_list 列表中的任意一个子字符串
    def find_substring_in_list(self, query_string, string_list):
        """
        检查 query_string 是否包含 string_list 列表中的任意一个子字符串

        Args:
            query_string (str): 待查询的字符串。
            string_list (list of str): 被查询的字符串列表。

        Returns:
            str or None: 如果找到子串，则返回该子串；否则返回 None。
        """
        for string in string_list:
            if string in query_string:
                return string
        return None

    def text2pinyin(self, text):
        """文本转拼音

        Args:
            text (str): 传入待转换的文本

        Returns:
            str: 拼音字符串
        """
        pinyin_list = []
        for char in text:
            # 把每个汉字转为拼音
            char_pinyin_list = pinyin(char, style=Style.NORMAL)
            if char_pinyin_list:
                _pinyin = char_pinyin_list[0][0]
            else:
                _pinyin = char

            # 将ü等转换为v
            _pinyin = re.sub(r"ü", "v", _pinyin)

            pinyin_list.append(_pinyin)

        return " ".join(pinyin_list)

    def merge_consecutive_asterisks(self, s):
        """合并字符串末尾连续的*

        Args:
            s (str): 待处理的字符串

        Returns:
            str: 处理完后的字符串
        """
        # 从字符串末尾开始遍历，找到连续的*的起始索引
        idx = len(s) - 1
        while idx >= 0 and s[idx] == "*":
            idx -= 1

        # 如果找到了超过3个连续的*，则进行替换
        if len(s) - 1 - idx > 3:
            s = s[: idx + 1] + "*" + s[len(s) - 1 :]

        return s

    def replace_special_characters(self, input_string, special_characters):
        """
        将指定的特殊字符替换为空字符。

        Args:
            input_string (str): 要替换特殊字符的输入字符串。
            special_characters (str): 包含要替换的特殊字符的字符串。

        Returns:
            str: 替换后的字符串。
        """
        for char in special_characters:
            input_string = input_string.replace(char, "")

        return input_string

    # 将cookie数据字符串分割成键值对列表
    def parse_cookie_data(self, data_str, field_name):
        """将cookie数据字符串分割成键值对列表

        Args:
            data_str (str): 待提取数据的cookie字符串
            field_name (str): 要提取的键名

        Returns:
            str: 键所对应的值
        """
        # 将数据字符串分割成键值对列表
        key_value_pairs = data_str.split(";")

        # print(key_value_pairs)

        # 遍历键值对列表，查找指定字段名
        for pair in key_value_pairs:
            key, sep, value = pair.strip().partition("=")
            # 结尾的 ';' 会切出空项；值本身含 '='（如 base64 填充）时只按第一个 '=' 切
            if not sep:
                continue
            if key == field_name:
                return value

        # 如果未找到指定字段，返回空字符串
        return ""

    # 动态变量替换
    def dynamic_variable_replacement(self, template: str, data_json: dict = None):
        """动态变量替换

        Args:
            template (str): 待替换变量的字符串
            data_json (dict): 用于替换的变量json数据

        Returns:
            str: 替换完成后的字符串
        """
        try:
            if data_json is None:
                return template

            pattern = r"{(\w+)}"
            var_names = re.findall(pattern, template)

            for var_name in var_names:
                if var_name in data_json:
                    template = template.replace("{" + var_name + "}", str(data_json[var_name]))
                else:
                    # 变量不存在,保留原样
                    pass

            logger.debug(f"template={template}")

            return template
        except Exception:
            logger.error(traceback.format_exc())
            return None

    # [1|2]括号语法随机获取一个值，返回取值完成后的字符串
    def brackets_text_randomize(self, text: str):
        """
        [1|2]括号语法随机获取一个值，返回取值完成后的字符串
        Args:
            text (str): 原始字符串

        Returns:
            str: 最终字符串
        """
        # 查找所有括号内的内容
        brackets_content = re.findall(r"\[([^\]]*)\]", text)

        for content in brackets_content:
            # 分割每个括号内的选项
            choices = content.split("|")
            # 从选项中随机选择一个
            random_choice = random.choice(choices)
            # 替换文本中的括号内容
            text = text.replace(f"[{content}]", random_choice, 1)

        return text

    # 从列表中随机获取一个字符串，并进行变量语法转换。如果列表为空，使用单个字符串进行转换。
    def get_random_str_in_list_and_format(
        self, ori_content: str = None, ori_list: list = None, var_json: dict = None
    ) -> dict:
        """
        从列表中随机获取一个字符串，并进行变量语法转换。如果列表为空，使用单个字符串进行转换。

        参数:
            ori_content (str): 单个待处理的字符串。
            ori_list (list of str): 待处理字符串的列表。
            var_json (dict): 动态变量替换所需的键值对。

        返回:
            dict: 包含转换后内容的字典和返回码。成功时返回 {"ret": 0, "content": content}，失败时返回 {"ret": -1, "content": None}。
        """

        # 检查并处理字符串列表
        if ori_list:
            content = random.choice(ori_list)
        elif ori_content:
            content = ori_content
        else:
            return {"ret": -1, "content": None}

        # [1|2]括号语法随机获取一个值，返回取值完成后的字符串
        content = self.brackets_text_randomize(content)

        # 动态变量替换
        content = self.dynamic_variable_replacement(content, var_json)

        return {"ret": 0, "content": content}

    def get_list_random_or_default(self, strings: list, default_value):
        """

        从列表中随机选择一个字符串，如果列表为空，则返回默认值。

        参数:
            strings (list of str): 字符串列表。
            default_value (str): 默认值。

        返回:
            str: 随机选择的字符串或默认值。
        """
        if not strings:  # 如果列表是空的
            return default_value
        else:
            return random.choice(strings)

    # llm响应内容<> </>标签内容过滤 主要针对deepseek返回
    def llm_resp_content_filter_tags(self, text: str, filter_state: dict) -> str:
        """
        过滤标签内容的辅助函数

        Args:
            text: 要处理的文本
            filter_state: 过滤状态字典，包含：
                - is_filtering: 是否正在过滤
                - current_tag: 当前正在处理的标签
                - buffer: 未处理完的文本缓冲

        Returns:
            过滤后的文本
        """
        result = ""
        i = 0

        # logger.debug(f"[过滤] 标签过滤前：{text}")
        # logger.debug(f"[过滤] 过滤状态：{filter_state}")

        while i < len(text):
            if text[i] == "<":
                # logger.debug(f"[过滤] 发现开始标签：{text[i]}")
                # 可能是开始标签
                tag_end = text.find(">", i)
                if tag_end != -1:
                    tag = text[i : tag_end + 1]
                    if tag.startswith("</"):
                        # logger.debug(f"[过滤] 发现结束标签：{tag}")
                        # 结束标签
                        tag_name = tag[2:-1]
                        if filter_state["is_filtering"] and tag_name == filter_state["current_tag"]:
                            filter_state["is_filtering"] = False
                            filter_state["current_tag"] = None
                    else:
                        # logger.debug(f"[过滤] 发现开始标签：{tag}")
                        # 开始标签
                        tag_name = tag[1:-1]
                        filter_state["is_filtering"] = True
                        filter_state["current_tag"] = tag_name
                    i = tag_end + 1
                    continue

            if not filter_state["is_filtering"]:
                # logger.debug(f"[过滤] 发现非过滤状态：{text[i]}")
                result += text[i]
            i += 1

        # logger.debug(f"[过滤] 标签过滤后：{result}")
        return result

    r"""
    
            .@@@             @@@        @@^ =@@@@@@@@    /@@ /@@              =@@@@@*,@@\]]]]  ,@@@@@@@@@@@@*                      .@@@         @@/.\]`@@@       =@@\]]]]]]]   =@@..@@@@@@@@@   =@@\   /@@^           
      *@@@@@@@@@@@@@@@*=@@@@@@@@@@@@@@.@@@@@=@@@@@@@@   =@@`=@@@@@@@@@^       =@/[@@@@@@@@@@/.@@@`     .]@@/                 *@@@@@@@@@@@@@@@* =@@.=@@]@@@]]]. ,@@@@@@@@@@@@ ,@@@@@@@@/[[[\@@ =@@@@@@@@@@@@@^         
         =@@`   ,@@^       .@@@@@.      @@^=@@@@^@@@@@ =@@@=@@`@@^            =@@@@@,[@@@@@/  \/,@@`]/@@@@@]                    =@@`   ,@@^   ,@@@,@@@@@@@@@/.\@/,@@@`/@@@`  .[\@@[[@@@@@@@@@ ,[[[[[@@@[[[[[`         
          \@@` ,@@/       /@@@@@@@\    .@@@O@\/@^@@]@@=@@@@,@`*@@@@@@^        ]]=@@=@@@@@@@@@^,@@@,@@/`  .\@@.                   \@@` ,@@/   ,@@@@[@/  @@@       ,]@@@@[      ,@@@@\@@^   =@@.@@@@@@@@@@@@@@@`        
           =@@@@@^     ./@@/ @@@ \@@\`=@@@/`   =@@     @=@@   *@@^     =@@@@^ @@=@@@,@@@@@@@^,@@@^.@@@@@@@@@^                     =@@@@@^    .@\@@@@@@@@@@@@@/@@@@@@@@@@@@@@.,@@@@[`@@@@@@@@@.[[[[[\@@@/[[[[[`        
          ,/@@@@@\`   .\@/@@@@@@@@@\@/  @@^\@@@@@@@@@/. =@@   *@@@@@@@        @@=@@ *@@[[[@@^ .=@^    =@@.    ./`                ,/@@@@@\`     =@@     @@@      @@@      =@@..@=@@..@@^   =@@    ,/@@[@@@`            
      .@@@@@@` ,\@@@@@`      @@@      ,]@@^/@@/=@@[@@@` =@@   *@@^           =@@@@@@^@@@@@@@^  =@^@@@@@@@@@@@^,@@@`          .@@@@@@` ,\@@@@@` =@@     @@@      @@@@@@@@@@@@.  =@@..@@@@@@@@@./@@@@/   [@@@@@`        
       .[`         ,[        \@/      .[[[ ..  ,@/      ,@/   .@@`            .     .@/.  \@`  ,[`,[[[[[[[[[[.  ,[            .[`         ,[   ,@/     \@/      \@/      ,[[.  ,@/..\@`   ,@/ .[[         ,[    
    
    """

    # 读取指定文件中所有文本内容并返回 如果文件不存在则创建
    def read_file_return_content(self, file_path):
        try:
            if not os.path.exists(file_path):
                logger.warning(f"文件不存在，将创建新文件: {file_path}")
                # 创建文件
                with open(file_path, "w", encoding="utf-8") as file:
                    content = ""
                return content

            with open(file_path, encoding="utf-8") as file:
                content = file.read()
            return content
        except OSError as e:
            logger.error(f"无法写入文件:{file_path}\n{e}")
            return None

    # 将一个文件路径的字符串切分成路径和文件名
    def split_path_and_filename(self, file_path):
        folder_path, file_name = os.path.split(file_path)
        # 检查路径末尾是否已经包含了'/'，如果没有，则添加
        if not folder_path.endswith("/"):
            folder_path += "/"

        return folder_path, file_name

    # 从文件路径中提取出带有扩展名的文件名
    def extract_filename(self, file_path, with_extension=False):
        """从文件路径中提取出带有扩展名的文件名

        Args:
            file_path (_type_): 文件路径
            with_extension (bool, optional): 是否需要拓展名. Defaults to False.

        Returns:
            str: 文件名
        """
        file_name_with_extension = os.path.basename(file_path)
        if with_extension:
            return file_name_with_extension
        else:
            file_name_without_extension = os.path.splitext(file_name_with_extension)[0]
            return file_name_without_extension

    # 获取指定文件夹下的所有文件夹的名称
    def get_folder_names(self, path):
        folder_names = next(os.walk(path))[1]
        return folder_names

    # 返回指定文件夹内所有文件的文件绝对路径（包括文件扩展名）
    def get_all_file_paths(self, folder_path):
        """返回指定文件夹内所有文件的文件绝对路径（包括文件扩展名）

        Args:
            folder_path (str): 文件夹路径

        Returns:
            list: 文件绝对路径列表
        """
        file_paths = []  # 用于存储文件绝对路径的列表

        # 使用 os.walk 遍历文件夹内所有文件和子文件夹
        for root, _directories, files in os.walk(folder_path):
            for filename in files:
                file_path = os.path.join(root, filename)  # 获取文件的绝对路径
                file_paths.append(file_path)

        return file_paths

    # 获取指定路径下指定拓展名的文件名列表
    def get_specify_extension_names_in_folder(self, path: str, extension: str):
        """
        获取指定路径下指定拓展名的文件名列表

        Parameters:
            path (str): 指定的路径
            extension (str): 指定的拓展名（例如：.json、.txt、.jpg等）

        Returns:
            list: 文件名列表
        """
        if not os.path.exists(path):
            logger.error(f"路径 '{path}' 不存在")
            return []

        file_names = glob.glob(os.path.join(path, f"*{extension}"))
        return [os.path.basename(file_name) for file_name in file_names]

    def remove_extension_from_list(self, file_name_list):
        """
        将包含多个带有拓展名的文件名的列表中的拓展名去掉，只返回文件名部分组成的新列表

        Args:
            file_name_list (list): 包含多个带有拓展名的文件名的列表

        Returns:
            list: 文件名组成的新列表
        """
        # 使用列表推导来处理整个列表，去掉每个文件名的拓展名
        file_name_without_extension_list = [file_name.split(".")[0] for file_name in file_name_list]
        return file_name_without_extension_list

    def is_audio_file(self, file_path):
        """判断文件是否是音频文件

        Args:
            file_path (str): 文件路径

        Returns:
            bool: True / False
        """
        _, extension = os.path.splitext(file_path)
        return extension.lower() in SUPPORTED_AUDIO_EXTENSIONS

    def random_search_a_audio_file(self, root_dir):
        """搜索指定文件夹内所有的音频文件，并随机返回一个音频文件路径

        Args:
            root_dir (str): 搜索的文件夹路径

        Returns:
            str: 随机返回一个音频文件路径
        """
        audio_files = []

        for root, _dirs, files in os.walk(root_dir):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, root_dir)
                relative_path = relative_path.replace("\\", "/")

                logger.debug(file_path)

                # 判断文件是否是音频文件
                if self.is_audio_file(relative_path):
                    audio_files.append(file_path)

        if audio_files:
            # 随机返回一个音频文件路径
            return random.choice(audio_files)
        else:
            return None

    r"""
                                                                                                 
              .]]@@              .@]]       @@@@        O@@`  ,]]]]]]]]]]]].      /]]   /@]`                  
               =@@@\             =@@@`.@@@^ @@@@        @@@^  =@@@@@@@@@@@@.     =@@@` =@@@`                  
      @@@@@@@@@@@@@@@@@@@@@@@   ,@@@^ =@@@` @@@@      ]]@@@\]`=@@@@@@@@@@@@.    ,@@@^ ,@@@@@@@@@@@@@@^        
      @@@@@@@@@@@@@@@@@@@@@@@  .@@@@ .@@@@@@@@@@@@@@@ @@@@@@@^,[[[[[[[[[[[[.   .@@@@..@@@@@@@@@@@@@@@`        
          \@@@`     =@@@@     .@@@@@ =@@@[[[@@@@[[[[`   @@@^ =@@@@@@^=@@@@@@^ .@@@@@,@@@/ @@@^                
          .@@@@`   ,@@@@.     /@@@@@,@@@^   @@@@        @@@\]=@@ =@@^=@@.=@@^.@@@@@@.@@/  @@@@@@@@@@          
            \@@@\./@@@@      .@@@@@@,]]]]]]]@@@@]]]]]/@@@@@@@=@@@@@@^=@@@@@@^ @@O@@@..`   @@@/[[[[[[          
             =@@@@@@@^        =/=@@@=@@@@@@@@@@@@@@@@^@@@@@^,]]]]]]@@@\]]]]]] =`=@@@.     @@@^                
            ./@@@@@@@]          =@@@        @@@@        @@@^=@@@@@@@@@@@@@@@@   =@@@.     @@@@@@@@@@^         
        ,]@@@@@@@[@@@@@@@]`     =@@@        @@@@        @@@^  .]@@@@@@@@@\.     =@@@.     @@@/[[[[[[`         
      \@@@@@@@[    .[@@@@@@@/   =@@@        @@@@     .@@@@@`@@@@@` @@@^.\@@@@.  =@@@.     @@@^                
       ,@/[            .[\@`    =@@@        @@@@      \@@@`  ,`    @@@^   .[    =@@@.     @@@^             

    """

    # 读取文件内容 它接受文件路径和返回类型参数，并根据参数返回文件内容作为字典或纯文本。如果读取文件过程中出现异常，则返回 None。
    def read_file(self, file_path: str, return_type: str):
        try:
            with open(file_path, encoding="utf-8") as file:
                content = file.read()

            if return_type == "dict":
                return json.loads(content)
            elif return_type == "text":
                return content
            else:
                logger.error("Invalid return type. Use 'dict' or 'text'.")
                return None
        except Exception:
            logger.error(traceback.format_exc())
            return None

    def ensure_directory_exists(self, path):
        # 检查路径是否存在
        if not os.path.exists(path):
            # 如果路径不存在，创建它
            os.makedirs(path)
            logger.info(f"路径已创建：{path}")

    # 写入内容到指定文件中 返回T/F
    def write_content_to_file(self, file_path, content, write_log=True):
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(content)

            if write_log:
                logger.info(f"写入文件:{file_path}，内容：【{content}】")

            return True
        except OSError as e:
            logger.error(f"无法写入 【{content}】 到文件:{file_path}\n{e}")
            return False
        except Exception:
            logger.error(traceback.format_exc())
            return False

    # 移动文件到指定路径 src dest
    def move_file(self, source_path, destination_path, rename=None, format="wav"):
        """移动文件到指定路径

        Args:
            source_path (str): 文件路径含文件名
            destination_path (_type_): 目标文件夹
            rename (str, optional): 文件名. Defaults to None.
            format (str, optional): 文件格式（实际上只是个假拓展名）. Defaults to "wav".

        Returns:
            str: 输出到的完整路径含文件名
        """
        logger.debug(f"source_path={source_path},destination_path={destination_path},rename={rename}")

        # if rename is not None:
        #     destination_path = os.path.join(os.path.dirname(destination_path), rename)

        # shutil.move(source_path, destination_path)
        # logger.info(f"文件移动成功：{source_path} -> {destination_path}")
        destination_directory = os.path.dirname(destination_path)
        logger.debug(f"destination_directory={destination_directory}")
        destination_filename = os.path.basename(source_path)

        if rename is not None:
            destination_filename = rename + "." + format

        destination_path = os.path.join(destination_directory, destination_filename)

        if os.path.exists(destination_path):
            # 如果目标位置已存在同名文件，则先删除
            os.remove(destination_path)

        shutil.move(source_path, destination_path)
        logger.info(f"文件移动成功：{source_path} -> {destination_path}")

        return destination_path

    # 删除文件
    def del_file(self, file_path) -> bool:
        """
        删除文件

        Args:
            file_path (str): 文件路径

        Returns:
            bool：True/False
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"文件删除成功：{file_path}")

                return True

            logger.error(f"文件不存在：{file_path}")
            return False
        except Exception:
            logger.error(traceback.format_exc())
            return False

    # 从给定的文件路径中提取文件名及其扩展名
    def get_filename_from_path(self, file_path):
        """
        从给定的文件路径中提取文件名及其扩展名。

        参数:
        file_path (str): 文件的绝对路径或相对路径。

        返回:
        dict: 包含状态码和数据的字典。成功时返回文件名，失败时返回错误信息。
        """
        response = {
            "code": 200,  # 默认成功状态码
            "data": None,
            "error": None,
        }

        try:
            # 验证输入路径是否为空
            if not file_path:
                response["code"] = 400  # 客户端错误状态码
                response["error"] = "路径不能为空"
                raise ValueError(response["error"])

            # 验证文件是否存在
            if not os.path.exists(file_path):
                response["code"] = 404  # 文件未找到状态码
                response["error"] = f"文件 {file_path} 不存在"
                raise FileNotFoundError(response["error"])

            # 提取文件名及其扩展名
            filename = os.path.basename(file_path)
            response["data"] = filename

        except ValueError as ve:
            logger.error(ve)
        except FileNotFoundError as fnf:
            logger.error(fnf)
        except Exception as e:
            response["code"] = 500  # 服务器错误状态码
            response["error"] = "发生未知错误"
            logger.error(e)

        return response

    r"""
    
                   ,@@@^              .@@@. .@@@@@@@@@@@@.  .@@@.  ,]]]]]]]]]]]]`     ]@@@`     ,@@@\.        
          .@@@@@@@@@@@@@@@@@@@@@^ .@@O.@@@\]`@@@@@@@@@@@@.  .@@@.  =@@@@@@@@@@@@^      \@@@@.  =@@@/          
              .]@@^     ,@@\`     .@@O.@@@@@^,]]/@@@]]]]`.@@@@@@@@@=@@^     .@@@^  =@@@@@@@@@@@@@@@@@@@@      
         .@@@@@@@@@@@@@@@@@@@@@@@..@@O.@@@.  =@@@@@@@@@@^.[[[@@@/[[=@@@]]]]]/@@@^  =@@@@@@@@@@@@@@@@@@@O      
         .@@@@@@@@@@@@@@@@@@@@@@@*@@@@@@@@@@@=@@^,]]`=@@^   /@@@`  =@@@@@@@@@@@@^          =@@@^              
            =@@@@@@@@@@@@@@@@@^       =@@O   =@@^=@@^=@@^  /@@@@@@@/@@^     .@@@^.@@@@@@@@@@@@@@@@@@@@@@@.    
            =@@@@@@@@@@@@@@@@@^    /@@\@@O=@@/@@^=@@^=@@^./@@@@@[@`=@@@@@@@@@@@@^.O@@@@@@@@@@@@@@@@@@@@@O.    
            =@@@]]]]]]]]]]]@@@^   =@@^=@@@@@/=@@^@@@.=@@^.@@`@@@.  =@@@@@@@@@@@@^        .@@@@@@@`            
            =@@@@@@@@@@@@@@@@@^  .,\^ ./@@@^ ,[[@@@@\,[[` =`.@@@.  =@@^     .@@@^      ,@@@@/ \@@@@]          
            =@@@]]]]]]]]]]]@@@^    .]@@@@/   ,/@@@/@@@@]    .@@@.  =@@@@@@@@@@@@^ .,/@@@@@/.   .\@@@@@@\].    
            =@@@@@@@@@@@@@@@@@^   \@@@@`   ,@@@@[   .\@@@.  .@@@.  =@@@@@@@@@@@@^ ,@@@@@`         ,\@@@/.     
            ....           ....    ,.        ,.        .     ...   ....     .....   .                        

    """

    # 获取新的音频路径
    def get_new_audio_path(self, audio_out_path, file_name):
        # 判断路径是否为绝对路径
        if os.path.isabs(audio_out_path):
            # 如果是绝对路径，直接使用
            voice_tmp_path = os.path.join(audio_out_path, file_name)
        else:
            # 如果不是绝对路径，检查是否包含 ./，如果不包含，添加 ./，然后拼接路径
            if not audio_out_path.startswith("./"):
                audio_out_path = "./" + audio_out_path
            voice_tmp_path = os.path.normpath(os.path.join(audio_out_path, file_name))

        voice_tmp_path = os.path.abspath(voice_tmp_path)

        return voice_tmp_path

    # 获取所有的声卡设备信息
    def get_all_audio_device_info(self, type):
        """获取所有的声卡设备信息

        Args:
            type (str): 声卡类型，"in" 或 "out"

        Returns:
            list: 声卡设备信息列表
        """
        audio = pyaudio.PyAudio()
        device_infos = []
        try:
            device_count = audio.get_device_count()

            for device_index in range(device_count):
                device_info = audio.get_device_info_by_index(device_index)
                if type == "out":
                    if device_info["maxOutputChannels"] > 0:
                        device_infos.append({"device_index": device_index, "device_info": device_info["name"]})
                elif type == "in":
                    if device_info["maxInputChannels"] > 0:
                        device_infos.append({"device_index": device_index, "device_info": device_info["name"]})
                else:
                    device_infos.append({"device_index": device_index, "device_info": device_info["name"]})
        finally:
            # 不 terminate 就会一直占着 PortAudio 实例，
            # 聊天页每次打开都要调这里一次，进几次页面后设备枚举会开始失败
            audio.terminate()

        return device_infos

    r"""

                                                                        ..        ,]]].                ,]]].  ,]            
    .@@@@.      ,@@@\ .@@@@@@@@@@@@@@`@@@@@@@@@@@@@@` =@@@@@@\]]`    =@@@^ ,]]]]]/@@@\]]]]]]          =@@@. \@@@@`         
    .@@@@.      =@@@@ *@@@@@@@@@@@@@@^@@@@@@@@@@@@@@^ =@@@@@@@@@@@\   ,@@@\,[[[[[\@@@[[[[[[[ ]]]]]]]]]/@@@\]]]/@\]]]       
    .@@@@.      =@@@@      .@@@@.         .@@@@.      =@@@^   .@@@@^   .[` .@@@@@@@@@@@@@@@. @@@@@@@@@@@@@@@@@@@@@@@       
    .@@@@.      =@@@@      .@@@@.         .@@@@.      =@@@^    =@@@@,]]]]],]]]]]]/@@@]]]]]]]`  ,@`    =@@@`     /\.        
    .@@@@@@@@@@@@@@@@      .@@@@.         .@@@@.      =@@@^  .]@@@@`=@@@@@,[[[[[[[[[[[[[[[[[` ,@@@@\. =@@@@` ./@@@@`       
    .@@@@@@@@@@@@@@@@      .@@@@.         .@@@@.      =@@@@@@@@@@/.   =@@@  =@@@@@@@@@@@@@^     .\@@` =@@@@@@@@@/.         
    .@@@@.      =@@@@      .@@@@.         .@@@@.      =@@@/[[`.       =@@@  =@@@]]]]]]]@@@^       ,/@@@@@@\@@@\            
    .@@@@.      =@@@@      .@@@@.         .@@@@.      =@@@^           =@@@.`=@@@@@@@@@@@@@^  .]@@@@@@/\@@@.,@@@@@]         
    .@@@@.      =@@@@      .@@@@.         .@@@@.      =@@@^           =@@@@@=@@@@@@@@@@@@@^  \@@@/`   =@@@.  ,@@@@@@       
    .[[[[.      ,[[[[      .[[[[.         .[[[[.      ,[[[`           =@@@@[=@@@      .@@@^   [.  @@@@@@@@.     [@/        
                                                                    .@/.  =@@@  ,@@@@@@@.       =@@@@@@`            
                                                                    
    """

    """
    HTTP 客户端（实现已拆分到 utils/http_client.py，这里保留委托门面，
    平台监听器等既有调用方以 common.xxx 方式调用不受影响）
    """

    def send_request(self, *args, **kwargs):
        return http_client.send_request(*args, **kwargs)

    async def send_async_request(self, *args, **kwargs):
        return await http_client.send_async_request(*args, **kwargs)

    async def send_heartbeat(self):
        return await http_client.send_heartbeat()

    def check_login(self, api_url: str, username: str, password: str):
        return http_client.check_login(api_url, username, password)

    async def send_to_web_captions_printer(self, api_ip_port, data):
        return await http_client.send_to_web_captions_printer(api_ip_port, data)

    def test_openai_key(self, data_json, type=1):
        return http_client.test_openai_key(data_json, type)

    def get_openai_models(self, base_url: str, api_keys: str):
        return http_client.get_openai_models(base_url, api_keys)

    """
    屏幕与摄像头采集（实现已拆分到 utils/screen.py，这里保留委托门面）
    """

    def list_visible_windows(self):
        return screen.list_visible_windows()

    def capture_window_by_title(self, img_save_path: str, window_title: str):
        return screen.capture_window_by_title(img_save_path, window_title)

    def list_cameras(self, max_tested=5):
        return screen.list_cameras(max_tested)

    def capture_image(self, img_save_path="./out/图像识别", camera_index=0):
        return screen.capture_image(img_save_path, camera_index)
