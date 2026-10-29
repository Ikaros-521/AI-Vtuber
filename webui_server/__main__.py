"""启动入口：python -m webui_server [--host 0.0.0.0] [--port 8082]。

host/port 默认取 config.json 的 webui.ip / webui.port；环境变量 WEBUI_V3_HOST /
WEBUI_V3_PORT 可覆盖（开发时旧版 webui 还占着 webui.port，就用环境变量错开）。
"""
import argparse
import os

import uvicorn

from webui_server.port_guard import ensure_port_free
from webui_server.runtime import runtime


def main():
    parser = argparse.ArgumentParser(description="AI-Vtuber WebUI v3 服务端")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    try:
        config = runtime.read_config()
        default_host = (config.get("webui") or {}).get("ip") or "127.0.0.1"
        default_port = int((config.get("webui") or {}).get("port") or 8081)
    except Exception:
        default_host, default_port = "127.0.0.1", 8081

    host = args.host or os.environ.get("WEBUI_V3_HOST") or default_host
    port = args.port or int(os.environ.get("WEBUI_V3_PORT") or default_port)

    if host == "0.0.0.0":
        host = "0.0.0.0"  # uvicorn 监听所有网卡

    # 起服前回收强退残留的旧实例（连它拉起的 main.py 等子进程一起），避免 10048
    if not ensure_port_free(host, port):
        raise SystemExit(1)

    uvicorn.run("webui_server.app:create_app", factory=True, host=host, port=port)


if __name__ == "__main__":
    main()
