import json
import threading
from pathlib import Path


class Config:
    """进程内配置访问器（按解析后的文件路径单例）。

    设计约定：
    - 同一配置文件在进程内只有一个实例，作为该文件唯一的配置视图（单一事实来源）；
    - 磁盘配置变更后由调用方显式 reload() 刷新；读取方（get/__getitem__）无锁，
      拿到的始终是某一时刻的完整快照引用；
    - get(*keys) 保持历史语义：按层级链式取值，任意一级缺失即返回 None。

    历史行为说明：老实现每次实例化都会重读文件（类上"单例"注释从未生效），
    因此原先依靠"重新实例化"来刷新配置的调用点，现均改为显式 reload()。
    """

    _instances = {}
    _class_lock = threading.Lock()

    def __new__(cls, config_file="config.json"):
        key = str(Path(config_file).resolve())
        with cls._class_lock:
            inst = cls._instances.get(key)
            if inst is None:
                inst = super().__new__(cls)
                cls._instances[key] = inst
            return inst

    def __init__(self, config_file="config.json"):
        key = str(Path(config_file).resolve())
        # __new__ 返回既有实例时 __init__ 会再次执行，必须保持幂等
        if getattr(self, "_config_path", None) == key and getattr(self, "config", None) is not None:
            return
        self._config_path = key
        try:
            self.reload()
        except Exception:
            # 初始化失败时不能把残缺实例留在注册表里，否则后续实例化拿到坏对象
            with Config._class_lock:
                if Config._instances.get(key) is self:
                    del Config._instances[key]
            raise

    def reload(self) -> None:
        """从磁盘重新读取配置文件，原子替换内部视图。"""
        with open(self._config_path, encoding="utf-8") as f:
            # 直接整体替换引用：并发读取方要么看到旧快照要么看到新快照，不会读到半份
            self.config = json.load(f)

    def __getitem__(self, key):
        return self.config.get(key)

    def get(self, *keys):
        result = self.config
        for key in keys:
            result = result.get(key, None)
            if result is None:
                break
        return result
