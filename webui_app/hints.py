"""把塞在 placeholder 里的长解释挪成字段下方的常驻 helper（走查 audit-19）。

placeholder 一输入就消失：用户照着「取值范围 (0.0,1.0]，不能等于 0」这种规则填到一半，
规则本身先没了。实测 624 个带 placeholder 的字段里 273 个超过 24 字、112 个超过 40 字，
最长的 176 字（Gradio 的请求参数格式），而这些字段下方一条 helper 都没有。

按长度分两档：
- 24～90 字：整段挪到 helper，placeholder 清空（留着就是同一段字出现两次）
- 90 字以上：整段常驻会把卡片撑出十来行，字段下方只留首句，全文交给这个字段的 tooltip。
  实测这 9 个字段原本一个 tooltip 都没有，所以 tooltip 要新建而不是复用；
  已经有 tooltip 的（273 个里占 119 个）不再加第二条，Quasar 会把两个弹层叠在同一目标上。

helper 用 Quasar 的 hint + persistent-hint，跟着字段自己的 DOM 走；
不动栅格结构，避免像另起一行 label 那样把列数顶乱。
"""
from nicegui import context, ui
from nicegui.elements.number import Number
from nicegui.elements.tooltip import Tooltip

# 短于此长度的 placeholder 本来就是示例值（「例如：COM1」），留在原位
HINT_MIN_LEN = 24
# 超过这个长度不再整段常驻，只留首句 + tooltip 看全文
HINT_MAX_LEN = 90
# 打在字段根节点上的标记类，样式见 webui.py 的 PAGE_SCRIPTS
PERSIST_CLASS = 'has-persistent-hint'

INPUT_LIKE = (ui.input, ui.textarea, Number)


def first_sentence(text):
    """取首句：先按换行找到第一段够长的，再按中文句读断句，都没有就截断加省略号。"""
    for part in text.split('\n'):
        part = part.strip()
        if len(part) >= HINT_MIN_LEN:
            text = part
            break
    for sep in ('。', '；'):
        index = text.find(sep)
        if HINT_MIN_LEN <= index < len(text) - 1:
            return text[:index + 1]
    if len(text) <= HINT_MAX_LEN:
        return text
    return text[:HINT_MAX_LEN - 1] + '…'


def move_long_placeholders_to_hints():
    """返回 {控件 id: helper 文本}，便于测试与排查。"""
    elements = list(context.client.elements.values())
    tipped = {str(t.props.get('target') or '') for t in elements if isinstance(t, Tooltip)}
    changed = {}
    for element in elements:
        if not isinstance(element, INPUT_LIKE):
            continue
        placeholder = str(element._props.get('placeholder') or '').strip()
        if len(placeholder) < HINT_MIN_LEN:
            continue
        if len(placeholder) <= HINT_MAX_LEN:
            hint = placeholder
        else:
            hint = first_sentence(placeholder)
            target = f'#{element.html_id}'
            if target not in tipped:
                # 必须把 tooltip 建到字段所在的那个容器里：写成兄弟节点之外的位置
                # （比如页面根节点）时，实测 hover 弹不出来——建页时同写法的那些 tooltip 能弹，
                # 差别就在离目标远不远。
                with element.parent_slot:
                    element.tooltip(placeholder)
                tipped.add(target)
        element.props['hint'] = hint
        element.props['persistent-hint'] = True
        element.props.pop('placeholder', None)
        # Quasar 把 .q-field__bottom 做成绝对定位 + translateY(100%) 的「抽屉」，只在聚焦/报错时滑出来；
        # 常驻 helper 要占回自己的高度，否则两三行说明会直接压到下一行字段上（实测按键映射页整片重叠）。
        # 打个标记类给 webui.py 的样式用，避免把没有常驻说明的字段也一起改了。
        element.classes(PERSIST_CLASS)
        changed[element.id] = hint
    return changed
