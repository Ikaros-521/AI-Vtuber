"""WebUI v3 的 FastAPI 后端。

与 v2 的 NiceGUI 版（webui.py / webui_app）并行存在：这里只提供 HTTP API 与
React 构建产物的静态托管，不再在服务端渲染页面。对 main.py 与外部脚本暴露的
旧接口（/set_config、/sys_cmd、/send、/callback、/tts、/llm）原样保留。
"""
