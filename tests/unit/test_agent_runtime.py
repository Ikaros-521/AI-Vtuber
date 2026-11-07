"""AgentRuntime 决策循环：直答 / 工具轮 / 降级链 / 安全门 / 预算熔断。"""

from types import SimpleNamespace

from fakes import FakeConfig
from luna.agent.llm_adapter import AdapterResult
from luna.agent.runtime import AgentRuntime
from luna.infra.db import SQLiteDB


def make_config(**agent_overrides):
    agent = {
        "enabled": True,
        "max_tool_rounds": 3,
        "timeout_seconds": 8,
        "llm": {"channel": "text"},
        "tools": {
            "enabled": ["speak", "query_integral", "query_danmu_summary", "search_online", "memory_save"],
            "dangerous_enabled": [],
        },
        "budget": {"tokens_per_hour": 0},
        "memory": {"viewer_profile": True, "episodic": True},
        "safety": {"per_viewer_tool_rate": {"count": 3, "window_seconds": 60}},
    }
    agent.update(agent_overrides)
    return FakeConfig(
        {
            "agent": agent,
            "platform": "bilibili",
            "chat_type": "chatgpt",
            "before_prompt": "",
            "after_prompt": "",
        }
    )


class FakeHandle:
    """只实现 runtime 用到的 My_handle 接口。"""

    def __init__(self, config, db=None):
        self.config = config
        self.db = db
        self.common = SimpleNamespace(
            get_bj_time=lambda fmt="": "2026-11-07 20:00:00",
            get_list_random_or_default=lambda items, default: default if not items else items[0],
        )
        self.synthesized = []
        self.chat_log = []
        self.comment_logs = []

    def prohibitions_handle(self, content):
        return None if content.startswith("违禁") else content

    def webui_show_chat_log_callback(self, data_type, data, resp_content):
        self.chat_log.append((data_type, resp_content))

    def write_to_comment_log(self, resp_content, data):
        self.comment_logs.append(resp_content)

    def audio_synthesis_handle(self, message):
        self.synthesized.append(message)

    def is_playback_busy(self):
        return False


class FakeAdapter:
    """按序回放预设结果，并记录每次调用收到的 messages。"""

    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def call(self, messages, tool_specs):
        self.calls.append(list(messages))
        return self.results.pop(0)


def make_runtime(config=None, results=None, db=None):
    handle = FakeHandle(config or make_config(), db=db)
    adapter = FakeAdapter(results or [])
    runtime = AgentRuntime(handle, adapter=adapter)
    return runtime, handle, adapter


def make_event(content="今天天气怎么样", username="alice"):
    return {"username": username, "content": content, "ori_username": username, "ori_content": content}


def test_direct_answer_speaks_and_reports_true(tmp_path):
    runtime, handle, adapter = make_runtime(results=[AdapterResult(text="今天晴天哦")])
    data = make_event()
    assert runtime.handle_chat(data, "comment") is True
    assert len(handle.synthesized) == 1
    message = handle.synthesized[0]
    assert message["content"] == "今天晴天哦"
    assert message["username"] == "alice"
    assert message["type"] == "comment"
    # 回显/落库/给门面的触发文本都已就位
    assert handle.chat_log and handle.chat_log[0][1] == "今天晴天哦"
    assert handle.comment_logs == ["今天晴天哦"]
    assert data["content"] == "今天晴天哦"
    assert adapter.calls and adapter.calls[0][0]["role"] == "system"


def test_tool_round_feeds_observation_then_answers(tmp_path):
    db = SQLiteDB(str(tmp_path / "t.db"))
    db.execute(
        "CREATE TABLE IF NOT EXISTS integral (platform TEXT, username TEXT, uid TEXT, integral INT, "
        "view_num INT, sign_num INT, last_sign_ts DATETIME, total_price INT, last_ts DATETIME)"
    )
    db.execute("INSERT INTO integral VALUES ('bilibili', 'alice', '1', 99, 10, 3, '', 66, '')")
    config = make_config()
    results = [
        AdapterResult(tool_calls=[{"name": "query_integral", "args": {"top": 3}, "id": None}]),
        AdapterResult(text="alice 现在积分 99 分"),
    ]
    runtime, handle, adapter = make_runtime(config=config, results=results, db=db)
    assert runtime.handle_chat(make_event(), "comment") is True
    # 第二轮 prompt 里要带上工具返回的 OBSERVATION
    second_call = adapter.calls[1]
    assert any("积分" in msg.get("content", "") for msg in second_call)
    assert handle.synthesized[-1]["content"] == "alice 现在积分 99 分"


def test_rounds_exhausted_degrades(tmp_path):
    config = make_config(max_tool_rounds=2)
    results = [
        AdapterResult(tool_calls=[{"name": "query_integral", "args": {}, "id": None}]),
        AdapterResult(tool_calls=[{"name": "query_integral", "args": {}, "id": None}]),
        AdapterResult(text="永远不会被消费"),
    ]
    runtime, handle, adapter = make_runtime(config=config, results=results)
    assert runtime.handle_chat(make_event(), "comment") is False
    assert handle.synthesized == []
    assert len(adapter.calls) == 2  # 轮次触顶后不再请求


def test_adapter_exception_degrades():
    class BoomAdapter:
        def call(self, messages, tool_specs):
            raise RuntimeError("llm down")

    handle = FakeHandle(make_config())
    runtime = AgentRuntime(handle, adapter=BoomAdapter())
    assert runtime.handle_chat(make_event(), "comment") is False
    assert handle.synthesized == []


def test_prohibited_output_is_silent_but_taken():
    runtime, handle, _ = make_runtime(results=[AdapterResult(text="违禁内容就不播")])
    assert runtime.handle_chat(make_event(), "comment") is True
    assert handle.synthesized == []  # 刻意沉默，不回落原路径二次生成


def test_unknown_tool_returns_error_observation(tmp_path):
    results = [
        AdapterResult(tool_calls=[{"name": "not_registered", "args": {}, "id": None}]),
        AdapterResult(text="那我说点别的"),
    ]
    runtime, handle, adapter = make_runtime(results=results)
    assert runtime.handle_chat(make_event(), "comment") is True
    second_call = adapter.calls[1]
    assert any("不存在或未启用" in msg.get("content", "") for msg in second_call)


def test_tool_rate_limit_blocks_second_call():
    config = make_config()
    config.config["agent"]["safety"]["per_viewer_tool_rate"] = {"count": 1, "window_seconds": 60}
    results = [
        AdapterResult(
            tool_calls=[
                {"name": "memory_save", "args": {"kind": "highlight", "content": "a"}, "id": None},
                {"name": "memory_save", "args": {"kind": "highlight", "content": "b"}, "id": None},
            ]
        ),
        AdapterResult(text="好的"),
    ]
    runtime, handle, adapter = make_runtime(config=config, results=results)
    assert runtime.handle_chat(make_event(), "comment") is True
    observation = adapter.calls[1][-1]["content"]
    assert "过于频繁" in observation


def test_hourly_budget_fuse_skips_llm():
    config = make_config(budget={"tokens_per_hour": 10})
    runtime, handle, adapter = make_runtime(config=config)
    runtime._hour_used = 999999  # 模拟本小时额度已耗尽
    assert runtime.handle_chat(make_event(), "comment") is False
    assert adapter.calls == []  # 没有请求 LLM
    assert handle.synthesized == []


def test_viewer_memory_injected_into_prompt(tmp_path):
    from luna.agent.memory import MemorySystem

    db = SQLiteDB(str(tmp_path / "t.db"))
    memory = MemorySystem(db)
    memory.save_note("bilibili", "alice", "喜欢点歌")

    handle = FakeHandle(make_config(), db=db)
    adapter = FakeAdapter([AdapterResult(text="欢迎回来")])
    runtime = AgentRuntime(handle, adapter=adapter)
    assert runtime.handle_chat(make_event(), "comment") is True
    system_prompt = adapter.calls[0][0]["content"]
    assert "喜欢点歌" in system_prompt


def test_intent_decline_degrades():
    from luna.agent.intent import IntentRouter

    class DeclineRouter(IntentRouter):
        def __init__(self):
            pass  # 覆写后不接 config：should_agent 已完全自定义

        def should_agent(self, context):
            return False

    handle = FakeHandle(make_config())
    runtime = AgentRuntime(handle, adapter=FakeAdapter([]))
    runtime.intent = DeclineRouter()
    assert runtime.handle_chat(make_event(), "comment") is False


def test_kill_switch_silences_agent():
    runtime, handle, adapter = make_runtime(results=[AdapterResult(text="不该出现")])
    runtime.kill_switch = True
    assert runtime.handle_chat(make_event(), "comment") is False
    assert adapter.calls == []
    runtime.kill_switch = False
    assert runtime.handle_chat(make_event(), "comment") is True


def test_duplicate_burst_skips_agent():
    config = make_config()
    config.config["agent"]["intent"] = {"duplicate_burst": {"count": 3, "window_seconds": 30}}
    results = [AdapterResult(text=f"回复{i}") for i in range(5)]
    runtime, handle, adapter = make_runtime(config=config, results=results)
    # 同一段内容连刷：第 1、2 次正常接管，第 3 次起跳过（落回规则链路）
    assert runtime.handle_chat(make_event("666"), "comment") is True
    assert runtime.handle_chat(make_event("666"), "comment") is True
    assert runtime.handle_chat(make_event("666"), "comment") is False
    assert len(adapter.calls) == 2
    # 别的内容不受影响
    assert runtime.handle_chat(make_event("你好"), "comment") is True


def test_duplicate_burst_disabled_by_config():
    config = make_config()
    config.config["agent"]["intent"] = {"duplicate_burst": {"count": 0}}
    results = [AdapterResult(text="回复") for _ in range(4)]
    runtime, _, adapter = make_runtime(config=config, results=results)
    for _ in range(4):
        assert runtime.handle_chat(make_event("666"), "comment") is True
    assert len(adapter.calls) == 4


def test_overlong_content_truncated():
    config = make_config()
    config.config["agent"]["intent"] = {"max_content_chars": 10}
    runtime, _, adapter = make_runtime(config=config, results=[AdapterResult(text="收到")])
    assert runtime.handle_chat(make_event("字" * 100), "comment") is True
    user_message = adapter.calls[0][-1]["content"]
    assert "……（内容过长已截断）" in user_message
    assert len(user_message) < 40


def test_reply_template_wraps_output():
    config = make_config()
    config.config["reply_template"] = {"enable": True, "username_max_len": 10, "copywriting": ["【{data}】"]}
    runtime, handle, _ = make_runtime(config=config, results=[AdapterResult(text="大家好")])
    assert runtime.handle_chat(make_event(), "comment") is True
    assert handle.synthesized[-1]["content"] == "【大家好】"
    assert handle.synthesized[-1]["username"] == "alice"


def test_generate_proactive_uses_context_and_budget(tmp_path):
    config = make_config()
    results = [AdapterResult(text="来聊聊大家刚才点的歌")]
    runtime, handle, adapter = make_runtime(config=config, results=results)
    topic = runtime.generate_proactive()
    assert topic == "来聊聊大家刚才点的歌"
    system_prompt = adapter.calls[0][0]["content"]
    assert "主动开一个直播话题" in system_prompt
    assert "当前时间" in system_prompt


def test_generate_proactive_falls_back_on_budget():
    config = make_config(budget={"tokens_per_hour": 10})
    runtime, _, adapter = make_runtime(config=config)
    runtime._hour_used = 999999
    assert runtime.generate_proactive() is None
    assert adapter.calls == []


def test_generate_proactive_falls_back_on_kill_switch():
    runtime, _, adapter = make_runtime(results=[AdapterResult(text="x")])
    runtime.kill_switch = True
    assert runtime.generate_proactive() is None
    assert adapter.calls == []
