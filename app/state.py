"""进程级运行状态：拆分自 main.py 的模块级全局变量。"""

from luna.common.helpers import Common
from luna.infra.config import Config


class AppState:
    """main 进程的共享运行上下文。

    原先散落在 main.py 模块作用域的 config/common/my_handle/platform 等
    全局变量收拢到这里，由 main.py 构造一次、显式传递给各子模块：
    - 消除隐式全局依赖（此前 platform 等只在 __main__ 赋值，import main 即 NameError）
    - 让各子模块可独立测试（构造一个 AppState 或其替身即可）

    说明：config 是 Config 按路径单例，state.config 与 My_handle 内部
    持有的是同一实例，任何一方 reload() 全局可见。
    """

    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = Config(config_path)
        self.common = Common()
        self.platform = self.config.get("platform")
        self.my_handle = None

        # 定时任务调度线程句柄；dy 平台的监听器会 join 它保持阻塞
        self.schedule_thread = None
