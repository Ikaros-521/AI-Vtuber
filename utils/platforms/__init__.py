"""直播平台弹幕监听的注册表。

各平台模块统一暴露 ``start_listen(config, common, my_handle, platform)``，
这里只保存“平台标识 -> 模块”的映射，调用时才按需导入，
避免启动时把没装的平台 SDK 一并拉起来。
"""

import importlib

# 平台标识 -> 承载 start_listen 的模块
PLATFORM_LISTENERS = {
    "bilibili": "utils.platforms.bilibili",
    "bilibili2": "utils.platforms.bilibili2",
    "dy": "utils.platforms.dy",
    "dy2": "utils.platforms.dy2",
    "ks": "utils.platforms.ks",
    "ks2": "utils.platforms.lx_live_monitor_assistant",
    "pdd": "utils.platforms.lx_live_monitor_assistant",
    "douyu": "utils.platforms.lx_live_monitor_assistant",
    "1688": "utils.platforms.lx_live_monitor_assistant",
    "taobao": "utils.platforms.lx_live_monitor_assistant",
    "tiktok": "utils.platforms.tiktok",
    "twitch": "utils.platforms.twitch",
    "wxlive": "utils.platforms.wxlive",
    "youtube": "utils.platforms.youtube",
    "hntv": "utils.platforms.hntv",
    "ordinaryroad_barrage_fly": "utils.platforms.ordinaryroad_barrage_fly",
}

# 这些平台的 start_listen 额外接收定时任务线程（dy 靠它阻塞）
PLATFORMS_WITH_SCHEDULE_THREAD = {"dy"}


def start_platform_listen(platform, config, common, my_handle, schedule_thread=None):
    """按平台分发到对应模块的 start_listen。

    成功返回 (True, "")；平台未登记或依赖缺失返回 (False, 原因)。
    """
    module_name = PLATFORM_LISTENERS.get(platform)
    if module_name is None:
        return False, f"未知平台：{platform}，请检查 config.json 的 platform 配置"

    try:
        listen = importlib.import_module(module_name).start_listen
    except ImportError as e:
        return False, f"平台 {platform} 缺少依赖：{e}，请按 requirements/platform.txt 安装"

    if platform in PLATFORMS_WITH_SCHEDULE_THREAD:
        listen(config, common, my_handle, platform, schedule_thread)
    else:
        listen(config, common, my_handle, platform)
    return True, ""
