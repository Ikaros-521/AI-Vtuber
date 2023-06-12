import json

class Config:
    _instance = None
    config = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Config, cls).__new__(cls)  # 不再传递 *args, **kwargs
        return cls._instance

    def __init__(self, config_file):
        if self.config is None:
            with open(config_file, 'r', encoding="utf-8") as f:
                self.config = json.load(f)

    def get(self, *keys):
        result = self.config
        for key in keys:
            result = result.get(key, None)
            if result is None:
                break
        return result

    def update(self, json):
        if len(json) > 0:
            print(json)
            self.config.update(json)
