"""MCP host（v5 P2）：stdio JSON-RPC 客户端与 runtime 集成（假 server 离线集成测）。"""

import sys
import textwrap

from luna.agent.mcp_client import MCPManager, full_tool_name

FAKE_SERVER = textwrap.dedent(
    """
    import sys, json
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        method = req.get("method")
        if method == "initialize":
            resp = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                    "serverInfo": {"name": "fake", "version": "1"}}
        elif method == "tools/list":
            resp = {"tools": [{"name": "echo", "description": "回显文本",
                               "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}}}]}
        elif method == "tools/call":
            text = req["params"]["arguments"].get("text", "")
            resp = {"content": [{"type": "text", "text": f"echo:{text}"}]}
        else:
            resp = {}
        if "id" in req:
            print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "result": resp}), flush=True)
    """
)


def make_manager(tmp_path, **extra):
    server_script = tmp_path / "fake_mcp_server.py"
    server_script.write_text(FAKE_SERVER, encoding="utf-8")
    return MCPManager(
        [
            {
                "name": "fake",
                "command": sys.executable,
                "args": [str(server_script)],
                "env": {"PYTHONIOENCODING": "utf-8"},
            }
        ],
        timeout_seconds=10,
        **extra,
    )


def test_mcp_client_end_to_end(tmp_path):
    """握手 → 工具发现 → 工具调用 → 状态 → 停止（全离线假 server）。"""
    manager = make_manager(tmp_path)
    try:
        manager.start()
        assert manager.wait_ready(10), "MCP manager 未在超时内就绪"

        specs = manager.tool_specs()
        assert [spec["name"] for spec in specs] == ["mcp__fake__echo"]
        assert "回显" in specs[0]["description"]

        observation = manager.call_tool("mcp__fake__echo", {"text": "你好"})
        assert observation == "echo:你好"

        status = manager.status()
        assert status["servers"][0]["state"] == "ready"
    finally:
        manager.stop()


def test_call_unknown_server_raises(tmp_path):
    manager = make_manager(tmp_path)
    manager.start()
    manager.wait_ready(10)
    try:
        try:
            manager.call_tool("mcp__ghost__echo", {})
        except RuntimeError as e:
            assert "未就绪" in str(e) or "非 MCP" in str(e)
    finally:
        manager.stop()


def test_runtime_merges_mcp_tools_and_routes(tmp_path, monkeypatch):
    """MCP 工具并入工具清单，模型调用经 mcp__ 前缀路由到外部 server。"""
    from fakes import FakeConfig
    from luna.agent.llm_adapter import AdapterResult
    from luna.agent.runtime import AgentRuntime

    manager = make_manager(tmp_path)
    manager.start()
    manager.wait_ready(10)
    try:
        config = FakeConfig(
            {
                "agent": {
                    "enabled": True,
                    "timeout_seconds": 8,
                    "llm": {"channel": "text"},
                    "tools": {"enabled": ["speak"], "dangerous_enabled": []},
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
        synthesized = []
        handle.audio_synthesis_handle = synthesized.append
        handle.webui_show_chat_log_callback = lambda *a: None
        handle.write_to_comment_log = lambda *a: None
        handle.is_playback_busy = lambda: False

        results = [
            AdapterResult(tool_calls=[{"name": "mcp__fake__echo", "args": {"text": "hi"}, "id": None}]),
            AdapterResult(text="工具说：echo:hi"),
        ]
        runtime = AgentRuntime(handle, adapter=_ScriptedAdapter(results))
        runtime.mcp = manager

        specs = runtime._all_tool_specs()
        assert "mcp__fake__echo" in [s["name"] for s in specs]

        data = {"username": "alice", "content": "试试回显", "ori_username": "alice", "ori_content": "试试回显"}
        assert runtime.handle_chat(data, "comment") is True
        assert any("echo:hi" in (m.get("content") or "") for m in runtime_logs(runtime, 2))
    finally:
        manager.stop()


def runtime_logs(runtime, count):
    return runtime.adapter.calls[-1] if runtime.adapter.calls else []


class _ScriptedAdapter:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def call(self, messages, tool_specs):
        self.calls.append(list(messages))
        return self.results.pop(0)


def test_full_tool_name_format():
    assert full_tool_name("srv", "echo") == "mcp__srv__echo"
