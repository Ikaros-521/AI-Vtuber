"""「启用」补对象名（webui_app/labels.py）。

对象名从元素树上取：所在卡片/折叠区的标题，取不到就退回页名——整页只有一个功能的页面
（助播、翻译、积分的「通用」卡）页名就是它启用的东西。不另立一张表，标题改了这里跟着变。
"""
import pytest
from nicegui import Client, ui
from nicegui.page import page

from webui_app.labels import SHOW_CARD_NAMES, name_bare_enable_switches, rename_show_card_switches

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


def test_wall_switches_get_one_spelling(in_client):
    """开关墙不再「念弹幕」和 gpt_sovits 并排站着（走查 audit-5）。"""
    with in_client:
        with ui.card():
            ui.label('文本转语音')
            a = ui.switch('gpt_sovits', value=True)
            b = ui.switch('Edge TTS', value=True)
            c = ui.switch('音频播放', value=True)
    changed = rename_show_card_switches()
    assert changed == {a.id: 'GPT-SoVITS', b.id: 'Edge-TTS'}
    assert c.text == '音频播放'          # 本来就是中文的不动


def test_opaque_keys_keep_the_key_in_the_label(in_client):
    """拼音键补中文，但键必须留在文案里：这些文字就是全局搜索的键，
    而且用户会拿它去对 config.json 和文档。"""
    with in_client:
        with ui.card():
            ui.label('虚拟身体')
            a = ui.switch('xuniren', value=True)
            b = ui.switch('live2d_TTS_LLM_GPT_SoVITS_Vtuber', value=True)
    rename_show_card_switches()
    for switch in (a, b):
        key = [k for k in SHOW_CARD_NAMES if SHOW_CARD_NAMES[k] == switch.text][0]
        assert key.lower() in switch.text.lower()


def test_glossary_only_renames_whole_texts(in_client):
    """按完整文案匹配，别拿子串去改「自定义LLM」这类已经规范了的标签。"""
    with in_client:
        untouched = ui.switch('自定义LLM', value=True)
        renamed = ui.switch('gemini', value=True)
    assert rename_show_card_switches() == {renamed.id: 'Gemini'}
    assert untouched.text == '自定义LLM'
