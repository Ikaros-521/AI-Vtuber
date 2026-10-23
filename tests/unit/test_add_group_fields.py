"""「增加配置组」这类回调的字段自检。

这些函数是复制粘贴重灾区，而且只在点击时才跑，页面能正常构建不代表它们是好的：
key_mapping_add 就同时坏了两处——读 tmp_config["serial_name"] 时键根本不存在（一点就 KeyError，
界面上什么也不发生），另外两个控件抄错成了「文案」「串口发送内容」的重复项。
"""
import ast
import io
import re
from pathlib import Path

PAGES_DIR = Path(__file__).resolve().parents[2] / 'webui_app' / 'pages'
PAGES = sorted(PAGES_DIR.glob('*.py'))

# 每个 <名>_add() 里，控件的 label 顺序要与建页循环里同一批 _var 的顺序一致
ADD_RE = re.compile(r'def (\w+)_add\(\):')


def _functions(src):
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            yield node


def _tmp_config_keys(func):
    """func 里 `tmp_config = {...}` 声明的键。"""
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if 'tmp_config' in names:
                return {k.value for k in node.value.keys if isinstance(k, ast.Constant)}
    return None


def _tmp_config_reads(func):
    out = set()
    for node in ast.walk(func):
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name)
                and node.value.id == 'tmp_config' and isinstance(node.slice, ast.Constant)):
            out.add(node.slice.value)
    return out


def _labels(func):
    """按源码顺序取这个函数里控件的 label（去掉 #N 后缀）。"""
    out = []
    for node in ast.walk(func):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            for kw in node.keywords:
                if kw.arg == 'label' and isinstance(kw.value, ast.JoinedStr):
                    text = ''.join(v.value for v in kw.value.values if isinstance(v, ast.Constant))
                    out.append(re.sub(r'#.*$', '', text).strip())
    return out


def test_add_callbacks_only_read_declared_defaults():
    """每个 *_add() 读到的默认值键，必须在它自己的 tmp_config 里声明过。"""
    bad = []
    for path in PAGES:
        for func in _functions(io.open(path, encoding='utf-8').read()):
            if not func.name.endswith('_add'):
                continue
            declared = _tmp_config_keys(func)
            assert declared is not None, f'{path.name}:{func.name} 没有 tmp_config 字面量'
            missing = _tmp_config_reads(func) - declared
            if missing:
                bad.append(f'{path.name}:{func.name} 读了没有默认值的键 {sorted(missing)}')
    assert not bad, '\n'.join(bad)


def test_key_mapping_group_matches_the_saved_fields():
    """按键映射一组的九个字段：新增出来的要和建页循环、保存读回的是同一批。"""
    src = io.open(PAGES_DIR / 'common_config.py', encoding='utf-8').read()
    func = next(f for f in _functions(src) if f.name == 'key_mapping_add')
    assert _labels(func) == ['关键词', '礼物', '按键', '相似度', '文案', '本地音频', '串口名',
                             '串口发送内容', '图片路径']
    assert _tmp_config_reads(func) == _tmp_config_keys(func)
