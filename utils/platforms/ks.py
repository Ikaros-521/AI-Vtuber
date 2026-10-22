from playwright.sync_api import sync_playwright, TimeoutError
from google.protobuf.json_format import MessageToDict
import kuaishou_pb2

import os
import threading
import traceback
import time

from utils.my_log import logger
import utils.my_global as my_global

def start_listen(config, common, my_handle, platform: str):
    class kslive(object):
        def __init__(self):
            global config, common, my_handle

            self.path = os.path.abspath("")
            self.chrome_path = r"\firefox-1419\firefox\firefox.exe"
            self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
            self.uri = "https://live.kuaishou.com/u/"
            self.context = None
            self.browser = None
            self.page = None

            try:
                self.live_ids = config.get("room_display_id")
                self.thread = 2
                # 没什么用的手机号配置，也就方便登录
                self.phone = "123"
            except Exception as e:
                logger.error(traceback.format_exc())
                logger.error("请检查配置文件")
                my_handle.abnormal_alarm_handle("platform")
                exit()

        def find_file(self, find_path, file_type) -> list:
            """
            寻找文件
            :param find_path: 子路径
            :param file_type: 文件类型
            :return:
            """
            path = self.path + "\\" + find_path
            data_list = []
            for root, dirs, files in os.walk(path):
                if root != path:
                    break
                for file in files:
                    file_path = os.path.join(root, file)
                    if file_path.find(file_type) != -1:
                        data_list.append(file_path)
            return data_list

        def main(self, lid, semaphore):
            if not os.path.exists(self.path + "\\cookie"):
                os.makedirs(self.path + "\\cookie")

            cookie_path = self.path + "\\cookie\\" + self.phone + ".json"
            # if not os.path.exists(cookie_path):
            #     with open(cookie_path, 'w') as file:
            #         file.write('{"a":"a"}')
            #     logger.info(f"'{cookie_path}' 创建成功")
            # else:
            #     logger.info(f"'{cookie_path}' 已存在，无需创建")

            with semaphore:
                thread_name = threading.current_thread().name.split("-")[0]
                with sync_playwright() as p:
                    self.browser = p.chromium.launch(headless=False)
                    # self.browser = p.firefox.launch(headless=False)
                    # executable_path=self.path + self.chrome_path
                    cookie_list = self.find_file("cookie", "json")

                    live_url = self.uri + lid

                    if not os.path.exists(cookie_path):
                        self.context = self.browser.new_context(
                            storage_state=None, user_agent=self.ua
                        )
                    else:
                        self.context = self.browser.new_context(
                            storage_state=cookie_list[0], user_agent=self.ua
                        )
                    self.page = self.context.new_page()
                    self.page.add_init_script(
                        "Object.defineProperties(navigator, {webdriver:{get:()=>undefined}});"
                    )
                    self.page.goto("https://live.kuaishou.com/")
                    # self.page.goto(live_url)
                    element = self.page.get_attribute(".no-login", "style")

                    if not element:
                        logger.info("未登录，请先登录~")
                        self.page.locator(".login").click()
                        self.page.locator(
                            "li.tab-panel:nth-child(2) > h4:nth-child(1)"
                        ).click()
                        self.page.locator(
                            "div.normal-login-item:nth-child(1) > div:nth-child(1) > input:nth-child(1)"
                        ).fill(self.phone)
                    try:
                        self.page.wait_for_selector(
                            "#app > section > div.header-placeholder > header > div.header-main > "
                            "div.right-part > div.user-info > div.tooltip-trigger > span",
                            timeout=1000 * 60 * 2,
                        )
                        if not os.path.exists(self.path + "\\cookie"):
                            os.makedirs(self.path + "\\cookie")
                        self.context.storage_state(path=cookie_path)
                        # 检测是否开播
                        selector = (
                            "html body div#app div.live-room div.detail div.player "
                            "div.kwai-player.kwai-player-container.kwai-player-rotation-0 "
                            "div.kwai-player-container-video div.kwai-player-plugins div.center-state div.state "
                            "div.no-live-detail div.desc p.tip"
                        )  # 检测正在直播时下播的选择器
                        try:
                            msg = self.page.locator(selector).text_content(
                                timeout=3000
                            )
                            logger.info("当前%s" % thread_name + "，" + msg)
                            self.context.close()
                            self.browser.close()

                        except Exception as e:
                            logger.info("当前%s，[%s]正在直播" % (thread_name, lid))

                            logger.info(f"跳转直播间：{live_url}")
                            # self.page.goto(live_url)
                            # time.sleep(1)

                            self.page.goto(live_url)

                            # 等待一段时间检查是否有验证码弹窗
                            try:
                                captcha_selector = "html body div.container"  # 假设这是验证码弹窗的选择器
                                self.page.wait_for_selector(
                                    captcha_selector, timeout=5000
                                )  # 等待5秒看是否出现验证码
                                logger.info("检测到验证码，处理验证码...")
                                # 等待验证码弹窗从DOM中被完全移除
                                self.page.wait_for_selector(
                                    captcha_selector,
                                    state="detached",
                                    timeout=10000,
                                )  # 假设最长等待10秒验证码验证完成
                                logger.info("验证码已验证，弹窗已移除")
                                # 弹窗处理逻辑之后等待1秒
                                time.sleep(1)
                                # 处理完验证码后，可能需要再次跳转页面
                                # self.page.goto(live_url)
                            except TimeoutError:
                                logger.error("没有检测到验证码，继续执行...")

                            logger.info(f"请在10s内手动打开直播间：{live_url}")

                            time.sleep(10)

                            self.page.on("websocket", self.web_sockets)
                            logger.info(f"24h监听直播间等待下播...")
                            self.page.wait_for_selector(selector, timeout=86400000)
                            logger.error(
                                "当前%s，[%s]的直播结束了" % (thread_name, lid)
                            )
                            self.context.close()
                            self.browser.close()

                    except Exception as e:
                        logger.error(traceback.format_exc())
                        self.context.close()
                        self.browser.close()

        def web_sockets(self, web_socket):
            logger.info("web_sockets...")
            urls = web_socket.url
            logger.info(urls)
            if "/websocket" in urls:
                logger.info("websocket连接成功，创建监听事件")
                web_socket.on("close", self.websocket_close)
                web_socket.on("framereceived", self.handler)

        def websocket_close(self):
            self.context.close()
            self.browser.close()

        def handler(self, websocket):
            Message = kuaishou_pb2.SocketMessage()
            Message.ParseFromString(websocket)
            if Message.payloadType == 310:
                SCWebFeedPUsh = kuaishou_pb2.SCWebFeedPush()
                SCWebFeedPUsh.ParseFromString(Message.payload)
                obj = MessageToDict(SCWebFeedPUsh, preserving_proto_field_name=True)

                logger.debug(obj)

                if obj.get("commentFeeds", ""):
                    msg_list = obj.get("commentFeeds", "")
                    for i in msg_list:
                        # 闲时计数清零
                        my_global.idle_time_auto_clear(config, "comment")

                        username = i["user"]["userName"]
                        pid = i["user"]["principalId"]
                        content = i["content"]
                        logger.info(f"[📧直播间弹幕消息] [{username}]:{content}")

                        data = {
                            "platform": platform,
                            "username": username,
                            "content": content,
                        }

                        my_handle.process_data(data, "comment")
                if obj.get("giftFeeds", ""):
                    my_global.idle_time_auto_clear(config, "gift")

                    msg_list = obj.get("giftFeeds", "")
                    for i in msg_list:
                        username = i["user"]["userName"]
                        # pid = i['user']['principalId']
                        giftId = i["giftId"]
                        comboCount = i["comboCount"]
                        logger.info(
                            f"[🎁直播间礼物消息] 用户：{username} 赠送礼物Id={giftId} 连击数={comboCount}"
                        )
                if obj.get("likeFeeds", ""):
                    msg_list = obj.get("likeFeeds", "")
                    for i in msg_list:
                        username = i["user"]["userName"]
                        pid = i["user"]["principalId"]
                        logger.info(f"{username}")

    class run(kslive):
        def __init__(self):
            super().__init__()
            self.ids_list = self.live_ids.split(",")

        def run_live(self):
            """
            主程序入口
            :return:
            """
            t_list = []
            # 允许的最大线程数
            if self.thread < 1:
                self.thread = 1
            elif self.thread > 8:
                self.thread = 8
                logger.info("线程最大允许8，线程数最好设置cpu核心数")

            semaphore = threading.Semaphore(self.thread)
            # 用于记录数量
            n = 0
            if not self.live_ids:
                logger.info("请导入网页直播id，多个以','间隔")
                return

            for i in self.ids_list:
                n += 1
                t = threading.Thread(
                    target=kslive().main, args=(i, semaphore), name=f"线程：{n}-{i}"
                )
                t.start()
                t_list.append(t)
            for i in t_list:
                i.join()

    run().run_live()