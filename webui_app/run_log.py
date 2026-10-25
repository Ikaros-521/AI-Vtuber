"""底栏的「运行日志」入口：把今天日志文件的末尾读进对话框。

走查 audit-3 剩下的那一半：一键运行 / 停止 / 重启之后，界面只有一条会自行消失的顶部 toast，
真出问题（端口被占、平台连不上、依赖没装）用户得自己去翻文件。这里给一个入口，
并且明确写死只读末尾若干行——日志文件按 1GB 滚动，整份读进来会把 webui 自己拖死。
"""
import os

from nicegui import ui

from webui_app.errors import explain

# 硬上限：只从文件尾部按字节往回读这么多，再多就不读
MAX_LINES = 400
BYTES_PER_LINE = 2048


def tail(path, limit=MAX_LINES):
    """返回 (行列表, 一句话说明)。文件不在/读不动时不抛异常，界面要能说明原因。

    行数要真的截住：实测今天的日志 3427 行 / 544KB，只按「字节窗口」判断
    （窗口 = 行数 × 每行估算字节数）会以为"文件比窗口小"而把整份塞进浏览器。
    """
    try:
        with open(path, 'rb') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - limit * BYTES_PER_LINE))
            read_from = f.tell()
            text = f.read().decode('utf-8', errors='replace')
    except OSError as e:
        return [], f'读不到日志文件：{explain(e)}'
    lines = text.splitlines()
    if read_from > 0 and lines:
        lines = lines[1:]       # 窗口开头那行是被切开的半行
    cut = read_from > 0 or len(lines) > limit
    lines = lines[-limit:]
    if cut:
        return lines, f'只显示最后 {len(lines)} 行（文件共 {max(1, size // 1024)} KB，往前的没读）'
    return lines, f'共 {len(lines)} 行'


class RunLog:
    """对话框必须在建页时建好（NiceGUI 的 dialog 在事件回调里现建不落布局），点入口只填内容。"""

    def __init__(self, path_getter):
        self._path_getter = path_getter
        self.dialog = None
        self._title = None
        self._note = None
        self._body = None

    def build(self):
        with ui.dialog() as self.dialog, ui.card().style('width:100%;max-width:1000px;'):
            with ui.row().classes('items-center').style('gap:8px;width:100%;'):
                self._title = ui.label('运行日志').style('font-size:15px;font-weight:600;')
                self._note = ui.label('').style('font-size:12px;color:#4b5563;')
                ui.space()
                ui.button('刷新', icon='refresh', on_click=self.refresh).props('flat dense no-caps')
                ui.button('关闭', on_click=self.dialog.close).props('flat dense no-caps')
            self._body = ui.code('', language=None).classes('w-full').style(
                'max-height:60vh;overflow:auto;white-space:pre-wrap;word-break:break-all;'
                'font-size:12px;line-height:1.5;')
        return self

    def refresh(self):
        path = self._path_getter() or ''
        lines, note = tail(path)
        self._title.set_text(f'运行日志 · {os.path.basename(path)}')
        self._note.set_text(note)
        # ui.code 是 ContentElement，没有 set_text，改内容要写 .content
        self._body.content = '\n'.join(lines) or '（这个日志文件目前是空的）'

    def open(self):
        self.refresh()
        self.dialog.open()
