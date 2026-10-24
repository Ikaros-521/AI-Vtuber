"""长 tab 的区块索引。

长页面（拆分前的 通用配置 有 17,000px、二十来个区块）光靠滚动看不出「这页到底有什么」。
这里把每个 tab 顶层的卡片/折叠区标题列成一排，点一下滚过去并描一下边。
搜索解决「知道名字找得到」，这条解决「不知道有什么」。
"""
import json

from nicegui import context, ui
from nicegui.elements.card import Card
from nicegui.elements.expansion import Expansion
from nicegui.elements.label import Label
from nicegui.elements.tabs import TabPanel

# 区块少于这个数的页面不值得加索引，免得白占一行；再多就截断，索引条不该比内容还长
MIN_SECTIONS = 5
MAX_CHIPS = 24

INK_MUT = '#4b5563'

# 用 %-格式而不是 str.format：这段脚本里全是花括号。
# DOM 里没有可用的 id（NiceGUI 3.18 不给普通元素渲染 id），所以按「区块第一行文字」认；
# 折叠区标题里会混进 material-icon 的连字文本，因此除了精确相等还留了 startsWith / includes 兜底。
JS_SCROLL_TO = """(function () {
    const want = %s;
    const titleOf = (e) => {
        const h = e.querySelector(':scope > .q-expansion__header');
        const src = h ? h.textContent : (e.innerText || '');
        const first = (src.split('\\n').find(s => s.trim()) || '').trim();
        return first.replace(/\\s+/g, ' ');
    };
    const cards = [...document.querySelectorAll('.q-tab-panel .q-card,.q-tab-panel .q-expansion')];
    let hit = cards.find(e => titleOf(e) === want);
    if (!hit) hit = cards.find(e => (e.innerText || '').trim().startsWith(want));
    if (!hit) hit = cards.find(e => (e.innerText || '').includes(want));
    if (!hit) return;
    window.__sectionHit = true;
    hit.scrollIntoView({block: 'start'});
    hit.style.outline = '2px solid %s';
    hit.style.outlineOffset = '2px';
    setTimeout(function () { hit.style.outline = ''; hit.style.outlineOffset = ''; }, 1800);
})()"""


def _title_of(section):
    if isinstance(section, Expansion):
        return str(section._props.get('label') or '').strip()
    for child in section:
        if isinstance(child, Label) and (child.text or '').strip():
            return child.text.strip()
    return ''


def _sections_of(container, depth=0):
    """顶层区块。

    卡片里再套卡片的不重复列；但折叠区要钻进去——一个页面可能就只摆三四个大折叠区，
    不钻进去就没有什么可索引的。
    """
    out = []
    for child in container:
        if isinstance(child, Expansion):
            inner = _sections_of(child, depth + 1) if depth == 0 else []
            if inner:
                out.extend(inner)
                continue
            title = _title_of(child)
            if title:
                out.append(title)
            continue
        if isinstance(child, Card):
            title = _title_of(child)
            if title:
                out.append(title)
            continue
        out.extend(_sections_of(child, depth))
    return out


def _scroll_to(title, accent):
    context.client.run_javascript(JS_SCROLL_TO % (json.dumps(title, ensure_ascii=False), accent))


def add_section_indexes(accent):
    """给所有区块够多的 tab 面板，在开头插一条区块索引。返回 {tab 名: [区块名]} 便于测试与排查。"""
    accent = accent.rstrip(';')
    panels = [e for e in context.client.elements.values() if isinstance(e, TabPanel)]
    result = {}
    for panel in panels:
        sections = _sections_of(panel)[:MAX_CHIPS]
        if len(sections) < MIN_SECTIONS:
            continue
        result[str(panel._props.get('name') or '')] = sections
        with ui.row().classes('section-index').style(
                'gap:2px;flex-wrap:wrap;align-items:center;padding:2px 4px 6px;') as row:
            ui.label('本页区块').style(f'font-size:12px;color:{INK_MUT};align-self:center;')
            for name in sections:
                ui.button(name, on_click=lambda target=name, a=accent: _scroll_to(target, a)).props(
                    'flat dense no-caps size=xs').style(f'font-size:12px;color:{INK_MUT} !important;')
        row.move(panel, 0)
    return result
