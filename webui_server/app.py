"""FastAPI 应用装配：API 路由 + React 构建产物托管。"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from utils.my_log import logger
from webui_server import actions_api, auth_api, compat_api, config_api, logs_api, ops_api
from webui_server.runtime import runtime, ROOT_DIR

DIST_DIR = ROOT_DIR / "webui_react" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(title="AI-Vtuber WebUI", version="3.0")

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

    @app.on_event("startup")
    async def on_startup():
        logger.info(f"webui_server 启动，配置文件：{runtime.config_path}")

    # v2 的「本地目录映射为 URL」能力保留
    try:
        config = runtime.read_config()
        for entry in (config.get("webui", {}).get("local_dir_to_endpoint", {}) or {}).get("config", []) or []:
            if entry.get("enable", True) and entry.get("url_path") and entry.get("local_dir"):
                app.mount(entry["url_path"], StaticFiles(directory=entry["local_dir"]), name=entry["url_path"].strip("/"))
    except Exception as e:
        logger.warning(f"本地目录映射未生效：{e}")

    if DIST_DIR.exists():
        app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="webui")
    else:
        @app.get("/")
        async def index():
            return {"code": 200, "message": "AI-Vtuber WebUI v3 API 正在运行。前端未构建：请到 webui_react/ 执行 npm run build，或使用 npm run dev。"}

    return app
