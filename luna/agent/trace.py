"""决策 trace：每次 Agent 决策一条 JSON line，供排查与 WebUI 决策回放（P1）。

没有 trace 的 Agent 在直播场景等于盲飞——「为什么它说了这话/没说话/超时」
全靠这里回放。RECENT 是进程内滚动窗口，后续 WebUI 决策回放页从这里取。
"""

import json
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

from luna.infra.my_log import logger

RECENT: deque = deque(maxlen=200)
_LOCK = threading.Lock()


@dataclass
class Trace:
    """单次决策的 trace 记录器，随决策创建、finish 时落日志。"""

    event_type: str
    username: str
    source: str
    started_at: float = field(default_factory=time.monotonic)
    tool_calls: list = field(default_factory=list)
    degraded: bool = False
    reason: str = ""

    def tool_done(self, name: str, args_digest: str, elapsed_ms: float, ok: bool) -> None:
        self.tool_calls.append({"name": name, "args_digest": args_digest, "ms": round(elapsed_ms, 1), "ok": ok})

    def finish(self, degraded: bool = False, reason: str = "", output_chars: int = 0, prompt_chars: int = 0) -> None:
        record = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "event_type": self.event_type,
            "username": self.username,
            "source": self.source,
            "duration_ms": round((time.monotonic() - self.started_at) * 1000, 1),
            "tool_calls": self.tool_calls,
            "degraded": degraded,
            "reason": reason,
            "output_chars": output_chars,
            "prompt_chars": prompt_chars,
        }
        with _LOCK:
            RECENT.append(record)
        logger.info("[agent-trace] " + json.dumps(record, ensure_ascii=False))
