"""WebUI 功能卡片与配置项的功能描述元数据与辅助函数。

解决部分配置命名较为专业或生僻（如 chat_with_file、metahuman_stream、DDSP-SVC 等）
导致用户光看卡片标题无法直观理解其功能与使用场景的问题。
"""
from nicegui import ui
from webui_app.theme import INK_MUT

# 全站核心功能卡片与配置项的通俗功能描述字典
CARD_DESCRIPTIONS = {
    # ---------------- 大语言模型 (LLM) ----------------
    'OpenAI / 兼容接口': '兼容 OpenAI 标准接口协议的大语言模型服务（如 ChatGPT、DeepSeek、Moonshot、通义千问兼容端点等）。',
    'ChatGPT': '基于 OpenAI 官方/中转 API 接口的大语言模型对话服务。',
    'Langchain_ChatChat': '基于 Langchain-ChatChat 开源框架部署的本地知识库与搜索引擎问答服务接口。',
    'ChatGLM': '清华大学智谱清言开源 ChatGLM 系列大语言模型本地部署或 API 接口。',
    'Ollama': '本地开源大模型运行环境，支持离线运行 Qwen、Llama、Mistral、DeepSeek 等主流大模型（免 API Key）。',
    '智谱AI': '智谱开放平台 GLM 系列大语言模型服务（支持联网搜索与代码执行）。',
    '千帆大模型': '百度智能云千帆大模型平台（文心一言 ERNIE 系列模型接口）。',
    'Gemini': 'Google 谷歌多模态大语言模型，具备极高的响应速度与丰富的知识储备。',
    'AnythingLLM': '对接 AnythingLLM 工作区 API，将整套本地工作区文档库集成进直播问答中。',
    '通义千问/阿里云百炼': '阿里云通义千问（Qwen）官方大模型 API，支持超长上下文与丰富的系统人设。',
    '通义千问': '阿里云通义千问（Qwen）官方大模型 API，支持超长上下文与丰富的系统人设。',
    'Dify': '对接 Dify.ai 企业级大语言模型工作流/Agent 平台，支持复杂提示词编排与多工具协同。',
    '火山引擎': '字节跳动火山引擎豆包（Doubao）大语言模型 API 接入。',
    '自定义LLM': '自定义通用 HTTP 接口，可灵活对接任意遵循标准 JSON 格式的自建大模型或第三方中转服务。',

    # ---------------- 形象驱动 (Avatar) ----------------
    'Live2D': '基于 Web 端的 Live2D 虚拟形象驱动服务，支持与网页播放器口型同步、表情动作触发。',
    'EasyAIVtuber': '对接 EasyAIVtuber 客户端，实现轻量级二次元虚拟主播形象动作与说话联动。',
    '数字人视频播放器': '基于预录制动作视频片段无缝切片轮播的数字人驱动（无需高性能独立显卡）。',
    'metahuman_stream': '对接虚幻引擎（Unreal Engine）MetaHuman 实时视频流驱动，呈现电影级超写实 3D 数字人。',
    'MetaHuman 推流 metahuman_stream': '对接虚幻引擎（Unreal Engine）MetaHuman 实时视频流驱动，呈现电影级超写实 3D 数字人。',
    'live2d_TTS_LLM_GPT_SoVITS_Vtuber': '第三方开源 Live2D+LLM+GPT-SoVITS 开源一体化 Vtuber 推流客户端联动方案。',
    'Vtuber 组合方案 live2d_TTS_LLM_GPT_SoVITS_Vtuber': '第三方开源 Live2D+LLM+GPT-SoVITS 开源一体化 Vtuber 推流客户端联动方案。',
    'xuniren': '对接腾讯智影/虚拟人驱动服务，呈现高拟真口型同步与虚拟主播画面推流。',
    '虚拟人 xuniren': '对接腾讯智影/虚拟人驱动服务，呈现高拟真口型同步与虚拟主播画面推流。',
    'Unity': '通过 WebSocket / TCP 与 Unity 3D 虚拟主播项目联动，传递语音口型、骨骼动画与交互特效。',

    # ---------------- 语音合成 (TTS) ----------------
    'TTS 语音合成调试': '在线试听与快速测试当前配置的语音合成效果与音色表现。',
    'Edge-TTS': '微软 Edge 浏览器内置的高品质云端语音合成，免费免配置、多语言、开箱即用。',
    'VITS-Simple-API': '基于 VITS-Simple-API 开源推理服务的本地/云端高拟真二次元音色生成。',
    'bert_vits2': 'Bert-VITS2 情感语音合成系统，引入 BERT 增强语意，音调更自然富含情感。',
    'Bert-VITS2': 'Bert-VITS2 情感语音合成系统，引入 BERT 增强语意，音调更自然富含情感。',
    'elevenlabs': 'ElevenLabs 商业级极高拟真度多语言语音生成服务。',
    'ElevenLabs': 'ElevenLabs 商业级极高拟真度多语言语音生成服务。',
    'OpenAI TTS': 'OpenAI 官方语音合成模型（如 tts-1 / tts-1-hd），发音清晰自然。',
    'Gradio': '通用 Gradio WebUI TTS 接口对接，可连接各类以 Gradio 形式部署的语音合成服务。',
    'GPT-SoVITS': '少样本零样本语音克隆神器，仅需数秒音频即可精准复刻主播或特定角色声线。',
    'WebTTS相关配置': '基于浏览器端 Web Speech API 或网页端 TTS 服务生成音频。',
    'azure_tts': '微软 Azure 认知服务官方语音合成，提供工业级稳定性和超丰富多国语言音色。',
    'Azure TTS': '微软 Azure 认知服务官方语音合成，提供工业级稳定性和超丰富多国语言音色。',
    'CosyVoice': '阿里通义实验室开源的多语言情感语音合成与零样本音色克隆模型。',
    'F5-TTS': '基于非自回归 Flow Matching 的零样本语音克隆框架，生成速度极快。',
    'MultiTTS': '对接安卓端 MultiTTS 语音引擎聚合服务端。',
    'MeloTTS': '轻量级极速多语言 TTS 库，CPU 上即可实现毫秒级快速合成。',
    'Index-TTS': 'Index 语音合成模型接口，适用于特定训练音色。',

    # ---------------- 变声后期 (SVC) ----------------
    'DDSP-SVC': '基于可微数字信号处理（DDSP）的超低延迟实时歌声与语音变声，适合直播实时换声。',
    'SO-VITS-SVC': '基于 SoftVC VITS 深度学习架构的高保真音色转换变声系统。',

    # ---------------- 语音识别 (STT / 语音对话) ----------------
    '语音对话与拾音': '通过本地麦克风捕捉说话声音并转写为文字，让主播能与 AI 进行面对面语音对话。',
    '对话打断': '当主播插话或麦克风再次拾音时，立即中断正在播放的 AI 语音，体验如同真人交谈。',
    '清除类型': '控制何时丢弃未能及时完成转写的历史录音片段，防止语音堆积延迟。',
    '语音唤醒与睡眠': '设置唤醒词（如“小助手”）与休眠词，进入睡眠状态后将忽略普通对话。',
    'faster_whisper': '基于 CTranslate2 高性能加速的本地 Whisper 语音转文字模型，免网络延迟。',
    'SenseVoice': '阿里开源高精度多语言多情感富文本语音识别模型，秒级超低延迟。',

    # ---------------- 互动与玩法 ----------------
    '念弹幕': '弹幕播报策略：过滤、排序、频率控制与回复逻辑，避免弹幕刷屏或遗漏关键互动。',
    '本地问答': '优先于大模型的预设问答库：命中关键词时秒回预设文案，不耗 Token 且回答 100% 精准。',
    '答谢': '入场欢迎、礼物赠送、关注感谢的自动语音播报与文案轮播系统。',
    '点歌': '弹幕点歌玩法：观众发送“点歌 歌名”自动检索并播放歌曲，支持插队与优先级排序。',
    '点歌模式': '弹幕点歌玩法：观众发送“点歌 歌名”自动检索并播放歌曲，支持插队与优先级排序。',
    '定时任务': '周期性广播与通知：按固定的时间周期（如每隔 5 分钟）循环播报指定公告或互动提示。',
    '闲时任务': '直播间冷场自动保活：当一定时间内没有任何弹幕时，AI 自动发起话题暖场，防止冷场。',
    '动态文案': '文件夹文案库轮播：从指定文件夹读取文案，支持由大语言模型二次润色后再播报。',
    '按键/文案/音频/串口/图片 映射': '弹幕指令与外部联动：观众发送特定弹幕时，自动触发键盘按键、本地音效、串口硬件或图片弹窗。',
    '按键/文案映射': '弹幕指令与外部联动：观众发送特定弹幕时，自动触发键盘按键、本地音效、串口硬件或图片弹窗。',
    'Stable Diffusion': '弹幕绘图玩法：观众发送指令让 AI 实时画画，并在直播间动态展示生成的画面。',
    '洛曦 直播弹幕助手': '对接第三方“洛曦 直播弹幕助手”软件，扩展支持更多平台的弹幕数据监听。',

    # ---------------- 外设与系统联动 ----------------
    '串口': '通过串口与 Arduino / ESP32 等单片机通信，联动控制物理指示灯、舵机机械臂或互动实体道具。',
    '助播': '虚拟双主播/副播配合：主副双主播协作，根据关键词或音频特征触发副播捧哏、接话或音效。',
    '基本': '助播基础设置：配置助播名称与独立的 TTS 语音合成引擎（实现主副主播不同音色）。',
    '触发类型': '助播触发范围：勾选由助播负责响应的互动场景（如礼物答谢、念弹幕、点歌等）。',
    '文本匹配': '助播文本匹配库：当主讲内容或弹幕命中特定关键词时，由助播自动接话回复。',
    '音频匹配': '助播音频匹配库：命中预设规则时，由助播播放对应的预录音频或捧哏声效。',
    '联动程序': '伴随进程生命周期管理：随 AI-Vtuber 启动/停止时自动唤起或终止绑定的第三方配套软件。',
    '自定义命令': '弹幕高级指令匹配：通过正则或关键词触发自定义外部脚本或快捷操作。',

    # ---------------- 图像识别与翻译 ----------------
    '电脑截图': '屏幕画面捕捉：截取指定游戏或软件窗口画面，交由多模态 AI 模型进行视觉识别与实时解说。',
    '摄像头截图': '摄像头画面捕捉：定时抓取外接 USB 摄像头画面并进行图像识别，支持手势或实物互动。',
    '翻译设置': '直播双语翻译：支持观众外语弹幕实时中译、主播回复自动外译，降低跨语种直播门槛。',
    '百度翻译': '对接百度翻译开放平台官方 API 接口。',
    '谷歌翻译': '对接 Google 在线翻译接口。',

    # ---------------- 积分系统 ----------------
    '积分系统': '直播间观众互动成长体系：通过签到、送礼、入场获取积分，支持积分兑换与弹幕查询。',
    '签到': '观众发送签到命令（如“签到”）获取积分与专属欢迎问候。',
    '增删改查': '观众通过弹幕命令自助查询自己的积分余额或排名。',

    # ---------------- 文案与批量音频 ----------------
    '播放控制': '长篇文案轮播引擎：控制预录文案音频的循环播报、随机播报及弹幕插入间隙。',
    '文案音频合成': '文案批量语音合成：将长篇文本按标点/换行自动切片并调用 TTS 批量生成音频文件。',

    # ---------------- 直播接入与风控 ----------------
    '平台相关': '直播间连接协议与登录鉴权（如 B站 Cookie/开放平台、Twitch 账号等）。',
    '直播弹幕监听助手': '接收由浏览器油猴脚本“直播弹幕监听助手”推送的弹幕与互动数据（快手/拼多多/淘宝等）。',
    '音频播放': '播报音频排队调度器：控制多条音频之间的播放间隔、文本切分与播放状态回调。',
    '音频随机变速': '给合成后的播报音频加入微小的随机语速波动，打破机械感，让语音听起来更自然生动。',
    'web字幕打印机': '透明背景实时字幕网页挂件：专为 OBS 浏览器源设计，随台词逐字打字机式滚动展示。',
    '过滤': '弹幕风控与防刷屏：敏感词黑名单、短时间内重复弹幕丢弃、防爆音与历史消息堆积清理。',

    # ---------------- 运维与系统 ----------------
    'webui配置': '设置 WebUI 控制台的监听 IP、端口号、主题配色方案及会话安全参数。',
    '本地路径指定URL路径访问': '本地静态资源 HTTP 映射：将本机音频、图片文件夹映射为 Web 访问路径供网页端调用。',
    'CSS': '自定义注入前端 CSS 样式表，实现 WebUI 界面深度的视觉个性化定制。',
    '配置模板': '配置方案快照管理：一键保存或载入不同直播主题（如“游戏模式”、“深夜闲聊”）的预设配置。',
    '板块显示/隐藏': 'WebUI 界面个性化降噪：隐藏当前不需要的功能板块卡片，让控制台更加清爽专注。',
    '账号管理': 'WebUI 网页登录访问认证：设置管理员用户名与密码，保障局域网或公网部署时的安全。',
    '数据库': '配置本地 SQLite 数据库存储历史弹幕、礼物记录与交互日志。',
    '日志': '实时运行日志控制台与日志文件持久化记录。',
}

# 别名映射归一化
ALIASES = {
    'chatgpt': 'ChatGPT',
    'gemini': 'Gemini',
    'dify': 'Dify',
    'volcengine': '火山引擎',
    'my_wenxinworkshop': '千帆大模型',
    'zhipu': '智谱AI',
    'tongyi': '通义千问',
    'custom_llm': '自定义LLM',
    'vits': 'VITS-Simple-API',
    'edge-tts': 'Edge-TTS',
    'edge_tts': 'Edge-TTS',
    'openai_tts': 'OpenAI TTS',
    'gradio_tts': 'Gradio',
    'gradio': 'Gradio',
    'gpt_sovits': 'GPT-SoVITS',
    'azure_tts': 'Azure TTS',
    'cosyvoice': 'CosyVoice',
    'f5_tts': 'F5-TTS',
    'multitts': 'MultiTTS',
    'melotts': 'MeloTTS',
    'index_tts': 'Index-TTS',
    'ddsp_svc': 'DDSP-SVC',
    'ddsp svc': 'DDSP-SVC',
    'so_vits_svc': 'SO-VITS-SVC',
    'live2d': 'Live2D',
    'unity': 'Unity',
    'easyaivtuber': 'EasyAIVtuber',
    'read_comment': '念弹幕',
    'thanks': '答谢',
    'choose_song': '点歌',
    'sd': 'Stable Diffusion',
    'schedule': '定时任务',
    'idle_time_task': '闲时任务',
    'trends_copywriting': '动态文案',
    'play_audio': '音频播放',
    'web_captions_printer': 'web字幕打印机',
    'key_mapping': '按键/文案映射',
    'trends_config': '动态配置',
    'abnormal_alarm': '异常报警',
    'coordination_program': '联动程序',
}


def get_desc(key_or_name: str, default: str = '') -> str:
    """获取指定卡片或配置项的功能描述文本，支持别名自动解析。"""
    if not key_or_name:
        return default
    text = key_or_name.strip()
    if text in CARD_DESCRIPTIONS:
        return CARD_DESCRIPTIONS[text]
    lower_text = text.lower()
    if lower_text in ALIASES:
        resolved = ALIASES[lower_text]
        return CARD_DESCRIPTIONS.get(resolved, default)
    if text in ALIASES:
        resolved = ALIASES[text]
        return CARD_DESCRIPTIONS.get(resolved, default)
    return default


def attach_tooltip(element, key_or_name: str):
    """为控件元素附加对应功能点的描述作为 Tooltip。"""
    desc = get_desc(key_or_name)
    if desc:
        element.tooltip(desc)
    return element


def show_card_desc(key_or_desc: str):
    """在卡片主标题下方渲染一行统一风格的功能描述副标题。

    注意：必须紧跟在主标题 ui.label 之后调用，切勿放在主标题之前，
    以确保 Card 的第一个 Label 仍然是主标题，保持 locate()、repage() 完美兼容。
    """
    if not key_or_desc:
        return None
    desc = get_desc(key_or_desc, key_or_desc)
    if not desc:
        return None
    return ui.label(desc).style(
        f'font-size:12px;color:{INK_MUT};margin-top:-4px;margin-bottom:8px;line-height:1.45;'
    )
