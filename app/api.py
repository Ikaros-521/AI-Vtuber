"""内部 HTTP API：/send /llm /tts /callback /get_sys_info。

拆分自 main.py 的 http_api_thread；行为保持一致：
- 供 webui/外部脚本调用的机器接口，无鉴权（与 v2 相同的契约）
- /tts 直达 My_handle 单例的 audio.tts_handle
"""

import threading
import traceback

from luna.infra.my_log import logger
import luna.infra.my_global as my_global


def create_api_app(state):
    """构造内部 API 的 FastAPI 应用（app 工厂，便于 TestClient 测试）。"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from starlette.requests import Request

    from luna.infra.models import CallbackMessage, CommonResult, LLMMessage, SendMessage

    app = FastAPI()

    # 允许跨域
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/send")
    async def send(msg: SendMessage):
        try:
            tmp_json = msg.dict()
            logger.info(f"内部HTTP API send接口收到数据：{tmp_json}")
            data_json = tmp_json["data"]
            if "type" not in data_json:
                data_json["type"] = tmp_json["type"]

            if data_json["type"] in ["reread", "reread_top_priority"]:
                state.my_handle.reread_handle(data_json, type=data_json["type"])
            elif data_json["type"] == "comment":
                state.my_handle.process_data(data_json, "comment")
            elif data_json["type"] == "tuning":
                state.my_handle.tuning_handle(data_json)
            elif data_json["type"] == "gift":
                state.my_handle.gift_handle(data_json)
            elif data_json["type"] == "entrance":
                state.my_handle.entrance_handle(data_json)

            return CommonResult(code=200, message="成功")
        except Exception as e:
            logger.error(f"发送数据失败！{e}")
            return CommonResult(code=-1, message=f"发送数据失败！{e}")

    @app.post("/llm")
    async def llm(msg: LLMMessage):
        try:
            data_json = msg.dict()
            logger.info(f"API收到数据：{data_json}")

            resp_content = state.my_handle.llm_handle(data_json["type"], data_json, webui_show=False)

            return CommonResult(code=200, message="成功", data={"content": resp_content})
        except Exception as e:
            logger.error(f"调用LLM失败！{e}")
            return CommonResult(code=-1, message=f"调用LLM失败！{e}")

    @app.post("/tts")
    async def tts(request: Request):
        try:
            data_json = await request.json()
            logger.info(f"API收到数据：{data_json}")

            resp_json = await state.my_handle.audio.tts_handle(data_json)

            return {"code": 200, "message": "成功", "data": resp_json}
        except Exception as e:
            logger.error(traceback.format_exc())
            return {"code": -1, "message": f"失败！{e}"}

    @app.post("/callback")
    async def callback(msg: CallbackMessage):
        try:
            data_json = msg.dict()

            # 特殊回调特殊处理
            if data_json["type"] == "audio_playback_completed":
                my_global.wait_play_audio_num = int(data_json["data"]["wait_play_audio_num"])
                my_global.wait_synthesis_msg_num = int(data_json["data"]["wait_synthesis_msg_num"])
                logger.info(
                    f"内部HTTP API callback接口 音频播放完成回调，待播放音频数量：{my_global.wait_play_audio_num}，待合成消息数量：{my_global.wait_synthesis_msg_num}"
                )
            else:
                logger.info(f"内部HTTP API callback接口收到数据：{data_json}")

            # 音频播放完成
            if data_json["type"] in ["audio_playback_completed"]:
                my_global.wait_play_audio_num = int(data_json["data"]["wait_play_audio_num"])

                # 如果等待播放的音频数量大于10
                if data_json["data"]["wait_play_audio_num"] > int(
                    state.config.get("idle_time_task", "wait_play_audio_num_threshold")
                ):
                    logger.info(
                        f"等待播放的音频数量大于限定值，闲时任务的闲时计时由 {my_global.global_idle_time} -> {int(state.config.get('idle_time_task', 'idle_time_reduce_to'))}秒"
                    )
                    # 闲时任务的闲时计时 清零
                    my_global.global_idle_time = int(state.config.get("idle_time_task", "idle_time_reduce_to"))

            return CommonResult(code=200, message="callback处理成功！")
        except Exception as e:
            logger.error(f"callback处理失败！{e}")
            return CommonResult(code=-1, message=f"callback处理失败！{e}")

    @app.get("/get_sys_info")
    async def get_sys_info():
        try:
            data = {
                "audio": state.my_handle.get_audio_info(),
                "metahuman-stream": {
                    "wait_play_audio_num": my_global.wait_play_audio_num,
                    "wait_synthesis_msg_num": my_global.wait_synthesis_msg_num,
                },
            }

            return CommonResult(code=200, data=data, message="get_sys_info处理成功！")
        except Exception as e:
            logger.error(f"get_sys_info处理失败！{e}")
            return CommonResult(code=-1, message=f"get_sys_info处理失败！{e}")

    # 将本地目录中的静态文件（如 CSS、JavaScript、图片等）暴露给 web 服务器，以便用户可以通过特定的 URL 访问这些文件。
    if state.config.get("webui", "local_dir_to_endpoint", "enable"):
        for tmp in state.config.get("webui", "local_dir_to_endpoint", "config"):
            from fastapi.staticfiles import StaticFiles

            app.mount(tmp["url_path"], StaticFiles(directory=tmp["local_dir"]), name=tmp["local_dir"])

    return app


def start_api_server(state) -> threading.Thread:
    """在独立线程中启动内部 HTTP API（阻塞运行 uvicorn）。"""
    thread = threading.Thread(target=_run_api_server, args=(state,), name="http-api")
    thread.start()
    return thread


def _run_api_server(state):
    import uvicorn

    app = create_api_app(state)

    logger.info("HTTP API线程已启动！")

    uvicorn.run(app, host="0.0.0.0", port=state.config.get("api_port"))
