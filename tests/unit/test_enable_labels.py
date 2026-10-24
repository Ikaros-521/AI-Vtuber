"""「启用」补对象名（webui_app/labels.py）。

对象名从元素树上取：所在卡片/折叠区的标题，取不到就退回页名——整页只有一个功能的页面
（助播、翻译、积分的「通用」卡）页名就是它启用的东西。不另立一张表，标题改了这里跟着变。
"""
import pytest
from nicegui import Client, ui
from nicegui.page import page

from webui_app.labels import name_bare_enable_switches

TEST_PAGE = page('/webui-enable-labels-test')


@pytest.fixture
def in_client():
    client = Client(TEST_PAGE)
    with client:
        yield client
    if not client.is_deleted:
        client.delete()


def test_switch_adopts_its_card_title(in_client):
    with in_client:
        with ui.card():
            ui.label('音频播放')
            box = ui.switch('启用', value=False)
    assert name_bare_enable_switches() == {box.id: '启用音频播放'}
    assert box.text == '启用音频播放'


def test_generic_card_title_falls_back_to_the_tab(in_client):
    with in_client:
        with ui.tabs() as tabs:
            tab = ui.tab('积分')
        with ui.tab_panels(tabs):
            with ui.tab_panel(tab):
                with ui.card():
                    ui.label('通用')
                    box = ui.switch('启用', value=False)
    assert name_bare_enable_switches() == {box.id: '启用积分'}


def test_already_named_switch_is_left_alone(in_client):
    with in_client:
        with ui.card():
            ui.label('过滤')
            box = ui.switch('启用弹幕黑名单', value=True)
    assert name_bare_enable_switches() == {}
    assert box.text == '启用弹幕黑名单'


def test_switch_with_no_titled_container_and_no_tab_stays(in_client):
    """找不到对象就别硬凑一个「启用」+ 空串。"""
    with in_client:
        box = ui.switch('启用', value=False)
    assert name_bare_enable_switches() == {}
    assert box.text == '启用'
