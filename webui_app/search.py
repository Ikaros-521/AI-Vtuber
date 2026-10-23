"""全局搜索配置项。

近 900 个输入控件散在 29 个页面上——找不到控件比配错控件更常见。
索引不另存一份清单，直接从元素树现建，所以运行期「增加配置组」新加的控件也搜得到。
定位与高亮走 webui_app/fields.py，和总览的「去配置」、未保存清单共用同一套。
"""
from nicegui import context, ui

from webui_app.dirty_guard import INPUT_TYPES
from webui_app.fields import build_index, jump_to

MAX_HITS = 12

INK = '#111827'
INK_MUT = '#4b5563'


class ConfigSearch:
    """一个搜索对话框 + Ctrl/Cmd+K 唤起。索引每次打开时重建，不养陈旧数据。"""

    def __init__(self, select_tab, accent):
        self._select_tab = select_tab
        self._accent = accent.rstrip(';')
        self._index = []
        self.dialog = None
        self._results = None
        self._summary = None
        self._input = None

    def build(self):
        dialog = ui.dialog()
        self.dialog = dialog
        with dialog, ui.card().style('width:100%;max-width:640px;padding:14px;'):
            self._input = ui.input(placeholder='搜配置项，例如 保留条数', on_change=self._paint).props(
                'autofocus outlined dense clearable').classes('w-full')
            self._summary = ui.label('').style(f'font-size:12px;color:{INK_MUT};margin:6px 0 2px;')
            self._results = ui.column().style('width:100%;gap:2px;max-height:50vh;overflow-y:auto;')
        ui.keyboard(self._on_key)

    def open(self):
        self._index = build_index()
        # 索引是重建的，上一轮的关键词留着只会误导，所以每次打开都从空查询开始
        self._input.set_value('')
        self._paint(None)
        self.dialog.open()

    def _on_key(self, e):
        if not e.action.keydown:
            return
        if e.key not in ('KeyK', 'k'):
            return
        if e.modifiers.ctrl or e.modifiers.meta:
            self.open()

    def _hits(self, query):
        q = (query or '').strip().lower()
        if not q:
            return []
        return [row for row in self._index if q in row[0].lower() or q in row[1].lower()]

    def _paint(self, e):
        query = ((e.value if e is not None else self._input.value) or '').strip()
        self._results.clear()
        if not query:
            self._summary.set_text(f'共 {len(self._index)} 个配置项，输入关键词开始找')
            return
        hits = self._hits(query)
        self._summary.set_text(f'命中 {len(hits)} 项' + (f'（只显示前 {MAX_HITS} 项）' if len(hits) > MAX_HITS else ''))
        with self._results:
            if not hits:
                with ui.row().style('align-items:center;gap:10px;padding:18px 6px;'):
                    ui.icon('search_off').style(f'font-size:26px;color:{INK_MUT};')
                    ui.label(f'没有匹配「{query}」的配置项，换个更短的关键词试试').style(
                        f'font-size:13px;color:{INK_MUT};')
                return
            for row in hits[:MAX_HITS]:
                name, section, tab = row[0], row[1], row[2]
                with ui.button(on_click=lambda r=row: self._jump(r)).props(
                        'flat no-caps align=left dense').classes('w-full'):
                    with ui.column().style('gap:0;align-items:flex-start;'):
                        ui.label(name).style(f'font-size:14px;color:{INK};font-weight:500;')
                        where = ' · '.join(x for x in (tab, section) if x)
                        if where:
                            ui.label(where).style(f'font-size:12px;color:{INK_MUT};')

    def _jump(self, row):
        name, _section, tab, ordinal, expansion = row[0], row[1], row[2], row[3], row[4]
        self.dialog.close()
        jump_to(name, ordinal, self._accent, self._select_tab, tab, expansion)
