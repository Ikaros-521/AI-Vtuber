"""「只看已启用」过滤视图（走查 audit-9）的归属规则与显隐切换。

最容易写错的两点都有对应测试：
开关归属到**最近的**卡片/折叠区（不然「过滤」那张 60 字段的卡会被两个子折叠区带走）；
藏只能加 CSS 类（走 set_visibility 会被 fields.hidden() 当成不存在，搜索索引直接少 359 项）。
"""

import pytest
from nicegui import Client, ui
from nicegui.page import page

from webui_app.enabled_filter import (EMPTY_CLASS, FILTER_CLASS, OFF_CLASS, EnabledFilter,
                                      config_field_count, disabled_containers)
from webui_app.fields import jump_to_element, set_reveal_hook

TEST_PAGE = page('/webui-enabled-filter-unit-test')


@pytest.fixture
def in_client():
    client = Client(TEST_PAGE)
    with client:
        yield client
    if not client.is_deleted:
        client.delete()


def card_with(switch_label, on, *extra_fields):
    with ui.card() as card:
        ui.label(switch_label.replace('启用', '') or '卡')
        sw = ui.switch(switch_label, value=on)
        for name in extra_fields:
            ui.input(label=name)
    return card, sw


def test_off_switch_hides_its_own_card_only(in_client):
    off_card, _ = card_with('启用点歌', False, '点歌关键词')
    on_card, _ = card_with('启用联网搜索', True, 'IP地址')
    plain = ui.card()
    picked = disabled_containers()
    assert off_card in picked
    assert on_card not in picked
    assert plain not in picked


def test_switch_belongs_to_the_nearest_expansion_not_the_page_card(in_client):
    """子折叠区里的开关不能把整张父卡带走——实测「过滤」页 60 个字段就是这么被误藏的。"""
    with ui.card() as outer, ui.expansion('弹幕黑名单') as inner:
        ui.switch('启用弹幕黑名单', value=False)
        ui.input(label='黑名单路径')
    picked = disabled_containers()
    assert inner in picked
    assert outer not in picked
    assert config_field_count(picked) == 2      # 开关 + 输入框，父卡别的字段不算


def test_nested_off_containers_are_counted_once(in_client):
    with ui.card() as parent:
        ui.switch('启用按键映射', value=False)
        with ui.card() as child:
            ui.switch('启用子开关', value=False)
            ui.input(label='子字段')
    picked = disabled_containers()
    assert picked == [parent]
    assert child not in picked


def test_hiding_keeps_elements_visible_to_the_index(in_client):
    """藏是 CSS 层面的：NiceGUI 的 visible 必须还是 True，否则搜索与未保存清单收不到。"""
    card, _ = card_with('启用日志', False, '日志级别')
    filt = EnabledFilter()
    panels = ui.column()
    filt.bind_panels(panels)
    filt._on = True
    filt.resweep()
    assert card._classes.count(OFF_CLASS) == 1
    assert card.visible is True
    assert FILTER_CLASS in panels._classes


def test_resweep_follows_the_current_switch_value(in_client):
    card, sw = card_with('启用闲时任务', False, '最小闲时时间')
    filt = EnabledFilter()
    panels = ui.column()
    filt.bind_panels(panels)
    filt._on = True
    filt.resweep()
    assert OFF_CLASS in card._classes
    sw.value = True                             # 用户把功能打开了
    filt.resweep()
    assert OFF_CLASS not in card._classes


def test_turn_off_is_idempotent_when_already_off(in_client):
    filt = EnabledFilter()
    filt.bind_panels(ui.column())
    filt.turn_off()                             # 没开过：不该建标记也不该炸
    assert filt.is_on is False


def test_a_page_that_empties_out_says_so(in_client):
    """一页只剩一张未启用的卡时，过滤后整页空白会被当成页面坏了（实测点歌页）。"""
    with ui.tabs() as tabs:
        tab = ui.tab('点歌')
    with ui.tab_panels(tabs) as panels:
        with ui.tab_panel(tab) as panel:
            with ui.card():
                ui.switch('启用点歌模式', value=False)
    filt = EnabledFilter()
    filt.bind_panels(panels)
    filt._on = True
    filt.resweep()
    assert EMPTY_CLASS in panel._classes


def test_a_page_with_something_left_enabled_is_not_marked_empty(in_client):
    with ui.tabs() as tabs:
        tab = ui.tab('播报与输出')
    with ui.tab_panels(tabs) as panels:
        with ui.tab_panel(tab) as panel:
            with ui.card():
                ui.switch('启用web字幕打印机', value=False)
            with ui.card():
                ui.switch('启用语音播报', value=True)
    filt = EnabledFilter()
    filt.bind_panels(panels)
    filt._on = True
    filt.resweep()
    assert EMPTY_CLASS not in panel._classes


def test_jump_reveals_hidden_fields(in_client, monkeypatch):
    """跳到被藏的框之前必须先取消过滤，不然 scrollIntoView 对着 display:none 空转。"""
    monkeypatch.setattr(in_client, 'run_javascript', lambda *a, **kw: None)
    called = []
    set_reveal_hook(lambda: called.append(1))
    try:
        with ui.card():
            ui.switch('启用图像识别', value=False)
            box = ui.input(label='IP地址')
        jump_to_element(box, '#3e78bd')
        assert called == [1]
    finally:
        set_reveal_hook(None)
