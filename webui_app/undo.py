"""删除后的 5 秒撤销托盘（走查 audit-7 后半）。

`ui.notify` 在 NiceGUI 3 没有 `actions=`，撤销入口没法挂在 toast 上，只能自己摆一条：
托盘在页面构建期建好、平时隐藏，删除时填文案 + 显示 + 倒计时；在事件回调里新建
`ui.page_sticky` 不会落进布局，所以不能按需建（同 confirm 对话框的理由）。

和 ConfirmBox 一样是全站单例：NiceGUI 每来一个标签页就把页面重跑一遍，后建的那份会
顶掉先建的，多标签页同时操作时撤销只会作用在最后打开的那个页面上。
"""
import time
from typing import Callable, Optional

from nicegui import ui

SECONDS = 5.0
TICK = 0.5

TRAY_CSS = 'width:100%;justify-content:center;align-items:center;pointer-events:none;'
# 只有药丸本身吃点击：position='bottom' 的 QPageSticky 默认铺满整行，整条带不设
# pointer-events:none 的话，底部这一横条会把压在下面的控件全挡住
PILL_CSS = ('gap:10px;padding:7px 12px;border-radius:10px;background:#1f2937;'
            'box-shadow:0 2px 10px rgba(0,0,0,0.30);pointer-events:auto;')
LABEL_CSS = 'font-size:13px;color:#f9fafb;'
# 按钮内联色必须带 !important：NiceGUI 给每个 ui.button 挂了 Quasar 的 text-primary
BUTTON_CSS = 'font-size:13px;color:#fbbf24 !important;'


class UndoTray:
    def __init__(self):
        self.sticky = None
        self.label = None
        self._restore: Optional[Callable[[], None]] = None
        self._deadline = 0.0

    def build(self):
        # 放底部居中：顶部是 notify 的位置（删除失败、保存成功都会往那儿弹），右下角是状态
        # 徽标与操作条，只有底部中间空着。注意 QPageSticky 只认 top/bottom/left/right 与四角，
        # 写 'bottom-center' 会被 Quasar 忽略、整条掉进正常流里跑到屏幕外面。
        self.sticky = ui.page_sticky(position='bottom', x_offset=0, y_offset=12).style('pointer-events:none;')
        with self.sticky, ui.row().style(TRAY_CSS):
            with ui.row().style(PILL_CSS):
                self.label = ui.label('').style(LABEL_CSS)
                ui.button('撤销', on_click=self.restore).props('flat no-caps dense size=sm').style(BUTTON_CSS)
        self.sticky.set_visibility(False)
        ui.timer(TICK, self._tick)
        return self

    def offer(self, message: str, restore: Callable[[], None]) -> None:
        """摆出「刚删了什么、还能撤销」。再删一次就只留最后一次的撤销。"""
        self.label.set_text(f'{message} · {int(SECONDS)} 秒内可撤销')
        self._restore = restore
        self._deadline = time.monotonic() + SECONDS
        self.sticky.set_visibility(True)

    def restore(self) -> None:
        action, self._restore = self._restore, None
        self._hide()
        if action:
            action()

    def forget(self) -> None:
        """配置已经写盘，撤销窗口关掉：再恢复回去只会和盘上的内容对不上。"""
        self._restore = None
        self._hide()

    def _tick(self) -> None:
        if self._restore and time.monotonic() > self._deadline:
            self._restore = None
            self._hide()

    def _hide(self) -> None:
        self.sticky.set_visibility(False)


undo = UndoTray()
