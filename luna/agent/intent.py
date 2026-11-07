"""IntentRouter：进入 Agent 循环前的意图分流。

P1 落一条规则，其余放行：
- 复读风暴：同一段内容在窗口内被刷到第 N 次，跳过 Agent（落回规则链路直答），
  防止弹幕玩梗刷屏把 token 烧穿。计数含当前这次——第 3 次同内容触发跳过。
P2 的小模型分流（高频闲聊分类等）继续落在这个类。
内容过长的截断不在这里做——由 runtime 组 prompt 时截断（保留上下文，省 token）。
"""

import threading
import time
from collections import deque


class IntentRouter:
    # 风暴历史表的键数上限：弹幕内容理论上无限多，超限整体清空重新统计
    # （风暴窗口本来就短，清空不会造成误放行风暴）
    MAX_HISTORY_KEYS = 1000

    def __init__(self, config, now_fn=time.monotonic):
        self.config = config
        self._now = now_fn
        self._history: dict = {}
        self._lock = threading.Lock()

    def should_agent(self, context) -> bool:
        burst = self.config.get("agent", "intent", "duplicate_burst") or {}
        max_count = int(burst.get("count", 3))
        window = float(burst.get("window_seconds", 30))
        content = str(context.event.get("content") or "").strip()
        if max_count <= 0 or not content:
            return True
        now = self._now()
        with self._lock:
            if len(self._history) > self.MAX_HISTORY_KEYS:
                self._history.clear()
            hits = self._history.setdefault(content, deque())
            while hits and now - hits[0] > window:
                hits.popleft()
            hits.append(now)
            return len(hits) < max_count
