"""人设知识库 RAG（v5 P2 轻量版）：分块 / 检索 / mtime 重载 / runtime 注入。"""

from luna.agent.rag import KnowledgeBase, tokenize


def test_tokenize_cjk_bigrams_and_latin_words():
    terms = tokenize("查一下晴天这首歌")
    assert "晴天" in terms and "首歌" in terms
    assert any(t.startswith("查一") for t in terms)
    assert "song" not in terms  # 中文查询没有英数词
    assert "abc" in tokenize("play abc")


def test_chunk_and_retrieve(tmp_path):
    kb = KnowledgeBase(str(tmp_path))
    (tmp_path / "人设.md").write_text(
        "# 主播设定\n主播叫小樱，喜欢唱歌。\n直播间规矩：不要骂人。\n\n# 口头禅\n就是那种啦～",
        encoding="utf-8",
    )
    kb.reload_if_changed()
    assert len(kb.chunks) >= 2

    hit = kb.retrieve("主播叫什么名字")
    assert "小樱" in hit
    assert kb.retrieve("完全无关的量子力学内容") == ""


def test_reload_on_mtime_change(tmp_path):
    kb = KnowledgeBase(str(tmp_path))
    kb.reload_if_changed()
    assert kb.chunks == []
    (tmp_path / "a.md").write_text("# 玩法\n每周五开歌回。", encoding="utf-8")
    kb.reload_if_changed()
    assert len(kb.chunks) == 1
    (tmp_path / "a.md").write_text("# 玩法\n每周五、周六开歌回。", encoding="utf-8")
    kb.reload_if_changed()
    assert "周六" in kb.chunks[0]["text"]


def test_runtime_injects_knowledge(tmp_path, monkeypatch):
    """开启 rag 后，命中的知识片段进入 system prompt（真机回归点）。"""
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "设定.md").write_text("# 世界观\n主播的猫叫团子。", encoding="utf-8")

    from fakes import FakeConfig
    from luna.agent.runtime import AgentRuntime

    config = FakeConfig(
        {
            "agent": {
                "enabled": True,
                "timeout_seconds": 8,
                "llm": {"channel": "text"},
                "tools": {"enabled": ["speak"], "dangerous_enabled": []},
                "rag": {"enabled": True, "knowledge_dir": str(knowledge_dir)},
            },
            "platform": "bilibili",
            "chat_type": "chatgpt",
        }
    )
    handle = type(
        "H",
        (),
        {
            "config": property(lambda self: self._config),
            "db": None,
            "chat_type_list": ["chatgpt"],
            "__init__": lambda self, cfg: setattr(self, "_config", cfg),
        },
    )(config)
    handle.common = type("C", (), {"get_bj_time": lambda self, fmt="": "2026-11-07 20:00:00"})()
    handle.prohibitions_handle = lambda text: text
    handle.audio_synthesis_handle = lambda message: None
    handle.webui_show_chat_log_callback = lambda *a: None
    handle.write_to_comment_log = lambda *a: None
    handle.is_playback_busy = lambda: False

    class Adapter:
        def call(self, messages, tool_specs):
            Adapter.system = messages[0]["content"]
            from luna.agent.llm_adapter import AdapterResult

            return AdapterResult(text="好的呀")

    runtime = AgentRuntime(handle, adapter=Adapter())
    assert runtime.knowledge is not None
    data = {"username": "alice", "content": "你的猫叫什么", "ori_username": "alice", "ori_content": "你的猫叫什么"}
    assert runtime.handle_chat(data, "comment") is True
    assert "团子" in Adapter.system
