"""「第 N 组」的选取器：下拉列出真实存在的行，不再让人数序号（走查 audit-10）。

原先每个可增删的组旁边摆着一个「配置索引」输入框，提示写着「第一个组是1，第二个组是2」：
一是要手数列；二是删过一次之后**位置与 #N 标号就会错位**——屏幕上标着 #2 的那行才是第一个位置，
按 2 填进去删掉的反而是标号 #3 那行。所以这里直接列出还看得见的行，摘要取行上第一个控件的
名字与当前值：用户挑的是自己看到的东西，位置由这里换算。
"""
from nicegui import ui

from webui_app import confirm as confirm_module
from webui_app.confirm import GROUP_DETAIL
from webui_app.fields import field_name, value_text

SELECT_WIDTH = 'width:320px;'


class GroupPicker:
    """一张「一组一行」的卡片 + 一个下拉。删除动作由各页面传进来的 action(位置) 完成。

    card 传的是「取卡片的函数」：真实页面里那几张卡片是在这一行之后才 ui.card() 出来的，
    直接传元素会变成 UnboundLocalError；同理第一次列行也要等建页循环跑完，交给一次性定时器补。
    """

    def __init__(self, card, name, action):
        self._card = card
        self._name = name
        self._action = action
        self._titles = {}
        self.select = None

    def build(self):
        self.select = ui.select(label=f'要删除的{self._name}组', options={}) \
            .props('outlined dense options-dense clearable').style(SELECT_WIDTH)
        # 它只是个选择器，值不写进配置：标一下，脏状态守卫与全局搜索都跳过它
        self.select.is_config_field = False
        ui.timer(0.2, self.refresh, once=True)
        return self

    def rows(self):
        """(卡片里的位置, 行元素)，只数还看得见的行。"""
        return [(i, row) for i, row in enumerate(self._card())
                if getattr(row, 'visible', True) is not False]

    def _title(self, row):
        for element in row.descendants():
            label = field_name(element)
            if label:
                return f'{label} · {value_text(element)}'[:46]
        return '（这一行没有控件）'

    def refresh(self):
        options = {pos: self._title(row) for pos, row in self.rows()}
        self._titles = options
        keep = self.select.value
        self.select.options = options
        self.select.value = keep if keep in options else None
        self.select.update()

    @property
    def position(self):
        return self.select.value

    def ask_delete(self):
        """没选组就不删；删之前把「删的是哪一行」写在确认框里。"""
        pos = self.position
        if pos is None:
            ui.notify(position='top', type='warning', message=f'请先选要删除的「{self._name}」组')
            return
        confirm_module.confirm.ask(f'确认删除「{self._name}」这一组？（{self._titles.get(pos, pos)}）',
                                   lambda: (self._action(pos), self.refresh()), GROUP_DETAIL)
