"""「第 N 组」的选取器：下拉列出真实存在的行，不再让人数序号（走查 audit-10）。

原先每个可增删的组旁边摆着一个「配置索引」输入框，提示写着「第一个组是1，第二个组是2」：
一是要手数列；二是删过一次之后**位置与 #N 标号就会错位**——屏幕上标着 #2 的那行才是第一个位置，
按 2 填进去删掉的反而是标号 #3 那行。所以这里直接列出还看得见的行，摘要取行上第一个控件的
名字与当前值：用户挑的是自己看到的东西，位置由这里换算。
"""
from nicegui import context, ui

from webui_app import confirm as confirm_module
from webui_app.confirm import GROUP_DETAIL
from webui_app.fields import field_name, value_text
from webui_app.undo import undo

SELECT_WIDTH = 'width:320px;'
# 每个客户端自己一份（一个标签页一套元素树，共用列表会串页）
_REGISTRY = '_group_pickers'


def _registry():
    client = context.client
    pickers = getattr(client, _REGISTRY, None)
    if pickers is None:
        pickers = []
        setattr(client, _REGISTRY, pickers)
    return pickers


def refresh_pickers():
    """建页收尾时把所有选取器的下拉填上——别用定时器补。

    原先是 ui.timer(0.2, refresh, once=True)：这页要建 10 多秒，0.2 秒的那一枪经常在
    浏览器还没连上时就打完了，once 的定时器不会补第二枪，实测结果就是下拉点开是空的
    （「要删除的文案组」里啥也没有），得切一次页再回来才有选项。
    """
    for picker in _registry():
        picker.refresh()


class GroupPicker:
    """一张「一组一行」的卡片 + 一个下拉。

    card 与 var 传的都是「取值函数」：真实页面里卡片和控件字典是在这一行之后才创建的，
    直接传会变成 UnboundLocalError；同理第一次列行要等建页循环跑完，收尾时统一 refresh。
    action(位置) 只负责把这一组的键从 var 里挪走——行的收起与撤销在这里做。
    """

    def __init__(self, card, name, action, var):
        self._card = card
        self._name = name
        self._action = action
        self._var = var
        self._titles = {}
        self.select = None

    def build(self):
        self.select = ui.select(label=f'要删除的{self._name}组', options={}) \
            .props('outlined dense options-dense clearable').style(SELECT_WIDTH)
        # 它只是个选择器，值不写进配置：标一下，脏状态守卫与全局搜索都跳过它
        self.select.is_config_field = False
        _registry().append(self)      # 选项在建页收尾时由 refresh_pickers() 填
        return self

    def rows(self):
        """(第几组, 行元素)：只数还看得见的行，序号从 0 连续。

        连续序号同时是 var 里的组号——各页面删完会把后面的键往前挪，所以两边对得上；
        收起的行仍占着卡片里的位置，不能拿它当序号。
        """
        visible = [row for row in self._card() if getattr(row, 'visible', True) is not False]
        return list(enumerate(visible))

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
        row = dict(self.rows()).get(pos)
        if row is None:
            ui.notify(position='top', type='warning', message=f'请先选要删除的「{self._name}」组')
            return
        title = self._titles.get(pos, f'第 {pos + 1} 组')
        confirm_module.confirm.ask(
            f'确认删除「{self._name}」这一组？（{title}）',
            lambda: self._delete(row, pos, dict(self._var()), title), GROUP_DETAIL)

    def _delete(self, row, pos, snapshot, title):
        # 行一旦被 card.remove() 掉，NiceGUI 会清空它整棵子树的 slot 与事件监听，重建不回来；
        # 所以「删除」= 收起这一行 + 把它的键从 var 挪走。保存链路读的是 var，效果与硬删一致。
        row.set_visibility(False)
        self._action(pos)
        self.refresh()
        undo.offer(f'已删除「{self._name}」{title}', lambda: self._restore(row, snapshot))

    def _restore(self, row, snapshot):
        var = self._var()
        var.clear()
        var.update(snapshot)
        row.set_visibility(True)
        self.refresh()
