import websockets
import json
import asyncio
import traceback

from utils.my_log import logger
import utils.my_global as my_global

def start_listen(config, common, my_handle, platform: str):
    # websockets 14 起 handler 只收一个 connection 参数，多写一个 path 会在每次客户端
    # 连上时抛 TypeError，douyu/ks2/pdd/1688/taobao 全靠这个监听器，一个弹幕都进不来
    async def on_message(websocket):

        async for message in websocket:
            # logger.info(f"收到消息: {message}")
            # await websocket.send("服务器收到了你的消息: " + message)

            try:
                data_json = json.loads(message)
                # logger.debug(data_json)
                if data_json["type"] == "comment":
                    # logger.info(data_json)
                    # 闲时计数清零
                    my_global.idle_time_auto_clear(config, "comment")

                    username = data_json["username"]
                    content = data_json["content"]

                    logger.info(f"[📧直播间弹幕消息] [{username}]：{content}")

                    data = {
                        "platform": platform,
                        "username": username,
                        "content": content,
                    }

                    my_handle.process_data(data, "comment")

                    # 添加用户名到最新的用户名列表
                    my_global.add_username_to_last_username_list(username)

            except Exception as e:
                logger.error(traceback.format_exc())
                logger.error("数据解析错误！")
                my_handle.abnormal_alarm_handle("platform")
                continue

    async def ws_server():
        ws_url = "127.0.0.1"
        ws_port = 5001
        server = await websockets.serve(on_message, ws_url, ws_port)
        logger.info(f"WebSocket 服务器已在 {ws_url}:{ws_port} 启动")
        await server.wait_closed()

    asyncio.run(ws_server())