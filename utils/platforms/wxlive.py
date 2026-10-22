import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from utils.models import SendMessage, LLMMessage, CallbackMessage, CommonResult

import traceback

from utils.my_log import logger
import utils.my_global as my_global

def start_listen(config, common, my_handle, platform: str):
    # 定义FastAPI应用
    app = FastAPI()
    seq_list = []

    # 允许跨域
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/wxlive")
    async def wxlive(request: Request):
        try:
            # 获取 POST 请求中的数据
            data = await request.json()
            # 这里可以添加代码处理接收到的数据
            logger.debug(data)

            if data["events"][0]["seq"] in seq_list:
                return CommonResult(code=-1, message="重复数据过滤")

            # 如果列表长度达到30，移除最旧的元素
            if len(seq_list) >= 30:
                seq_list.pop(0)

            # 添加新元素
            seq_list.append(data["events"][0]["seq"])

            # 弹幕数据
            if data["events"][0]["decoded_type"] == "comment":
                # 闲时计数清零
                my_global.idle_time_auto_clear(config, "comment")

                content = data["events"][0]["content"]  # 获取弹幕内容
                username = data["events"][0]["nickname"]  # 获取发送弹幕的用户昵称

                logger.info(f"[{username}]: {content}")

                data = {
                    "platform": platform,
                    "username": username,
                    "content": content,
                }

                my_handle.process_data(data, "comment")
            # 入场数据
            elif data["events"][0]["decoded_type"] == "enter":
                my_global.idle_time_auto_clear(config, "entrance")

                username = data["events"][0]["nickname"]

                logger.info(f"用户：{username} 进入直播间")

                # 添加用户名到最新的用户名列表
                my_global.add_username_to_last_username_list(username)

                data = {
                    "platform": platform,
                    "username": username,
                    "content": "进入直播间",
                }

                my_handle.process_data(data, "entrance")
                pass

            # 响应
            return CommonResult(code=200, message="成功接收")
        except Exception as e:
            logger.error(traceback.format_exc())
            my_handle.abnormal_alarm_handle("platform")
            return CommonResult(code=-1, message=f"发送数据失败！{e}")

    # 定义POST请求路径和处理函数
    @app.post("/send")
    async def send(msg: SendMessage):
        try:
            tmp_json = msg.dict()
            logger.info(f"API收到数据：{tmp_json}")
            data_json = tmp_json["data"]
            if "type" not in data_json:
                data_json["type"] = tmp_json["type"]

            if data_json["type"] in ["reread", "reread_top_priority"]:
                my_handle.reread_handle(data_json, type=data_json["type"])
            elif data_json["type"] == "comment":
                my_handle.process_data(data_json, "comment")
            elif data_json["type"] == "tuning":
                my_handle.tuning_handle(data_json)
            elif data_json["type"] == "gift":
                my_handle.gift_handle(data_json)
            elif data_json["type"] == "entrance":
                my_handle.entrance_handle(data_json)

            return CommonResult(code=200, message="成功")
        except Exception as e:
            logger.error(f"发送数据失败！{e}")
            return CommonResult(code=-1, message=f"发送数据失败！{e}")

    @app.post("/llm")
    async def llm(msg: LLMMessage):
        try:
            data_json = msg.dict()
            logger.info(f"API收到数据：{data_json}")

            resp_content = my_handle.llm_handle(
                data_json["type"], data_json, webui_show=False
            )

            return CommonResult(
                code=200, message="成功", data={"content": resp_content}
            )
        except Exception as e:
            logger.error(f"调用LLM失败！{e}")
            return CommonResult(code=-1, message=f"调用LLM失败！{e}")

    @app.post("/callback")
    async def callback(msg: CallbackMessage):
        try:
            data_json = msg.dict()
            logger.info(f"API收到数据：{data_json}")

            # 音频播放完成
            if data_json["type"] in ["audio_playback_completed"]:
                # 如果等待播放的音频数量大于10
                if data_json["data"]["wait_play_audio_num"] > int(
                    config.get("idle_time_task", "wait_play_audio_num_threshold")
                ):
                    logger.info(
                        f'等待播放的音频数量大于限定值，闲时任务的闲时计时由 {my_global.global_idle_time} -> {int(config.get("idle_time_task", "idle_time_reduce_to"))}秒'
                    )
                    # 闲时任务的闲时计时 清零
                    my_global.global_idle_time = int(
                        config.get("idle_time_task", "idle_time_reduce_to")
                    )

            return CommonResult(code=200, message="callback处理成功！")
        except Exception as e:
            logger.error(f"callback处理失败！{e}")
            return CommonResult(code=-1, message=f"callback处理失败！{e}")

    logger.info("HTTP API线程已启动！")
    uvicorn.run(app, host="0.0.0.0", port=config.get("api_port"))