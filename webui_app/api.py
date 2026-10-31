"""WebUI 对 main.py 暴露的 HTTP 接口。

这些路由在 webui 启动时注册一次：main.py 通过它们回传聊天数据、请求 TTS/LLM，
外部脚本则用 /set_config、/sys_cmd 远程改配置和启停程序。
"""

import json
import traceback

from nicegui import app
from starlette.requests import Request

from utils.my_log import logger
from utils.models import CommonResult, SendMessage, SetConfigMessage, SysCmdMessage
from webui_app.chat_log import chat_log
from webui_app.processes import (
    factory,
    restart_application,
    run_external_program,
    stop_external_program,
)


def register_api(config, common, audio):
    """把接口注册到 nicegui 的 FastAPI app 上。

    Args:
        config: 配置对象，读取 api_ip / api_port。
        common: 通用工具，转发请求用。
        audio: 音频类，/tts 调它的 tts_handle。
    """

    @app.post('/set_config')
    async def set_config(msg: SetConfigMessage):
        """
        配置config

            config_path (str): 配置文件路径
            data (dict): 传入的json

        return:
            {"code": 200, "message": "成功"}
        """
        try:
            data_json = msg.dict()
            logger.info(f'set_config接口 收到数据：{data_json}')

            config_data = None

            try:
                with open(data_json["config_path"], encoding="utf-8") as config_file:
                    config_data = json.load(config_file)
            except Exception as e:
                logger.error(f"无法读取配置文件！\n{e}")
                return CommonResult(code=-1, message=f"无法读取配置文件！{e}")

            # 合并字典
            config_data.update(data_json["data"])

            # 写入配置到配置文件
            try:
                with open(data_json["config_path"], 'w', encoding="utf-8") as config_file:
                    json.dump(config_data, config_file, indent=2, ensure_ascii=False)
                    config_file.flush()  # 刷新缓冲区，确保写入立即生效

                logger.info("配置数据已成功写入文件！")

                return CommonResult(code=200, message="配置数据已成功写入文件！")
            except Exception as e:
                logger.error(f"无法写入配置文件！\n{str(e)}")
                return CommonResult(code=-1, message=f"无法写入配置文件！{e}")
        except Exception as e:
            logger.error(traceback.format_exc())
            return CommonResult(code=-1, message=f"执行失败！{e}")

    @app.post('/sys_cmd')
    async def sys_cmd(msg: SysCmdMessage):
        """
        系统命令
            type 命令类型（run/stop/restart/factory）
            data 传入的json

        data_json = {
            "type": "命令名",
            "data": {
                "key": "value"
            }
        }

        return:
            {"code": 200, "message": "成功"}
            {"code": -1, "message": "失败"}
        """
        try:
            data_json = msg.dict()
            logger.info(f'sys_cmd接口 收到数据：{data_json}')
            logger.info(f"开始执行 {data_json['type']}命令...")

            resp_json = {}

            if data_json['type'] == 'run':
                # 运行
                resp_json = run_external_program(config, data_json['data']['config_path'], type="api")
            elif data_json['type'] == 'stop':
                # 停止
                resp_json = stop_external_program(config, type="api")
            elif data_json['type'] == 'restart':
                # 重启
                resp_json = restart_application(config, type=data_json['api_type'])
            elif data_json['type'] == 'factory':
                # 恢复出厂
                resp_json = factory(config, data_json['data']['src_path'], data_json['data']['dst_path'], type="api")

            return resp_json
        except Exception as e:
            logger.error(traceback.format_exc())
            return CommonResult(code=-1, message=f"{data_json['type']}执行失败！{e}")

    @app.post('/send')
    async def send(msg: SendMessage):
        """
        发送数据
            type 数据类型（comment/gift/entrance/reread/tuning/...）
            key  根据数据类型自行适配

        data_json = {
            "type": "数据类型",
            "key": "value"
        }

        return:
            {"code": 200, "message": "成功"}
            {"code": -1, "message": "失败"}
        """
        try:
            data_json = msg.dict()
            logger.info(f'WEBUI API send接口收到数据：{data_json}')

            main_api_ip = "127.0.0.1" if config.get("api_ip") == "0.0.0.0" else config.get("api_ip")
            resp_json = await common.send_async_request(f'http://{main_api_ip}:{config.get("api_port")}/send', "POST", data_json)

            return resp_json
        except Exception as e:
            logger.error(traceback.format_exc())
            return CommonResult(code=-1, message=f"发送数据失败！{e}")

    @app.post('/callback')
    async def callback(request: Request):
        """
        数据回调
            data 传入的json

        data_json = {
            "type": "数据类型（llm）",
            "data": {
                "type": "LLM类型",
                "username": "用户名",
                "content_type": "内容的类型（question/answer）",
                "content": "回复内容",
                "timestamp": "时间戳"
            }
        }

        return:
            {"code": 200, "message": "成功"}
            {"code": -1, "message": "失败"}
        """
        try:
            data_json = await request.json()
            logger.info(f'WEBUI API callback接口收到数据：{data_json}')

            chat_log.add(data_json)

            return {"code": 200, "message": "成功"}
        except Exception as e:
            logger.error(traceback.format_exc())
            return CommonResult(code=-1, message=f"失败！{e}")

    @app.post('/tts')
    async def tts(request: Request):
        """
        TTS合成，获取合成的音频文件路径
            data 传入的json

        例如：
        data_json = {
            "type": "reread",
            "tts_type": "gpt_sovits",
            "data": {
                "type": "api",
                "api_ip_port": "http://127.0.0.1:9880",
                "ref_audio_path": "F:\\\\GPT-SoVITS\\\\raws\\\\ikaros\\\\21.wav",
                "prompt_text": "マスター、どうりょくろか、いいえ、なんでもありません",
                "prompt_language": "日文",
                "language": "自动识别",
                "cut": "凑四句一切",
                "gpt_model_path": "F:\\\\GPT-SoVITS\\\\GPT_weights\\\\ikaros-e15.ckpt",
                "sovits_model_path": "F:\\\\GPT-SoVITS\\\\SoVITS_weights\\\\ikaros_e8_s280.pth"
            },
            "username": "主人",
            "content": "你好，这就是需要合成的文本内容"
        }

        return:
            {"code": 200, "message": "成功", "data": {...}}
            {"code": -1, "message": "失败"}
        """
        try:
            data_json = await request.json()
            logger.info(f'WEBUI API tts接口收到数据：{data_json}')

            resp_json = await audio.tts_handle(data_json)

            return {"code": 200, "message": "成功", "data": resp_json}
        except Exception as e:
            logger.error(traceback.format_exc())
            return CommonResult(code=-1, message=f"失败！{e}")

    @app.post('/llm')
    async def llm(request: Request):
        """
        LLM推理，获取推理结果
            data 传入的json

        例如：type就是聊天类型实际对应的值
        data_json = {
            "type": "chatgpt",
            "username": "用户名",
            "content": "你好"
        }

        return:
            {"code": 200, "message": "成功", "data": {"content": "..."}}
            {"code": -1, "message": "失败"}
        """
        try:
            data_json = await request.json()
            logger.info(f'WEBUI API llm接口 收到数据：{data_json}')

            main_api_ip = "127.0.0.1" if config.get("api_ip") == "0.0.0.0" else config.get("api_ip")
            resp_json = await common.send_async_request(f'http://{main_api_ip}:{config.get("api_port")}/llm', "POST", data_json, "json", timeout=60)
            if resp_json:
                return resp_json

            return CommonResult(code=-1, message="失败！")
        except Exception as e:
            logger.error(traceback.format_exc())
            return CommonResult(code=-1, message=f"失败！{e}")

    @app.get("/get_sys_info")
    async def get_sys_info():
        """获取 main.py 侧的系统信息。"""
        try:
            main_api_ip = "127.0.0.1" if config.get("api_ip") == "0.0.0.0" else config.get("api_ip")
            resp_json = await common.send_async_request(f'http://{main_api_ip}:{config.get("api_port")}/get_sys_info', "GET", None, "json", timeout=60)
            if resp_json:
                return resp_json
            return CommonResult(code=-1, message="失败！")
        except Exception as e:
            logger.error(f"get_sys_info处理失败！{e}")
            return CommonResult(code=-1, message=f"get_sys_info处理失败！{e}")
