"""平台监听器的作用域静态检查 + websockets handler 契约。

这三个检查都是为了一类反复出现的真实缺陷：监听器互相抄，抄的时候把
`global`/模块级绑定丢了，于是「在线人数到区间就切配置模板」这种分支
一跑到就 UnboundLocalError，被外面的 except 吞成一条 traceback。
2026-10-22 修掉的三处（dy.py 的 config_path、dy2.py 的 config/config_path + 5 个漏掉的
import、ks.py 里 `global config, common, my_handle` 遮蔽外层形参）都能被这里抓到。
"""

import ast
import builtins
import inspect
import os
import pathlib

import pytest

from fakes import FakeConfig

CRLF, NL = chr(13) + chr(10), chr(10)
DUNDER = {"__file__", "__name__", "__doc__", "__package__", "__spec__", "__loader__", "__builtins__", "__debug__"}

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _production_files():
    out = [str(p) for d in ("luna",) for p in (ROOT / d).rglob("*.py")]
    out += [str(ROOT / "main.py")]
    return sorted(f for f in out if "__pycache__" not in f)


PRODUCTION_FILES = _production_files()
LISTENERS = sorted(str(p) for p in (ROOT / "utils" / "platforms").glob("*.py"))


def read(path):
    return open(path, encoding="utf-8", newline="").read().replace(CRLF, NL)


def add_bindings(tree, bound):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name != "*":
                    bound.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            bound.add(node.id)
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
    return bound


def module_scope(path, tree):
    """这个模块里「按名字能解析到」的东西，含 from x import * 带进来的"""
    bound = set(dir(builtins)) | DUNDER
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name != "*":
                    continue
                dep = (node.module or "").replace(".", os.sep)
                for cand in (str(ROOT / dep / "__init__.py"), str(ROOT / (dep + ".py"))):
                    if os.path.exists(cand):
                        add_bindings(ast.parse(read(cand)), bound)
    add_bindings(tree, bound)
    return bound


def top_level_names(tree):
    """模块作用域里绑定的名字。

    要下钻模块层的 if/try/for/with —— `if __name__ == '__main__':` 里的赋值同样是
    模块级绑定（main.py 的语音状态标志就在那里初始化）。函数体和类体是另一层作用域，
    不算进来。
    """
    names = set()

    def add_target(t):
        for inner in ast.walk(t):
            if isinstance(inner, ast.Name):
                names.add(inner.id)

    def walk(nodes):
        for node in nodes:
            if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in targets:
                    add_target(t)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    if alias.name != "*":
                        names.add((alias.asname or alias.name).split(".")[0])
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.With):
                for item in node.items:
                    if item.optional_vars is not None:
                        add_target(item.optional_vars)
                walk(node.body)
            elif isinstance(node, ast.Try):
                for body in (node.body, node.orelse, node.finalbody):
                    walk(body)
                for handler in node.handlers:
                    if handler.name:
                        names.add(handler.name)
                    walk(handler.body)
            elif isinstance(node, (ast.If, ast.For, ast.While)):
                walk(node.body)
                walk(node.orelse)

    walk(tree.body)
    return names


def own_body(func):
    """只遍历这个函数体本身，不下钻到嵌套的函数/类"""
    stack, out = list(func.body), []
    while stack:
        node = stack.pop()
        out.append(node)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        stack.extend(ast.iter_child_nodes(node))
    return out


def first_lines(nodes):
    assigned, loaded = {}, {}
    for node in nodes:
        if isinstance(node, ast.Name):
            bucket = assigned if isinstance(node.ctx, ast.Store) else loaded if isinstance(node.ctx, ast.Load) else None
            if bucket is None:
                continue
            if node.id not in bucket or node.lineno < bucket[node.id]:
                bucket[node.id] = node.lineno
    return assigned, loaded


def unbound_names(path):
    tree = ast.parse(read(path))
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return sorted(used - module_scope(path, tree))


def reads_before_assignment(path):
    """函数在赋值之前先读了「外层已有绑定」的名字 -> 一跑到就是 UnboundLocalError"""
    tree = ast.parse(read(path))
    offenders = []
    for outer in ast.walk(tree):
        if not isinstance(outer, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        candidates = top_level_names(tree) | {a.arg for a in outer.args.args + outer.args.kwonlyargs}
        for inner in ast.walk(outer):
            if inner is outer or not isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            nodes = own_body(inner)
            declared = set()
            for node in nodes:
                if isinstance(node, (ast.Global, ast.Nonlocal)):
                    declared |= set(node.names)
            assigned, loaded = first_lines(nodes)
            for name in sorted((set(assigned) & candidates) - declared):
                if name in loaded and loaded[name] < assigned[name]:
                    offenders.append("%s:%s %s 在赋值前先读了 %s" % (path, inner.lineno, inner.name, name))
    return sorted(offenders)


def globals_without_module_binding(path):
    tree = ast.parse(read(path))
    top = top_level_names(tree)
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Global):
            bad += [
                "%s:%s global %s（模块级没有这个绑定）" % (path, node.lineno, name)
                for name in node.names
                if name not in top
            ]
    return sorted(bad)


@pytest.mark.parametrize("path", PRODUCTION_FILES)
def test_no_name_used_without_any_binding(path):
    assert unbound_names(path) == []


@pytest.mark.parametrize("path", PRODUCTION_FILES)
def test_no_read_of_outer_name_before_local_assignment(path):
    assert reads_before_assignment(path) == []


@pytest.mark.parametrize("path", PRODUCTION_FILES)
def test_global_declares_only_module_level_names(path):
    assert globals_without_module_binding(path) == []


def process_types_without_idle_reset(path):
    """收到消息就要把闲时计时清零，否则闲时自动讲话会在观众正聊得欢时插进来。

    每个 my_handle.process_data(data, "X") 的类型 X，都该在同文件里有一次
    my_global.idle_time_auto_clear(config, "X")。
    """
    tree = ast.parse(read(path))
    sent, cleared = set(), set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if len(node.args) < 2 or not isinstance(node.args[1], ast.Constant):
            continue
        if node.func.attr == "process_data":
            sent.add(node.args[1].value)
        elif node.func.attr == "idle_time_auto_clear":
            cleared.add(node.args[1].value)
    return sorted(sent - cleared)


@pytest.mark.parametrize("path", LISTENERS)
def test_every_message_type_also_resets_the_idle_timer(path):
    assert process_types_without_idle_reset(path) == []


# ---------- websockets handler 契约 ----------


def _capture_served_handler(monkeypatch, module):
    captured = {}

    class FakeServer:
        async def wait_closed(self):
            return None

    async def fake_serve(handler, *args, **kwargs):
        captured["handler"] = handler
        return FakeServer()

    monkeypatch.setattr(module.websockets, "serve", fake_serve)
    module.start_listen(FakeConfig({}), None, None, "douyu")
    return captured["handler"]


def test_lx_handler_takes_the_single_connection_argument(monkeypatch):
    """websockets 14 起 serve 只把 connection 一个参数传给 handler。
    多写一个 path 会在每次客户端连上时抛 TypeError，而走这个助手的平台
    （统一项 + ks2/pdd/douyu/1688/taobao 五个旧别名）全靠它，一条弹幕都进不来。"""
    import luna.platforms.lx_live_monitor_assistant as lx

    handler = _capture_served_handler(monkeypatch, lx)
    params = [
        p
        for p in inspect.signature(handler).parameters.values()
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
    ]
    assert len(params) == 1, "on_message 应该只收 connection 一个参数，现在是 %s" % ([p.name for p in params])
