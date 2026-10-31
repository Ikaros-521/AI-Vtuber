import pytchat
import time
import re
import traceback

from utils.my_log import logger
import utils.my_global as my_global


def start_listen(config, common, my_handle, platform: str):
    def get_video_id():
        try:
            return config.get("room_display_id")
        except Exception as e:
            logger.error(f"获取直播间号失败！\n{e}")
            return None

    def process_chat(live):
        while live.is_alive():
            try:
                for c in live.get().sync_items():
                    # 过滤表情包
                    chat_raw = re.sub(r":[^\s]+:", "", c.message)
                    chat_raw = chat_raw.replace("#", "")
                    if chat_raw != "":
                        # 闲时计数清零
                        my_global.idle_time_auto_clear(config, "comment")

                        content = chat_raw  # 获取弹幕内容
                        username = c.author.name  # 获取发送弹幕的用户昵称

                        logger.info(f"[{username}]: {content}")

                        data = {
                            "platform": platform,
                            "username": username,
                            "content": content,
                        }

                        my_handle.process_data(data, "comment")

                    # time.sleep(1)
            except Exception as e:
                logger.error(traceback.format_exc())
                logger.error(f"Error receiving chat: {e}")
                my_handle.abnormal_alarm_handle("platform")
                break  # 退出内部while循环以触发重连机制

    # 以前是「快速重连满 3 次就 break，然后 finally os._exit(0)」：YouTube 一路断开就把
    # 整个程序（音频、webui、其他平台监听）带走。现在一直退避重连，只管这条线程；
    # 每次重建客户端都把上一把 terminate 掉——不 terminate 会攒出多个监听线程，
    # 同一条弹幕被处理好几遍。
    while True:
        live = None
        try:
            video_id = get_video_id()
            if video_id is None:
                logger.error("取不到 YouTube 直播间号，停止该平台监听（不影响其他功能）")
                return

            live = pytchat.create(video_id=video_id)
            process_chat(live)
            reason = "直播间连接结束（主播可能已下播）"
        except KeyboardInterrupt:
            logger.warning("程序被强行退出")
            return
        except Exception:
            logger.error(traceback.format_exc())
            reason = "连接失败"
        finally:
            if live is not None and live.is_alive():
                live.terminate()

        logger.warning(f"{reason}，60 秒后重连")
        time.sleep(60)
