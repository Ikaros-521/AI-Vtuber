"""一键运行 / 停止 / 重启 / 恢复出厂，以及运行态查询。"""

from fastapi import APIRouter
from pydantic import BaseModel

from webui_server.runtime import runtime
from webui_server.schemas import Envelope, OpsStatus

router = APIRouter(prefix="/api/ops")


class FactoryRequest(BaseModel):
    src_path: str = "config.json.bak"
    dst_path: str | None = None


@router.get("/status", response_model=OpsStatus)
def status():
    return {"code": 200, "running": bool(runtime.running_flag)}


@router.post("/run", response_model=Envelope)
def run():
    ok, message = runtime.run()
    return {"code": 200 if ok else -1, "message": message}


@router.post("/stop", response_model=Envelope)
def stop():
    ok, message = runtime.stop()
    return {"code": 200 if ok else -1, "message": message}


@router.post("/restart", response_model=Envelope)
def restart():
    """重启 webui_server 本身。进程会 os.execl 自替换，这个响应可能送不到。"""
    runtime.restart()
    return {"code": 200, "message": "重启中..."}


@router.post("/factory", response_model=Envelope)
def factory(req: FactoryRequest):
    ok, message = runtime.factory(req.src_path, req.dst_path)
    if ok:
        runtime.restart()
    return {"code": 200 if ok else -1, "message": message}
