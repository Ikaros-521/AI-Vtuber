/** 下拉选项表，与 v2 webui_app/options.py、helpers.py 保持一致。 */

export const CHAT_TYPE_OPTIONS: Record<string, string> = {
  none: '不启用',
  reread: '复读机',
  chatgpt: 'ChatGPT',
  langchain_chatchat: 'langchain_chatchat',
  zhipu: '智谱AI',
  gemini: 'Gemini',
  tongyi: '通义千问/阿里云百炼',
  my_wenxinworkstudio: '千帆大模型',
  anythingllm: 'AnythingLLM',
  dify: 'Dify',
  volcengine: '火山引擎',
  custom_llm: '自定义LLM',
}

export const PLATFORM_OPTIONS: Record<string, string> = {
  talk: '聊天模式',
  bilibili: '哔哩哔哩',
  bilibili2: '哔哩哔哩2',
  dy: '抖音',
  dy2: '抖音2',
  ks: '快手',
  live_monitor_assistant: '直播弹幕监听助手',
  wxlive: '微信视频号',
  youtube: 'YouTube',
  twitch: 'twitch',
  tiktok: 'tiktok',
}

// 快手2/拼多多/斗鱼/1688/淘宝 的弹幕都由「直播弹幕监听助手」推给本机；
// 老 config 里存的还是这些旧平台名时，把它显示回下拉里，不能让老用户看到空白平台。
export const LEGACY_LIVE_MONITOR_PLATFORMS: Record<string, string> = {
  ks2: '快手2（并入直播弹幕监听助手）',
  pdd: '拼多多（并入直播弹幕监听助手）',
  douyu: '斗鱼（并入直播弹幕监听助手）',
  1688: '1688（并入直播弹幕监听助手）',
  taobao: '淘宝（并入直播弹幕监听助手）',
}

export function platformOptions(current: unknown): Record<string, string> {
  if (typeof current === 'string' && current in LEGACY_LIVE_MONITOR_PLATFORMS) {
    return { ...PLATFORM_OPTIONS, [current]: LEGACY_LIVE_MONITOR_PLATFORMS[current] }
  }
  return PLATFORM_OPTIONS
}

export const LIVE_MONITOR_PLATFORM_KEYS = [
  'live_monitor_assistant',
  ...Object.keys(LEGACY_LIVE_MONITOR_PLATFORMS),
]

export const VISUAL_BODY_OPTIONS: Record<string, string> = {
  其他: '其他（外置）',
  metahuman_stream: 'metahuman_stream',
  EasyAIVtuber: 'EasyAIVtuber',
  digital_human_video_player: '数字人视频播放器',
  live2d_TTS_LLM_GPT_SoVITS_Vtuber: 'live2d-TTS-LLM-GPT-SoVITS-VTuber',
  xuniren: 'xuniren',
}

export const AUDIO_SYNTHESIS_TYPE_OPTIONS: Record<string, string> = {
  none: '不启用',
  'edge-tts': 'Edge-TTS',
  vits: 'VITS',
  bert_vits2: 'bert_vits2',
  elevenlabs: 'elevenlabs',
  openai_tts: 'OpenAI TTS',
  gradio_tts: 'Gradio',
  gpt_sovits: 'GPT_SoVITS',
  azure_tts: 'azure_tts',
  cosyvoice: 'CosyVoice',
  f5_tts: 'F5-TTS',
  multitts: 'MultiTTS',
  melotts: 'MeloTTS',
  index_tts: 'Index-TTS',
}

export const NEED_LANG_OPTIONS: Record<string, string> = {
  none: '所有',
  zh: '中文',
  en: '英文',
  jp: '日文',
}

export const BILIBILI_LOGIN_TYPE_OPTIONS: Record<string, string> = {
  cookie: 'cookie',
  手机扫码: '手机扫码',
  '手机扫码-终端': '手机扫码-终端',
  open_live: '开放平台',
  不登录: '不登录',
}

export const AUDIO_PLAYER_OPTIONS: Record<string, string> = {
  pygame: 'pygame',
  audio_player_v2: 'audio_player_v2',
  audio_player: 'audio_player',
}
