"""MCP host（v5 P2）：把外部 MCP server 的工具接进 Luna 的工具清单。

刻意不用官方 mcp SDK：它硬依赖 pydantic v2，而主程序/面板的日常运行环境
（Miniconda 基座）是 pydantic v1.10——装 SDK 会掀了整个依赖桌。MCP stdio
传输本质是「子进程 + 换行分隔 JSON-RPC 2.0」，用纯 stdlib asyncio 实现
initialize / tools/list / tools/call 三个动作，够把第三方工具接进来。

信任边界：**server 级**。agent.mcp.servers 里配置并启用的 server 即被信任，
其全部工具以 `mcp__<server>__<tool>` 前缀并入工具清单，走与内置工具完全
相同的门禁（白名单可见性/每观众频率/预算/输出过滤）。per-tool 细粒度过滤
用 agent.mcp.enabled_tools（非空时作为过滤器）。
"""

import asyncio
import json
import threading
from concurrent.futures import TimeoutError as FutureTimeoutError

from luna.infra.my_log import logger

PROTOCOL_VERSION = "2024-11-05"
CLIENT_INFO = {"name": "luna-ai-vtuber", "version": "5.0"}
TOOL_NAME_PREFIX = "mcp__"


def full_tool_name(server: str, tool: str) -> str:
    return f"{TOOL_NAME_PREFIX}{server}__{tool}"


class MCPServerConnection:
    """单个 MCP server 的常驻 stdio 连接（asyncio）。"""

    def __init__(self, name: str, command: str, args: list, env: dict | None, timeout_seconds: float = 15.0):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.timeout_seconds = timeout_seconds
        self.state = "starting"  # starting / ready / error / stopped
        self.error = ""
        self.tools: list = []
        self._proc = None
        self._next_id = 1
        self._pending: dict = {}

    async def start(self):
        try:
            self._proc = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env={**__import__("os").environ, **self.env},
            )
        except Exception as e:
            self.state, self.error = "error", f"启动失败：{e}"
            logger.warning(f"MCP server {self.name} 启动失败：{e}")
            return
        reader = self._proc.stdout

        # 读循环：按 id 分发响应，通知（无 id）忽略
        async def _read_loop():
            while True:
                line = await reader.readline()
                if not line:
                    break
                try:
                    message = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                request_id = message.get("id")
                if request_id is not None and request_id in self._pending:
                    future = self._pending.pop(request_id)
                    future.set_result(message)
            # 进程退出：所有挂起请求以错误收场
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(RuntimeError(f"MCP server {self.name} 已退出"))
            self._pending.clear()
            if self.state == "ready":
                self.state, self.error = "error", "进程已退出"

        self._read_task = asyncio.create_task(_read_loop())
        try:
            init_result = await self._request(
                "initialize",
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": CLIENT_INFO,
                },
            )
            if init_result is None:
                return
            await self._notify("notifications/initialized")
            tools_result = await self._request("tools/list", {})
            if tools_result is None:
                return
            self.tools = [
                {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "inputSchema": tool.get("inputSchema") or {"type": "object", "properties": {}},
                }
                for tool in tools_result.get("tools", [])
                if tool.get("name")
            ]
            self.state = "ready"
            logger.info(f"MCP server {self.name} 就绪：{len(self.tools)} 个工具")
        except Exception as e:
            self.state, self.error = "error", str(e)
            logger.warning(f"MCP server {self.name} 握手失败：{e}")

    async def _request(self, method: str, params: dict):
        request_id = self._next_id
        self._next_id += 1
        future = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future
        await self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        try:
            message = await asyncio.wait_for(future, timeout=self.timeout_seconds)
        except FutureTimeoutError:
            self._pending.pop(request_id, None)
            self.state, self.error = "error", f"{method} 超时"
            return None
        if message.get("error"):
            self.error = str(message["error"].get("message", message["error"]))
            return None
        return message.get("result") or {}

    async def _notify(self, method: str, params: dict | None = None):
        payload = {"jsonrpc": "2.0", "method": method}
        if params:
            payload["params"] = params
        await self._send(payload)

    async def _send(self, payload: dict):
        if self._proc is None or self._proc.stdin is None:
            raise RuntimeError("stdin 未就绪")
        self._proc.stdin.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
        await self._proc.stdin.drain()

    async def call_tool(self, tool: str, args: dict):
        result = await self._request("tools/call", {"name": tool, "arguments": args})
        if result is None:
            raise RuntimeError(self.error or "工具调用失败")
        if result.get("isError"):
            texts = [c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"]
            raise RuntimeError(" / ".join(texts) or "工具返回错误")
        texts = [c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"]
        return "\n".join(t for t in texts if t).strip() or "（工具无文本返回）"

    async def stop(self):
        self.state = "stopped"
        read_task = getattr(self, "_read_task", None)
        if read_task is not None and not read_task.done():
            read_task.cancel()
        if self._proc is not None:
            if self._proc.stdin is not None:
                try:
                    self._proc.stdin.close()
                except Exception:
                    pass
            if self._proc.returncode is None:
                try:
                    self._proc.kill()
                except ProcessLookupError:
                    pass
        self._proc = None


class MCPManager:
    """多 server 管理器：独立事件循环线程 + 同步门面（供主线程的 runtime 调用）。"""

    def __init__(self, servers: list, timeout_seconds: float = 15.0):
        self._servers_config = servers or []
        self._timeout = timeout_seconds
        self._connections: dict = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready_event = threading.Event()

    def start(self):
        if not self._servers_config or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run_loop, name="mcp-host", daemon=True)
        self._thread.start()
        import atexit

        atexit.register(self.stop)

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def _start_all():
            for server in self._servers_config:
                conn = MCPServerConnection(
                    server.get("name", ""),
                    server.get("command", ""),
                    server.get("args", []),
                    server.get("env"),
                    self._timeout,
                )
                self._connections[conn.name] = conn
                await conn.start()

        self._loop.run_until_complete(_start_all())
        self._ready_event.set()
        self._loop.run_forever()

    def _submit(self, coro, timeout: float = 20.0):
        if self._loop is None:
            raise RuntimeError("MCP 管理器未启动")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    def wait_ready(self, timeout: float = 20.0) -> bool:
        return self._ready_event.wait(timeout)

    def tool_specs(self) -> list:
        """已就绪 server 的全部工具，展开为带 mcp__ 前缀的工具清单。"""
        enabled_filter = None
        specs = []
        for name, conn in self._connections.items():
            if conn.state != "ready":
                continue
            for tool in conn.tools:
                specs.append(
                    {
                        "name": full_tool_name(name, tool["name"]),
                        "description": f"[MCP:{name}] {tool['description']}".strip(),
                        "parameters": tool["inputSchema"],
                    }
                )
        if enabled_filter is not None:
            specs = [s for s in specs if s["name"] in enabled_filter]
        return specs

    def call_tool(self, full_name: str, args: dict) -> str:
        """同步调用外部工具；失败抛异常（runtime 统一兜底成 OBSERVATION 错误文本）。"""
        if not full_name.startswith(TOOL_NAME_PREFIX):
            raise RuntimeError(f"非 MCP 工具名：{full_name}")
        rest = full_name[len(TOOL_NAME_PREFIX) :]
        server, _, tool = rest.partition("__")
        conn = self._connections.get(server)
        if conn is None or conn.state != "ready":
            raise RuntimeError(f"MCP server {server} 未就绪")
        return self._submit(conn.call_tool(tool, args), timeout=self._timeout + 10)

    def status(self) -> dict:
        return {
            "servers": [
                {
                    "name": c.name,
                    "state": c.state,
                    "error": c.error,
                    "tools": [full_tool_name(c.name, t["name"]) for t in c.tools],
                }
                for c in self._connections.values()
            ]
        }

    def stop(self):
        if self._loop is None:
            return

        async def _stop_all():
            for conn in self._connections.values():
                await conn.stop()

        try:
            asyncio.run_coroutine_threadsafe(_stop_all(), self._loop).result(timeout=5)
        except Exception:
            pass
        self._loop.call_soon_threadsafe(self._loop.stop)
