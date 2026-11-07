# Luna AI Agent 化升级设计（v5）

> 状态：**P0（Agent-Ready）已实施**——`luna/agent` 骨架、ToolRegistry + 5 工具、LLMAdapter 双通道、`_interaction_pipeline` 门控分支、config `agent` 段、trace、单测/守卫/冒烟均已落地；P1/P2 待排期。分支 `v5`（自 v4.0.0 切出）。
> 前置阅读：[backend-architecture.md](./backend-architecture.md)——本文所有集成点都建立在该分层之上，不推翻任何现有决策。

## 1. 背景与定位

**现状**：Luna 是"事件驱动的流水线"。弹幕/礼物经 `_interaction_pipeline`（`luna/core/my_handle.py`）按硬编码顺序过滤、积分、关键词触发（点歌/画图/本地问答/按键映射），最后把 prompt 拼好（`before_prompt + content + after_prompt`）交给 LLM 生成一段文本，经 `build_message()` → `audio_synthesis_handle()` 合成播放。**LLM 在这里的角色只是文本生成器**：何时说话、能做什么，全部由代码里的 if 链决定。

**目标**：LLM 升级为**决策者**——它自己判断要不要说话、说什么、调用哪些工具、要不要记住这个观众。即"感知 → 决策 → 行动"闭环的 AI Agent。

**产品定位**：不做通用 Agent 平台，聚焦"**直播间数字员工**"——人设即灵魂、工具即手脚、记忆即经验。对应三类用户价值：

| 痛点（现状） | Agent 化后 |
| --- | --- |
| 触发死板：关键词之外不会主动、不会组合 | 闲时自主策划话题；一条弹幕触发多步动作（"放首XX的歌然后报下积分榜"） |
| 没有观众记忆：同一人每次都是陌生人 | 观众画像（互动史/礼物史/标签），个性化回应 |
| 运营靠感觉 | 直播复盘：互动率、高光时刻、流失点 |

## 2. 设计原则

1. **复用现有资产，不重写**。v4 已完成分层（main → app → luna）、配置单例、provider 注册表，Agent 是**插入一个新决策域 `luna/agent/`**，不是替换 `my_handle`。
2. **双引擎热切换，规则引擎是安全网**。直播不能翻车：`agent.enabled=false` 即时回到现状路径；Agent 超时/异常/预算耗尽静默降级到原 LLM 直答。
3. **成本与延迟优先**。直播 7×24、弹幕洪峰：决策循环有界、分层模型、预算熔断。
4. **安全护栏先行**。输入过滤/输出违禁/工具白名单/急停，全部复用或扩展现有 `filters`/`prohibitions` 机制。
5. **pydantic v1/v2 双兼容、AST 守卫依赖方向**——延续 v4 的工程约束。

## 3. 总体架构

```
┌──────────────────────────────────────────────────────────────┐
│ 感知层（小改造）                                                │
│  luna/platforms 13 平台事件 ──┐                                │
│  screen 画面识别 / ASR ───────┼→ AgentContext（归一化事件+会话态）│
│  弹幕 db / 积分 / 礼物数据 ────┘                                │
├──────────────────────────────────────────────────────────────┤
│ 决策层（新增 luna/agent/）                                      │
│  IntentRouter   规则意图分流：关键词直通 / Agent 分支              │
│  AgentRuntime   有界 ReAct 循环（≤max_tool_rounds）             │
│  MemorySystem   观众画像 + 场次高光 + 人设注入                   │
│  SafetyGuard    工具白名单/频率/预算/输出违禁                     │
│  LLMAdapter     双通道：原生 Function Calling / 文本协议兜底      │
├──────────────────────────────────────────────────────────────┤
│ 行动层（现有能力工具化，注册表模式照抄 PROVIDERS）                  │
│  ToolRegistry：speak / query_integral / play_song / sd 生图 /   │
│               search_online / 弹幕分析 / 按键游戏 / memory_save  │
├──────────────────────────────────────────────────────────────┤
│ 执行层（完全不动）                                               │
│  build_message → audio_synthesis_handle → Audio 队列 → TTS/播放 │
│  luna/core/filters / integral / data_analysis / platforms       │
└──────────────────────────────────────────────────────────────┘
```

## 4. 组件详细设计

### 4.1 AgentContext（上下文与能力注入）

一次 Agent 决策的全部输入与能力出口，`luna/agent/context.py`：

```python
@dataclass
class AgentContext:
    event: dict          # 归一化事件：type(comment/gift/entrance/talk/idle...)、
                         #   username、content、gift_info、platform、ts
    viewer: dict | None  # 观众画像摘要（MemorySystem 查询结果，按预算截断）
    state: dict          # 本场会话态：互动计数、最近话题、播放队列状态、开播时长
    handle: Any          # My_handle 实例引用（能力出口，见下）
    config: Config       # 现有配置单例
    budget: Budget       # 本次决策的 token/工具调用计数器
    trace: Trace         # 可观测记录器
```

**依赖方向的关键决策**：`luna/agent` **不得 import `my_handle`/`app`**（延续 AST 守卫约束）。工具要调用的既有能力（点歌/积分/弹幕分析等都在 `My_handle` 方法上）一律经 `ctx.handle` **参数注入**——与 `luna/core/integral.py` 的 `integral_handle(handle, type, data)` 同款模式，由 `My_handle` 初始化 AgentRuntime 时传入 `self`。

### 4.2 AgentRuntime（有界决策循环）

`luna/agent/runtime.py`。每个事件走一遍：

```
run(event):
  1. IntentRouter 分流（见 4.3）
  2. 组装 system prompt：人设 preset + 工具清单 + 上下文注入
     （观众画像摘要 / 最近弹幕摘要 / 当前时间 / 播放队列状态 / 开播时长）
  3. loop ≤ agent.max_tool_rounds（默认 3）:
       resp = LLMAdapter.call(messages)
       ├─ 纯文本 → SafetyGuard 输出过滤 → speak(text) → 结束
       └─ 工具调用 → SafetyGuard 门禁（白名单/频率/预算）→ tool.run()
            OBSERVATION 回填 messages → 继续循环
  4. 超轮次/超时(timeout_seconds)/异常 → 降级链（见 4.7）
```

`speak` 本身也是一个显式工具：模型可以分多句说、插队播报、或决定本轮不说话。最终文本统一走 `build_message(source, username, text)` → `audio_synthesis_handle()`，**与现状出口完全一致**，TTS/播放/Live2D 链路零改动。

**行动顺序归模型安排**（真机回归修正）：工具按调用顺序即时执行、先调用先进播放队列——因此"先说话再放歌"由模型先调 `speak` 再调 `play_song` 实现（system prompt 与两个动作工具的描述里都有顺序引导）。配套语义：**动作已执行而模型收尾无话时视为完成（静默），不再降级**——降级会触发一次无视工具结果的裸 LLM 回复，盖在已入队的音频上（trace 记 `acted_no_final`）；无成功动作时收尾无话仍照旧降级。

### 4.3 IntentRouter（意图分流）与 ToolRegistry

**P0 关键决策：已有关键词触发的功能一律保持直通，不走 Agent**。`_interaction_pipeline` 里点歌/画图/积分指令/自定义命令/本地问答这些"触发后短路"的分支原样保留——零回归风险；Agent 只接管**原本就走到 LLM 的那一段**（闲聊回复），以及新增的闲时主动行为。P1 再评估把"关键词命中"降级为"提示模型可用工具"。

ToolRegistry（`luna/agent/registry.py`）**与 `luna/llm/gpt.py` 的 `PROVIDERS` 完全同构**：

```python
# name -> (module, class)，importlib 懒加载
TOOLS = {
    "speak":             ("luna.agent.tools.basic", "Speak"),
    "query_integral":    ("luna.agent.tools.integral", "QueryIntegral"),
    "query_danmu_summary": ("luna.agent.tools.danmu", "QueryDanmuSummary"),
    "search_online":     ("luna.agent.tools.search", "SearchOnline"),
    "memory_save":       ("luna.agent.tools.memory", "MemorySave"),
    # P1：play_song / generate_image / local_qa / control_game / translate
}

class Tool(ABC):
    name: str
    description: str      # 给模型看的说明，直接决定调用质量
    parameters: dict      # JSON Schema
    dangerous: bool = False
    def run(self, args: dict, ctx: AgentContext) -> str: ...  # 返回 OBSERVATION 文本
```

首批 5 个工具全部只读或低风险。P1 增补动作类工具时逐个评估 `dangerous` 标记（按键控制、串口硬件默认白名单关闭）。

### 4.4 LLMAdapter（双通道接入）

现状约束：provider 接口是**纯文本** `get_gpt_resp(username, prompt, stream)`（`luna/llm/gpt.py`），10 家 provider 无一支持 function calling。因此：

- **通道 A（原生 FC）**：chatgpt / gemini / zhipu / tongyi / volcengine 等 API 支持 `tools` 参数的，adapter 内直接用原生 tool_calls 循环。**新增 `luna/agent/llm_adapter.py`，不改动现有 provider 类**——provider 的会话管理（per-username LRU）保留给直答降级路径用，Agent 循环自己维护消息列表。
- **通道 B（文本协议）**：任何 provider（dify / anythingllm / custom_llm / 本地模型）用统一 ReAct 文本协议兜底：

  ```
  THOUGHT: 观众问积分榜，先查数据
  ACTION: {"tool": "query_integral", "args": {"top": 5}}
  ```
  adapter 解析 `ACTION` 行执行工具、回填 `OBSERVATION:`。协议失败（连续两次解析不出）即降级。
- `channel: "auto" | "native" | "text"` 配置选择；`auto` = 按 chat_type 判断支持度。

### 4.5 MemorySystem（分层记忆）

现状只有 provider 内 per-username 会话历史（LRU 10000）+ `preset` 人设 + danmu sqlite 表。新增 `luna/agent/memory.py`，存储接现有 `luna/infra` db（sqlite）：

| 层 | 内容 | 存储 | 写入方 |
| --- | --- | --- | --- |
| L1 会话记忆 | 本轮对话上下文 | 沿用 provider sessions（不动） | 现状 |
| L2 观众画像 | 互动史/礼物史/积分/标签/称呼 | `viewer_profile(platform, uid, first_seen, last_seen, total_gift_price, integral, tags, note)` | gift/entrance/integral 事件自动写 + `memory_save` 工具 |
| L3 场次记忆 | 开播/下播、互动计数、高光摘要 | `stream_session(id, start, end, counts, highlights)` + `episodic(ts, kind, summary)` | 事件钩子 + 下播自动总结 |
| L4 人设知识库 | 主播设定/直播间规矩/玩法说明 | P0 沿用 `before_prompt/after_prompt`；P2 可选 RAG | 主播在 WebUI 编辑 |

**注入与预算**：prompt 注入画像摘要按 `memory.inject_max_chars`（默认 500）截断——记忆是好东西，token 不是免费的。**可解释可编辑**：画像与 episodic 在 WebUI 可查/改/删，这是 ToC Agent 产品的信任底线。

### 4.6 SafetyGuard（安全护栏与预算）

`luna/agent/safety.py`，四道门：

1. **输入侧**：现有 `prohibitions_handle` / 去重 / 黑名单**在 Agent 分支之前原样执行**（`_interaction_pipeline` 前半段共用），Agent 拿到的已是干净输入。
2. **工具侧**：`tools.enabled` 白名单（未列出的工具模型看不见也不执行）；`dangerous` 工具独立开关；每观众工具调用频率限制（防"刷弹幕薅 Agent 算力"）。
3. **预算侧**：`Budget` 计数 token 估算 + 工具调用次数，`budget.tokens_per_hour` 全局熔断——超限自动切直答模式，直播不中断。
4. **输出侧**：Agent 最终文本**仍走 `prohibitions_handle`**（复用现有双重过滤设计），再进 TTS。直播是强监管场景，Agent 自由生成的合规风险比模板高一档，这道门不能省。

急停三通道：`config.agent.enabled=false`（`/set_config` 即时生效）→ WebUI 一键开关 → `/sys_cmd` 既有机制。

### 4.7 降级链（直播不翻车的核心）

```
Agent 决策失败（超时 / 异常 / 预算耗尽 / FC 不可用）
  → ① 原 LLM 直答路径（llm_handle，provider sessions 现状逻辑）
  → ② 静默放弃本轮（现状 llm 无返回时的既有行为）
```

每次降级写 trace。规则引擎的所有关键词功能不受影响——**它从"被替代者"变成了"安全网"**。

## 5. 集成点与改动面（文件级清单）

| 文件 | 改动 | 量级 |
| --- | --- | --- |
| `luna/agent/`（新建包） | context / intent / runtime / registry / tools / llm_adapter / memory / safety / trace | 全部新代码 |
| `luna/core/my_handle.py` | `config_load` 初始化 AgentRuntime 并注入 self；`_interaction_pipeline` 在"走到 LLM"处插 ~30 行门控分支（`agent.enabled` 时走 runtime，异常捕获后走原路径）。**不删除任何现有逻辑** | 小 |
| `config.json` | 新增 `agent` 段（见附录，默认 `enabled=false`，存量用户零感知） | 小 |
| `webui_server/` | 新增 `agent_api.py` 路由域（开关/trace 查询/记忆读写/工具列表）+ `schemas.py` 增响应模型（沿用 response_model 规范） | 中 |
| `tests/unit/` | agent 四件套单测 + AST 守卫（`test_platform_scoping`）扩展覆盖 `luna/agent` | 中 |
| `docs/backend-architecture.md` | 分层图补 agent 域一行 | 小 |
| `app/idle_tasks.py`（P1） | 闲时任务从固定文案池改为可配置走 Agent 话题策划 | 中 |

## 6. 可观测性（trace）

`luna/agent/trace.py`：每次决策一条 JSON line 追加到独立日志（复用 `my_log` 基建），字段：`ts / event_type / username / prompt_chars / tool_calls[(name, args_digest, ms, ok)] / output_chars / degraded / tokens_est / cost_flag`。WebUI trace 查看器按场次过滤。没有 trace 的 Agent 在直播场景等于盲飞——排查"为什么它说了这话/没说话/说话超时"全靠它。

## 7. WebUI：Agent 工作台（已实装，2026-11-07）

一级导航"Agent 工作台"（`webui_react/src/components/AgentPage.tsx` + `webui_server/agent_api.py`），四块：

1. **总控**：enabled 持久开关（走 configStore 草稿，保存后重启生效）+ **一键急停**（代理主进程 `/agent_kill`，进程内即时生效不落盘）+ 轮次/超时/预算/LLM 通道/人设参数。
2. **工具管理**：工具卡片墙，逐个启用/禁用（`agent.tools.enabled` 数组草稿），dangerous 类红色标识。
3. **记忆管理**：观众画像表（搜索/备注编辑/删除）+ 高光时间线；webui 侧经 `MemorySystem` 直接读写共享 sqlite。
4. **决策回放**：trace 流水 + 单条展开（工具调用/耗时/降级原因），代理主进程 `/agent_trace`。

主进程侧新增机机接口：`/agent_status` `/agent_trace` `/agent_kill`（app/api.py）。`resolveTab` 顺带修复页面中文标题深链（此前 `?tab=玩法库` 等一律回 dash）。

## 8. 分期实施计划

| 阶段 | 范围 | 验收标准 |
| --- | --- | --- |
| **P0 Agent-Ready**（**已实施** b737b69） | `luna/agent` 骨架；ToolRegistry + 首批 5 工具；LLMAdapter 双通道；`_interaction_pipeline` 门控分支；config 段；trace；单测+守卫+冒烟；真机 LLM 验证通过 | "积分榜前五是谁""刚才在聊什么"能被回答并播报；`enabled=false` 零回归 |
| **P1 大脑升级**（**已实施** 2026-11-07） | IntentRouter v1（复读风暴跳过 + 内容截断）；动作类工具 **play_song / generate_image** 入册（handle 提炼干净入口，关键词链路不动）；**stop_playback** 播放控制工具（观众喊停/切歌，停当前 + 清队列；system prompt 注入播放状态）；`idle_tasks` 文案模式接 `generate_proactive()`（高光+弹幕上下文注入，失败回落文案池）；reply_template 对齐；WebUI 卡片墙自动收录新工具 | 观众自然语言点歌/求画可被模型自主触发；刷屏弹幕不再重复烧 token |
| **P1 剩余（待做）** | 小模型意图分流；互动率/降级率度量对比 | 对比规则模式互动率提升；降级率 < 5% |
| **P2 生态化** | MCP 协议接入（Luna 作 MCP host，第三方工具即插即用）；Agent 工作台完整版；直播复盘报告；人设知识库 RAG | 第三方工具接入成本 ≤ 一个 JSON 描述 + 一个类；复盘报告成为留存功能 |

## 9. 测试策略

- **单测**（`.venv`，pytest）：注册表完整性（description/schema 非空、白名单一致性）；runtime 循环（mock LLM：零轮直答 / 一轮工具 / 超轮次 / 异常降级 / 预算熔断）；记忆读写与截断；安全门（白名单外调用拒绝、频率限制、dangerous 拦截）。
- **双环境**：webui_server 的 agent_api 遵守 pydantic v1/v2 兼容约束，Miniconda（v1.10）起一遍验证。
- **AST 守卫**：`test_platform_scoping` 扩展——`luna/agent` 只准依赖 `luna/infra`、`luna/common` 与标准库，能力一律经 ctx 注入。
- **回归锚点**：`agent.enabled=false` 时现有全部用例行为不变；`tools/smoke_test.py` 的 `[4/5] Agent 决策域` 段覆盖配置读取/注册表加载（Miniconda 与 .venv 双环境跑通）。

**已知问题（v4 遗留，非 agent 引入）**：全量单测在 pytest 报告全部通过后，解释器退出会因若干未 cancel 的非 daemon `threading.Timer` 线程挂住（本地可见，CI 按进程退出不受影响）；来源是 `start_timers`/audio 的既有 Timer，待后续统一治理。

## 10. 风险与对策

| 风险 | 对策 |
| --- | --- |
| 多轮工具拖慢首响应 | 有界循环 + timeout_seconds 超时降级 + 首句优先合成（复用流式切句经验） |
| token 成本失控 | 分层模型（分流用便宜模型）+ Budget 熔断 + Ollama 本地档 + 闲时任务错峰 |
| 输出合规风险 | 输出侧 prohibitions 强过滤不可关 + 工具白名单默认最小集 |
| 模型不支持 FC | 通道 B 文本协议全 provider 兜底 |
| 复杂度上升难以排查 | 双引擎开关 + trace 全量记录 + WebUI 决策回放 |
| 观众恶意消耗（刷弹幕骗工具调用） | 每观众频率限制 + 黑名单前置 + 预算熔断 |

## 11. 产品度量

- **技术层**：首响应延迟 P95（目标 ≤ 规则模式 +1.5s）；单次决策 token 成本；工具调用成功率；降级率。
- **产品层**：互动率（有回复弹幕占比）、人均互动次数、观众回头率（viewer_profile 回访）、礼物转化对比、主播满意度（群内问卷）。
- 全部指标从 trace + 现有 db 数据即可统计，P0 就埋好。

## 附录 A：`config.json` 新增段草案

```json
"agent": {
  "enabled": false,
  "max_tool_rounds": 3,
  "timeout_seconds": 8,
  "llm": { "channel": "auto" },
  "tools": {
    "enabled": ["speak", "query_integral", "query_danmu_summary", "search_online", "memory_save"],
    "dangerous_enabled": []
  },
  "budget": { "tokens_per_hour": 200000, "tool_calls_per_minute": 20 },
  "memory": { "viewer_profile": true, "episodic": true, "inject_max_chars": 500 },
  "safety": { "per_viewer_tool_rate": { "count": 3, "window_seconds": 60 } }
}
```

## 附录 B：`luna/agent/` 目录规划

```
luna/agent/
  __init__.py
  context.py      # AgentContext / Budget
  intent.py       # IntentRouter（P0 规则实现）
  runtime.py      # AgentRuntime 决策循环
  registry.py     # TOOLS 注册表 + Tool 基类
  tools/          # 每工具一文件，run(args, ctx) -> str
  llm_adapter.py  # 双通道：原生 FC / ReAct 文本协议
  memory.py       # MemorySystem（viewer_profile / episodic）
  safety.py       # SafetyGuard（白名单/频率/预算/输出过滤）
  trace.py        # 决策 trace 日志
```

依赖方向：`luna/agent → luna/infra、luna/common`（+ 经 `ctx.handle` 注入访问 core 能力）；AST 守卫强制。
