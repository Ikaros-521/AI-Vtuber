"""登录门禁（对齐 v2 login.enable 的 UI 门控行为）。

* v2 走 UMS 云账号；v3 是本地校验：账号密码取 config.json 的 login.username/password。
* 与 v2 一致只挡 UI，不挡 /set_config 等机机接口（main.py 不带凭证调用它们）。
* 会话存内存令牌（cookie），服务重启后需要重新登录。
"""

import secrets

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from webui_server.runtime import runtime

router = APIRouter(prefix="/api/auth")

# 内存会话表：token -> username。重启即清空
_sessions: dict[str, str] = {}

COOKIE_NAME = "webui_v3_session"


def _login_enabled() -> bool:
    try:
        return bool(runtime.get("login", "enable"))
    except Exception:
        return False


def _check_credentials(username: str, password: str) -> bool:
    expect_user = str(runtime.get("login", "username") or "")
    expect_pass = str(runtime.get("login", "password") or "")
    return secrets.compare_digest(username, expect_user) and secrets.compare_digest(password, expect_pass)


@router.get("/status")
def status(request: Request):
    token = request.cookies.get(COOKIE_NAME, "")
    authed = token in _sessions
    return {"code": 200, "enabled": _login_enabled(), "authed": authed, "username": _sessions.get(token)}


@router.post("/login")
def login(request: Request, body: dict):
    if not _login_enabled():
        return {"code": 200, "message": "登录功能未启用"}
    username = str(body.get("username") or "")
    password = str(body.get("password") or "")
    if not username or not password:
        return {"code": -1, "message": "用户名或密码不能为空"}
    if not _check_credentials(username, password):
        return {"code": -1, "message": "用户名或密码不正确"}

    token = secrets.token_urlsafe(32)
    _sessions[token] = username
    resp = JSONResponse({"code": 200, "message": f"登录成功，欢迎 {username}"})
    resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax")
    return resp


@router.post("/logout")
def logout(request: Request):
    token = request.cookies.get(COOKIE_NAME, "")
    _sessions.pop(token, None)
    resp = JSONResponse({"code": 200, "message": "已退出登录"})
    resp.delete_cookie(COOKIE_NAME)
    return resp
