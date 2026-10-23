"""未保存改动守卫。

这版 webui 的语义是「点保存才把所有控件值写盘」，改到一半刷新或关标签页会静默丢光，
而全站原本没有任何提示（走查 audit-2 blocker）。

脏状态不去逐个控件手写监听——输入类控件有 850 多个，分散在 16 个页面模块里就地创建，
往十几层函数签名上串一个回调不划算——而是在页面构建完成后遍历元素树，统一给这些控件
挂 on_value_change；运行期新加的组（增加配置组）靠定时器补挂。
"""
from nicegui import app, context, ui

# 只有真会改配置的控件算脏；ui.expansion / ui.tabs 也是 ValueElement，
# 但展开面板、切页不该被当成「有未保存修改」。
INPUT_TYPES = (ui.input, ui.textarea, ui.select, ui.switch, ui.checkbox)

# 浏览器侧的拦截开关：Chrome 只在用户已经和页面交互过之后才允许 beforeunload 弹窗，
# 而「改过控件」本身就意味着交互过，所以这里不需要额外兜底。
HEAD_SCRIPT = """
<script>
window.__unsavedGuard = function (count) {
    window.onbeforeunload = count > 0
        ? function (ev) { ev.returnValue = '有未保存的配置修改'; return ev.returnValue; }
        : null;
};
</script>
"""


class DirtyGuard:
    """数出改过但还没保存的控件，脏时拦住浏览器关闭/刷新。"""

    def __init__(self) -> None:
        self._watched = set()
        self._dirty = set()
        self._sent = None
        self._label = None
        self._status = None

    def install(self) -> None:
        """注入页面脚本并在浏览器连上时补发一次当前脏状态。"""
        ui.add_head_html(HEAD_SCRIPT)
        app.on_connect(self._on_connect)

    def bind_label(self, label) -> None:
        """把角标元素交给守卫，由它负责文案与配色。"""
        self._label = label
        self._paint_label()

    def bind_status(self, label) -> None:
        """总览页那行完整句子，与角标同步刷新。"""
        self._status = label
        self._paint_label()

    def count(self) -> int:
        return len(self._dirty)

    def watch(self, force: bool = False) -> None:
        """给还没盯过的输入控件挂上变更记录，可重复调用。"""
        client = context.client
        if not force and not client.has_socket_connection:
            return
        for element in list(client.elements.values()):
            if not isinstance(element, INPUT_TYPES) or element.id in self._watched:
                continue
            self._watched.add(element.id)
            element.on_value_change(lambda e: self.note_change(e.sender.id))

    def note_change(self, element_id: int) -> None:
        self._dirty.add(element_id)
        self.sync()

    def mark_saved(self) -> None:
        """保存成功后调用：清零脏集合，重新允许直接关页面。"""
        self._dirty.clear()
        self.sync()

    def sync(self) -> None:
        count = len(self._dirty)
        if self._sent != count and context.client.has_socket_connection:
            self._sent = count
            context.client.run_javascript(f'window.__unsavedGuard({count})')
        self._paint_label()

    def _on_connect(self, client) -> None:
        # 第二个标签页连进来时，页面脚本是全新的，得把当前状态补发一次
        count = len(self._dirty)
        self._sent = count
        client.run_javascript(f'window.__unsavedGuard({count})')
        self._paint_label()

    def _paint_label(self) -> None:
        count = len(self._dirty)
        if self._label is not None:
            self._label.set_text(f'● {count} 项未保存' if count else '● 配置已保存')
            self._label.style('color:' + ('#b45309' if count else '#16a34a'))
        if self._status is not None:
            self._status.set_text(f'当前有 {count} 项改动还没写进配置文件' if count else '所有改动都已保存')
            self._status.style('color:' + ('#b45309' if count else '#4b5563'))
