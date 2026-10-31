"""把异常翻成一句能照着做的提示（走查 audit-28）。

原先串口那四处回调把整段 traceback 拼进 toast：用户读到的是路径和术语，没有下一步动作。
traceback 本来就已经进日志了，toast 只留一句可行动的话。
"""

import json

from nicegui import ui

# 模块名不等于发行包名，照着 ModuleNotFoundError.name 让用户 pip install 会装错东西
# （`pip install serial` 装的是另一个无关包，串口要的是 pyserial）
DISTS = {"serial": "pyserial", "PIL": "pillow"}


def explain(e: BaseException) -> str:
    """常见成因给具体指引，其余截断后原样给出（别让提示自己变成一屏堆栈）。"""
    if isinstance(e, ModuleNotFoundError):
        name = getattr(e, "name", None) or str(e)
        dist = DISTS.get(name.split(".")[0], name)
        return f"缺少依赖 {name}，装上再重启 webui：pip install {dist}"
    if isinstance(e, PermissionError):
        return "文件被别的程序占用或没有写入权限，关掉编辑器/资源管理器后重试"
    if isinstance(e, FileNotFoundError):
        path = getattr(e, "filename", None) or str(e)
        return f"找不到文件或文件夹：{path}，检查配置里填的路径"
    if isinstance(e, json.JSONDecodeError):
        return f"JSON 语法不正确（第 {e.lineno} 行第 {e.colno} 列）"
    # 折行：多行的异常文本会撑出一条刷屏的 toast
    text = " ".join(str(e).split()) or e.__class__.__name__
    return text[:160]


def notify_error(e: BaseException, what: str) -> None:
    """统一出口：一句「什么失败了 + 为什么 + 怎么办」。"""
    ui.notify(position="top", type="negative", message=f"{what}失败：{explain(e)}（完整错误见服务端日志）")
