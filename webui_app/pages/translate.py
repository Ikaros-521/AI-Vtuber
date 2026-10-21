"""翻译页：百度/谷歌翻译配置。"""
from nicegui import ui

from webui_app.pages import PageConfig


def build_translate_tab(config, card_css, switch_internal_css):
    with ui.row():
        switch_translate_enable = ui.switch('启用', value=config.get("translate", "enable")).style(switch_internal_css)
        select_translate_type = ui.select(
            label='类型',
            options={'baidu': '百度翻译', 'google': '谷歌翻译'},
            value=config.get("translate", "type")
        ).style("width:100px;")
        select_translate_trans_type = ui.select(
            label='翻译类型',
            options={'弹幕': '弹幕', '回复': '回复', '弹幕+回复': '弹幕+回复'},
            value=config.get("translate", "trans_type")
        ).style("width:150px;")

    with ui.card().style(card_css):
        ui.label("百度翻译")
        with ui.row():
            input_translate_baidu_appid = ui.input(label='APP ID', value=config.get("translate", "baidu", "appid"), placeholder='翻译开放平台 开发者中心 APP ID')
            input_translate_baidu_appkey = ui.input(label='密钥', value=config.get("translate", "baidu", "appkey"), placeholder='翻译开放平台 开发者中心 密钥')
            select_translate_baidu_from_lang = ui.select(
                label='源语言',
                options={'auto': '自动检测', 'zh': '中文', 'cht': '繁体中文', 'en': '英文', 'jp': '日文', 'kor': '韩文', 'yue': '粤语', 'wyw': '文言文'},
                value=config.get("translate", "baidu", "from_lang")
            ).style("width:100px;")
            select_translate_baidu_to_lang = ui.select(
                label='目标语言',
                options={'zh': '中文', 'cht': '繁体中文', 'en': '英文', 'jp': '日文', 'kor': '韩文', 'yue': '粤语', 'wyw': '文言文'},
                value=config.get("translate", "baidu", "to_lang")
            ).style("width:100px;")

    with ui.card().style(card_css):
        ui.label("谷歌翻译")
        with ui.row():
            input_translate_google_proxy = ui.input(label='代理地址', value=config.get("translate", "google", "proxy"), placeholder='代理的完整地址，请携带协议')
            select_translate_google_src_lang = ui.select(
                label='源语言',
                options={'auto': '自动', 'zh-CN': '中文', 'en': '英文', 'ja': '日文'},
                value=config.get("translate", "google", "src_lang")
            ).style("width:100px;")
            select_translate_google_tgt_lang = ui.select(
                label='目标语言',
                options={'zh-CN': '中文', 'en': '英文', 'ja': '日文'},
                value=config.get("translate", "google", "tgt_lang")
            ).style("width:100px;")

    return PageConfig(mapping={
        "translate": {
            "enable": (switch_translate_enable, 'bool'),
            "type": (select_translate_type, 'str'),
            "trans_type": (select_translate_trans_type, 'str'),
            "baidu": {
                "appid": (input_translate_baidu_appid, 'str'),
                "appkey": (input_translate_baidu_appkey, 'str'),
                "from_lang": (select_translate_baidu_from_lang, 'str'),
                "to_lang": (select_translate_baidu_to_lang, 'str'),
            },
            "google": {
                "proxy": (input_translate_google_proxy, 'str'),
                "src_lang": (select_translate_google_src_lang, 'str'),
                "tgt_lang": (select_translate_google_tgt_lang, 'str'),
            },
        }
    })
