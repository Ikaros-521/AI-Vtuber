import socks
from emoji import demojize

import re
import traceback

from utils.my_log import logger
import utils.my_global as my_global


def start_listen(config, common, my_handle, platform: str):
    try:
        server = "irc.chat.twitch.tv"
        port = 6667
        nickname = "主人"

        try:
            channel = "#" + config.get(
                "room_display_id"
            )  # 要从中检索消息的频道，注意#必须携带在头部 The channel you want to retrieve messages from
            token = config.get("twitch", "token")  # 访问 https://twitchapps.com/tmi/ 获取
            user = config.get("twitch", "user")  # 你的Twitch用户名 Your Twitch username
            # 代理服务器的地址和端口
            proxy_server = config.get("twitch", "proxy_server")
            proxy_port = int(config.get("twitch", "proxy_port"))
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f"获取Twitch配置失败！\n{e}")
            my_handle.abnormal_alarm_handle("platform")

        # 配置代理服务器
        socks.set_default_proxy(socks.HTTP, proxy_server, proxy_port)

        # 创建socket对象
        sock = socks.socksocket()

        try:
            sock.connect((server, port))
            logger.info("成功连接 Twitch IRC server")
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f"连接 Twitch IRC server 失败: {e}")
            my_handle.abnormal_alarm_handle("platform")

        sock.send(f"PASS {token}\n".encode())
        sock.send(f"NICK {nickname}\n".encode())
        sock.send(f"JOIN {channel}\n".encode())

        regex = r":(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :(.+)"

        # 重连次数
        retry_count = 0

        while True:
            try:
                resp = sock.recv(2048).decode("utf-8")

                # 输出所有接收到的内容，包括PING/PONG
                # logger.info(resp)

                if resp.startswith("PING"):
                    sock.send(b"PONG\n")

                elif user not in resp:
                    # 闲时计数清零
                    my_global.idle_time_auto_clear(config, "comment")

                    resp = demojize(resp)

                    logger.debug(resp)

                    match = re.match(regex, resp)

                    username = match.group(1)
                    content = match.group(2)
                    content = content.rstrip()

                    logger.info(f"[{username}]: {content}")

                    data = {
                        "platform": platform,
                        "username": username,
                        "content": content,
                    }

                    my_handle.process_data(data, "comment")
            except AttributeError as e:
                logger.error(traceback.format_exc())
                logger.error(f"捕获到异常: {e}")
                logger.error("发生异常，重新连接socket")
                my_handle.abnormal_alarm_handle("platform")

                if retry_count >= 3:
                    logger.error("多次重连失败，程序结束！")
                    return

                retry_count += 1
                logger.error(f"重试次数: {retry_count}")

                # 在这里添加重新连接socket的代码
                # 例如，你可能想要关闭旧的socket连接，然后重新创建一个新的socket连接
                sock.close()

                # 创建socket对象
                sock = socks.socksocket()

                try:
                    sock.connect((server, port))
                    logger.info("成功连接 Twitch IRC server")
                except Exception as e:
                    logger.error(f"连接 Twitch IRC server 失败: {e}")

                sock.send(f"PASS {token}\n".encode())
                sock.send(f"NICK {nickname}\n".encode())
                sock.send(f"JOIN {channel}\n".encode())
            except Exception as e:
                logger.error(traceback.format_exc())
                logger.error(f"Error receiving chat: {e}")
                my_handle.abnormal_alarm_handle("platform")
    except Exception:
        logger.error(traceback.format_exc())
        my_handle.abnormal_alarm_handle("platform")
