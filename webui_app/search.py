"""全局搜索配置项。

近 900 个输入控件散在 29 个页面上——找不到控件比配错控件更常见。
索引不另存一份清单，直接从元素树现建，所以运行期「增加配置组」新加的控件也搜得到。

定位用的是「标签文本 + 同名第几个」而不是 DOM id：NiceGUI 3.18 不给普通元素渲染 id
（props('id=...') 只有 select/switch 会落到某个内层节点上，input 干脆没有），
而标签文本是这份配置页本来就要求唯一的。
"""
import json

from nicegui import context, ui
from nicegui.elements.card import Card
from nicegui.elements.expansion import Expansion
from nicegui.elements.label import Label
from nicegui.elements.tabs import TabPanel

from webui_app.dirty_guard import INPUT_TYPES

MAX_HITS = 12

INK = '#111827'
INK_MUT = '#4b5563'

# Quasar 的 QTabPanels 一次只把当前那一页挂在 DOM 上（实测 .q-tab-panel 只有 1 个），
# 所以定位不靠面板序号：切完页就在唯一可见的面板里找。
# 输入类的标签在 .q-field__label；开关/勾选框没有这个节点，标签就是它自己的 innerText。
# 开关的原生 input 是隐藏的，focus 不上去，所以一律给目标描一圈临时高亮；
# 切页时 keep-alive 会把面板重新挂一次、内联样式会被冲掉，所以高亮补打三次再统一擦掉。
# 用 %-格式而不是 str.format：这段脚本里全是花括号，format 要逐个转义反而容易错
JS_LOCATE = """(function () {
    const want = %s, ord = %d;
    let tries = 0;
    window.__searchHit = false;
    const find = () => {
        const panel = [...document.querySelectorAll('.q-tab-panel')]
            .find(e => getComputedStyle(e).display !== 'none');
        if (!panel) return null;
        const hit = [...panel.querySelectorAll('.q-field,.q-toggle,.q-checkbox')].filter(e => {
            const l = e.querySelector('.q-field__label');
            return l ? l.textContent.trim() === want : (e.innerText || '').trim() === want;
        });
        return hit.length > ord ? hit[ord] : null;
    };
    const mark = () => {
        const f = find();
        if (!f) return;
        window.__searchHit = true;
        f.scrollIntoView({block: 'center'});
        const i = f.querySelector('input,textarea');
        if (i && i.offsetParent) i.focus({preventScroll: true});
        f.style.outline = '2px solid %s';
        f.style.outlineOffset = '2px';
    };
    const t = setInterval(function () {
        tries++;
        if (find()) {
            clearInterval(t);
            mark();
            setTimeout(mark, 600);
            setTimeout(mark, 1400);
            setTimeout(function () {
                [...document.querySelectorAll('.q-field,.q-toggle,.q-checkbox')]
                    .forEach(e => { e.style.outline = ''; e.style.outlineOffset = ''; });
            }, 2800);
        } else if (tries > 30) {
            clearInterval(t);
        }
    }, 100);
})()"""


def _locate(element):
    """这个控件在哪个 tab、哪个分区、哪个折叠区里。"""
    tab = section = ''
    expansion = None
    for a in element.ancestors():
        if isinstance(a, TabPanel):
            if not tab:
                tab = str(a._props.get('name') or '')
            continue
        if expansion is None and isinstance(a, Expansion):
            expansion = a
            section = str(a._props.get('label') or '')
        elif not section and isinstance(a, Card):
            for child in a:
                if isinstance(child, Label) and (child.text or '').strip():
                    section = child.text.strip()
                    break
    return tab, section, expansion


def _name_of(element):
    """控件显示名：ui.input / textarea / select 存在 label 上，ui.switch / checkbox 存在 text 上。

    这两个不是同一个属性（Switch 压根没有 label 属性），只读 label 会把 178 个开关
    和 8 个勾选框整个漏出索引。
    """
    for attr in ('label', 'text'):
        value = getattr(element, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ''


def build_index():
    """(控件名, 分区, tab 名, 同名第几个, 所在折叠区) 列表。

    同名第几个用来区分「音频存储路径#1/#2」这类重名项，跳过去时取对的那一个。
    """
    rows = []
    seen = {}
    for element in context.client.elements.values():
        if not isinstance(element, INPUT_TYPES):
            continue
        label = _name_of(element)
        if not label:
            continue
        tab, section, expansion = _locate(element)
        ordinal = seen.get((tab, label), 0)
        seen[(tab, label)] = ordinal + 1
        rows.append((label, section, tab, ordinal, expansion))
    rows.sort(key=lambda r: (r[2], r[1], r[0]))
    return rows


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
                name, section, tab, _ord, _expansion = row
                with ui.button(on_click=lambda r=row: self._jump(r)).props(
                        'flat no-caps align=left dense').classes('w-full'):
                    with ui.column().style('gap:0;align-items:flex-start;'):
                        ui.label(name).style(f'font-size:14px;color:{INK};font-weight:500;')
                        where = ' · '.join(x for x in (tab, section) if x)
                        if where:
                            ui.label(where).style(f'font-size:12px;color:{INK_MUT};')

    def _jump(self, row):
        name, _section, tab, ordinal, expansion = row
        self.dialog.close()
        if tab:
            self._select_tab(tab)
        if expansion is not None:
            expansion.open()
        context.client.run_javascript(JS_LOCATE % (json.dumps(name, ensure_ascii=False), ordinal, self._accent))
