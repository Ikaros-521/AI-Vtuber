"""给只写着「启用」两个字的开关补上对象名（走查 audit-22）。

全站有 30 个开关的文案就是光秃秃一个「启用」：卡片标题折叠起来、或者窄屏被截断之后，
完全看不出启用的是什么。对象名不另立一张表——运行时从元素树上取这个开关所在卡片/折叠区
的标题（和全局搜索、未保存清单用的是同一个 locate），标题改了这里跟着变，不会失同步。
"""
from nicegui import context, ui

from webui_app.fields import locate

# 这些标题本身就是「一堆开关的容器」，拼上去只会得到「启用通用」「启用基本」这种废话——
# 这种情况退回用页面名
GENERIC = {'通用', '其它', '其他', '设置', '配置', '基本'}


def name_bare_enable_switches():
    """返回 {控件 id: 新文案}，便于测试与排查。"""
    changed = {}
    for element in list(context.client.elements.values()):
        if not isinstance(element, ui.switch) or (element.text or '').strip() != '启用':
            continue
        tab, section, _expansion = locate(element)
        object_name = (section or '').strip()
        if not object_name or object_name in GENERIC:
            # 整页就一个功能的页面（助播、翻译、积分的「通用」卡、图像识别的「通用」卡），
            # 页名就是它启用的东西
            object_name = tab.strip()
        if not object_name:
            continue
        element.text = f'启用{object_name}'
        changed[element.id] = element.text
    return changed


# 板块开关墙（页面配置）里有 31 个开关的文案就是配置键本身（走查 audit-5）：
# 「念弹幕 / 答谢 / 点歌」旁边站着 chat_with_file、gpt_sovits、xuniren、unity，
# 同一类东西两套称谓，用户分不清哪些是功能、哪些是厂商。
# 规则两条：英文品牌名统一成官方写法；拼音键与复合键补一个中文名，但**把键留在文案里**——
# 一是这些文案就是全局搜索的键，抹掉键就搜不到了；二是有人要拿去对文档/对 config.json。
SHOW_CARD_NAMES = {
    'gemini': 'Gemini',
    'gradio': 'Gradio',
    'unity': 'Unity',
    'elevenlabs': 'ElevenLabs',
    'openai_tts': 'OpenAI TTS',
    'gpt_sovits': 'GPT-SoVITS',
    'azure_tts': 'Azure TTS',
    'langchain_chatchat': 'Langchain_ChatChat',
    'Edge TTS': 'Edge-TTS',
    'VITS': 'VITS-Simple-API',
    'Bert VITS2': 'Bert-VITS2',
    'VITS Fast': 'VITS-Fast',
    'DDSP SVC': 'DDSP-SVC',
    '通义千问': '通义千问/阿里云百炼',
    'chat_with_file': '本地文件问答 chat_with_file',
    'xuniren': '虚拟人 xuniren',
    'metahuman_stream': 'MetaHuman 推流 metahuman_stream',
    'digital_human_video_player': '数字人视频播放器',
    'live2d_TTS_LLM_GPT_SoVITS_Vtuber': 'Vtuber 组合方案 live2d_TTS_LLM_GPT_SoVITS_Vtuber',
}


def rename_show_card_switches():
    """把开关墙上裸键/不规范写法换成统一文案。返回 {控件 id: 新文案}。"""
    changed = {}
    for element in list(context.client.elements.values()):
        if not isinstance(element, ui.switch):
            continue
        text = (element.text or '').strip()
        if text in SHOW_CARD_NAMES:
            element.text = SHOW_CARD_NAMES[text]
            changed[element.id] = element.text
    return changed
