"""聊天记录存储：/callback 接口与前端聊天页共用。

v2 版（webui_app/chat_log.py）要管 NiceGUI 每个连接的组件树，v3 只存数据，
前端自己轮询拉取。
"""

from collections import deque

MAX_MESSAGES = 100


class ChatLog:
    def __init__(self):
        self.messages = deque(maxlen=MAX_MESSAGES)
        # 单调递增序号，前端用 after= 增量拉取
        self._seq = 0

    def add(self, data_json):
        if data_json.get("type") != "llm":
            return
        data = data_json["data"]
        is_question = data["content_type"] == "question"
        self._seq += 1
        self.messages.append(
            {
                "seq": self._seq,
                "content": data["content"],
                "name": data["username"] if is_question else data["type"],
                "stamp": data["timestamp"],
                "mine": is_question,
            }
        )

    def since(self, after=0):
        return [m for m in self.messages if m["seq"] > after]


chat_log = ChatLog()
