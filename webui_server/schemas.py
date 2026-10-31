"""webui_server 的响应模型（response_model）。

作用：
- OpenAPI 文档里前端能看到每个接口的真实返回形状；
- response_model 会过滤未声明字段，等于把「信封结构」从测试约定升级为接口契约。

兼容性：启动环境可能是 pydantic v1（仓库自带 Miniconda）或 v2（.venv），
注解一律用 v1/v2 都支持的写法（Optional[X]、dict、list[str]），
不用 model_dump / v2 独有特性。

字段声明原则：错误分支只返回 {code, message}，所以业务字段全部带默认值；
这与前端 src/api/client.ts 的类型声明一一对应，改动形状需两边同步。
未覆盖：actions_api（动作按钮返回形状松散，维持信封约定由测试锁定）
与 compat_api（机机接口，保持 v2 混用 code/msg 的历史契约）。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class Envelope(BaseModel):
    code: int
    message: str = ""


class ConfigGetResult(Envelope):
    config: Dict[str, Any] = {}
    sha256: str = ""
    path: str = ""


class ConfigSaveResult(Envelope):
    # 422 校验失败时回传配置路径数组供前端跳转
    path: Optional[List[Any]] = None


class OpsStatus(Envelope):
    running: bool = False


class AuthStatus(Envelope):
    enabled: bool = False
    authed: bool = False
    username: Optional[str] = None


class RunLogResult(Envelope):
    title: str = ""
    note: str = ""
    lines: List[str] = []


class ChatLogResult(Envelope):
    messages: List[Dict[str, Any]] = []
