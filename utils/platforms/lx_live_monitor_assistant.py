import websockets
import json
import asyncio
import traceback

from utils.my_log import logger
import utils.my_global as my_global

# 助手往本机哪个地址推弹幕。以前这两个值写死在函数里，想换端口只能改源码
DEFAULT_WS_IP = "127.0.0.1"
DEFAULT_WS_PORT = 5001


def listen_addr(config):
    """读本机监听地址，配置缺段或端口不合法就回落到默认值。

    端口是页面上的自由文本框，填错是最常见的事故；绑到一个随机端口上表现为
    「一条弹幕都收不到」，所以宁可报错并用默认值，也别静静地起在别的端口。
    """
    ip = config.get("live_monitor_assistant", "ws_ip")
    port = config.get("live_monitor_assistant", "ws_port")

    try:
        port = int(port)
    except (TypeError, ValueError):
        port = 0

    if not 0 < port <= 65535:
        logger.error(f"直播弹幕监听助手端口配置不合法：{port}，改用默认端口 {DEFAULT_WS_PORT}")
        port = DEFAULT_WS_PORT

    return (ip or DEFAULT_WS_IP), port


def start_listen(config, common, my_handle, platform: str):
    # websockets 14 起 handler 只收一个 connection 参数，多写一个 path 会在每次客户端
    # 连上时抛 TypeError，而走这个助手的平台（统一项 + 5 个旧别名）全靠它，
    # 一抛就是一条弹幕都进不来
    async def on_message(websocket):

        async for message in websocket:
            # logger.info(f"收到消息: {message}")
            # await websocket.send("服务器收到了你的消息: " + message)

            try:
                data_json = json.loads(message)
                # logger.debug(data_json)
                # 助手那边还会推 gift（礼物）和 like（点赞），这里没接、直接丢掉。
                # 不是助手没推，是本程序这一路只接弹幕——排查「收不到礼物」时别去查助手。
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
        ws_url, ws_port = listen_addr(config)
        server = await websockets.serve(on_message, ws_url, ws_port)
        logger.info(f"直播弹幕监听助手 WebSocket 服务器已在 {ws_url}:{ws_port} 启动（助手侧填这个地址）")
        await server.wait_closed()

    asyncio.run(ws_server())