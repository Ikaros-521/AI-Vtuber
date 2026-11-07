"""My_handle.agent_handle_chat 门面：守卫条件、降级回落、回复侧触发对齐。

门面是 Agent 与规则引擎之间的切换开关（docs/agent-upgrade-design.md §4.7），
这里用桩 runtime 验证门面自身的门控逻辑，不构造真 AgentRuntime。
"""

BASE_CONFIG = {
    "agent": {"enabled": True},
    "chat_type": "chatgpt",
    "filter": {"before_must_str_for_llm": [], "after_must_str_for_llm": []},
    "key_mapping": {"type": "弹幕"},
    "custom_cmd": {"type": "弹幕"},
}


class StubRuntime:
    def __init__(self, result=True):
        self.result = result
        self.calls = []

    def handle_chat(self, data_json, source):
        self.calls.append((data_json, source))
        return self.result


def make_data(content="你好"):
    return {"username": "alice", "content": content, "ori_username": "alice", "ori_content": content}


def test_disabled_without_runtime(handle, configure):
    configure(BASE_CONFIG)
    handle.chat_type_list = ["chatgpt"]
    # 绕过 __init__ 的实例没有 agent_runtime 属性（getattr 默认 None）
    assert handle.agent_handle_chat(make_data(), "comment") is False


def test_config_disabled_falls_through(handle, configure):
    configure({**BASE_CONFIG, "agent": {"enabled": False}})
    handle.chat_type_list = ["chatgpt"]
    handle.agent_runtime = StubRuntime()
    assert handle.agent_handle_chat(make_data(), "comment") is False
    assert handle.agent_runtime.calls == []


def test_non_llm_chat_type_not_intercepted(handle, configure):
    handle.chat_type_list = ["chatgpt"]
    handle.agent_runtime = StubRuntime()
    configure({**BASE_CONFIG, "chat_type": "none"})
    assert handle.agent_handle_chat(make_data(), "comment") is False  # chat_type=none
    configure({**BASE_CONFIG, "chat_type": "game"})
    assert handle.agent_handle_chat(make_data(), "comment") is False  # chat_type=game
    assert handle.agent_runtime.calls == []


def test_must_str_filter_falls_through(handle, configure):
    configure(
        {
            **BASE_CONFIG,
            "filter": {"before_must_str_for_llm": ["小助手"], "after_must_str_for_llm": []},
        }
    )
    handle.chat_type_list = ["chatgpt"]
    handle.agent_runtime = StubRuntime()
    # 与 llm_handle 前置过滤一致：不带前缀的弹幕不触发回复
    assert handle.agent_handle_chat(make_data("随便聊聊"), "comment") is False
    assert handle.agent_handle_chat(make_data("小助手你好"), "comment") is True


def test_success_triggers_reply_side_mapping(handle, configure, monkeypatch):
    configure(
        {
            **BASE_CONFIG,
            "key_mapping": {"type": "回复"},
            "custom_cmd": {"type": "弹幕+回复"},
        }
    )
    handle.chat_type_list = ["chatgpt"]
    runtime = StubRuntime(True)
    handle.agent_runtime = runtime

    called = []
    monkeypatch.setattr(handle, "key_mapping_handle", lambda type_, data: called.append(("key_mapping", type_)) or True)
    monkeypatch.setattr(handle, "custom_cmd_handle", lambda type_, data: called.append(("custom_cmd", type_)) or True)

    data = make_data()
    assert handle.agent_handle_chat(data, "comment") is True
    assert runtime.calls == [(data, "comment")]
    # 与原 LLM 直答路径对齐：回复侧按键映射与自定义命令都触发
    assert ("key_mapping", "回复") in called
    assert ("custom_cmd", "回复") in called


def test_runtime_degradation_falls_through(handle, configure, monkeypatch):
    configure(BASE_CONFIG)
    handle.chat_type_list = ["chatgpt"]
    handle.agent_runtime = StubRuntime(result=False)
    monkeypatch.setattr(handle, "key_mapping_handle", lambda *a: True)
    monkeypatch.setattr(handle, "custom_cmd_handle", lambda *a: True)
    # runtime 返回 False → 门面 False，回复侧触发不应执行
    assert handle.agent_handle_chat(make_data(), "comment") is False
