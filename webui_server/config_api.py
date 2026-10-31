"""配置读写 API。

保存采用「diff 应用」语义：前端把改动算成 [{path, value}] 列表发来，服务端在
最新文件上打补丁后落盘——外部脚本通过 /set_config 改过的配置不会被页面上
打开时的旧快照覆盖（与 v2 的 update_config 只写映射字段的语义对齐）。
"""

from fastapi import APIRouter
from pydantic import BaseModel

from utils.my_log import logger
from webui_server.runtime import runtime
from webui_server.schemas import ConfigGetResult, ConfigSaveResult

router = APIRouter(prefix="/api/config")


class ConfigChange(BaseModel):
    path: list
    value: object


class SaveRequest(BaseModel):
    base_sha256: str
    changes: list[ConfigChange]


def _update_nested(target, keys, value):
    if len(keys) == 1:
        target[keys[0]] = value
        return
    if not isinstance(target.get(keys[0]), dict):
        target[keys[0]] = {}
    _update_nested(target[keys[0]], keys[1:], value)


def validate_config(config_data):
    """保存前校验，移植自 v2 common_config.check_config 的拦截部分。

    返回 None 表示可以写盘，否则 (提示语, 配置路径)。
    """
    platform = config_data.get("platform")
    if platform == "bilibili2":
        bilibili = config_data.get("bilibili") or {}
        login_type = bilibili.get("login_type")
        if login_type == "cookie" and not (bilibili.get("cookie") or "").strip():
            return "B站登录方式选的是 cookie，但 cookie 还空着", ["bilibili", "cookie"]
        if login_type == "open_live":
            open_live = bilibili.get("open_live") or {}
            missing = [
                k
                for k in ("ACCESS_KEY_ID", "ACCESS_KEY_SECRET", "APP_ID", "ROOM_OWNER_AUTH_CODE")
                if not str(open_live.get(k) or "").strip()
            ]
            if missing:
                return (
                    "B站开放平台四项（ACCESS_KEY_ID / ACCESS_KEY_SECRET / 项目ID / 身份码）还没填全",
                    ["bilibili", "open_live", missing[0]],
                )
    return None


@router.get("", response_model=ConfigGetResult)
def get_config():
    try:
        config_data = runtime.read_config()
        return {"code": 200, "config": config_data, "sha256": runtime.file_sha256(), "path": runtime.config_path}
    except Exception as e:
        logger.error(f"读取配置失败: {e}")
        return {"code": -1, "message": f"读取配置失败：{e}"}


@router.post("/save", response_model=ConfigSaveResult)
def save_config(req: SaveRequest):
    try:
        current_sha = runtime.file_sha256()
    except Exception as e:
        return {"code": -1, "message": f"配置文件读不出来：{e}"}

    if current_sha != req.base_sha256:
        return {"code": 409, "message": "配置文件在页面打开后被外部程序修改过，为防覆盖已拦截。请刷新页面后再改。"}

    try:
        config_data = runtime.read_config()
    except Exception as e:
        return {"code": -1, "message": f"配置文件读不出来：{e}"}

    for change in req.changes:
        _update_nested(config_data, list(change.path), change.value)

    error = validate_config(config_data)
    if error is not None:
        message, path = error
        return {"code": 422, "message": message, "path": path}

    try:
        runtime.write_config(config_data)
        logger.info(f"配置数据已成功写入文件（{len(req.changes)} 项改动）")
        _side_effects(config_data, req.changes)
        return {"code": 200, "message": "配置数据已成功写入文件！", "sha256": runtime.file_sha256()}
    except Exception as e:
        logger.error(f"无法写入配置文件！\n{e}")
        return {"code": -1, "message": f"配置文件写不进去：{e}"}


def _side_effects(config_data, changes):
    """v2 各页面 on_save 里的落盘副作用，按改动触发。"""
    # Live2D 模型名写进 Live2D/js/model_name.js（v2 visual_body.write_live2d_model_name）
    if any(list(c.path) == ["live2d", "name"] for c in changes):
        from webui_server.runtime import ROOT_DIR

        name = (config_data.get("live2d") or {}).get("name") or ""
        path = ROOT_DIR / "Live2D" / "js" / "model_name.js"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f'var model_name = "{name}";')
        logger.info(f"Live2D 模型名已写入 {path}：{name}")
