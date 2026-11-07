"""SafetyGuard：每观众滑窗频率限制。"""

from fakes import FakeConfig
from luna.agent.safety import SafetyGuard


def test_rate_limit_blocks_within_window():
    clock = {"now": 0.0}
    guard = SafetyGuard(
        FakeConfig({"agent": {"safety": {"per_viewer_tool_rate": {"count": 2, "window_seconds": 60}}}}),
        now_fn=lambda: clock["now"],
    )
    assert guard.viewer_rate_ok("alice")
    assert guard.viewer_rate_ok("alice")
    assert not guard.viewer_rate_ok("alice")
    clock["now"] = 61.0  # 窗口滑过，配额恢复
    assert guard.viewer_rate_ok("alice")


def test_rate_limit_is_per_viewer():
    guard = SafetyGuard(FakeConfig({"agent": {"safety": {"per_viewer_tool_rate": {"count": 1, "window_seconds": 60}}}}))
    assert guard.viewer_rate_ok("alice")
    assert not guard.viewer_rate_ok("alice")
    assert guard.viewer_rate_ok("bob")


def test_defaults_apply_when_config_missing():
    guard = SafetyGuard(FakeConfig({}))
    assert guard.max_calls == 3
    assert guard.window_seconds == 60.0
    assert guard.viewer_rate_ok("alice")
