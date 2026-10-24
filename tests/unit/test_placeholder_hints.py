"""长 placeholder 挪成常驻 helper（webui_app/hints.py）。

placeholder 一输入就消失，规则不能跟着消失；但 90 字以上的长文常驻会把卡片撑高十几行，
那一档只留首句，全文交给 tooltip——前提是这个字段原本没有 tooltip，
Quasar 会把两条叠在同一个目标上。
"""
import pytest
from nicegui import Client, ui
from nicegui.elements.tooltip import Tooltip
from nicegui.page import page

from webui_app.hints import (HINT_MAX_LEN, PERSIST_CLASS, first_sentence,
                          move_long_placeholders_to_hints)

TEST_PAGE = page('/webui-hints-test')

RULE = '取值范围 (0.0,1.0]，不能等于 0，默认值为 0.95。值越大输出越随机。'
ESSAY = '\n'.join([
    '一定要注意格式啊！{content}用于替换待合成的文本。',
    'url是请求地址；',
    'fn_index是api对应的索引；',
    'data_analysis是数据解析规则，暂时只支持元组和列表数据的index索引，请参考模板进行配置',
])


@pytest.fixture
def in_client():
    client = Client(TEST_PAGE)
    with client:
        yield client
    if not client.is_deleted:
        client.delete()


def targets(client, element):
    return [e for e in client.elements.values()
            if isinstance(e, Tooltip) and str(e.props.get('target')) == f'#{element.html_id}']


def test_short_placeholder_stays_an_example(in_client):
    with in_client:
        box = ui.input(label='串口名', placeholder='例如：COM1')
    assert move_long_placeholders_to_hints() == {}
    assert box._props['placeholder'] == '例如：COM1'
    assert 'hint' not in box._props


def test_long_placeholder_moves_below_the_field(in_client):
    with in_client:
        box = ui.input(label='温度', placeholder=RULE)
    assert move_long_placeholders_to_hints() == {box.id: RULE}
    assert box._props['hint'] == RULE
    assert box._props['persistent-hint'] is True
    assert 'placeholder' not in box._props
    # 样式靠这个标记类认领：只有常驻说明的字段才把 .q-field__bottom 的抽屉改成常规流
    assert PERSIST_CLASS in box.classes
    assert len(targets(in_client, box)) == 0


def test_number_and_textarea_are_covered_too(in_client):
    with in_client:
        num = ui.number(label='并发数', placeholder='取值范围 1 到 8，默认 2，超过 8 会把服务端压垮')
        area = ui.textarea(label='额外参数', placeholder='每行一个参数，例如 --temp 0.7，填了会带进合成请求')
    changed = move_long_placeholders_to_hints()
    assert set(changed) == {num.id, area.id}
    assert num._props['hint'] == '取值范围 1 到 8，默认 2，超过 8 会把服务端压垮'


def test_essay_keeps_first_line_and_gains_a_tooltip(in_client):
    with in_client:
        area = ui.textarea(label='请求参数', placeholder=ESSAY)
    assert move_long_placeholders_to_hints() == {area.id: ESSAY.split('\n')[0]}
    assert 'placeholder' not in area._props
    tips = targets(in_client, area)
    assert len(tips) == 1
    assert tips[0].text == ESSAY


def test_existing_tooltip_is_not_stacked_with_a_second(in_client):
    with in_client:
        box = ui.input(label='请求参数', placeholder=ESSAY).tooltip('已有说明')
    assert move_long_placeholders_to_hints() == {box.id: ESSAY.split('\n')[0]}
    assert len(targets(in_client, box)) == 1


def test_blank_placeholder_is_ignored(in_client):
    with in_client:
        box = ui.input(label='标题', placeholder='      ')
    assert move_long_placeholders_to_hints() == {}
    assert 'hint' not in box._props


def test_first_sentence_prefers_a_full_stopped_line():
    assert first_sentence(ESSAY) == '一定要注意格式啊！{content}用于替换待合成的文本。'
    assert first_sentence('短') == '短'
    assert len(first_sentence('说' * 300)) == HINT_MAX_LEN
