"""未保存改动守卫。

这版 webui 的语义是「点保存才把所有控件值写盘」，改到一半刷新或关标签页会静默丢光，
而全站原本没有任何提示（走查 audit-2 blocker）。

脏状态不去逐个控件手写监听——输入类控件有 850 多个，分散在十几个页面模块里就地创建，
往十几层函数签名上串一个回调不划算——而是在页面构建完成后遍历元素树，统一给这些控件
挂 on_value_change；运行期新加的组（增加配置组）靠定时器补挂。

角标还能点开，列出「改了哪些项、现在是什么值」，点某一项跳到那个框（story-2 的验收标准）。
"""
from nicegui import app, context, ui

from webui_app.fields import INPUT_TYPES, field_name, hidden, jump_to_element, locate, value_text

INK = '#111827'
INK_MUT = '#4b5563'

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
        self._elements = {}
        self._select_tab = None
        self._accent = '#3e78bd'
        self.dialog = None
        self._list = None
        self._hint = None

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

    def bind_nav(self, select_tab, accent) -> None:
        """未保存清单要点开某一项就能跳过去，所以需要切页回调与主题色。"""
        self._select_tab = select_tab
        self._accent = accent.rstrip(';')

    def build_list(self) -> None:
        """未保存清单对话框：全站建一次复用（同 confirm 的理由）。"""
        dialog = ui.dialog()
        self.dialog = dialog
        with dialog, ui.card().style('width:100%;max-width:620px;padding:14px;'):
            self._hint = ui.label('').style(f'font-size:12px;color:{INK_MUT};margin-bottom:6px;')
            self._list = ui.column().style('width:100%;gap:2px;max-height:50vh;overflow-y:auto;')

    def open_list(self) -> None:
        items = self.items()
        self._list.clear()
        self._hint.set_text(f'共 {len(items)} 项改动还没写进配置文件；点某一项跳到那个框'
                            if items else '没有未保存的改动')
        with self._list:
            for label, value, tab, section, element in items:
                with ui.button(on_click=lambda el=element: self._jump_to_field(el)).props(
                        'flat no-caps align=left dense').classes('w-full'):
                    with ui.column().style('gap:0;align-items:flex-start;'):
                        ui.label(f'{label} = {value}').style(f'font-size:14px;color:{INK};')
                        where = ' · '.join(x for x in (tab, section) if x)
                        if where:
                            ui.label(where).style(f'font-size:12px;color:{INK_MUT};')
        self.dialog.open()

    def _jump_to_field(self, element):
        self.dialog.close()
        jump_to_element(element, self._accent, self._select_tab)

    def items(self):
        """(控件名, 当前值, tab, 分区, 控件)，按页面与控件顺序。"""
        rows = []
        for element in self._live():
            label = field_name(element)
            if not label:
                props = getattr(element, '_props', {}) or {}
                label = str(props.get('placeholder') or props.get('hint') or f'未命名配置项#{element.id}').strip()
            tab, section, _expansion = locate(element)
            rows.append((label, value_text(element), tab, section, element))
        rows.sort(key=lambda r: (r[2], r[3], r[0]))
        return rows

    def _live(self):
        """还看得见的那些脏控件：删到一半收起的那一组，它的改动不再算「待保存」。"""
        return [element for element in (self._elements.get(i) for i in self._dirty)
                if element is not None and not element.is_deleted and not hidden(element)]

    def count(self) -> int:
        return len(self.items())

    def watch(self, force: bool = False) -> None:
        """给还没盯过的输入控件挂上变更记录，可重复调用。"""
        client = context.client
        if not force and not client.has_socket_connection:
            return
        for element in list(client.elements.values()):
            if not isinstance(element, INPUT_TYPES) or element.id in self._watched:
                continue
            if getattr(element, 'is_config_field', True) is False:   # 选择器之类的界面控件
                continue
            if not field_name(element) and getattr(element, 'is_config_field', None) is not True:
                continue
            self._watched.add(element.id)
            self._elements[element.id] = element
            element.on_value_change(lambda e: self.note_change(e.sender.id))

    def note_change(self, element_id: int) -> None:
        self._dirty.add(element_id)
        self.sync()

    def mark_saved(self) -> None:
        """保存成功后调用：清零脏集合，重新允许直接关页面。"""
        self._dirty.clear()
        self.sync()

    def sync(self) -> None:
        count = self.count()
        if self._sent != count and context.client.has_socket_connection:
            self._sent = count
            context.client.run_javascript(f'window.__unsavedGuard({count})')
        self._paint_label()

    def _on_connect(self, client) -> None:
        # 第二个标签页连进来时，页面脚本是全新的，得把当前状态补发一次
        count = self.count()
        self._sent = count
        client.run_javascript(f'window.__unsavedGuard({count})')
        self._paint_label()

    def _paint_label(self) -> None:
        count = self.count()
        if self._label is not None:
            self._label.set_text(f'● {count} 项未保存' if count else '● 配置已保存')
            # 角标是 ui.button，NiceGUI 给它挂的 Quasar text-primary 是 !important 规则，
            # 内联色不带 !important 压不过它
            self._label.style('color:' + ('#b45309' if count else '#16a34a') + ' !important;')
        if self._status is not None:
            self._status.set_text(f'当前有 {count} 项改动还没写进配置文件' if count else '所有改动都已保存')
            self._status.style('color:' + ('#b45309' if count else '#4b5563'))
