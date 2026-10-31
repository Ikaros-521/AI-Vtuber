"""时段问候语文本：定时任务与闲时任务共用。

原先同一段时段映射在 main.py 里复制粘贴了 3 处（schedule_task 与
idle_time_task.do_task 的文案/弹幕模式），任何调整都要改三遍。
"""


def time_period_text(hour: int, minute: int) -> str:
    """把北京时间（时、分）转换为"凌晨X点Y分"式的时段描述。

    hour 取值 0-23；分支边界与原实现逐条一致。
    """
    if 0 <= hour < 6:
        return f"凌晨{hour}点{minute}分"
    if 6 <= hour < 9:
        return f"早晨{hour}点{minute}分"
    if 9 <= hour < 12:
        return f"上午{hour}点{minute}分"
    if hour == 12:
        return f"中午{hour}点{minute}分"
    if 13 <= hour < 18:
        return f"下午{hour - 12}点{minute}分"
    if 18 <= hour < 20:
        return f"傍晚{hour - 12}点{minute}分"
    if 20 <= hour < 24:
        return f"晚上{hour - 12}点{minute}分"
    return f"{hour}点{minute}分"
