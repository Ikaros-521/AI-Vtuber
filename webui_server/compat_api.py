"""对 main.py 与外部脚本暴露的旧接口，行为与 v2 webui_app/api.py 保持一致。

/set_config、/sys_cmd、/send、/callback、/tts、/llm、/get_sys_info。
"""

import json
import traceback

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from utils.models import CommonResult, SendMessage, SetConfigMessage, SysCmdMessage
from utils.my_log import logger
from webui_server.chat_log import chat_log
from webui_server.runtime import runtime

router = APIRouter()


@router.post("/set_config")
async def set_config(msg: SetConfigMessage):
    """外部脚本改配置：在指定配置文件上做浅合并后写盘。"""
    try:
        try:
            with open(msg.config_path, encoding="utf-8") as config_file:
                config_data = json.load(config_file)
        except Exception as e:
            logger.error(f"无法读取配置文件！\n{e}")
            return CommonResult(code=-1, message=f"无法读取配置文件！{e}")

        config_data.update(msg.data)

        try:
            with open(msg.config_path, "w", encoding="utf-8") as config_file:
                json.dump(config_data, config_file, indent=2, ensure_ascii=False)
                config_file.flush()
            logger.info("配置数据已成功写入文件！")
            return CommonResult(code=200, message="配置数据已成功写入文件！")
        except Exception as e:
            logger.error(f"无法写入配置文件！\n{e}")
            return CommonResult(code=-1, message=f"无法写入配置文件！{e}")
    except Exception as e:
        logger.error(traceback.format_exc())
        return CommonResult(code=-1, message=f"执行失败！{e}")


@router.post("/sys_cmd")
async def sys_cmd(msg: SysCmdMessage):
    """系统命令：run / stop / restart / factory。"""
    try:
        logger.info(f"sys_cmd接口 收到数据：{msg.dict()}")
        if msg.type == "run":
            ok, message = runtime.run()
            return {"code": 200 if ok else -1, "msg": message}
        if msg.type == "stop":
            ok, message = runtime.stop()
            return {"code": 200 if ok else -1, "msg": message}
        if msg.type == "restart":
            runtime.restart()
            return {"code": 200, "msg": "重启中..."}
        if msg.type == "factory":
            data = msg.data or {}
            ok, message = runtime.factory(data.get("src_path", "config.json.bak"), data.get("dst_path"))
            if ok:
                runtime.restart()
            return {"code": 200 if ok else -1, "msg": message}
        return CommonResult(code=-1, message=f"未知命令：{msg.type}")
    except Exception as e:
        logger.error(traceback.format_exc())
        return CommonResult(code=-1, message=f"{msg.type}执行失败！{e}")


@router.post("/send")
async def send(msg: SendMessage):
    """转发数据到 main.py 的 /send。"""
    try:
        config = runtime.read_config()
        main_api_ip = "127.0.0.1" if config.get("api_ip") == "0.0.0.0" else config.get("api_ip")
        return await runtime.common.send_async_request(
            f"http://{main_api_ip}:{config.get('api_port')}/send", "POST", msg.dict()
        )
    except Exception as e:
        logger.error(traceback.format_exc())
        return CommonResult(code=-1, message=f"发送数据失败！{e}")


@router.post("/callback")
async def callback(request: Request):
    """main.py 回传的聊天数据，进聊天记录。"""
    try:
        data_json = await request.json()
        chat_log.add(data_json)
        return {"code": 200, "message": "成功"}
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "message": f"失败！{e}"}


@router.post("/tts")
async def tts(request: Request):
    """TTS 合成，返回合成结果（音频路径等）。"""
    try:
        data_json = await request.json()
        resp_json = await runtime.audio.tts_handle(data_json)
        return {"code": 200, "message": "成功", "data": resp_json}
    except Exception as e:
        logger.error(traceback.format_exc())
        return CommonResult(code=-1, message=f"失败！{e}")


@router.post("/llm")
async def llm(request: Request):
    """LLM 推理，转发到 main.py 的 /llm。"""
    try:
        data_json = await request.json()
        config = runtime.read_config()
        main_api_ip = "127.0.0.1" if config.get("api_ip") == "0.0.0.0" else config.get("api_ip")
        resp_json = await runtime.common.send_async_request(
            f"http://{main_api_ip}:{config.get('api_port')}/llm", "POST", data_json, "json", timeout=60
        )
        if resp_json:
            return JSONResponse(resp_json)
        return CommonResult(code=-1, message="失败！")
    except Exception as e:
        logger.error(traceback.format_exc())
        return CommonResult(code=-1, message=f"失败！{e}")


@router.get("/get_sys_info")
async def get_sys_info():
    """获取 main.py 侧的系统信息。"""
    try:
        config = runtime.read_config()
        main_api_ip = "127.0.0.1" if config.get("api_ip") == "0.0.0.0" else config.get("api_ip")
        resp_json = await runtime.common.send_async_request(
            f"http://{main_api_ip}:{config.get('api_port')}/get_sys_info", "GET", None, "json", timeout=60
        )
        if resp_json:
            return JSONResponse(resp_json)
        return CommonResult(code=-1, message="失败！")
    except Exception as e:
        logger.error(f"get_sys_info处理失败！{e}")
        return CommonResult(code=-1, message=f"get_sys_info处理失败！{e}")
