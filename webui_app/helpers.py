"""页面共用的小工具与选项常量。"""


def textarea_data_change(data):
    """把字符串列表转成多行文本框内容。"""
    if data is None:
        return ""
    return "".join(f"{item}\n" for item in data)


def common_textarea_handle(content):
    """把多行文本框内容转成去空行的字符串列表。"""
    return [token.strip() for token in content.split("\n") if token.strip()]


AUDIO_SYNTHESIS_TYPE_OPTIONS = {
    'none': '不启用',
    'edge-tts': 'Edge-TTS',
    'vits': 'VITS',
    'bert_vits2': 'bert_vits2',
    'vits_fast': 'VITS-Fast',
    'elevenlabs': 'elevenlabs',
    'openai_tts': 'OpenAI TTS',
    'gradio_tts': 'Gradio',
    'gpt_sovits': 'GPT_SoVITS',
    'azure_tts': 'azure_tts',
    'cosyvoice': 'CosyVoice',
    'f5_tts': 'F5-TTS',
    'multitts': 'MultiTTS',
    'melotts': 'MeloTTS',
    'index_tts': 'Index-TTS',
}
