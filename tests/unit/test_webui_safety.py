"""危险操作确认框与未保存改动守卫（webui_app/confirm.py、webui_app/dirty_guard.py）。

这两个模块是走查里两条 blocker 的落点：误点不可回、改一半刷新就丢。
它们的行为全在「服务端组件树 + 一条 JS 钩子」上，所以用手工 Client 当浏览器连接，
不真起服务、不碰 config.json。
"""

import pytest
from nicegui import Client, ui
from nicegui.page import page

from webui_app.confirm import ConfirmBox, confirm_delete_file
from webui_app.dirty_guard import DirtyGuard
from webui_app.fields import jump_to

TEST_PAGE = page('/webui-safety-unit-test')


@pytest.fixture
def in_client():
    """在一个假浏览器连接里建元素，用完删掉，别污染同会话的其它用例。"""
    client = Client(TEST_PAGE)
    with client:
        yield client
    if not client.is_deleted:
        client.delete()


# ─────────────────────────────────────────── 确认框

def test_ask_before_build_is_a_loud_error(in_client):
    """没 build 就 ask 必须炸，不能静默跳过确认——静默等于守卫失效。"""
    box = ConfirmBox()
    with pytest.raises(RuntimeError):
        box.ask('删？', lambda: None)


def test_cancel_never_runs_the_action(in_client):
    box = ConfirmBox()
    box.build()
    ran = []
    box.ask('确认删除？', lambda: ran.append(1), '细节')
    assert box.dialog.value is True
    box._cancel()
    assert ran == []
    assert box.dialog.value is False


def test_confirm_runs_action_exactly_once(in_client):
    box = ConfirmBox()
    box.build()
    ran = []
    box.ask('确认重启？', lambda: ran.append(1))
    box._accept()
    box._accept()                      # 对话框已关，再点一次也不该重复执行
    assert ran == [1]


def test_action_cannot_fire_after_cancel(in_client):
    """取消后残留的回调不能被下一次「确认」捡起来执行。"""
    box = ConfirmBox()
    box.build()
    ran = []
    box.ask('危险', lambda: ran.append(1))
    box._cancel()
    box._accept()
    assert ran == []


def test_detail_label_hidden_when_empty(in_client):
    box = ConfirmBox()
    box.build()
    box.ask('只有标题', lambda: None)
    assert box._detail.visible is False
    box.ask('有标题', lambda: None, '有细节')
    assert box._detail.visible is True


def test_delete_file_message_carries_the_path(in_client):
    from webui_app import confirm as confirm_module
    box = ConfirmBox()
    box.build()
    confirm_module.confirm = box
    ran = []
    confirm_delete_file('out/copy1/abc.wav', lambda: ran.append(1))
    assert 'out/copy1/abc.wav' in box._detail.text
    assert '不可恢复' in box._detail.text
    box._accept()
    assert ran == [1]


# ─────────────────────────────────────────── 未保存守卫

def test_watch_only_hooks_real_inputs(in_client):
    """ui.expansion / ui.tabs 也是 ValueElement，展开和切页不该算改配置。"""
    guard = DirtyGuard()
    with in_client:
        ui.input('标题')
        ui.textarea('文案')
        ui.select(label='平台', options=['a'])
        ui.switch('启用')
        ui.checkbox('同意')
        ui.expansion('功能管理')
        ui.tabs()
    guard.watch(force=True)
    assert len(guard._watched) == 5


def test_editing_marks_dirty_and_saving_clears(in_client):
    guard = DirtyGuard()
    with in_client:
        box = ui.input('房间号', value='123')
    guard.watch(force=True)
    assert guard.count() == 0

    box.value = '456'
    assert guard.count() == 1
    box.value = '789'
    assert guard.count() == 1          # 同一个控件改十次也只是一项
    guard.mark_saved()
    assert guard.count() == 0


def test_badge_and_status_line_stay_in_sync(in_client):
    guard = DirtyGuard()
    with in_client:
        box = ui.input('房间号', value='1')
        badge = ui.label('')
        status = ui.label('')
    guard.bind_label(badge)
    guard.bind_status(status)
    guard.watch(force=True)
    assert badge.text == '● 配置已保存'
    assert status.text == '所有改动都已保存'

    box.value = '2'
    assert badge.text == '● 1 项未保存'
    assert status.text == '当前有 1 项改动还没写进配置文件'
    guard.mark_saved()
    assert badge.text == '● 配置已保存'


def test_guard_js_is_sent_only_when_state_changes(in_client, monkeypatch):
    """每 3 秒补挂一次控件，不能每次都往浏览器塞一遍拦截脚本。"""
    calls = []
    monkeypatch.setattr(Client, 'has_socket_connection', True)
    monkeypatch.setattr(Client, 'run_javascript', lambda self, code, **kw: calls.append(code))
    guard = DirtyGuard()
    with in_client:
        box = ui.input('房间号', value='1')
    guard.watch(force=True)
    box.value = '2'
    box.value = '3'
    assert calls == ['window.__unsavedGuard(1)']
    guard.mark_saved()
    assert calls == ['window.__unsavedGuard(1)', 'window.__unsavedGuard(0)']


def test_no_js_sent_when_no_browser_is_connected(in_client, monkeypatch):
    calls = []
    monkeypatch.setattr(Client, 'has_socket_connection', False)
    monkeypatch.setattr(Client, 'run_javascript', lambda self, code, **kw: calls.append(code))
    guard = DirtyGuard()
    with in_client:
        box = ui.input('房间号', value='1')
    guard.watch(force=True)
    box.value = '2'
    assert calls == []
    assert guard.count() == 1          # 脏状态照记，等浏览器连上再补发


def test_widgets_created_later_are_picked_up(in_client):
    """「增加配置组」是运行期现建控件，定时补挂必须接得住。"""
    guard = DirtyGuard()
    with in_client:
        first = ui.input('第一组')
    guard.watch(force=True)
    with in_client:
        later = ui.input('新加的一组')
    guard.watch(force=True)
    first.value = 'a'
    later.value = 'b'
    assert guard.count() == 2


# ─────────────────────────────────────────── 未保存清单（角标点开那一层）

def test_list_rows_carry_name_value_and_page(in_client):
    """清单要报出「哪一项、现在是什么值」，开关也要有可读值而不是 True。"""
    guard = DirtyGuard()
    with in_client:
        room = ui.input('直播间号', value='1')
        tts = ui.switch('启用语音合成', value=False)
        guard.bind_nav(lambda name: None, '#3e78bd;')
        guard.build_list()
        guard.watch(force=True)
        room.value = '2783339'
        tts.value = True
        guard.open_list()
        rows = [child for child in guard._list if isinstance(child, ui.button)]
    assert len(rows) == 2
    texts = [el.text for row in rows for el in row.descendants() if isinstance(el, ui.label)]
    assert '直播间号 = 2783339' in texts
    assert '启用语音合成 = 开' in texts


def test_highlight_color_stays_valid_css(in_client, monkeypatch):
    """主题色是从 config 读的，末尾常带分号；带着它拼 outline 会整条失效，描边静默不出现。"""
    calls = []
    monkeypatch.setattr(Client, 'has_socket_connection', True)
    monkeypatch.setattr(Client, 'run_javascript', lambda self, code, **kw: calls.append(code))
    with in_client:
        jump_to('直播间号', 0, '#3e78bd;')
    assert len(calls) == 1
    assert "2px solid #3e78bd'" in calls[0]
    assert "solid #3e78bd;'" not in calls[0]


def test_unnamed_or_non_config_inputs_are_not_watched(in_client):
    """无名称控件（如聊天调试框）或标记 is_config_field=False 的控件不应计入脏状态。"""
    guard = DirtyGuard()
    with in_client:
        valid_box = ui.input('配置字段', value='1')
        unnamed_box = ui.input(placeholder='临时输入')
        explicit_non_cfg = ui.input('临时UI', value='a')
        explicit_non_cfg.is_config_field = False
    guard.watch(force=True)
    assert len(guard._watched) == 1
    assert valid_box.id in guard._watched

    unnamed_box.value = 'hello'
    explicit_non_cfg.value = 'b'
    assert guard.count() == 0

    valid_box.value = '2'
    assert guard.count() == 1
    assert guard.count() == len(guard.items())


def test_count_and_items_never_diverge(in_client):
    """count() 与 items() 数量必须绝对一致，防止出现'有N项未保存但弹窗为空'。"""
    guard = DirtyGuard()
    with in_client:
        box = ui.input('直播间号', value='100')
        # 即使极端情况下有无 label 控件被显式标记为 config 字段且脏了
        mystery = ui.input(placeholder='神秘输入框', value='xyz')
        mystery.is_config_field = True
    guard.watch(force=True)
    box.value = '200'
    mystery.value = 'uvw'

    assert guard.count() == 2
    items = guard.items()
    assert len(items) == 2
    assert guard.count() == len(items)
    labels = [r[0] for r in items]
    assert '直播间号' in labels
    assert '神秘输入框' in labels
