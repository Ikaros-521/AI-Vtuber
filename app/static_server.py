"""Live2D 静态页面服务：拆分自 main.py 的 web_server_thread。"""

import asyncio
import http.server
import socketserver
import threading

from utils.my_log import logger


async def web_server_thread(web_server_port):
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", web_server_port), handler) as httpd:
        logger.info(f"Web运行在端口：{web_server_port}")
        logger.info(f"可以直接访问Live2D页， http://127.0.0.1:{web_server_port}/Live2D/")
        httpd.serve_forever()


def start_static_server(web_server_port: int) -> threading.Thread:
    """启动 Live2D 静态页服务线程。"""
    thread = threading.Thread(target=lambda: asyncio.run(web_server_thread(web_server_port)), name="live2d-static")
    thread.start()
    return thread
