"""SafetyGuard：每观众工具调用频率限制。

工具白名单在 ToolRegistry（未列入 config 白名单的工具不会实例化，模型也看不见）；
全局成本熔断在 AgentRuntime 的小时预算；输出侧违禁过滤复用
My_handle.prohibitions_handle（由 runtime 调用方负责）——本类只管防观众刷弹幕
薅 Agent 算力这一件事。
"""

import threading
import time
from collections import deque


class SafetyGuard:
    """按观众名滑窗计数工具调用；窗口内超限直接拒绝。"""

    def __init__(self, config, now_fn=time.monotonic):
        self.config = config
        self._now = now_fn
        rate = config.get("agent", "safety", "per_viewer_tool_rate") or {}
        self.window_seconds = float(rate.get("window_seconds", 60))
        self.max_calls = int(rate.get("count", 3))
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()

    def viewer_rate_ok(self, username: str) -> bool:
        now = self._now()
        with self._lock:
            hits = self._hits.setdefault(username or "", deque())
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()
            if len(hits) >= self.max_calls:
                return False
            hits.append(now)
            return True
