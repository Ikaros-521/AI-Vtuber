"""聊天记录面板：/callback 接口与聊天页共用。"""
from collections import deque

from nicegui import Client, ui

MAX_MESSAGES = 100


class ChatLog:
    """聊天记录面板。

    nicegui 3 每来一个浏览器连接就把 webui.py 重跑一遍，页面组件树是每个连接各自一份的，
    所以面板按连接逐个登记：只记最后挂载的那个，先打开的页面就再也收不到消息；
    刷新后的页面拿不到历史，看起来像「一条弹幕都没显示」。
    """

    def __init__(self):
        self.scroll_areas = []
        self.messages = deque(maxlen=MAX_MESSAGES)

    def mount(self, scroll_area):
        self.scroll_areas = self._live() + [scroll_area]
        for message in self.messages:
            self._append(scroll_area, message)
        scroll_area.scroll_to(percent=1, duration=0.2)

    def add(self, data_json):
        if data_json.get("type") != "llm":
            return

        data = data_json["data"]
        is_question = data["content_type"] == "question"
        message = {
            "content": data["content"],
            "name": data["username"] if is_question else data["type"],
            "stamp": data["timestamp"],
            "avatar": "https://robohash.org/ui" if is_question else "http://127.0.0.1:8081/favicon.ico",
        }
        # 先入历史：一个页面都没打开时收到的弹幕，等页面打开后还能看见
        self.messages.append(message)

        self.scroll_areas = self._live()
        for scroll_area in self.scroll_areas:
            self._append(scroll_area, message)
            scroll_area.scroll_to(percent=1, duration=0.2)

    def _append(self, scroll_area, message):
        with scroll_area:
            ui.chat_message(message["content"], name=message["name"],
                            stamp=message["stamp"], avatar=message["avatar"])

        children = list(scroll_area)
        if len(children) > MAX_MESSAGES:
            scroll_area.remove(children[0])

    def _live(self):
        # 连接断开超过重连宽限后 nicegui 会删掉 client，往它那棵树上加元素只是白加，
        # 而且每刷新一次页面就多一棵，必须收掉
        live = []
        for scroll_area in self.scroll_areas:
            try:
                client = scroll_area.client
            except RuntimeError:
                continue
            if not client.is_deleted and client.id in Client.instances:
                live.append(scroll_area)
        return live


chat_log = ChatLog()
