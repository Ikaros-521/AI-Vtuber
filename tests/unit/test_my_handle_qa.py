"""本地问答库匹配：find_answer（成对文本行）与 find_similar_answer（JSON 关键词）。"""

import json


def test_find_answer_returns_paired_line(configure, tmp_path):
    handle = configure({"filter": {}})
    qa = tmp_path / "qa.txt"
    qa.write_text("今天天气\n晴天\n你叫什么\n小助手\n", encoding="utf-8")

    assert handle.find_answer("今天天气", str(qa)) == "晴天"
    assert handle.find_answer("你叫什么", str(qa)) == "小助手"


def test_find_answer_requires_exact_text_at_default_similarity(configure, tmp_path):
    handle = configure({"filter": {}})
    qa = tmp_path / "qa.txt"
    qa.write_text("今天天气\n晴天\n", encoding="utf-8")

    assert handle.find_answer("今天天气怎么样", str(qa)) is None


def test_find_answer_matches_fuzzily_when_similarity_lowered(configure, tmp_path):
    handle = configure({"filter": {}})
    qa = tmp_path / "qa.txt"
    qa.write_text("今天天气\n晴天\n", encoding="utf-8")

    assert handle.find_answer("今天天气怎么样", str(qa), similarity=0.5) == "晴天"


def test_find_answer_returns_none_when_answer_line_is_missing(configure, tmp_path):
    handle = configure({"filter": {}})
    qa = tmp_path / "qa.txt"
    qa.write_text("问题没有答案", encoding="utf-8")

    assert handle.find_answer("问题没有答案", str(qa)) is None


def test_find_similar_answer_picks_by_keyword(configure, tmp_path):
    handle = configure({"filter": {}})
    qa = tmp_path / "qa.json"
    qa.write_text(json.dumps([
        {"关键词": ["你好", "您好"], "回答": ["你好呀"]},
        {"关键词": ["点歌"], "回答": ["想听什么"]},
    ], ensure_ascii=False), encoding="utf-8")

    assert handle.find_similar_answer("你好", str(qa)) == "你好呀"
    assert handle.find_similar_answer("您好", str(qa)) == "你好呀"


def test_find_similar_answer_below_threshold_returns_none(configure, tmp_path):
    handle = configure({"filter": {}})
    qa = tmp_path / "qa.json"
    qa.write_text(json.dumps([{"关键词": ["点歌"], "回答": ["想听什么"]}], ensure_ascii=False),
                  encoding="utf-8")

    assert handle.find_similar_answer("完全无关的一句话", str(qa)) is None


def test_find_similar_answer_survives_broken_json(configure, tmp_path):
    handle = configure({"filter": {}})
    qa = tmp_path / "qa.json"
    qa.write_text("{not json", encoding="utf-8")

    assert handle.find_similar_answer("你好", str(qa)) is None


def test_find_similar_answer_survives_missing_file(configure, tmp_path):
    handle = configure({"filter": {}})

    assert handle.find_similar_answer("你好", str(tmp_path / "nope.json")) is None
