"""下拉选组（webui_app/groups.py）：列出行、摘要认得出来、没选就不删。

替代原先的「配置索引」输入框——那个要用户自己数第几组，而且删过一次之后
位置与 #N 标号就会错位。见走查 audit-10。
"""
import pytest
from nicegui import Client, ui
from nicegui.page import page

from webui_app import confirm as confirm_module
from webui_app.confirm import ConfirmBox
from webui_app.groups import GroupPicker

TEST_PAGE = page('/webui-group-picker-test')


@pytest.fixture
def in_client():
    """在一个假浏览器连接里建元素，用完删掉，别污染同会话的其它用例。"""
    client = Client(TEST_PAGE)
    with client:
        yield client
    if not client.is_deleted:
        client.delete()


@pytest.fixture
def box(in_client):
    picker_box = ConfirmBox()
    picker_box.build()
    confirm_module.confirm = picker_box
    return picker_box


def card_with_rows(count):
    """一卡片一组一行，行里第一个控件带标签——和真实页面一样的结构（行必须挂在卡片里）。"""
    card = ui.card()
    for i in range(count):
        with card:
            with ui.row():
                ui.input(label=f'文案存储路径#{i + 1}', value=f'data/copywriting{i + 1}/')
    return card


def test_picker_lists_every_visible_row_with_a_summary(in_client, box):
    with in_client:
        card = card_with_rows(3)
        picker = GroupPicker(lambda: card, '文案', lambda pos: None).build()
    picker.refresh()
    assert list(picker.select.options) == [0, 1, 2]
    assert picker.select.options[1] == '文案存储路径#2 · data/copywriting2/'


def test_nothing_selected_never_reaches_the_delete_action(in_client, box, monkeypatch):
    with in_client:
        card = card_with_rows(2)
        picker = GroupPicker(lambda: card, '文案', lambda pos: None).build()
    ran = []
    picker._action = ran.append
    notified = []
    monkeypatch.setattr(ui, 'notify', lambda **kw: notified.append(kw.get('message')))
    picker.ask_delete()
    assert ran == [] and box.dialog.value is not True
    assert any('请先选' in str(m) for m in notified)


def test_confirm_names_the_row_and_passes_its_position(in_client, box):
    ran = []
    with in_client:
        card = card_with_rows(3)
        picker = GroupPicker(lambda: card, '文案', ran.append).build()
    picker.refresh()
    picker.select.value = 1
    picker.ask_delete()
    assert 'data/copywriting2/' in box._title.text      # 确认框里写的就是选中的那一行
    assert '无法撤销' in box._detail.text
    box._accept()
    assert ran == [1]                                   # 传的是卡片里的位置，不是人肉数的组号


def test_refresh_drops_a_selection_that_went_away(in_client, box):
    with in_client:
        card = card_with_rows(2)
        picker = GroupPicker(lambda: card, '文案', lambda pos: None).build()
    picker.refresh()
    picker.select.value = 1
    list(card)[1].set_visibility(False)
    picker.refresh()
    assert list(picker.select.options) == [0]
    assert picker.select.value is None


def test_picking_a_row_is_not_an_unsaved_change(in_client, box):
    """选择器只是界面控件，值不写进配置——点一下不该把页面标成「有 N 项未保存」。"""
    from webui_app.dirty_guard import DirtyGuard

    guard = DirtyGuard()
    with in_client:
        card = card_with_rows(2)
        picker = GroupPicker(lambda: card, '文案', lambda pos: None).build()
        real = ui.input('文案存储路径#1', value='data/x/')
    guard.watch(force=True)
    picker.select.value = 1
    assert guard.count() == 0
    real.value = 'data/y/'
    assert guard.count() == 1
