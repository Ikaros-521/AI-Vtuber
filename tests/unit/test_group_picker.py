"""下拉选组 + 收起式删除 + 5 秒撤销（webui_app/groups.py、webui_app/undo.py）。

替代原先的「配置索引」输入框：那个要用户自己数第几组，而且删过一次之后位置与 #N 标号就会
错位。见走查 audit-10 与 audit-7 后半。
"""
import pytest
from nicegui import Client, ui
from nicegui.page import page

from webui_app import confirm as confirm_module
from webui_app.confirm import ConfirmBox
from webui_app.groups import GroupPicker
from webui_app.undo import undo

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
    """确认框与撤销托盘都是全站单例，测试里换成这一例自己的。"""
    picker_box = ConfirmBox()
    picker_box.build()
    undo.build()
    confirm_module.confirm = picker_box
    return picker_box


def card_with_rows(count):
    """一卡片一组一行，行里第一个控件带标签——和真实页面一样的结构。

    返回 (卡片, var)：var 用「一行一个控件」的最简形状模拟页面的 {位置: 控件} 字典。
    """
    card = ui.card()
    var = {}
    for i in range(count):
        with card:
            with ui.row():
                var[str(i)] = ui.input(label=f'文案存储路径#{i + 1}', value=f'data/copywriting{i + 1}/')
    return card, var


def make_picker(card, var, action):
    return GroupPicker(lambda: card, '文案', action, lambda: var).build()


def shift_out(var, pos):
    """页面 <名>_del 的形状（这里一行一个控件）：删掉这一组的键，后面的往前挪一位。"""
    if str(pos) in var:
        del var[str(pos)]
    tail = {str(int(k) - 1): v for k, v in var.items() if int(k) > pos}
    for k in [k for k in var if int(k) > pos]:
        del var[k]
    var.update(tail)


def test_picker_lists_every_visible_row_with_a_summary(in_client, box):
    with in_client:
        card, var = card_with_rows(3)
        picker = make_picker(card, var, lambda pos: None)
    picker.refresh()
    assert list(picker.select.options) == [0, 1, 2]
    assert picker.select.options[1] == '文案存储路径#2 · data/copywriting2/'


def test_nothing_selected_never_reaches_the_delete_action(in_client, box, monkeypatch):
    ran = []
    with in_client:
        card, var = card_with_rows(2)
        picker = make_picker(card, var, ran.append)
    picker.refresh()
    notified = []
    monkeypatch.setattr(ui, 'notify', lambda **kw: notified.append(kw.get('message')))
    picker.ask_delete()
    assert ran == [] and box.dialog.value is not True
    assert any('请先选' in str(m) for m in notified)


def test_confirm_names_the_row_and_passes_its_position(in_client, box):
    ran = []
    with in_client:
        card, var = card_with_rows(3)
        picker = make_picker(card, var, ran.append)
    picker.refresh()
    picker.select.value = 1
    picker.ask_delete()
    assert 'data/copywriting2/' in box._title.text      # 确认框里写的就是选中的那一行
    assert '页面顶部撤销' in box._detail.text
    box._accept()
    assert ran == [1]                                   # 传的是卡片里的位置，不是人肉数的组号


def test_refresh_drops_a_selection_that_went_away(in_client, box):
    with in_client:
        card, var = card_with_rows(2)
        picker = make_picker(card, var, lambda pos: None)
    picker.refresh()
    picker.select.value = 1
    list(card)[1].set_visibility(False)
    picker.refresh()
    assert list(picker.select.options) == [0]
    assert picker.select.value is None


def test_delete_hides_the_row_instead_of_destroying_it(in_client, box):
    """控件一旦被 card.remove() 就重建不回来，所以删除只是「收起 + 把键挪走」。"""
    with in_client:
        card, var = card_with_rows(2)
        rows = list(card)
        picker = make_picker(card, var, lambda pos: shift_out(var, pos))
    picker.refresh()
    picker.select.value = 0
    picker.ask_delete()
    box._accept()
    assert rows[0].visible is False and rows[1].visible is not False
    assert list(var) == ['0']                            # 保存链路读的是 var，效果与硬删一致
    assert list(picker.select.options) == [0]            # 下拉跟着刷新


def test_two_deletes_in_a_row_stay_aligned(in_client, box):
    """收起的行仍占着卡片位置，所以序号必须按「看得见的行」连续数。

    否则第二次删的 var 键和实际收起的那行对不上——软删最容易踩的就是这个坑。
    """
    with in_client:
        card, var = card_with_rows(3)
        rows = list(card)
        picker = make_picker(card, var, lambda pos: shift_out(var, pos))
    picker.refresh()
    for _ in range(2):
        picker.select.value = 0
        picker.ask_delete()
        box._accept()
    assert rows[0].visible is False and rows[1].visible is False
    assert list(var) == ['0'] and var['0'] is list(rows[2].descendants())[0]
    assert list(picker.select.options) == [0]


def test_undo_restores_both_the_row_and_the_keys(in_client, box):
    with in_client:
        card, var = card_with_rows(2)
        rows = list(card)
        before = dict(var)
        picker = make_picker(card, var, lambda pos: shift_out(var, pos))
    picker.refresh()
    picker.select.value = 0
    picker.ask_delete()
    box._accept()
    assert var != before and undo.sticky.visible is not False

    undo.restore()
    assert rows[0].visible is not False
    assert var == before
    assert list(picker.select.options) == [0, 1]
    assert undo.sticky.visible is False


def test_undo_is_one_shot(in_client, box):
    with in_client:
        card, var = card_with_rows(1)
        before = dict(var)
        picker = make_picker(card, var, lambda pos: shift_out(var, pos))
    picker.refresh()
    picker.select.value = 0
    picker.ask_delete()
    box._accept()
    undo.restore()
    undo.restore()                       # 撤销过一次就不该再有动作
    assert var == before


def test_forget_closes_the_undo_window(in_client, box):
    """保存之后撤销窗口要关掉：再恢复回去只会和盘上的内容对不上。"""
    with in_client:
        card, var = card_with_rows(1)
        picker = make_picker(card, var, lambda pos: shift_out(var, pos))
    picker.refresh()
    picker.select.value = 0
    picker.ask_delete()
    box._accept()
    undo.forget()
    assert undo.sticky.visible is False
    undo.restore()
    assert list(var) == []               # 已经没有可恢复的东西


def test_picking_a_row_is_not_an_unsaved_change(in_client, box):
    """选择器只是界面控件，值不写进配置——点一下不该把页面标成「有 N 项未保存」。"""
    from webui_app.dirty_guard import DirtyGuard

    guard = DirtyGuard()
    with in_client:
        card, var = card_with_rows(2)
        picker = make_picker(card, var, lambda pos: None)
        real = list(card)[0].descendants().__next__()
    guard.watch(force=True)
    picker.select.value = 1
    assert guard.count() == 0
    real.value = 'data/y/'
    assert guard.count() == 1


def test_edits_inside_a_deleted_group_stop_counting(in_client, box):
    """删掉的那一组只是收起来，控件还在树里；它的改动不该再算「待保存」。"""
    from webui_app.dirty_guard import DirtyGuard

    guard = DirtyGuard()
    with in_client:
        card, var = card_with_rows(2)
        rows = list(card)
        picker = make_picker(card, var, lambda pos: shift_out(var, pos))
    guard.watch(force=True)
    first = rows[0].descendants().__next__()
    first.value = 'data/changed/'
    assert guard.count() == 1
    picker.refresh()
    picker.select.value = 0
    picker.ask_delete()
    box._accept()
    assert guard.count() == 0
