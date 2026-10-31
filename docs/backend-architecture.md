# 后端架构说明

> 2026-10 企业级规范化重构后的后端架构。本次重构的入口提交：仓库清理 → ruff 基线 → 配置层 → `app/` 拆分 → webui_server 加固 → utils 治理。

## 分层总览

```
┌─────────────────────────────────────────────────────────┐
│ 入口层                                                    │
│   main.py            主程序入口（~120 行，只做编排）          │
│   webui_server/      WebUI v3 后端（FastAPI, python -m 启动）│
│                      schemas.py 响应模型=接口契约            │
├─────────────────────────────────────────────────────────┤
│ 应用服务层 app/（仅 main.py 使用）                          │
│   state.py       AppState 运行上下文（收编原模块级全局）      │
│   api.py         内部 HTTP API 工厂（/send /llm /tts ...）   │
│   voice_chat.py  VoiceChat 按键/语音聊天链路                 │
│   scheduler.py   单一调度线程（定时文案/图像识别/LiveTalking） │
│   idle_tasks.py  动态文案与闲时任务                          │
│   static_server.py / greeting.py                          │
├─────────────────────────────────────────────────────────┤
│ 核心层 utils/                                             │
│   my_handle.py     My_handle 单例：交互处理流水线/积分/过滤    │
│   audio.py         Audio：TTS 分发(_TTS_HANDLERS)/播放队列    │
│   audio_handle/    MY_TTS 各 TTS 实现、播放器、混音流          │
│   common.py        纯工具集 + 委托门面                       │
│   http_client.py   网络出站集中地（send_request/OPENAI 探测） │
│   screen.py        截屏/摄像头采集（visual 可选组）            │
│   config.py        Config 按路径单例 + reload()              │
│   my_log.py        loguru 日志（import 期容错）               │
│   platforms/       直播平台监听器注册表                       │
│   gpt_model/       LLM provider 注册表（PROVIDERS）          │
│   db / message / models / my_global / alarm / ...          │
├─────────────────────────────────────────────────────────┤
│ 契约                                                       │
│   config.json      跨进程唯一配置契约（磁盘格式与 key 不变）    │
│   根路径机机接口    /set_config /sys_cmd /send /callback ...  │
└─────────────────────────────────────────────────────────┘
```

**依赖方向（强制）**：`main → app → utils`；`webui_server → utils`；utils 内部不得 import app/main；app 模块之间只依赖 `state/greeting`。`test_platform_scoping` 的 AST 守卫会自动检查新增模块。

## 关键设计决策

### 配置层（utils/config.py）
- `Config` 按**解析后的路径**做进程内单例，显式 `reload()` 刷新磁盘变更；读取方拿到快照引用。
- 任何一方 reload（如 main.py 语音循环、`/set_config` 后续处理），全进程视图同步更新——单一事实来源。
- `webui_server/runtime.write_config_file()` 原子写（临时文件 + `os.replace` + fsync），与前端 sha256 乐观锁（409 拦截）配合。
- `my_log` import 期读配置失败自动退回默认值：日志模块是全仓 import 链之根，不允许因配置损坏炸掉整个程序。
- 环境变量 `LUNA_CONFIG_PATH` 可覆盖配置路径（main/webui/webui_server 三处一致），供多实例与隔离测试。

### main.py 与 app/ 包
- 原先 1547 行的 `start_server()`（内嵌 15+ 函数、18 处 global、隐式 `platform` 全局）拆为 `AppState` + 各子模块；`main.py` 可被安全 import。
- **调度线程唯一化**：原先 4 个线程各自 `while True: schedule.run_pending()` 且 sleep 被注释成忙等（烧 CPU）且 schedule 库非线程安全；现为单线程注册全部任务、`time.sleep(1)` 循环。
- dy 平台的监听器会 `join` 调度线程保持阻塞（历史行为保留）。

### 交互流水线（utils/my_handle.py）
- `comment_handle` / `talk_handle` 统一为 `_interaction_pipeline(data, source)`，差异全部 source 门控（去重/黑名单/洛曦转发/用户名处理/念弹幕仅弹幕；build_message 类型参数化）。
- 积分系统拆分至 `utils/integral.py`、过滤器四件套拆分至 `utils/filters.py`，My_handle 同名方法保留一行委托门面；依赖经 `handle` 实例注入，模块不反向 import my_handle。
- My_handle 仍是单例门面，13 个平台监听器以参数注入方式调用，接口不变。

### 共享状态与锁
- `My_handle.data_lock`：护 process_data 的 timers/last_data 缓冲（短临界区）。
- `My_handle.handle_lock`：串行化各 timer_flag 的处理器执行。
- `My_handle.state_lock`（RLock）：护类级共享可变状态的复合操作——live_data 去重遍历+append、clear_live_data 换新、task_data 计时/切片/清空、thanks_* 轮转判空+pop。访问路径不都经过 handle_lock（周期触发定时器、/send 直调 gift/entrance/follow 都会绕开），故在状态自身加锁。**锁序约定：handle_lock → state_lock，不得反向嵌套**。
- `Audio` 队列自带 Condition 线程安全；`copywriting_play_flag` 为 GIL 原子的纯流程控制标志，刻意不加锁（见类属性注释）。

### TTS / LLM provider 注册表
- LLM：`utils/gpt_model/gpt.py` 的 `PROVIDERS = {name: (module, class)}` + importlib 懒加载。
- TTS：`utils/audio.py` 的 `_TTS_HANDLERS = {tts_type: _tts_<name>}`。新增 TTS = 写一个 `_tts_<name>(self, message) -> voice_tmp_path` 方法并登记一行。
- 特例：elevenlabs 直接播放，经 `_TTS_EARLY_EXIT` 哨兵提前返回（保持历史行为）。

### webui_server（v3 后端）
- 路由按域拆分（config/ops/logs/actions/auth/compat），`create_app()` 工厂 + lifespan。
- 全局异常兜底为 `{code:-1, message}` 信封；未捕获异常不再裸 500。
- **登录门禁**：启用 login 后 `/api/*` 由中间件做服务端会话强制（401），会话 7 天过期；根路径机机接口（main.py 无凭证调用）保持开放。
- 信任模型：默认只绑 127.0.0.1；`/api/file` 支持编辑任意路径的外部文件（file-json 工作区需要），不做路径白名单——如需暴露到非回环地址，请自行加反向代理鉴权。

## 线程模型速览

| 线程 | 归属 | 说明 |
|---|---|---|
| http-api | app/api | 内部 FastAPI/uvicorn |
| key-listener | app/voice_chat | keyboard.wait() 阻塞（talk 平台主线程 join 它） |
| do-listen-and-comment | app/voice_chat | 单轮/连续录音+ASR |
| scheduler | app/scheduler | 唯一的 schedule.run_pending() 调用点 |
| trends-copywriting / idle-time-task | app/idle_tasks | asyncio.run 各自独立事件循环 |
| message_queue / only_play_audio / copywriting | utils/audio | TTS 合成与播放流水线 |
| 平台监听器线程 ×13 | utils/platforms | 各 SDK 自建 |

## 测试与验证

- 单测：`tests/unit`（650 用例），`.venv`（pydantic v2）运行：`python -m pytest`。
- 冒烟：`python tools/smoke_test.py`（配置/导入/平台注册表/WebUI 启动四段）。
- 双环境约束：**webui_server 与 app 代码必须兼容 pydantic v1/v2**（日常 Miniconda 是 v1.10 + fastapi 0.109）。改后请在 Miniconda 也起一遍：`./Miniconda3/python.exe -m webui_server`。
- Lint/Format：`ruff check .` + `ruff format --check .`（CI 强制）。全量格式化提交已登记 `.git-blame-ignore-revs`。

## 已知的缓办项（按需推进）

1. `Audio` 多实例共享类属性（webui 同进程建第二个 `Audio(type=2)` 时共享队列/标志位）——当前 main 与 webui 分进程运行，实际不触发；若未来同进程嵌入需改造为实例属性。
2. requirements/*.lock.txt 仍含 nicegui（v2 遗留，再生成 lock 时自然消失，装出来无害）。
3. actions_api / compat_api 未声明 response_model（见 schemas.py 注释的取舍理由）。

> 已完成：~~共享状态加锁~~（state_lock）、~~integral/filters 拆分~~（utils/integral.py + utils/filters.py）、~~v2 删除~~（webui.py/webui_app 及其单测/nicegui 依赖）、~~核心路由 response_model~~（webui_server/schemas.py）。以上均为 2026-10-31。
