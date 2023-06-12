# 导入所需的库
import re
import time
from datetime import datetime
from datetime import timedelta
from datetime import timezone

import langid

from profanity import profanity


class Common:
    # 获取北京时间
    def get_bj_time(self, type=0):
        if type == 0:
            """
            获取北京时间
            :return: 当前北京时间，格式为 '%Y-%m-%d %H:%M:%S'
            """
            utc_now = datetime.utcnow().replace(tzinfo=timezone.utc)  # 获取当前 UTC 时间
            SHA_TZ = timezone(
                timedelta(hours=8),
                name='Asia/Shanghai',
            )
            beijing_now = utc_now.astimezone(SHA_TZ)  # 将 UTC 时间转换为北京时间
            fmt = '%Y-%m-%d %H:%M:%S'
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

    # 删除多余单词
    def remove_extra_words(self, text="", max_len=30, max_char_len=50):
        words = text.split()
        if len(words) > max_len:
            words = words[:max_len]  # 列表切片，保留前30个单词
            text = ' '.join(words) + '...'  # 使用join()函数将单词列表重新组合为字符串，并在末尾添加省略号
        return text[:max_char_len]

    # 本地敏感词检测 传入敏感词库文件路径和待检查的文本
    def check_sensitive_words(self, file_path, text):
        with open(file_path, 'r', encoding='utf-8') as file:
            sensitive_words = [line.strip() for line in file.readlines()]

        for word in sensitive_words:
            if word in text:
                return True

        return False

    # 链接检测
    def is_url_check(self, text):
        url_pattern = re.compile(r'(?i)((?:(?:https?|ftp):\/\/)?[^\s/$.?#]+\.[^\s>]+)')

        if url_pattern.search(text):
            return True
        else:
            return False

    # 语言检测
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
        pattern = r'^[^\w\s]+$'
        return re.match(pattern, string) is not None

    # 违禁词校验
    def profanity_content(self, content):
        return profanity.contains_profanity(content)


config_list = 'config/config_list.txt'
support_platform = 'config/support_platform.txt'


# 加载支持的平台
def get_support_platform():
    platform = []
    with open(support_platform) as f:
        platform = [line.rstrip('\n') for line in f]
    return platform


# 加载配置文件的key
def load_config_key():
    keys = []
    with open(config_list, 'r') as f:
        keys = [line.rstrip('\n') for line in f]
        # for line in f:
        #     keys.append(line.strip('\n').split(','))
    return keys


# 根据用户自定义配置文件组装dict
def build_user_config(values):
    keys = load_config_key()
    user_config = {}

    i = 0
    for key in keys:
        user_config[key] = values[i]
        i += 1

    return user_config
