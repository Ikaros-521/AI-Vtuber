"""表单里的动作按钮后端：LLM 测试/模型搜索、本地文件读写、枚举类、串口、配置模板。

对应 v2 各页面里混在字段旁边的 ui.button。参数由前端从草稿里取值传过来；
密钥类参数不落日志。
"""
import asyncio
import json
import traceback
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from utils.my_log import logger
from webui_server.runtime import runtime, ROOT_DIR

router = APIRouter(prefix="/api")


# ---------- 本地文件读写（本地问答 JSON 等外部文件） ----------

class FileWriteRequest(BaseModel):
    path: str
    content: str


@router.get("/file")
def read_file(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        return {"code": 200, "content": text}
    except Exception as e:
        return {"code": -1, "message": f"读这个路径读不了：{e}"}


@router.put("/file")
def write_file(req: FileWriteRequest):
    try:
        with open(req.path, "w", encoding="utf-8") as f:
            f.write(req.content)
            f.flush()
        return {"code": 200, "message": "文件已写入"}
    except Exception as e:
        logger.error(f"写文件失败 {req.path}: {e}")
        return {"code": -1, "message": f"写文件失败：{e}"}


# ---------- LLM：OpenAI 兼容接口测试与模型搜索 ----------

class LlmTestRequest(BaseModel):
    base_url: str = ""
    api_keys: list[str] = []
    model: str = ""
    temperature: float = 0.9
    max_tokens: int = 0
    top_p: float = 1
    presence_penalty: float = 0
    frequency_penalty: float = 0
    preset: str = ""


@router.post("/actions/llm-test")
async def llm_test(req: LlmTestRequest):
    try:
        resp = await asyncio.to_thread(
            runtime.common.test_openai_key, req.model_dump(), 2)
        return resp
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "msg": f"测试失败：{e}"}


class LlmModelsRequest(BaseModel):
    base_url: str = ""
    api_keys: list[str] = []


@router.post("/actions/llm-models")
async def llm_models(req: LlmModelsRequest):
    try:
        resp = await asyncio.to_thread(
            runtime.common.get_openai_models, req.base_url, "\n".join(req.api_keys))
        if resp.get("code") == 200:
            return {"code": 200, "models": resp.get("models", [])}
        return {"code": -1, "message": resp.get("msg", "获取模型列表失败")}
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"获取模型列表失败：{e}"}


# ---------- 枚举：窗口标题 / 摄像头 / 配置模板 ----------

@router.get("/actions/window-titles")
def window_titles():
    try:
        return {"code": 200, "items": runtime.common.list_visible_windows()}
    except Exception as e:
        return {"code": -1, "message": f"枚举窗口失败：{e}"}


@router.get("/actions/cameras")
def cameras():
    try:
        return {"code": 200, "items": runtime.common.list_cameras()}
    except Exception as e:
        return {"code": -1, "message": f"枚举摄像头失败：{e}"}


@router.get("/actions/config-templates")
def config_templates():
    try:
        return {"code": 200, "items": runtime.common.get_specify_extension_names_in_folder(str(ROOT_DIR), "*.json")}
    except Exception as e:
        return {"code": -1, "message": f"枚举配置模板失败：{e}"}


# ---------- 配置模板：保存当前配置文件 / 读取模板覆盖配置文件 ----------

class TemplateRequest(BaseModel):
    path: str


@router.post("/actions/config-template-save")
def config_template_save(req: TemplateRequest):
    """把当前 config.json 原样存为模板。注意：未保存的界面改动不含在内（先点「保存配置」）。"""
    try:
        with open(runtime.config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        with open(req.path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
            f.flush()
        return {"code": 200, "message": "配置模板保存成功！"}
    except Exception as e:
        return {"code": -1, "message": f"配置模板保存失败：{e}"}


@router.post("/actions/config-template-load")
def config_template_load(req: TemplateRequest):
    """用模板覆盖当前 config.json，需重启 webui 生效。"""
    try:
        with open(req.path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        with open(runtime.config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
            f.flush()
        return {"code": 200, "message": "配置模板加载成功！重启 webui 后读取。想反悔就在重启前把配置改回来再保存。"}
    except Exception as e:
        return {"code": -1, "message": f"配置模板读取失败：{e}"}


# ---------- AnythingLLM 工作区列表 ----------

class AnythingllmRequest(BaseModel):
    api_ip_port: str = ""
    api_key: str = ""


@router.post("/actions/anythingllm-workspaces")
async def anythingllm_workspaces(req: AnythingllmRequest):
    try:
        def fetch():
            from utils.gpt_model.anythingllm import AnythingLLM

            anythingllm = AnythingLLM({"api_ip_port": req.api_ip_port, "api_key": req.api_key})
            return [w["slug"] for w in anythingllm.get_workspaces_list()]

        slugs = await asyncio.to_thread(fetch)
        return {"code": 200, "items": slugs, "message": "读取工作区成功"}
    except Exception as e:
        logger.error(f"读取工作区失败！{e}")
        return {"code": -1, "message": f"读取工作区失败！{e}"}


# ---------- 串口：列表 / 连接 / 断开 / 发送 ----------

def _serial_manager():
    from utils.serial_manager_instance import get_serial_manager

    return get_serial_manager()


@router.get("/actions/serial-ports")
async def serial_ports():
    try:
        ports = await _serial_manager().list_ports()
        return {"code": 200, "items": ports, "message": f"搜索到的串口：{ports}"}
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"搜索串口失败：{e}"}


class SerialConnectRequest(BaseModel):
    serial_name: str
    baudrate: str


@router.post("/actions/serial-connect")
async def serial_connect(req: SerialConnectRequest):
    try:
        resp = await _serial_manager().connect(req.serial_name, req.baudrate)
        return {"code": 200 if resp.get("ret") else -1, "message": resp.get("msg", "")}
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"连接串口失败：{e}"}


class SerialNameRequest(BaseModel):
    serial_name: str


@router.post("/actions/serial-disconnect")
async def serial_disconnect(req: SerialNameRequest):
    try:
        resp = await _serial_manager().disconnect(req.serial_name)
        return {"code": 200 if resp.get("ret") else -1, "message": resp.get("msg", "")}
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"关闭串口失败：{e}"}


class SerialSendRequest(BaseModel):
    serial_name: str
    data: str
    data_type: str = "ASCII"


@router.post("/actions/serial-send")
async def serial_send(req: SerialSendRequest):
    try:
        resp = await _serial_manager().send_data(req.serial_name, req.data, req.data_type)
        return {"code": 200 if resp.get("ret") else -1, "message": resp.get("msg", "")}
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"发送串口数据失败：{e}"}


# ---------- 图像识别：截图并发送（一次性） ----------

class ImgScreenshotRequest(BaseModel):
    source: str = "window"  # window / camera
    title_or_index: str = ""  # 窗口标题或摄像头索引
    img_save_path: str = ""
    prompt: str = ""
    model: str = "gemini"


@router.post("/actions/img-screenshot")
async def img_screenshot(req: ImgScreenshotRequest):
    """截屏 → 多模态模型 → 结果作为 reread 消息发给 main.py。需要核心程序在运行。"""
    if not runtime.running_flag:
        return {"code": -1, "message": "请先点击「一键运行」启动核心服务，再进行截图识别"}
    try:
        if req.source == "window":
            screenshot_path = await asyncio.to_thread(
                runtime.common.capture_window_by_title, req.img_save_path, req.title_or_index)
        else:
            screenshot_path = await asyncio.to_thread(
                runtime.common.capture_image, req.img_save_path, int(req.title_or_index or 0))

        if req.model == "zhipu":
            from utils.gpt_model.zhipu import Zhipu

            zhipu = Zhipu(runtime.get("image_recognition", "zhipu") or {})
            content = zhipu.get_resp_with_img(req.prompt, screenshot_path)
            data = {"type": "reread", "data": {
                "username": runtime.get("talk", "username") or "主播",
                "content": content, "insert_index": -1}}
        else:
            from utils.gpt_model.gemini import Gemini

            gemini = Gemini(runtime.get("image_recognition", "gemini") or {})
            content = gemini.get_resp_with_img(req.prompt, screenshot_path)
            data = {"type": "reread",
                    "username": runtime.get("talk", "username") or "主播",
                    "content": content, "insert_index": -1}

        config = runtime.read_config()
        main_api_ip = "127.0.0.1" if config.get("api_ip") == "0.0.0.0" else config.get("api_ip")
        await runtime.common.send_async_request(
            f"http://{main_api_ip}:{config.get('api_port')}/send", "POST", data)
        return {"code": 200, "message": "截图识别完成，结果已发送"}
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"截图识别失败：{e}"}
