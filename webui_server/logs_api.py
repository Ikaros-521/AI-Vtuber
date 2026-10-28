"""日志类 API：运行日志尾部、聊天记录拉取、聊天测试发送。"""
import os

from fastapi import APIRouter
from pydantic import BaseModel

from utils.my_log import logger, file_path as log_file_path
from webui_server.chat_log import chat_log
from webui_server.runtime import runtime

router = APIRouter(prefix="/api")


# ---------- 运行日志（实现取自 v2 webui_app/run_log.tail，去掉 NiceGUI 依赖） ----------

MAX_LINES = 400
BYTES_PER_LINE = 2048


def tail(path, limit=MAX_LINES):
    """返回 (行列表, 一句话说明)。文件不在/读不动时不抛异常。"""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - limit * BYTES_PER_LINE))
            read_from = f.tell()
            text = f.read().decode("utf-8", errors="replace")
    except OSError as e:
        return [], f"读不到日志文件：{e}"
    lines = text.splitlines()
    if read_from > 0 and lines:
        lines = lines[1:]  # 窗口开头那行是被切开的半行
    cut = read_from > 0 or len(lines) > limit
    lines = lines[-limit:]
    if cut:
        return lines, f"只显示最后 {len(lines)} 行（文件共 {max(1, size // 1024)} KB，往前的没读）"
    return lines, f"共 {len(lines)} 行"


@router.get("/logs/run")
def run_log():
    path = log_file_path
    lines, note = tail(path)
    return {"code": 200, "title": f"运行日志 · {os.path.basename(path)}", "note": note, "lines": lines}


# ---------- 聊天记录 ----------

@router.get("/chat-log")
def chat_log_view(after: int = 0):
    return {"code": 200, "messages": chat_log.since(after)}


# ---------- 聊天测试发送（对应 v2 pages/chat.py 的 do_send/do_reread/do_tuning） ----------

class ChatSendRequest(BaseModel):
    mode: str = "comment"  # comment / reread / tuning
    username: str = "主播"
    content: str


@router.post("/chat-log/send")
async def chat_send(req: ChatSendRequest):
    if not runtime.running_flag:
        return {"code": -1, "message": "核心服务未运行，请先点击「一键运行」"}
    content = req.content.strip()
    if not content:
        return {"code": -1, "message": "内容为空"}

    data = {
        "type": req.mode,
        "data": {
            "type": req.mode,
            "username": req.username.strip() or "主播",
            "content": content,
        },
    }
    if req.mode == "comment":
        data["data"]["platform"] = "webui"

    config = runtime.read_config()
    main_api_ip = "127.0.0.1" if config.get("api_ip") == "0.0.0.0" else config.get("api_ip")
    try:
        resp = await runtime.common.send_async_request(
            f"http://{main_api_ip}:{config.get('api_port')}/send", "POST", data)
    except Exception as e:
        logger.error(f"聊天发送失败: {e}")
        return {"code": -1, "message": f"发送失败：{e}"}

    # 同步弹幕开了的话，自己的发言也进聊天窗（v2 do_reread 的行为）
    if config.get("talk", "show_chat_log") and req.mode == "reread":
        chat_log.add({
            "type": "llm",
            "data": {
                "type": req.mode,
                "username": data["data"]["username"],
                "content_type": "question",
                "content": content,
                "timestamp": runtime.common.get_bj_time(0),
            },
        })

    return resp or {"code": 200, "message": "已发送"}
