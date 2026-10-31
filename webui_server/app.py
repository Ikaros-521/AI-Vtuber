"""FastAPI 应用装配：API 路由 + React 构建产物托管。"""

import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from utils.my_log import logger
from webui_server import actions_api, auth_api, compat_api, config_api, logs_api, ops_api
from webui_server.auth_api import COOKIE_NAME, is_valid_session
from webui_server.runtime import ROOT_DIR, runtime

DIST_DIR = ROOT_DIR / "webui_react" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"webui_server 启动，配置文件：{runtime.config_path}")
    yield
    # 正常退出（Ctrl+C / 停止）时把运行中的 main.py 等子进程一并停掉，避免残留
    try:
        runtime.stop()
    except Exception as e:
        logger.warning(f"退出时清理子进程失败：{e}")


def _login_enabled() -> bool:
    try:
        return bool(runtime.get("login", "enable"))
    except Exception:
        return False


def create_app() -> FastAPI:
    app = FastAPI(title="AI-Vtuber WebUI", version="3.0", lifespan=lifespan)

    # 开发期 Vite (5173) 直连后端时用；正式部署同源，不受影响
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(config_api.router)
    app.include_router(ops_api.router)
    app.include_router(logs_api.router)
    app.include_router(actions_api.router)
    app.include_router(auth_api.router)
    app.include_router(compat_api.router)

    # 统一异常兜底：业务路由全部走 {code, message} 信封，
    # 未捕获异常若漏成裸 500 会破坏前端信封约定
    @app.exception_handler(Exception)
    async def uncaught_exception_handler(request: Request, exc: Exception):
        logger.error(f"未处理异常 {request.method} {request.url.path}:\n{traceback.format_exc()}")
        return JSONResponse({"code": -1, "message": f"服务器内部错误：{exc}"})

    # 登录门禁：启用登录后，服务端强制校验 /api/* 的会话。
    # v2 只挡 UI 不挡接口；v3 对人机接口（/api/*）做服务端强制，
    # 机机接口（根路径 /set_config /sys_cmd /send 等，main.py 不带凭证调用）保持开放。
    @app.middleware("http")
    async def login_guard(request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/") and not path.startswith("/api/auth/") and _login_enabled():
            token = request.cookies.get(COOKIE_NAME, "")
            if not is_valid_session(token):
                return JSONResponse({"code": 401, "message": "未登录或会话已过期，请重新登录"}, status_code=401)
        return await call_next(request)

    # v2 的「本地目录映射为 URL」能力保留
    try:
        config = runtime.read_config()
        for entry in (config.get("webui", {}).get("local_dir_to_endpoint", {}) or {}).get("config", []) or []:
            if entry.get("enable", True) and entry.get("url_path") and entry.get("local_dir"):
                app.mount(
                    entry["url_path"], StaticFiles(directory=entry["local_dir"]), name=entry["url_path"].strip("/")
                )
    except Exception as e:
        logger.warning(f"本地目录映射未生效：{e}")

    if DIST_DIR.exists():
        app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="webui")
    else:

        @app.get("/")
        async def index():
            return {
                "code": 200,
                "message": "AI-Vtuber WebUI v3 API 正在运行。前端未构建：请到 webui_react/ 执行 npm run build，或使用 npm run dev。",
            }

    return app
