"""ToolRegistry：Agent 工具注册表，与 luna/llm/gpt.py 的 PROVIDERS 完全同构。

新增工具 = 写一个 Tool 子类（name/description/parameters/run）并在 TOOLS 登记
一行，再按需加进 config 的 agent.tools.enabled 白名单；dangerous 工具另有
独立开关（agent.tools.dangerous_enabled），默认一律拒绝。
"""

import importlib
from abc import ABC, abstractmethod

from luna.infra.my_log import logger


class Tool(ABC):
    """工具基类：run 返回给模型的 OBSERVATION 文本，抛异常由调用方兜底。"""

    name: str = ""
    description: str = ""
    # JSON Schema（给模型看的参数说明），子类必须给出
    parameters: dict = {}
    dangerous: bool = False

    @abstractmethod
    def run(self, args: dict, ctx) -> str:  # noqa: ANN001 - ctx: luna.agent.context.AgentContext（避免环）
        ...


# name -> (module, class)，importlib 懒加载（与 PROVIDERS 同款）
TOOLS = {
    "speak": ("luna.agent.tools.basic", "Speak"),
    "query_integral": ("luna.agent.tools.integral", "QueryIntegral"),
    "query_danmu_summary": ("luna.agent.tools.danmu", "QueryDanmuSummary"),
    "search_online": ("luna.agent.tools.search", "SearchOnline"),
    "memory_save": ("luna.agent.tools.memory_tool", "MemorySave"),
}


def load_tool_class(name):
    entry = TOOLS.get(name)
    if entry is None:
        return None
    module_name, class_name = entry
    try:
        return getattr(importlib.import_module(module_name), class_name)
    except ImportError as e:
        raise ImportError(
            f"Agent 工具 {name} 缺少依赖（{module_name}），请按 requirements/ 里的对应分组安装后重试"
        ) from e


class ToolRegistry:
    """按 config 白名单实例化工具；description/parameters 直接喂给模型。"""

    def __init__(self, config):
        self._tools: dict = {}
        enabled = config.get("agent", "tools", "enabled") or []
        dangerous_enabled = config.get("agent", "tools", "dangerous_enabled") or []
        for name in enabled:
            try:
                cls = load_tool_class(name)
            except ImportError as e:
                logger.warning(str(e))
                continue
            if cls is None:
                logger.warning(f"Agent 工具 {name} 未注册，已跳过")
                continue
            tool = cls()
            if tool.name != name:
                logger.warning(f"Agent 工具 {name} 的类属性 name={tool.name} 不一致，已跳过")
                continue
            if tool.dangerous and name not in dangerous_enabled:
                continue
            self._tools[tool.name] = tool

    def get(self, name):
        return self._tools.get(name)

    def specs(self) -> list:
        """喂给模型的工具清单（原生 FC 与文本协议共用）。"""
        return [
            {"name": tool.name, "description": tool.description, "parameters": tool.parameters}
            for tool in self._tools.values()
        ]
