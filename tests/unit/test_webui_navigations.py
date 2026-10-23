"""导航与页面拆分模块（overview / search / sections / repage）的行为。

repage 是按「区块标题」搬东西的，标题一改就会在 webui 启动时抛 LookupError，
所以这里既测小算法，也用源码扫一遍把 PAGE_PLAN 引用的标题钉住。
"""

import io
import pathlib
import re

import pytest
from nicegui import Client, ui
from nicegui.page import page

from webui_app.overview import NAV_GROUPS, OVERVIEW, group_of, readiness
from webui_app.repage import PAGE_PLAN, _blocks, _with_following
from webui_app.fields import field_name
from webui_app.search import ConfigSearch
from webui_app.sections import _sections_of

TEST_PAGE = page('/webui-nav-unit-test')
ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture
def in_client():
    client = Client(TEST_PAGE)
    with client:
        yield client
    if not client.is_deleted:
        client.delete()


# ─────────────────────────────────────────── 分组导航

def test_every_nav_page_is_listed_once():
    flat = [name for _group, members in NAV_GROUPS for name in members]
    assert len(flat) == len(set(flat)), '同一个页面被放进了两个组'


def test_group_of_maps_members_and_defaults_to_overview():
    for group, members in NAV_GROUPS:
        for name in members:
            assert group_of(name) == group
    assert group_of(OVERVIEW) == OVERVIEW
    assert group_of('没听过的页面') == OVERVIEW     # 未知页面归到总览，不在导航条上高亮一个不存在的组


def test_readiness_reports_real_config_only():
    class FakeConfig:
        def __init__(self, data):
            self.data = data

        def get(self, *keys):
            out = self.data
            for k in keys:
                out = out.get(k) if isinstance(out, dict) else None
                if out is None:
                    return None
            return out

    rows = readiness(FakeConfig({
        'platform': 'bilibili2', 'room_display_id': '278333', 'chat_type': 'chatgpt',
        'audio_synthesis_type': 'edge-tts', 'visual_body': '其他',
    }))
    assert [r['ok'] for r in rows] == [True, True, True, True]
    assert '278333' in rows[0]['value']

    empty = readiness(FakeConfig({'platform': 'talk', 'room_display_id': '', 'chat_type': 'none',
                                  'audio_synthesis_type': 'none', 'visual_body': None}))
    assert [r['ok'] for r in empty] == [False, False, False, False]
    # 就绪度跳的目标页必须真的在导航里，不然「去配置」会跳到一个不存在的 tab
    pages = {OVERVIEW} | {n for _g, m in NAV_GROUPS for n in m}
    assert all(r['tab'] in pages for r in rows)


# ─────────────────────────────────────────── 搜索

def test_name_of_covers_both_label_and_text():
    """ui.switch/checkbox 的文字在 .text 上，只读 .label 会静默漏掉全部开关。"""
    with Client(TEST_PAGE):
        box = ui.input('违禁词路径')
        sw = ui.switch('启用音频匹配')
        cb = ui.checkbox('同意')
        area = ui.textarea('回复模板')
        sel = ui.select(label='平台', options=['a'])
        empty = ui.input()
    assert field_name(box) == '违禁词路径'
    assert field_name(sw) == '启用音频匹配'
    assert field_name(cb) == '同意'
    assert field_name(area) == '回复模板'
    assert field_name(sel) == '平台'
    assert field_name(empty) == ''


def test_hits_match_name_and_section_case_insensitively():
    index = [('保留条数', '定时任务', '定时与闲时', 0, None, None),
             ('Max Tokens', '大语言模型', '大语言模型', 0, None, None),
             ('别的', '无关', '无关', 0, None, None)]
    search = ConfigSearch(lambda name: None, '#3e78bd;')
    search._index = index
    assert [r[0] for r in search._hits('保留')] == ['保留条数']
    assert [r[0] for r in search._hits('max tokens')] == ['Max Tokens']
    assert [r[0] for r in search._hits('定时任务')] == ['保留条数']   # 按分区也能命中
    assert search._hits('   ') == []


def test_duplicate_labels_get_distinct_ordinals(in_client):
    """同名控件（音频存储路径#1/#2）跳过去要落在对的那一个。"""
    from webui_app.search import build_index
    with in_client:
        with ui.tabs() as tabs:
            t = ui.tab('页面')
        with ui.tab_panels(tabs, value=t):
            with ui.tab_panel(t):
                ui.input(label='重复项')
                ui.input(label='重复项')
    rows = [r for r in build_index() if r[0] == '重复项']
    assert [r[3] for r in rows] == [0, 1]
    assert all(r[2] == '页面' for r in rows)          # 归属到所在 tab


# ─────────────────────────────────────────── 区块索引

def test_sections_of_stops_at_nested_cards(in_client):
    with in_client:
        with ui.column() as root:
            with ui.card():
                ui.label('外层')
                with ui.card():
                    ui.label('内层不该单独列')
            with ui.row():
                with ui.card():
                    ui.label('包在 row 里也要找到')
    assert _sections_of(root) == ['外层', '包在 row 里也要找到']


def test_sections_of_drills_into_expansions(in_client):
    """折叠区里有卡片就按卡片分块；只有一张无标题容器卡的（联动程序）整块算一个。"""
    with in_client:
        with ui.column() as root:
            with ui.expansion('互动功能'):
                with ui.card():
                    ui.label('念弹幕')
                with ui.card():
                    ui.label('答谢')
            with ui.expansion('联动程序'):
                ui.card()
    assert _sections_of(root) == ['念弹幕', '答谢', '联动程序']


def test_short_pages_get_no_index(in_client, monkeypatch):
    monkeypatch.setattr('webui_app.sections.MIN_SECTIONS', 2)
    with in_client:
        with ui.tabs() as tabs:
            t1 = ui.tab('短页')
            t2 = ui.tab('长页')
        with ui.tab_panels(tabs, value=t1) as panels:
            with ui.tab_panel(t1):
                with ui.card():
                    ui.label('只有一块')
            with ui.tab_panel(t2):
                for name in ('一', '二'):
                    with ui.card():
                        ui.label(name)
        from webui_app.sections import add_section_indexes
        result = add_section_indexes('#3e78bd;')
        short_panel, long_panel = list(panels)
    assert list(result) == ['长页']
    assert len(list(short_panel)) == 1                        # 短页不挂索引条
    index_row = list(long_panel)[0]                           # 索引条必须在最前面
    assert '本页区块' in [c.text for c in index_row if hasattr(c, 'text')]


# ─────────────────────────────────────────── 页面拆分

def test_unknown_block_title_fails_loudly(in_client):
    with in_client:
        with ui.column() as root:
            with ui.card():
                ui.label('存在的块')
    with pytest.raises(LookupError):
        _with_following(root, _blocks(root), ['不存在的块'])


def test_following_untitled_card_travels_with_its_group(in_client):
    """动态组容器卡没有标题，必须跟着上面那块一起搬走。"""
    with in_client:
        with ui.column() as root:
            with ui.card():
                ui.label('定时任务')
            group = ui.card()
            with ui.card():
                ui.label('下一块')
    picked = _with_following(root, _blocks(root), ['定时任务'])
    assert [id(p) for p in picked] == [id(list(root)[0]), id(group)]


def test_page_plan_titles_still_exist_in_the_source():
    """repage 按标题搬块，卡片标题一改就会在启动时抛 LookupError。

    这里直接扫源码把标题钉住：改卡片名的人会在测试里看到是哪一条对不上。
    """
    source = io.open(ROOT / 'webui_app' / 'pages' / 'common_config.py', encoding='utf-8').read()
    labels = set(re.findall(r'ui\.label\(\s*[\'"]([^\'"]+)[\'"]', source))
    labels |= set(re.findall(r'ui\.expansion\(\s*[\'"]([^\'"]+)[\'"]', source))
    fields = set(re.findall(r'label\s*=\s*[\'"]([^\'"]+)[\'"]', source))

    for _page, wanted in PAGE_PLAN:
        for item in wanted:
            if item.startswith('@row:'):
                assert item.split(':', 1)[1] in fields, f'裸 row 的锚定字段没了：{item}'
            else:
                assert item in labels, f'{_page} 页要的区块标题找不到了：{item}'


def test_split_filter_page_still_saves_the_same_fields():
    """过滤 页的保存面是一整块 mapping，字段少一个就是漏搬。"""
    from webui_app.pages.interact_filter import build_interact_filter_tab

    class FakeConfig:
        def get(self, *keys):
            # 只回答「板块显示/隐藏」，控件初值一律给 None（等价于配置里没有这一项）
            return True if keys[-1] == 'filter' and keys[0] == 'webui' else None

    with Client(TEST_PAGE):
        page_config = build_interact_filter_tab(FakeConfig(), '', '')
    fields = page_config.mapping['filter']
    assert {'before_must_str', 'badwords', 'priority_mapping', 'blacklist'} <= set(fields)
    assert fields['max_len'][1] == 'int'
    assert fields['badwords']['path'][1] == 'str'
