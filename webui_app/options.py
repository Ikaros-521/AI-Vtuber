"""WebUI 下拉选项表。"""

CHAT_TYPE_OPTIONS = {
    "none": "不启用",
    "reread": "复读机",
    "chatgpt": "ChatGPT",
    "langchain_chatchat": "langchain_chatchat",
    "zhipu": "智谱AI",
    "gemini": "Gemini",
    "tongyi": "通义千问/阿里云百炼",
    "my_wenxinworkshop": "千帆大模型",
    "anythingllm": "AnythingLLM",
    "dify": "Dify",
    "volcengine": "火山引擎",
    "custom_llm": "自定义LLM",
}

PLATFORM_OPTIONS = {
    "talk": "聊天模式",
    "bilibili": "哔哩哔哩",
    "bilibili2": "哔哩哔哩2",
    "dy": "抖音",
    "dy2": "抖音2",
    "ks": "快手",
    "live_monitor_assistant": "直播弹幕监听助手",
    "wxlive": "微信视频号",
    "youtube": "YouTube",
    "twitch": "twitch",
    "tiktok": "tiktok",
}

# 快手2/拼多多/斗鱼/1688/淘宝的弹幕都是「直播弹幕监听助手」用 websocket 推给本机的，
# 走的是同一个监听器，具体是哪个平台由助手那边决定，所以下拉里合成了一项。
# 这几个旧值在 utils/platforms/__init__.py 的注册表里仍然认，老 config 不用手改。
LEGACY_LIVE_MONITOR_PLATFORMS = {
    "ks2": "快手2（并入直播弹幕监听助手）",
    "pdd": "拼多多（并入直播弹幕监听助手）",
    "douyu": "斗鱼（并入直播弹幕监听助手）",
    "1688": "1688（并入直播弹幕监听助手）",
    "taobao": "淘宝（并入直播弹幕监听助手）",
}

# 走这个助手的所有平台标识，包含统一项自己
LIVE_MONITOR_PLATFORM_KEYS = ["live_monitor_assistant", *LEGACY_LIVE_MONITOR_PLATFORMS]


def platform_options(current):
    """老 config 里存的还是旧平台名时，把它显示回下拉里。

    不收这一步的话，选了「拼多多」的老用户打开页面看到的是空白平台，
    只要点一次保存，自己的平台配置就被改成别的了。
    """
    options = dict(PLATFORM_OPTIONS)
    if current in LEGACY_LIVE_MONITOR_PLATFORMS:
        options[current] = LEGACY_LIVE_MONITOR_PLATFORMS[current]
    return options


VISUAL_BODY_OPTIONS = {
    "其他": "其他（外置）",
    "metahuman_stream": "metahuman_stream",
    "EasyAIVtuber": "EasyAIVtuber",
    "digital_human_video_player": "数字人视频播放器",
    "live2d_TTS_LLM_GPT_SoVITS_Vtuber": "live2d-TTS-LLM-GPT-SoVITS-Vtuber",
    "xuniren": "xuniren",
}
