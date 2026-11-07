"""ToolRegistry 与内置工具的完整性（docs/agent-upgrade-design.md P0）。"""

import pytest

from fakes import FakeConfig
from luna.agent import registry as registry_module
from luna.agent.registry import TOOLS, Tool, ToolRegistry, load_tool_class

EXPECTED_TOOLS = {
    "speak",
    "query_integral",
    "query_danmu_summary",
    "search_online",
    "memory_save",
    "play_song",
    "generate_image",
    "stop_playback",
    "pause_playback",
    "resume_playback",
    "set_volume",
    "observe_screen",
}


def test_tools_registry_covers_the_p0_toolset():
    assert set(TOOLS) == EXPECTED_TOOLS


@pytest.mark.parametrize("name", sorted(TOOLS))
def test_every_tool_is_loadable_and_self_describing(name):
    cls = load_tool_class(name)
    assert cls is not None
    tool = cls()
    assert tool.name == name, "TOOLS 登记名要与类属性 name 一致，否则运行期会被跳过"
    assert tool.description.strip()
    assert tool.parameters.get("type") == "object"
    assert "properties" in tool.parameters  # 无参数工具（如 stop_playback）允许空 properties


def test_registry_respects_enabled_whitelist():
    registry = ToolRegistry(FakeConfig({"agent": {"tools": {"enabled": ["speak"]}}}))
    assert registry.get("speak") is not None
    assert registry.get("query_integral") is None
    assert [spec["name"] for spec in registry.specs()] == ["speak"]


def test_registry_skips_unknown_tools():
    registry = ToolRegistry(FakeConfig({"agent": {"tools": {"enabled": ["speak", "nope"]}}}))
    assert registry.get("nope") is None
    assert registry.get("speak") is not None


class Risky(Tool):
    name = "risky"
    description = "危险动作"
    parameters = {"type": "object", "properties": {}}
    dangerous = True

    def run(self, args, ctx):
        return "ok"


def test_dangerous_tool_requires_explicit_switch(monkeypatch):
    real_loader = registry_module.load_tool_class

    def fake_loader(name):
        return Risky if name == "risky" else real_loader(name)

    monkeypatch.setattr(registry_module, "load_tool_class", fake_loader)

    disabled = ToolRegistry(FakeConfig({"agent": {"tools": {"enabled": ["risky"]}}}))
    assert disabled.get("risky") is None

    enabled = ToolRegistry(FakeConfig({"agent": {"tools": {"enabled": ["risky"], "dangerous_enabled": ["risky"]}}}))
    assert enabled.get("risky") is not None
