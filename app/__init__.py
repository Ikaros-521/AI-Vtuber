"""main 进程的子任务模块包（自 main.py 巨型 start_server 拆分而来）。

模块划分：
- state         AppState 运行上下文（收编原模块级全局变量）
- api           内部 HTTP API（/send /llm /tts /callback /get_sys_info）
- voice_chat    按键/直接对话语音聊天链路
- scheduler     schedule 定时任务（单调度线程统一驱动）
- idle_tasks    动态文案与闲时任务
- static_server Live2D 静态页服务
- greeting      时段问候语文本（定时/闲时任务共用）

依赖方向：app/* 只依赖 utils/* 与 stdlib，模块之间只依赖 state/greeting，
不允许反向 import main。
"""
