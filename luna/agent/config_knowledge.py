"""配置助手的知识库：功能域目录 + 关键键语义 + 当前值注入域。

这是配置助手把「用户需求」翻译成「配置变更集」的依据——模型看不见
webui_react 的表单 schema，只能靠这里理解每个功能域能配什么。
按域组织，每域：说明 + 关键键（键名: 语义）。写得越准，翻译越对。

KNOWLEDGE 渲染进 system prompt；INJECT_SECTIONS 是随每轮对话注入实际值的
配置段清单（配置助手最常涉及的域，让模型知道"当前是什么"再提变更）。
"""

KNOWLEDGE = """
【平台接入】顶层 "platform" 选直播平台（bilibili/bilibili2/douyu/dy/dy2/ks/ks2/wxlive/twitch/youtube/tiktok/hntv/pdd/taobao/1688/live_monitor_assistant），
room_display_id 是直播间号；各平台以自身段名存接入参数（如 bilibili: uid/sessdata/roomid）。
"live_monitor_assistant" 是「直播弹幕监听助手」统一项：ip/port 由助手侧决定，本机只收推送。

【人设与大脑】"chat_type" 选大模型（chatgpt/langchain_chatchat/zhipu/tongyi/my_wenxinworkshop/gemini/anythingllm/custom_llm/dify/volcengine）。
"openai": api（OpenAI 兼容接口地址）、api_key（数组，可多 key）、model（模型名）。
"chatgpt": preset（系统人设提示词）、temperature（0-2 越高越发散）、max_tokens（单条回复长度上限）、stream（流式）。
"before_prompt"/"after_prompt"：每轮弹幕 prompt 的前后包裹（人设的主要载体，如"你是温柔的主播小助手。""请用口语回答。"）。
"reply_template": enable + copywriting（回复模板，{username}/{data}/{cur_time} 变量）。
"translate": enable + trans_type（弹幕/回复/弹幕+回复）翻译开关。

【声音】"audio_synthesis_type" 选 TTS（edge-tts/vits/bert_vits2/elevenlabs/openai_tts/gradio_tts/gpt_sovits/azure_tts/cosyvoice/f5_tts/multitts/melotts/index_tts），
各 TTS 以自身段名存参数（voice/api 等）。"audio_random_speed" 随机语速。

【互动玩法】
"choose_song" 点歌：enable 开关；start_cmd（点歌命令前缀数组，如["点歌"]）；random_cmd（随机点歌）；stop_cmd（取消点歌）；
  song_path（本地歌曲目录）；similarity（歌名模糊匹配相似度 0-1，越低越容易匹配上）；match_fail_copy（匹配失败文案，{content} 占位）。
"sd" 画图：enable 开关；trigger（画图命令前缀）；prompt_llm.type（画图提示词润色模型，none 直出）。
"integral" 积分：enable；sign（签到：enable/cmd 命令数组/copywriting 区间文案）；view（观看积分）；gift（礼物积分）；
  查询/排行榜命令在同段 cmd 类键。
"custom_cmd" 自定义命令：type（弹幕/回复/弹幕+回复 触发时机）+ commands（关键词→动作）。
"key_mapping" 按键映射：type 同上 + keys（关键词→按键，配合游戏）。
"local_qa" 本地问答：enable + qa_file（问答 JSON 文件路径）+ similarity。
"search_online" 联网搜索：enable；keyword_enable + before_keyword（命令前缀）；http_proxy/https_proxy。

【弹幕管理】
"filter": repeat_limit（限定时间去重时长秒）；prohibitions（违禁词数组，命中不处理）；
  before_must_str_for_llm / after_must_str_for_llm（弹幕必须以这些前缀/后缀开头才触发 LLM，空数组=不限制）；
  username_convert_digits_to_chinese（用户名数字转中文）。
"read_comment" 念弹幕：enable；read_username_enable（念用户名）；username_max_len；periodic_trigger（周期性合并触发）。
"thanks" 答谢：entrance（入场：enable/copywriting/最低值门槛）、gift（礼物同构）、follow（关注同构）；
  各自的"最低值"挡掉小额不答谢。
"idle_time_task" 闲时任务：enable；idle_time_min/max（闲时触发间隔秒）；copywriting（文案模式：enable/random/copy 文案池，支持{time}{user_num}{last_username}变量与[1|2]括号随机语法）；
  comment（弹幕触发LLM模式）；local_audio（本地音频模式）。
"schedule" 定时文案：enable + copywriting（定时播报文案池）+ 定时规则。
"talk" 本地聊天：username（说话人昵称）、show_chat_log（同步弹幕到聊天窗）、direct_run_talk（免按键直接拾音）。

【Agent 决策域（v5）】"agent"：enabled 总开关；max_tool_rounds（工具循环轮次上限）；timeout_seconds（单次决策超时）；
  persona（人设补充，空则沿用 before/after_prompt）；llm.channel（auto/native/text）、llm.model（覆盖 chatgpt.model）、
  llm.fallback_chat_type（主模型异常时的备用模型）、llm.small_chat_type + small_max_chars（简单弹幕小模型直答）；
  tools.enabled（工具白名单：speak/query_integral/query_danmu_summary/search_online/memory_save/play_song/generate_image/
  stop_playback/pause_playback/resume_playback/set_volume/observe_screen）、tools.dangerous_enabled；
  budget.tokens_per_hour（小时预算，0=不限）；intent.duplicate_burst（复读风暴分流）；intent.max_content_chars（超长截断）；
  memory（viewer_profile/episodic）；safety.per_viewer_tool_rate（每观众工具频率）；config_assistant（本助手：safety_level 三档）。

【数据与播放】"database": path（sqlite 路径，积分/弹幕/画像都在这）。"play_audio": player（pygame/audio_player 播放器选择）。
"webui": ip/port（面板地址）。"api_port"：主程序内部接口端口。

【无人值守直播（俗称"无人直播"）】指开播后不需要主播在镜头前，由程序自主维持直播内容与互动。
本产品的无人直播 = 选好平台 + 开启内容源 + 开启自动互动，三者齐备：
1. 平台接入：platform 选对应平台（抖音是 dy / dy2；注意抖音弹幕不能直连，需要观众侧装
   「直播弹幕监听助手」推送，或走其它接入方式，见"直播弹幕监听助手"段）。
2. 内容源（开播台 → 形象/内容）：digital_human_video_player（数字人视频播放）、EasyAIVtuber、
   metahuman_stream 等，或在"coordination_program"里挂外部程序（如视频循环播放器）。
3. 自动互动（任选组合）：idle_time_task 闲时任务（定时/闲时主动说话）、schedule 定时文案、
   thanks 答谢、read_comment 念弹幕、agent.enabled（Agent 自主话题与工具）。
典型需求映射：「帮我配无人直播」→ 引导确认平台与内容源，再建议开启 idle_time_task + agent。
"""

# 每轮对话注入实际值的配置段（助手最常涉及的域；控制体积，不注入平台密钥段）
INJECT_SECTIONS = [
    "chat_type",
    "before_prompt",
    "after_prompt",
    "choose_song",
    "filter",
    "thanks",
    "integral",
    "idle_time_task",
    "read_comment",
    "search_online",
    "local_qa",
    "custom_cmd",
    "sd",
    "schedule",
    "talk",
    "reply_template",
    "agent",
]

# 敏感键名：变更集路径命中即强制 danger=True（自动审核档也不许自动落盘）
SENSITIVE_KEY_HINTS = ("api_key", "password", "token", "sessdata", "cookie", "login", "secret")
