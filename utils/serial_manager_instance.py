from utils.serial_manager import SerialManager


class SingletonSerialManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SerialManager()
        return cls._instance


# 使用一个函数返回单例实例
def get_serial_manager():
    return SingletonSerialManager.get_instance()
