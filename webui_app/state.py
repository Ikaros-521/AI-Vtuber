"""WebUI 与各页面共享的运行态。

页面迁出后不再通过模块级 global 互相读写，统一走这里的单例。
"""


class AppState:
    def __init__(self):
        # main.py 子进程是否在运行（一键运行/停止）
        self.running_flag = False
        # 图像识别页的循环截图定时器
        self.loop_screenshot_timer = None
        self.loop_screenshot_timer_running = False


state = AppState()
