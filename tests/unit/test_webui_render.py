"""UI 结构回归：把整个 webui 在进程内构建一遍，并对元素树做指纹比对。

为什么需要这个：其余单测刻意绕开 nicegui，所以「某个控件不再渲染」这种回归它们完全看不见
——实测把 nicegui 从 1.4.30 换到 3.18.0，120 个用例一字不改全部通过。
这个测试直接跑真正的构建路径，是升级 nicegui 时唯一的 UI 侧安全网。

重新生成基线（确认过差异都是有意为之之后）：
    python -m pytest tests/unit/test_webui_render.py --update-ui-baseline
"""

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASELINE = pathlib.Path(__file__).resolve().parent / "webui_render_baseline.json"

KNOWN_TABS = [
    "通用配置", "大语言模型", "文本转语音", "变声", "虚拟身体", "文案", "聊天",
    "图像识别", "积分", "助播", "翻译", "串口", "数据分析", "页面配置",
    "文档&教程", "关于",
]


@pytest.fixture(scope="module")
def ui_root(tmp_path_factory):
    """在进程内构建整个 webui，返回元素树根。"""
    cfg = tmp_path_factory.mktemp("uicfg") / "config.json"
    data = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    # 别让「自动运行」在测试里真把 main.py 拉起来
    data.setdefault("webui", {})["auto_run"] = False
    data.setdefault("login", {})["enable"] = False
    cfg.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    helper = tmp_path_factory.mktemp("helper") / "build.py"
    helper_source = f"""\
import os, sys, json
sys.stdout.reconfigure(encoding='utf-8')
os.environ['LUNA_CONFIG_PATH'] = {str(cfg)!r}
sys.path.insert(0, {str(ROOT)!r})
os.chdir({str(ROOT)!r})
from nicegui import ui, Client
ui.run = lambda *a, **kw: None
import importlib.util
spec = importlib.util.spec_from_file_location('webui_app_under_test', 'webui.py')
mod = importlib.util.module_from_spec(spec)
sys.modules['webui_app_under_test'] = mod
spec.loader.exec_module(mod)

def find_root():
    # nicegui 1.x 把模块级 UI 挂在 Client.auto_index_client 上；
    # 3.x 删掉了 auto_index 这个概念，元素落在 Client.instances 里唯一的那个 client。
    # 两种都支持，这份基线才能在同一份测试下跨版本比对。
    auto = getattr(Client, 'auto_index_client', None)
    if auto is not None:
        return auto.layout
    instances = getattr(Client, 'instances', None) or {{}}
    if len(instances) != 1:
        raise SystemExit(f'期望恰好一个 client，实际 {{len(instances)}} 个')
    return next(iter(instances.values())).layout

root = find_root()

def kids(e):
    for slot in getattr(e, 'slots', {{}}).values():
        for c in slot:
            yield c

def walk(e):
    yield e
    for c in kids(e):
        yield from walk(c)

kinds, texts, total = {{}}, {{}}, 0

def visible_text(el):
    # ui.tab 的名字不在 .text/.label 上，而是落在 _props['label']；
    # ui.input/ui.select 的占位提示在 _props['placeholder']
    for attr in ('text', 'label'):
        v = getattr(el, attr, None)
        if isinstance(v, str) and v.strip():
            return v.strip()
    props = getattr(el, '_props', None) or {{}}
    for key in ('label', 'placeholder'):
        v = props.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None

for el in walk(root):
    n = type(el).__name__
    kinds[n] = kinds.get(n, 0) + 1
    total += 1
    v = visible_text(el)
    if v:
        texts[v] = texts.get(v, 0) + 1

print('@@FINGERPRINT@@' + json.dumps(
    {{'kinds': kinds, 'texts': texts, 'total_elements': total, 'distinct_texts': len(texts)}},
    ensure_ascii=False, sort_keys=True))
"""
    helper.write_text(helper_source, encoding="utf-8")

    # 子进程跑：webui 导入期会注册路由、建 Audio、起定时器，污染同一次 pytest 会话的其它用例。
    # errors="replace" 是必需的：loguru 往 stderr 写中文，Windows 上是 GBK，
    # 严格 utf-8 解码会让读取线程崩掉、把 proc.stdout/stderr 变成 None。
    proc = subprocess.run(
        [sys.executable, str(helper)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT), timeout=180,
    )
    marker = "@@FINGERPRINT@@"
    line = next((l for l in (proc.stdout or "").splitlines() if marker in l), None)
    if line is None:
        pytest.fail(
            "webui 构建失败（未拿到指纹）\n"
            f"returncode={proc.returncode}\n"
            f"stdout(tail):\n{(proc.stdout or '')[-3000:]}\n"
            f"stderr(tail):\n{(proc.stderr or '')[-3000:]}"
        )

    return json.loads(line.split(marker, 1)[1])


def _diff(baseline, current):
    out = []
    for section in ("kinds", "texts"):
        b, c = baseline.get(section, {}), current.get(section, {})
        for key in sorted(set(b) | set(c)):
            if b.get(key) != c.get(key):
                out.append(f"  {section}.{key}: {b.get(key)} -> {c.get(key)}")
    for key in ("total_elements", "distinct_texts"):
        if baseline.get(key) != current.get(key):
            out.append(f"  {key}: {baseline.get(key)} -> {current.get(key)}")
    return out


def test_webui_builds_and_matches_structure(ui_root, request):
    """整个 UI 必须能构建，且元素种类/文案与基线一致。"""
    if request.config.getoption("--update-ui-baseline"):
        BASELINE.write_text(json.dumps(ui_root, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        pytest.skip("已写入基线，请复核 git diff 后重新运行")

    assert BASELINE.exists(), (
        "缺少 UI 基线，先跑：python -m pytest tests/unit/test_webui_render.py --update-ui-baseline"
    )

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    delta = _diff(baseline, ui_root)

    assert not delta, "UI 结构相对基线发生变化：\n" + "\n".join(delta[:60])


def test_every_tab_is_rendered(ui_root):
    """16 个 tab 一个都不能少。"""
    texts = ui_root["texts"]

    missing = [t for t in KNOWN_TABS if t not in texts]
    assert not missing, f"以下 tab 未渲染：{missing}"


def test_no_empty_page(ui_root):
    """构建出来只剩个空壳通常是导入中途抛异常的表征。"""
    assert ui_root["total_elements"] > 1000, f"元素总数异常偏少：{ui_root['total_elements']}"
