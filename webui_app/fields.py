"""按「标签文本」定位并高亮一个配置框。

NiceGUI 3.18 不给普通元素渲染 DOM id，Quasar 的 tab 面板又只挂当前那一页，
所以服务端只能把「控件叫什么、同名第几个」交给浏览器去 DOM 里找。
搜索、总览的「去配置」、未保存清单三处共用这套定位，别再各写一份。
"""
import json

from nicegui import context
from nicegui.elements.card import Card
from nicegui.elements.checkbox import Checkbox
from nicegui.elements.input import Input
from nicegui.elements.select import Select
from nicegui.elements.switch import Switch
from nicegui.elements.textarea import Textarea
from nicegui.elements.expansion import Expansion
from nicegui.elements.label import Label
from nicegui.elements.tabs import TabPanel

# 开关的原生 input 是隐藏的，focus 不上去，所以一律描一圈临时高亮；
# 切页时 keep-alive 会把面板重挂一次、内联样式会被冲掉，所以补打三次再统一擦掉。
# 用 %-格式而不是 str.format：这段脚本里全是花括号，format 要逐个转义反而容易错
JS_LOCATE = """(function () {
    const want = %s, ord = %d;
    let tries = 0;
    window.__searchHit = false;
    const find = () => {
        const panel = [...document.querySelectorAll('.q-tab-panel')]
            .find(e => getComputedStyle(e).display !== 'none');
        if (!panel) return null;
        const hit = [...panel.querySelectorAll('.q-field,.q-toggle,.q-checkbox')].filter(e => {
            const l = e.querySelector('.q-field__label');
            return l ? l.textContent.trim() === want : (e.innerText || '').trim() === want;
        });
        return hit.length > ord ? hit[ord] : null;
    };
    const clear = () => {
        [...document.querySelectorAll('.q-field,.q-toggle,.q-checkbox')]
            .forEach(e => { e.style.outline = ''; e.style.outlineOffset = ''; });
    };
    const mark = () => {
        const f = find();
        if (!f) return;
        window.__searchHit = true;
        // 面板是 keep-alive 复用的，上一次跳转留下的描边会跟着节点回来，所以一次只留一个框
        clear();
        f.scrollIntoView({block: 'center'});
        const i = f.querySelector('input,textarea');
        if (i && i.offsetParent) i.focus({preventScroll: true});
        f.style.outline = '2px solid %s';
        f.style.outlineOffset = '2px';
    };
    const t = setInterval(function () {
        tries++;
        if (find()) {
            clearInterval(t);
            mark();
            setTimeout(mark, 600);
            setTimeout(mark, 1400);
            setTimeout(clear, 2800);
        } else if (tries > 30) {
            clearInterval(t);
        }
    }, 100);
})()"""


# 「什么算配置项」的唯一定义。ui.expansion / ui.tabs 也是 ValueElement，
# 但展开面板、切页不该被当成改了配置，所以按类型白名单挑。
INPUT_TYPES = (Input, Textarea, Select, Switch, Checkbox)


def field_name(element):
    """控件显示名：ui.input / textarea / select 存在 label 上，ui.switch / checkbox 存在 text 上。

    这两个不是同一个属性（Switch 压根没有 label 属性），只读 label 会静默漏掉全部开关。
    """
    for attr in ('label', 'text'):
        value = getattr(element, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ''


def locate(element):
    """这个控件在哪个 tab、哪个分区、哪个折叠区里。"""
    tab = section = ''
    expansion = None
    for a in element.ancestors():
        if isinstance(a, TabPanel):
            if not tab:
                tab = str(a._props.get('name') or '')
            continue
        if expansion is None and isinstance(a, Expansion):
            expansion = a
            section = str(a._props.get('label') or '')
        elif not section and isinstance(a, Card):
            for child in a:
                if isinstance(child, Label) and (child.text or '').strip():
                    section = child.text.strip()
                    break
    return tab, section, expansion


# 校验失败时描的圈：不用 Quasar 的语义名（negative），这段是拼进 outline 的裸 CSS
INVALID_RING = '#dc2626'


def hidden(element):
    """自己或被收起来的祖先不可见：删除中的那一组就是这种状态。"""
    return any(getattr(a, 'visible', True) is False for a in element.ancestors())


# 跳转前一刻要做的收尾，目前只有「只看已启用」要注册：被 CSS 藏起来的框还在 DOM 里，
# 但 display:none 让 scrollIntoView 滚不过去，等于跳了个寂寞（走查 audit-9）。
_reveal_hook = None


def set_reveal_hook(fn) -> None:
    global _reveal_hook
    _reveal_hook = fn


def jump_to(label, ordinal, accent, select_tab=None, tab=None, expansion=None, color=None):
    """跳到某个配置框：先切页、展开所在折叠区，再让浏览器定位并描边。

    color 给校验失败用（描红圈），不传就用主题色。
    """
    if _reveal_hook is not None:
        _reveal_hook()
    if tab and select_tab is not None:
        select_tab(tab)
    if expansion is not None:
        expansion.open()
    # 主题色是从 config 里一路传下来的，末尾可能带分号；拼进 '2px solid x' 会写成非法值，
    # 结果是描边静默不出现。这里是唯一把它拼进 CSS 的地方，在这一层收口。
    highlight = (color or accent or '').rstrip(';')
    context.client.run_javascript(
        JS_LOCATE % (json.dumps(label, ensure_ascii=False), ordinal, highlight))


def ordinal_of(element):
    """这个控件在同名控件里排第几个——浏览器按「标签文本 + 序号」找，所以跳之前要算准。

    只数还看得见的：浏览器在 DOM 里找也只会找得着可见的那些。
    """
    label = field_name(element)
    tab = locate(element)[0]
    return sum(1 for other in context.client.elements.values()
               if other.id < element.id and isinstance(other, INPUT_TYPES)
               and not hidden(other) and field_name(other) == label and locate(other)[0] == tab)


def jump_to_element(element, accent, select_tab=None, color=None):
    """手上就有控件对象时（校验失败、未保存清单）直接跳过去，省掉猜标签文本与序号。"""
    tab, _section, expansion = locate(element)
    jump_to(field_name(element), ordinal_of(element), accent, select_tab, tab, expansion, color)


def build_index():
    """(控件名, 分区, tab 名, 同名第几个, 所在折叠区, 控件) 列表。

    同名第几个用来区分「音频存储路径#1/#2」这类重名项，跳过去时取对的那一个。
    """
    rows = []
    seen = {}
    for element in context.client.elements.values():
        if not isinstance(element, INPUT_TYPES):
            continue
        if getattr(element, 'is_config_field', True) is False:
            continue
        if hidden(element):
            continue
        label = field_name(element)
        if not label:
            continue
        tab, section, expansion = locate(element)
        ordinal = seen.get((tab, label), 0)
        seen[(tab, label)] = ordinal + 1
        rows.append((label, section, tab, ordinal, expansion, element))
    rows.sort(key=lambda r: (r[2], r[1], r[0]))
    return rows


def value_text(element):
    """控件当前值的一行显示，未保存清单要用。"""
    value = getattr(element, 'value', None)
    if isinstance(value, bool):
        return '开' if value else '关'
    if value is None or value == '' or value == []:
        return '（空）'
    if isinstance(value, list):
        return f'{len(value)} 行'
    return str(value)[:40]
