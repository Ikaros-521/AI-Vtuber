"""luna/agent 依赖方向守卫（docs/agent-upgrade-design.md §2/§9）。

luna/agent 只准依赖：自身、luna/common、luna/infra，以及两个纯工具模块
luna.core.message（消息构造）与 luna.core.search_engine（搜索纯函数，工具内
延迟导入）。对 My_handle 其余能力一律经 ctx.handle 注入访问，禁止 import——
否则会跟 my_handle 形成 import 环，也会把 AST 守卫自动检查的价值稀释掉。
"""

import ast
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
AGENT_DIR = ROOT / "luna" / "agent"

ALLOWED_PREFIXES = ("luna.agent.", "luna.common.", "luna.infra.")
ALLOWED_EXACT = {"luna.agent", "luna.common", "luna.infra", "luna.core.message", "luna.core.search_engine"}

AGENT_FILES = sorted(str(p) for p in AGENT_DIR.rglob("*.py") if "__pycache__" not in str(p))


def _import_targets(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            # level > 0 是包内相对导入，天然合规
            yield node.module


def offending_imports(path):
    tree = ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))
    offenders = []
    for module in _import_targets(tree):
        if not module.startswith("luna."):
            continue
        if module in ALLOWED_EXACT or module.startswith(ALLOWED_PREFIXES):
            continue
        offenders.append(f"{path}: import {module}")
    return offenders


@pytest.mark.parametrize("path", AGENT_FILES)
def test_agent_only_imports_allowed_domains(path):
    assert offending_imports(path) == []


def test_agent_package_is_discovered():
    assert any(p.endswith(("runtime.py", "registry.py")) for p in AGENT_FILES), "luna/agent 不存在？"
