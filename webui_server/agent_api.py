"""Agent 工作台（v5）后端：总览 / 运行态代理 / 急停 / 记忆管理 / 决策回放。

数据分两路（docs/agent-upgrade-design.md §7）：
- 配置与工具目录：webui 侧直接读 config.json 与 luna.agent.registry（静态目录）；
- 运行态与 trace：代理到 main.py 的内部机机接口（/agent_status /agent_trace
  /agent_kill，见 app/api.py），主进程不在运行时降级为 running=false；
- 记忆（viewer_profile / agent_episodic）：sqlite 共享文件，webui 侧经
  MemorySystem 直接读写（与主进程各开短连接，SQLite 自身兜并发）。
"""

import traceback

from fastapi import APIRouter
from pydantic import BaseModel

from luna.infra.db import SQLiteDB
from luna.infra.my_log import logger
from webui_server.runtime import runtime
from webui_server.schemas import (
    AgentHighlightListResult,
    AgentOverviewResult,
    AgentTraceResult,
    AgentViewerListResult,
    AssistantSettingsResult,
    ConfigApplyResult,
    ConfigChatResult,
    Envelope,
)

router = APIRouter(prefix="/api/agent")


class AgentKillRequest(BaseModel):
    on: bool = True


class AgentNoteRequest(BaseModel):
    platform: str
    username: str
    note: str = ""


class AgentDeleteRequest(BaseModel):
    platform: str
    username: str


class AgentHighlightDeleteRequest(BaseModel):
    row_id: int


class ConfigChatRequest(BaseModel):
    session_id: str = "default"
    message: str


class ConfigApplyRequest(BaseModel):
    changes: list


class AssistantSettingsRequest(BaseModel):
    safety_level: str


_assistant_singleton = None


def _get_assistant():
    """配置助手懒单例（webui 进程内；测试可 monkeypatch 本函数）。"""
    global _assistant_singleton
    if _assistant_singleton is None:
        from webui_server.config_assistant import ConfigAssistant

        _assistant_singleton = ConfigAssistant(runtime)
    return _assistant_singleton


# ---------- 内部工具 ----------


def _main_api_base():
    """main.py 内部 API 地址（compat_api 同款取法）。"""
    config = runtime.read_config()
    main_api_ip = "127.0.0.1" if config.get("api_ip") == "0.0.0.0" else config.get("api_ip")
    return f"http://{main_api_ip}:{config.get('api_port')}"


async def _proxy_main(path: str, method: str = "GET", payload=None, timeout: int = 10):
    """代理到主进程机机接口；主进程不在运行时返回 (None, 提示)。"""
    try:
        resp = await runtime.common.send_async_request(
            f"{_main_api_base()}{path}", method, payload, "json", timeout=timeout
        )
        return resp, None
    except Exception as e:
        return None, str(e)


def _memory_system():
    """按当前配置开一个 MemorySystem（管理接口不受 enable_profile 限制）。"""
    from luna.agent.memory import MemorySystem

    db_path = runtime.get("database", "path") or "data/data.db"
    return MemorySystem(SQLiteDB(str(db_path)), enable_profile=True, enable_episodic=True)


def _tool_catalog() -> list:
    """静态工具目录：注册表全量（含未启用的），供前端卡片墙渲染。"""
    from luna.agent.registry import TOOLS, load_tool_class

    catalog = []
    for name, (_, _) in TOOLS.items():
        dangerous = False
        description = ""
        try:
            tool = load_tool_class(name)()
            dangerous = bool(tool.dangerous)
            description = tool.description
        except Exception as e:
            description = f"（工具加载失败：{e}）"
        catalog.append({"name": name, "description": description, "dangerous": dangerous})
    return catalog


# ---------- 总览 / 运行态 / 急停 ----------


@router.get("/overview", response_model=AgentOverviewResult)
async def overview():
    try:
        agent_cfg = runtime.get("agent") or {}
        runtime_state, proxy_error = await _proxy_main("/agent_status")
        running = False
        runtime_info = None
        if isinstance(runtime_state, dict) and runtime_state.get("code") == 200:
            running = True
            runtime_info = runtime_state.get("data", {}).get("runtime")
        elif proxy_error:
            logger.debug(f"Agent 运行态代理失败（主进程可能未运行）：{proxy_error}")
        return {
            "code": 200,
            "agent": agent_cfg,
            "tool_catalog": _tool_catalog(),
            "running": running,
            "runtime": runtime_info,
        }
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"获取 Agent 总览失败：{e}"}


@router.get("/stats", response_model=Envelope)
async def stats():
    """决策聚合统计（P1 尾部度量），代理主进程 /agent_stats。"""
    try:
        resp, proxy_error = await _proxy_main("/agent_stats")
        if isinstance(resp, dict) and resp.get("code") == 200:
            return {"code": 200, **resp.get("data", {})}
        message = proxy_error or (resp.get("message", "主进程未响应") if isinstance(resp, dict) else "主进程未响应")
        return {"code": -1, "message": f"读取统计失败：{message}"}
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"读取统计失败：{e}"}


@router.get("/trace", response_model=AgentTraceResult)
async def trace():
    try:
        resp, proxy_error = await _proxy_main("/agent_trace")
        if isinstance(resp, dict) and resp.get("code") == 200:
            return {"code": 200, "records": resp.get("data", {}).get("records") or []}
        if proxy_error:
            message = proxy_error
        elif isinstance(resp, dict):
            message = resp.get("message", "主进程未响应")
        else:
            message = "主进程未响应（可能未运行）"
        return {"code": -1, "records": [], "message": f"读取决策记录失败：{message}"}
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"读取决策记录失败：{e}"}


@router.post("/kill", response_model=Envelope)
async def kill(req: AgentKillRequest):
    """一键急停（主进程内立即生效，不落盘）；持久开关仍是 config 的 agent.enabled。"""
    try:
        resp, proxy_error = await _proxy_main("/agent_kill", "POST", {"on": req.on})
        if isinstance(resp, dict) and resp.get("code") == 200:
            return {"code": 200, "message": resp.get("message", "已执行")}
        if proxy_error:
            message = proxy_error
        elif isinstance(resp, dict):
            message = resp.get("message", "主进程未响应")
        else:
            message = "主进程未响应（可能未运行）"
        return {"code": -1, "message": f"急停失败：{message}"}
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"急停失败：{e}"}


# ---------- 配置助手（v5 P2：需求 → 配置变更集 → 按安全等级应用） ----------


@router.post("/config-chat", response_model=ConfigChatResult)
def config_chat(req: ConfigChatRequest):
    """一轮配置对话：模型输出变更集，按安全等级决定直接落盘还是挂起待确认。"""
    try:
        assistant = _get_assistant()
        result = assistant.chat(req.session_id, req.message)
        level = assistant.safety_level()
        for change in result["changes"]:
            if level == "full" or (level == "auto" and not change["danger"]):
                ok = assistant.apply_changes([change])[0]["ok"]
                change["status"] = "applied" if ok else "failed"
            else:
                change["status"] = "pending"
        return {
            "code": 200,
            "reply": result["reply"],
            "changes": result["changes"],
            "questions": result["questions"],
            "level": level,
        }
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"配置助手出错：{e}"}


@router.post("/config-apply", response_model=ConfigApplyResult)
def config_apply(req: ConfigApplyRequest):
    """应用（前端确认过的）变更集：原子写盘。"""
    try:
        results = _get_assistant().apply_changes(req.changes)
        ok_count = sum(1 for r in results if r["ok"])
        return {
            "code": 200,
            "message": f"已应用 {ok_count}/{len(results)} 条变更，重启程序后生效",
            "results": results,
        }
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"应用变更失败：{e}"}


@router.get("/assistant-settings", response_model=AssistantSettingsResult)
def assistant_settings():
    try:
        assistant = _get_assistant()
        return {"code": 200, "safety_level": assistant.safety_level()}
    except Exception as e:
        return {"code": -1, "message": f"读取助手设置失败：{e}"}


@router.post("/assistant-settings", response_model=AssistantSettingsResult)
def set_assistant_settings(req: AssistantSettingsRequest):
    try:
        ok, message = _get_assistant().set_safety_level(req.safety_level)
        return {"code": 200 if ok else -1, "message": message}
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"保存助手设置失败：{e}"}


# ---------- 记忆管理 ----------


@router.get("/memory/viewers", response_model=AgentViewerListResult)
def memory_viewers(keyword: str = "", limit: int = 100):
    try:
        viewers = _memory_system().list_viewers(keyword=keyword, limit=max(1, min(limit, 500)))
        return {
            "code": 200,
            "viewers": [
                {
                    "platform": row[0],
                    "username": row[1],
                    "first_seen": str(row[2]),
                    "last_seen": str(row[3]),
                    "interactions": row[4],
                    "note": row[5],
                }
                for row in viewers
            ],
        }
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"读取观众画像失败：{e}"}


@router.post("/memory/viewer/note", response_model=Envelope)
def memory_set_note(req: AgentNoteRequest):
    try:
        _memory_system().save_note(req.platform, req.username, req.note)
        return {"code": 200, "message": "备注已保存"}
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"保存备注失败：{e}"}


@router.post("/memory/viewer/delete", response_model=Envelope)
def memory_delete_viewer(req: AgentDeleteRequest):
    try:
        _memory_system().delete_viewer(req.platform, req.username)
        return {"code": 200, "message": "已删除该观众画像"}
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"删除画像失败：{e}"}


@router.get("/memory/highlights", response_model=AgentHighlightListResult)
def memory_highlights(limit: int = 50):
    try:
        highlights = _memory_system().list_highlights(limit=max(1, min(limit, 200)))
        return {
            "code": 200,
            "highlights": [
                {"row_id": row[0], "ts": str(row[1]), "username": row[2], "content": row[3]} for row in highlights
            ],
        }
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"读取高光失败：{e}"}


@router.post("/memory/highlight/delete", response_model=Envelope)
def memory_delete_highlight(req: AgentHighlightDeleteRequest):
    try:
        _memory_system().delete_highlight(req.row_id)
        return {"code": 200, "message": "已删除该条高光"}
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"删除高光失败：{e}"}
