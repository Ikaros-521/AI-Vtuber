"""推给音频合成的消息，统一在这里构造。

以前这个字典在 30 多个地方各写一遍，字段名或取值稍有出入不会报错，只会表现成
「某类消息播出来少个信息 / 用了错的 TTS 配置」，insert_index 那次就是这么来的。
"""


def build(config, type, username, content, tts_type=None, **extra):
    """按约定形状拼一条合成消息。

    Args:
        config (Config): 配置对象
        type (str): 消息类型（comment / gift / entrance / abnormal_alarm ...）
        username (str): 显示出来的用户名
        content (str): 要合成/播放的内容
        tts_type (str): 覆盖默认的 TTS 配置段，助播用自己的那套
        **extra: 该类型特有的字段（file_path / gift_info / insert_index ...）

    Returns:
        dict: 合成消息
    """

    if tts_type is None:
        tts_type = config.get("audio_synthesis_type")

    message = {
        "type": type,
        "tts_type": tts_type,
        "data": config.get(tts_type),
        "config": config.get("filter"),
        "username": username,
        "content": content,
    }
    message.update(extra)

    return message


def build_playback(message, voice_path):
    """已经合成好的音频，直接排队播放，不再走 TTS（tts_type 固定 none）。

    Args:
        message (dict): 上游消息，插入位置和正文都从它取
        voice_path (str): 要播的音频文件路径

    Returns:
        dict: 播放队列条目
    """

    data_json = {
        "type": message["type"],
        "tts_type": "none",
        "voice_path": voice_path,
        "content": message["content"],
    }

    if "insert_index" in message:
        data_json["insert_index"] = message["insert_index"]

    return data_json
