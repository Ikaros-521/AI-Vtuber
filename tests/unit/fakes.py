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

    def is_playback_busy(self):
        self.calls.append(("is_playback_busy", ()))
        return False

    def is_queue_less_or_greater_than(self, type, less, greater):
        self.calls.append(("is_queue_less_or_greater_than", (type, less, greater)))
        return True

    def get_audio_info(self):
        self.calls.append(("get_audio_info", ()))
        return {"message_queue": 0}

    def audio_synthesis(self, message):
        return self._guard("audio_synthesis", message)

    def get_dir_audios_filename(self, path, type=1):
        self.calls.append(("get_dir_audios_filename", (path, type)))
        return []

    def search_files(self, path, name):
        self.calls.append(("search_files", (path, name)))
        return []


class FakeSender:
    """替代 Common 里的网络调用，记录发出的请求。

    形参名必须和 utils/common.py 的 send_request 一一对上：生产代码里有几处是用
    method=/json_data= 关键字调的，名字对不上就会被吞进 **kwargs，
    断言读到的是 None 而不是真实数据。
    """

    def __init__(self, reply=None):
        self.requests = []
        self.reply = reply if reply is not None else {"code": 200}

    def send_request(self, url, method="GET", json_data=None, resp_data_type="json", timeout=60, proxy=None):
        self.requests.append((url, method, json_data))
        return self.reply

    def get_bj_time(self, type=0):
        return "2026-01-01 00:00:00"


class FakeAlarmCommon(FakeSender):
    """异常报警用的 Common 替身：只提供列目录和取文件名。"""

    def __init__(self, path_list=()):
        super().__init__()
        self.path_list = list(path_list)

    def get_all_file_paths(self, folder_path):
        return list(self.path_list)

    def extract_filename(self, file_path, with_extension=False):
        name = file_path.rsplit("/", 1)[-1]
        return name if with_extension else name.rsplit(".", 1)[0]
