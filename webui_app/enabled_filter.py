"""「只看已启用」视图（走查 audit-9）：把「启用…」开关关着的卡片与折叠区先从屏上拿走。

850 多个控件、单页最长 17,645px，新用户找「弹幕保留数」只能人肉滚。搜索解决「我知道名字」，
这个开关解决「我想知道还有啥没开」——实测默认配置下能拿走 25 处、359 个配置项。

两条不能破的规矩：
1. 藏只加 CSS 类，控件的 visible 仍是 True。走 set_visibility 会被 fields.hidden() 当成
   「不存在」，全局搜索与未保存清单就索引不到被藏的项了。
2. 藏是可见的：开关旁边实时写「已藏 N 处 · M 个配置项」，跳过去前自动取消过滤。
"""

from nicegui import context, ui
from nicegui.elements.card import Card
from nicegui.elements.expansion import Expansion
from nicegui.elements.tabs import TabPanel

from webui_app.fields import INPUT_TYPES, field_name
from webui_app.theme import INK_MUT

CONTAINERS = (Card, Expansion)
OFF_CLASS = "luna-off-card"  # 标在当前「启用开关全关」的容器上
FILTER_CLASS = "luna-only-on"  # 标在 tab_panels 上，样式表只在这类存在时才藏
EMPTY_CLASS = "luna-panel-empty"  # 标在「一页全被藏光」的面板上，样式表给它补一句解释


def _owner_container(switch):
    """开关归属哪个容器：最近的那个卡片或折叠区。

    不归最近的卡而往上找，「过滤」整张 60 字段的卡会被里面两个关着的子折叠区带走（实测踩过）。
    """
    for ancestor in switch.ancestors():
        if isinstance(ancestor, CONTAINERS):
            return ancestor
    return None


def _direct_switches(container):
    return [
        s
        for s in container.descendants()
        if isinstance(s, (ui.switch, ui.checkbox))
        and field_name(s).startswith("启用")
        and _owner_container(s) is container
    ]


def disabled_containers():
    """现在该被藏起来的容器（祖先已经入选的不重复算，统计口径才是「顶层」）。"""
    picked = []
    for element in context.client.elements.values():
        if not isinstance(element, CONTAINERS):
            continue
        switches = _direct_switches(element)
        if switches and all(bool(s.value) is False for s in switches):
            picked.append(element)
    return [el for el in picked if not any(isinstance(a, CONTAINERS) and a in picked for a in el.ancestors())]


def config_field_count(containers):
    """这些容器里有多少个配置项——按搜索索引同一口径数，报出来的数字才对得上。"""
    inside = set()
    for container in containers:
        inside.update(e.id for e in container.descendants())
    return sum(
        1
        for el in context.client.elements.values()
        if isinstance(el, INPUT_TYPES) and getattr(el, "is_config_field", True) is not False and el.id in inside
    )


class EnabledFilter:
    """导航条上那个「只看已启用」开关。全站每客户端一个，挂在 tab_panels 上做显示切换。"""

    def __init__(self):
        self._on = False
        self._switch = None
        self._tip = None
        self._panels = None
        self._timer = None
        self._marked = []

    def build_switch(self):
        """由 build_nav_chips 在搜索按钮后面调用，所以这里建在导航条那一行里。"""
        self._switch = (
            ui.switch("只看已启用", on_change=self._toggled)
            .props("dense size=sm")
            .tooltip("只藏起「启用…」开关关着的卡片和折叠区；配置不会丢，搜索或点未保存清单跳过去时会自动取消过滤")
        )
        # 视图过滤开关不是配置项：不打这个标，DirtyGuard 会把切换记成「1 项未保存」
        self._switch.is_config_field = False
        self._tip = ui.label("").style(f"font-size:12px;color:{INK_MUT};")
        # 运行期点「增加配置组」会现造带启用开关的行，开关开着时得跟得上
        self._timer = ui.timer(2.0, self.resweep, active=False)

    def bind_panels(self, panels) -> None:
        """把 ui.tab_panels 的元素交进来，过滤类只往它身上挂。"""
        self._panels = panels

    def _toggled(self, event) -> None:
        self._on = bool(event.value)
        if self._timer is not None:
            self._timer.active = self._on
        self.resweep()

    def resweep(self) -> None:
        off = disabled_containers()
        for element in self._marked:
            if element not in off:
                element.classes(remove=OFF_CLASS)
        for element in off:
            element.classes(OFF_CLASS)
        self._marked = off
        self._paint_empty_panels(off)
        if self._panels is not None:
            if self._on:
                self._panels.classes(FILTER_CLASS)
            else:
                self._panels.classes(remove=FILTER_CLASS)
        self._paint_tip(off)

    def _paint_empty_panels(self, off) -> None:
        """整页被藏光时要留一句话：实测点歌页只剩一条蓝带，看上去就是页面坏了。"""
        hidden = {id(e) for e in off}
        for e in off:
            hidden.update(id(d) for d in e.descendants())
        for panel in (p for p in context.client.elements.values() if isinstance(p, TabPanel)):
            tops = [
                c
                for c in panel.descendants()
                if isinstance(c, CONTAINERS) and not any(isinstance(a, CONTAINERS) for a in c.ancestors())
            ]
            if tops and all(id(c) in hidden for c in tops):
                panel.classes(EMPTY_CLASS)
            else:
                panel.classes(remove=EMPTY_CLASS)

    def _paint_tip(self, off) -> None:
        if self._tip is None:
            return
        if not self._on:
            self._tip.set_text("")
            return
        fields = config_field_count(off)
        self._tip.set_text(f"已藏 {len(off)} 处 · {fields} 个配置项" if off else "全部卡片都已启用")

    def turn_off(self) -> None:
        """跳转前先取消过滤：藏起来的框 scrollIntoView 是滚不到的。"""
        if not self._on:
            return
        self._on = False
        if self._timer is not None:
            self._timer.active = False
        if self._switch is not None:
            self._switch.set_value(False)
        self.resweep()

    @property
    def is_on(self):
        return self._on
