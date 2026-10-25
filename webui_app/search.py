"""全局搜索配置项。

近 900 个输入控件散在 29 个页面上——找不到控件比配错控件更常见。
索引不另存一份清单，直接从元素树现建，所以运行期「增加配置组」新加的控件也搜得到。
定位与高亮走 webui_app/fields.py，和总览的「去配置」、未保存清单共用同一套。

结果行必须带上「当前值」：全站光叫「API地址」的框就有 24 个，只列名字等于没列。
"""
from nicegui import ui

from webui_app.fields import build_index, jump_to, value_text

MAX_HITS = 12

INK = '#111827'
INK_MUT = '#4b5563'

# ↑/↓ 在结果里移动焦点，Enter 交给浏览器原生触发（VSCode 命令面板就是这么做的）。
# 判"对话框开着"不能靠 offsetParent——对话框是 position:fixed，它恒为 null（实测踩过）。
NAV_SCRIPT = """
<script>
document.addEventListener('keydown', function (e) {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    const card = document.querySelector('.luna-search-card');
    if (!card || card.getBoundingClientRect().height <= 0) return;
    const items = [...card.querySelectorAll('button.q-btn')];
    if (!items.length) return;          // 只命中一条也要能把焦点挪上去（原来要 ≥2，单条结果键盘选不了）
    e.preventDefault();
    let i = items.indexOf(document.activeElement);
    const step = e.key === 'ArrowDown' ? 1 : -1;
    items[((i < 0 ? (step > 0 ? -1 : 0) : i) + step + items.length) % items.length].focus();
}, true);
</script>
"""

# 选中行用「底色 + 内阴影描边」而不是 outline：Quasar 给按钮挂了 .no-outline{outline:0!important}，
# 实测即使自己写 outline:2px solid !important 且选择器确实匹配（b.matches 为真、计算色都进来了），
# 计算值仍是 0px none——不再跟它争，直接换成一定生效的背景色。
FOCUS_CSS = """
<style>
.luna-search-card button.q-btn:focus{background:#e8f0fb !important;
                                     box-shadow:inset 0 0 0 2px #2b5d9b !important;}
</style>
"""


def expansion_name(row):
    """这一行所在折叠区的名字（没有就空串）。"""
    expansion = row[4]
    return str(getattr(expansion, '_props', {}).get('label') or '') if expansion else ''


def norm(text):
    """搜的时候把大小写与 _ - 空格 三种分隔符统一掉。

    配置键写 openai_tts、界面标签写 OpenAI TTS（走查 audit-5 换的中文名），
    用户从 config.json 还是从屏幕上抄，都应该命中同一个东西。
    """
    return (text or '').lower().replace('_', '').replace('-', '').replace(' ', '')


def needles(row):
    """一行里能拿来搜的字符串：控件名、分区、页签、折叠区名。"""
    return [norm(x) for x in (row[0], row[1], row[2], expansion_name(row)) if x]


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
        ui.add_head_html(NAV_SCRIPT)
        ui.add_head_html(FOCUS_CSS)
        with dialog, ui.card().classes('luna-search-card').style(
                'width:100%;max-width:640px;padding:14px;'):
            self._input = ui.input(placeholder='搜配置项，例如 保留条数', on_change=self._paint).props(
                'autofocus outlined dense clearable').classes('w-full')
            # Enter 落在输入框里（还没 ↑↓ 过高亮）时也要能跳：命令面板的规矩是 Enter 选当前项，
            # 没有当前项就选第一条命中
            self._input.on('keydown.enter', self._pick_first)
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
        """名字、分区、页签名、折叠区名都能搜。"""
        q = norm((query or '').strip())
        if not q:
            return []
        rows = [row for row in self._index if any(q in n for n in needles(row))]
        # 名字本身命中的排在前面：搜「gpt_sovits」时 GPT-SoVITS 卡里 11 个字段都按折叠区名命中，
        # 那个开关本身反而沉到显示上限（12 行）之外——实测就是这样翻不到。
        return sorted(rows, key=lambda row: (0 if q in norm(row[0]) else 1, row[2], row[1], row[0]))

    def _paint(self, e):
        query = ((e.value if e is not None else self._input.value) or '').strip()
        self._results.clear()
        if not query:
            self._summary.set_text(f'共 {len(self._index)} 个配置项，输入关键词开始找'
                                   '（↑↓ 选，Enter 跳）')
            return
        hits = self._hits(query)
        more = len(hits) - MAX_HITS
        self._summary.set_text(
            f'命中 {len(hits)} 项' + (f'，只显示前 {MAX_HITS} 项，还有 {more} 项请换个更精确的词' if more > 0 else '')
            + ('；↑↓ 选，Enter 跳' if hits else ''))
        with self._results:
            if not hits:
                with ui.row().style('align-items:center;gap:10px;padding:18px 6px;'):
                    ui.icon('search_off').style(f'font-size:26px;color:{INK_MUT};')
                    ui.label(f'没有匹配「{query}」的配置项，换个更短的关键词试试').style(
                        f'font-size:13px;color:{INK_MUT};')
                return
            for row in hits[:MAX_HITS]:
                name, section, tab, element = row[0], row[1], row[2], row[5]
                where_extra = expansion_name(row)
                with ui.button(on_click=lambda r=row: self._jump(r)).props(
                        'flat no-caps align=left dense').classes('w-full'):
                    with ui.column().style('gap:0;align-items:flex-start;'):
                        with ui.row().classes('items-baseline').style('gap:8px;flex-wrap:wrap;'):
                            ui.label(name).style(f'font-size:14px;color:{INK};font-weight:500;')
                            # 同名控件太多，值才是区分它们的依据
                            ui.label(f'当前 {value_text(element)}').style(f'font-size:12px;color:{INK_MUT};')
                        where = ' · '.join(x for x in (tab, section, where_extra) if x)
                        if where:
                            ui.label(where).style(f'font-size:12px;color:{INK_MUT};')

    def _pick_first(self, _e=None):
        """Enter 没落在结果行上时（焦点还在输入框），跳第一条命中。"""
        hits = self._hits((self._input.value or '').strip())
        if hits:
            self._jump(hits[0])

    def _jump(self, row):
        name, _section, tab, ordinal, expansion = row[0], row[1], row[2], row[3], row[4]
        self.dialog.close()
        jump_to(name, ordinal, self._accent, self._select_tab, tab, expansion)
