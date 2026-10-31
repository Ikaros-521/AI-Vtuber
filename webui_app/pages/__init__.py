"""页面构建约定：创建 UI，并交出该页的保存动作。

- mapping 交给 webui_config_to_dict 里的 update_config 统一落盘
- on_save 处理无法用「控件 -> 字段」表达的副作用（如写 Live2D 模型名文件）
"""

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class PageConfig:
    mapping: dict = field(default_factory=dict)
    on_save: Optional[Callable[[dict], None]] = None
