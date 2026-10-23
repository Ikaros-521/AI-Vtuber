"""把 通用配置（现名 平台接入）的顶层区块整块改挂到新的 tab 上。

sitemap 的 24 页是按「配置对象」重切的，而 通用配置 里那 20 来个区块本来就是按这个逻辑
堆在一个 17,000px 的页面上的。所以这里只搬 DOM 归属：控件、闭包、save_common 全留在原文件，
保存链路一行不动 —— 拆分的风险全在保存路径上，能不碰就不碰。
"""
from nicegui import ui
from nicegui.elements.card import Card
from nicegui.elements.expansion import Expansion
from nicegui.elements.label import Label

# (新 tab 名, [要搬走的区块标题])；标题对不上时会直接抛错，不会静默少搬。
# '@row:字段名' 表示把面板里那条没包成卡片的裸 row 搬走——按行里某个字段定位它。
PAGE_PLAN = [
    ('播报与输出', ['@row:提示词前缀', '音频播放', 'web字幕打印机']),
    ('念弹幕与答谢', ['念弹幕', '答谢']),
    ('本地问答', ['本地问答']),
    ('点歌', ['点歌模式']),
    ('定时与闲时', ['定时任务', '闲时任务', '动态配置']),
    ('联网与动态文案', ['联网搜索', '动态文案']),
    ('按键与命令', ['按键/文案/音频/串口/图片 映射', '自定义命令']),
    ('外部软件对接', ['洛曦 直播弹幕助手', '联动程序']),
    ('出图', ['Stable Diffusion']),
    ('日志与数据库', ['日志', '数据库']),
    ('异常报警', ['异常报警']),
]

# 裸 row 搬走后要有个标题，不然在新页面上是悬着的一片输入框
ROW_TITLES = {'提示词前缀': '对话与回复模板'}

# 就地包一层卡片（不搬走）：平台接入 顶部那排是全页唯一的裸表单，和下面「一功能一卡片」
WRAP_IN_PLACE = [('平台', '平台与模型')]


def _title_of(section):
    if isinstance(section, Expansion):
        return str(section._props.get('label') or '').strip()
    for child in section:
        if isinstance(child, Label) and (child.text or '').strip():
            return child.text.strip()
    return ''


def _blocks(container):
    """容器里可搬的区块：卡片算一块；折叠区里有卡片就下钻，没卡片就算它自己一块。"""
    out = []
    for child in container:
        if isinstance(child, Expansion):
            inner = _blocks(child)
            # 折叠区里只有一张无标题的动态组容器卡时（联动程序 就是这种），整块算一个区块；
            # 否则下钻，把里面的卡片分别当区块，才能按主题分到不同页面
            if inner and all(not t for t, _ in inner):
                inner = []
            out.extend(inner or [(_title_of(child), child)])
            continue
        if isinstance(child, Card):
            out.append((_title_of(child), child))
            continue
        out.extend(_blocks(child))
    return out


def _with_following(root, blocks, wanted):
    """按标题取块，并把它后面紧跟的无标题兄弟块一起带上（动态组容器卡就是这种）。

    折叠区里有卡片时，_blocks 会把里面的卡片列成块、折叠区壳子本身不在名单里；
    所以标题找不到时再按折叠区标题找一次，允许整壳搬走。
    """
    picked = []
    titles = [t for t, _ in blocks]
    for want in wanted:
        if want in titles:
            i = titles.index(want)
            picked.append(blocks[i][1])
            for j in range(i + 1, len(blocks)):
                if blocks[j][0]:
                    break
                picked.append(blocks[j][1])
            continue
        shell = next((n for n in root.descendants()
                      if isinstance(n, Expansion)
                      and str(n._props.get('label') or '').strip() == want), None)
        if shell is None:
            raise LookupError('源页面里找不到区块：' + want)
        picked.append(shell)
    return picked


def _drop_empty_containers(root):
    """搬空之后，功能管理/互动功能 这类壳子留着只会多一个能点开的空标题。"""
    changed = True
    while changed:
        changed = False
        for node in list(root.descendants()):
            if isinstance(node, (Card, Expansion)) and not list(node):
                node.delete()
                changed = True
    return root


def _loose_row(root, label):
    """按行内某个字段，定位面板里那条没包成卡片的裸 row。"""
    for el in root.descendants():
        if (getattr(el, 'label', '') or '') == label:
            for a in el.ancestors():
                if 'nicegui-row' in list(a.classes):
                    return a
    raise LookupError('找不到含「%s」的裸 row' % label)


def apply_page_plan(tabs, tab_panels, source_panel, panel_css, card_css):
    """按计划新建 tab 并把区块搬过去。返回新建的 tab 名列表。"""
    blocks = _blocks(source_panel)
    made = []
    for name, wanted in PAGE_PLAN:
        rows = [w.split(':', 1)[1] for w in wanted if w.startswith('@row:')]
        picked = _with_following(source_panel, blocks, [w for w in wanted if not w.startswith('@row:')])
        with tabs:
            tab = ui.tab(name)
        with tab_panels:
            panel = ui.tab_panel(tab).style(panel_css)
        for label in rows:
            with panel:
                shell = ui.card().style(card_css)
            with shell:
                ui.label(ROW_TITLES.get(label, label))
            _loose_row(source_panel, label).move(shell)
            shell.move(panel, 0)
        for block in picked:
            block.move(panel)
        made.append(name)
    _wrap_in_place(source_panel, card_css)
    _drop_empty_containers(source_panel)
    return made


def _wrap_in_place(root, card_css):
    """给留在原页的裸 row 套一张带标题的卡片，位置和大小都不变。"""
    for anchor, title in WRAP_IN_PLACE:
        row = _loose_row(root, anchor)
        parent = row.parent_slot.parent
        index = list(parent).index(row)
        with parent:
            shell = ui.card().style(card_css)
        with shell:
            ui.label(title)
        row.move(shell)
        shell.move(parent, index)
