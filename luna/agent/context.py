"""AgentContext 与 Budget：一次 Agent 决策的全部输入与资源约束。

依赖方向约定（tests/unit/test_agent_deps.py 强制）：luna/agent 只准依赖
luna/infra、luna/common 与两个纯工具模块（luna.core.message / luna.core.search_engine）
加标准库；对 My_handle 能力（点歌/积分/音频合成等）一律经 ctx.handle 注入访问，
与 luna/core/integral.py 的参数注入模式一致，不反向 import my_handle。
"""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Budget:
    """单次决策的资源约束：工具循环轮次与耗时。

    字符数只做记录（trace 与小时预算折算），不参与单次熔断——单次熔断由
    轮次上限 + 超时兜底，跨决策的成本熔断在 AgentRuntime 的小时预算里。
    """

    max_tool_rounds: int = 3
    timeout_seconds: float = 8.0

    tool_rounds: int = 0
    prompt_chars: int = 0
    started_at: float = field(default_factory=time.monotonic)

    def rounds_exhausted(self) -> bool:
        return self.tool_rounds >= self.max_tool_rounds

    def timed_out(self) -> bool:
        return (time.monotonic() - self.started_at) >= self.timeout_seconds

    def exhausted(self) -> bool:
        """轮次/超时任一触顶即为耗尽，调用方降级。"""
        return self.rounds_exhausted() or self.timed_out()

    def add_chars(self, *texts: str) -> None:
        self.prompt_chars += sum(len(text or "") for text in texts)


@dataclass
class AgentContext:
    """一次决策的上下文与能力出口。

    event 为归一化事件（type/username/content/platform）；viewer 是记忆层
    查询出的画像摘要；state 是本场会话态快照；handle 为 My_handle 实例，
    工具经它访问既有能力。
    """

    event: dict
    source: str
    handle: Any
    budget: Budget
    trace: Any
    memory: Any = None
    viewer: dict | None = None
    state: dict = field(default_factory=dict)
