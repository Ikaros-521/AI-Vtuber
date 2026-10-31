"""危险操作的二次确认框。

NiceGUI 3 移除了 1.x 的 ui.confirm，只能用 ui.dialog 自建。
对话框本身是个元素，关闭只是隐藏而不是销毁，所以全站只建一次、反复复用；
在事件回调里 new 对话框会留下散落的 DOM 片段，别那么做。
"""

from typing import Callable, Optional

from nicegui import ui


# 删除一组配置的统一说明：删除只改内存里的配置字典和页面控件，不落盘；
# 收起之后有 5 秒撤销窗口，超时或点了保存就回不去了——这句要跟 undo.SECONDS 对得上。
GROUP_DETAIL = (
    "删除会先把这一组从页面上收起，点「保存配置」才写进配置文件；"
    "收起后 5 秒内可在页面底部撤销，超时或保存之后就回不去了。"
)
FILE_DETAIL = "这个文件是磁盘上的真实文件，删除后不可恢复。"


class ConfirmBox:
    """一个「取消 / 确认」对话框，供全站复用。"""

    def __init__(self) -> None:
        self.dialog = None
        self._action: Optional[Callable[[], None]] = None
        self._title = None
        self._detail = None

    def build(self) -> None:
        """在页面构建期调用一次。"""
        dialog = ui.dialog()
        self.dialog = dialog
        with dialog, ui.card().style("width:460px;max-width:92vw;padding:16px;"):
            self._title = ui.label("").style("font-size:15px;font-weight:600;")
            self._detail = ui.label("").style("font-size:13px;color:#4b5563;margin-top:6px;")
            with ui.row().style("justify-content:flex-end;width:100%;margin-top:14px;"):
                ui.button("取消", on_click=self._cancel).props("flat no-caps")
                # 确认键不抢焦点，避免用户习惯性回车/空格直接执行危险操作
                ui.button("确认", color="negative", on_click=self._accept).props("no-caps")

    def ask(self, title: str, action: Callable[[], None], detail: str = "") -> None:
        """弹出确认框，用户点「确认」才执行 action。"""
        if self.dialog is None:
            raise RuntimeError("确认框还没 build() 就被调用了：请在 webui.py 建好页面后再 ask")
        self._title.set_text(title)
        self._detail.set_text(detail)
        self._detail.set_visibility(bool(detail))
        self._action = action
        self.dialog.open()

    def _accept(self) -> None:
        action, self._action = self._action, None
        self.dialog.close()
        if action:
            action()

    def _cancel(self) -> None:
        self._action = None
        self.dialog.close()


confirm = ConfirmBox()


def delete_button(label: str, on_click: Callable[[], None]):
    """删除类按钮的统一出口：警示色 + 垃圾桶图标（走查 audit-18「危险与日常同形同色」）。

    危险色只能走调色板 `color='negative'`——NiceGUI 给每个按钮挂了 Quasar 的 text-primary，
    那是条 !important 规则，`.style('color:#dc2626')` 压不过它。
    """
    return ui.button(label, on_click=on_click, color="negative", icon="delete").props("no-caps")


def confirm_delete_file(path, action: Callable[[], None]) -> None:
    """删除磁盘文件：文案里必须带上具体路径，用户才知道删的是哪个。"""
    confirm.ask("确认删除这个音频文件？", action, f"{path}\n{FILE_DETAIL}")
