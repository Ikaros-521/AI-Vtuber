"""运行日志入口（webui_app/run_log.py）：只读文件末尾，且有硬上限。

日志文件按 1GB 滚动，"打开日志"要是整份读进来会把 webui 自己拖死，
所以这里钉两件事：读到的行数有上限、超限时的说明要如实写"往前的没读"。
"""

from webui_app.run_log import MAX_LINES, tail


def write_log(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_small_file_returns_every_line(tmp_path):
    log = tmp_path / "log.txt"
    write_log(log, ["第一行", "第二行", "第三行"])
    lines, note = tail(str(log))
    assert lines == ["第一行", "第二行", "第三行"]
    assert note == "共 3 行"


def test_big_file_is_cut_to_the_tail_and_says_so(tmp_path):
    log = tmp_path / "log.txt"
    write_log(log, [f"第{i}行 " + "x" * 300 for i in range(1, 101)])
    lines, note = tail(str(log), limit=5)
    assert len(lines) == 5
    assert lines[-1].startswith("第100行")
    assert "往前的没读" in note


def test_many_short_lines_are_still_capped(tmp_path):
    """真实日志就是一堆短行：按字节算窗口不够，行数必须自己截住。"""
    log = tmp_path / "log.txt"
    write_log(log, [f"2026-10-25 12:00:{i % 60:02d}.000 | INFO | 第 {i} 条" for i in range(1, 3428)])
    lines, note = tail(str(log))
    assert len(lines) == MAX_LINES
    assert lines[-1].startswith("2026-10-25")
    assert "只显示最后 400 行" in note


def test_missing_file_does_not_raise(tmp_path):
    lines, note = tail(str(tmp_path / "没有这个文件.txt"))
    assert lines == []
    assert "读不到日志文件" in note


def test_default_cap_is_bounded():
    assert MAX_LINES == 400
