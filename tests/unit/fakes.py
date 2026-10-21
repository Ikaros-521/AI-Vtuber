"""测试替身：只实现被测代码用到的那部分接口。"""


class FakeConfig:
    """与 utils.config.Config 相同的嵌套取值语义，但不读磁盘。"""

    def __init__(self, data):
        self.config = data

    def get(self, *keys):
        result = self.config
        for key in keys:
            if not isinstance(result, dict):
                return None
            result = result.get(key, None)
            if result is None:
                break
        return result

    def __getitem__(self, key):
        return self.config.get(key)


class FakeWidget:
    """替代 nicegui 输入控件，处理函数只用 .value。"""

    def __init__(self, value):
        self.value = value


class FakeAudio:
    """记录调用，便于断言委托关系。"""

    def __init__(self, raises=False):
        self.calls = []
        self.raises = raises

    def _guard(self, name, *args):
        self.calls.append((name, args))
        if self.raises:
            raise RuntimeError("audio down")
        return True

    def clear_queue(self, type):
        return self._guard("clear_queue", type)

    def stop_audio(self, type, mixer_normal, mixer_copywriting):
        return self._guard("stop_audio", type, mixer_normal, mixer_copywriting)

    def is_audio_queue_empty(self):
        self.calls.append(("is_audio_queue_empty", ()))
        return False

    def is_queue_less_or_greater_than(self, type, less, greater):
        self.calls.append(("is_queue_less_or_greater_than", (type, less, greater)))
        return True

    def get_audio_info(self):
        self.calls.append(("get_audio_info", ()))
        return {"message_queue": 0}


class FakeSender:
    """替代 Common 里的网络调用，记录发出的请求。"""

    def __init__(self, reply=None):
        self.requests = []
        self.reply = reply if reply is not None else {"code": 200}

    def send_request(self, url, type, data_json=None, **kwargs):
        self.requests.append((url, type, data_json))
        return self.reply

    def get_bj_time(self, type=0):
        return "2026-01-01 00:00:00"
