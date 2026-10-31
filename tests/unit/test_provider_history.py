"""历史长度统计，和「别把观众输入交给 re.sub 当替换模板」的静态检查。"""

import ast
import pathlib


from utils.history import total_chars

ROOT = pathlib.Path(__file__).resolve().parents[2]
CRLF, NL = chr(13) + chr(10), chr(10)


def test_dict_history_counts_the_content_not_the_key_names():
    history = [{"role": "user", "content": "今天天气怎么样"},
               {"role": "assistant", "content": "晴"}]

    # 以前那句 for string in sublist 遍历的是字典的键，恒等于 11 字符/条
    assert total_chars(history) == 8


def test_gemini_parts_list_is_flattened():
    history = [{"role": "user", "parts": ["你好"]}, {"role": "model", "parts": ["呀", "嘛"]}]

    assert total_chars(history) == 4


def test_pair_history_matches_the_old_expression():
    history = [["问一句话", "答一句话"], ["再问", "再答"]]
    old = sum(len(string) for sublist in history for string in sublist)

    assert total_chars(history) == old == 12


def test_empty_history_is_zero():
    assert total_chars([]) == 0


def _no_variable_replacement_templates():
    """re.sub 的第二个参数是替换模板：写成裸变量，值里的 \\1、\\g<0> 会被解析。

    违禁词、用户名、弹幕内容都可能带反斜杠，所以只允许字面量或函数形式的替换串。
    """
    offenders = []
    for path in sorted((ROOT / 'utils').rglob('*.py')):
        if '__pycache__' in str(path):
            continue
        tree = ast.parse(open(path, encoding='utf-8', newline='').read().replace(CRLF, NL))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'sub'):
                continue
            if len(node.args) < 2:
                continue
            repl = node.args[1]
            if isinstance(repl, ast.Name):        # 直接拿一个变量当模板
                offenders.append('%s:%s re.sub(..., %s, ...)' % (path.name, node.lineno, repl.id))
    return offenders


def test_no_bare_variable_used_as_re_sub_replacement():
    assert _no_variable_replacement_templates() == []
