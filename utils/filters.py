"""弹幕/用户名 过滤器：格式检查、违禁词、黑名单、限定时间去重。

自 utils/my_handle.py 拆分；My_handle 同名方法保留委托门面，
统一交互流水线与既有单测（test_my_handle_filters）零改动。

依赖通过 handle（My_handle 实例）注入：config / common / live_data。
"""

import re
import traceback

from .my_log import logger


def comment_check_and_replace(handle, content):
    """弹幕格式检查和特殊字符替换和指定语言过滤

    Args:
        content (str): 待处理的弹幕内容

    Returns:
        str: 处理完毕后的弹幕内容/None
    """
    # 判断弹幕是否以xx起始，如果是则返回None
    if handle.config.get("filter", "before_filter_str") and any(
        content.startswith(prefix) for prefix in handle.config.get("filter", "before_filter_str")
    ):
        return None

    # 判断弹幕是否以xx结尾，如果是则返回None
    if handle.config.get("filter", "after_filter_str") and any(
        content.endswith(prefix) for prefix in handle.config.get("filter", "after_filter_str")
    ):
        return None

    # 判断弹幕是否以xx起始，如果不是则返回None
    if handle.config.get("filter", "before_must_str") and not any(
        content.startswith(prefix) for prefix in handle.config.get("filter", "before_must_str")
    ):
        return None
    else:
        for prefix in handle.config.get("filter", "before_must_str"):
            if content.startswith(prefix):
                content = content[len(prefix) :]  # 删除匹配的开头
                break

    # 判断弹幕是否以xx结尾，如果不是则返回None
    if handle.config.get("filter", "after_must_str") and not any(
        content.endswith(prefix) for prefix in handle.config.get("filter", "after_must_str")
    ):
        return None
    else:
        for prefix in handle.config.get("filter", "after_must_str"):
            if content.endswith(prefix):
                content = content[: -len(prefix)]  # 删除匹配的结尾
                break

    # 全为标点符号
    if handle.common.is_punctuation_string(content):
        return None

    # 换行转为,
    content = content.replace("\n", ",")

    # 表情弹幕过滤
    if handle.config.get("filter", "emoji"):
        # 如b站的表情弹幕就是[表情名]的这种格式，采用正则表达式进行过滤
        content = re.sub(r"\[.*?\]", "", content)
        logger.info(f"表情弹幕过滤后：{content}")

    # 语言检测
    if handle.common.lang_check(content, handle.config.get("need_lang")) is None:
        logger.warning("语言检测不通过，已过滤")
        return None

    return content


def prohibitions_handle(handle, content):
    """违禁处理

    Args:
        content (str): 带判断的字符串内容

    Returns:
        str: 是：None 否返回：content
    """
    # 含有链接
    if handle.common.is_url_check(content):
        logger.warning(f"链接：{content}")
        return None

    # 违禁词检测
    if handle.config.get("filter", "badwords", "enable"):
        if handle.common.profanity_content(content):
            logger.warning(f"违禁词：{content}")
            return None

        bad_word = handle.common.check_sensitive_words2(handle.config.get("filter", "badwords", "path"), content)
        if bad_word is not None:
            logger.warning(f"命中本地违禁词：{bad_word}")

            # 是否丢弃
            if handle.config.get("filter", "badwords", "discard"):
                return None

            # 进行违禁词替换
            content = content.replace(bad_word, handle.config.get("filter", "badwords", "replace"))

            logger.info(f"违禁词替换后：{content}")

            # 回调，多次进行违禁词过滤替换
            return prohibitions_handle(handle, content)

        # 同拼音违禁词过滤
        if handle.config.get("filter", "badwords", "bad_pinyin_path") != "":
            if handle.common.check_sensitive_words3(
                handle.config.get("filter", "badwords", "bad_pinyin_path"), content
            ):
                logger.warning(f"同音违禁词：{content}")
                return None

    return content


def blacklist_handle(handle, data):
    """黑名单处理

    Args:
        data (dict): 包含用户名,弹幕内容

    Returns:
        bool: True是黑名单用户，False不是黑名单用户
    """
    try:
        if handle.config.get("filter", "blacklist", "enable"):
            username_blacklist = handle.config.get("filter", "blacklist", "username")
            if len(username_blacklist) == 0:
                return False

            if data["username"] in username_blacklist:
                logger.info(f"弹幕黑名单 过滤 用户名：{data['username']}")
                return True

        return False
    except Exception:
        logger.error(traceback.format_exc())
        return False


def is_data_repeat_in_limited_time(handle, type=None, data=None):
    # 遍历+append 是复合操作，且 clear_live_data 定时器会并发换新列表——上 state_lock
    with handle.state_lock:
        return _is_data_repeat_unlocked(handle, type, data)


def _is_data_repeat_unlocked(handle, type=None, data=None):
    """判断限定时间段内数据是否重复

    Args:
        type (str): 判断的数据类型（comment|gift|entrance)
        data (dict): 包含用户名,弹幕内容

    Returns:
        dict: 传递给音频合成的JSON数据
    """
    if handle.config.get("filter", "limited_time_deduplication", "enable"):
        logger.debug(f"限定时间段内数据重复 handle.live_data={handle.live_data}")

        if type is not None and type != "" and data is not None:
            if type == "comment":
                # 如果存在重复数据，返回True
                for tmp in handle.live_data[type]:
                    if tmp["username"] == data["username"] and tmp["content"] == data["content"]:
                        logger.debug(f"限定时间段内数据重复 type={type},data={data}")
                        return True
            elif type == "gift":
                # 如果存在重复数据，返回True
                for tmp in handle.live_data[type]:
                    if tmp["username"] == data["username"]:
                        logger.debug(f"限定时间段内数据重复 type={type},data={data}")
                        return True
            elif type == "entrance":
                # 如果存在重复数据，返回True
                for tmp in handle.live_data[type]:
                    if tmp["username"] == data["username"]:
                        logger.debug(f"限定时间段内数据重复 type={type},data={data}")
                        return True

            # 不存在则插入，返回False
            handle.live_data[type].append(data)
    return False
