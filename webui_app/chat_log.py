"""聊天记录面板：/callback 接口与聊天页共用。"""
from nicegui import ui

MAX_MESSAGES = 100


class ChatLog:
    def __init__(self):
        self.scroll_area = None
        self.message_num = 0

    def mount(self, scroll_area):
        self.scroll_area = scroll_area

    def add(self, data_json):
        if self.scroll_area is None or data_json.get("type") != "llm":
            return

        data = data_json["data"]
        is_question = data["content_type"] == "question"
        name = data["username"] if is_question else data["type"]
        avatar = "https://robohash.org/ui" if is_question else "http://127.0.0.1:8081/favicon.ico"

        with self.scroll_area:
            ui.chat_message(
                data["content"],
                name=name,
                stamp=data["timestamp"],
                avatar=avatar,
            )
            self.message_num += 1

        if self.message_num > MAX_MESSAGES:
            self.scroll_area.remove(0)

        self.scroll_area.scroll_to(percent=1, duration=0.2)


chat_log = ChatLog()
