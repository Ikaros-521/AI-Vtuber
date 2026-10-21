"""虚拟身体页：Live2D 与各家数字人/虚拟形象对接配置。"""
from nicegui import ui

from utils.my_log import logger
from webui_app.pages import PageConfig


def build_visual_body_tab(config, common, card_css, switch_internal_css):
    mapping = {}

    if config.get("webui", "show_card", "visual_body", "live2d"):
        with ui.card().style(card_css):
            ui.label("Live2D")
            with ui.row():
                switch_live2d_enable = ui.switch('启用', value=config.get("live2d", "enable")).style(switch_internal_css)
                input_live2d_port = ui.input(label='端口', value=config.get("live2d", "port"), placeholder='web服务运行的端口号，默认：12345，范围:0-65535，没事不要乱改就好')

                live2d_names = common.get_folder_names("Live2D/live2d-model")  # 路径写死
                logger.info(f"本地Live2D模型名列表：{live2d_names}")

                data_json = {}
                for line in live2d_names:
                    data_json[line] = line
                select_live2d_name = ui.select(
                    label='模型名',
                    options=data_json,
                    value=config.get("live2d", "name")
                ).style("width:150px")

        mapping["live2d"] = {
            "enable": (switch_live2d_enable, 'bool'),
            "port": (input_live2d_port, 'int'),
            "name": (select_live2d_name, 'str'),
        }

    if config.get("webui", "show_card", "visual_body", "EasyAIVtuber"):
        with ui.card().style(card_css):
            ui.label("EasyAIVtuber")
            with ui.row():
                input_EasyAIVtuber_api_ip_port = ui.input(
                    label='API地址',
                    value=config.get("EasyAIVtuber", "api_ip_port"),
                    placeholder='对接EasyAIVtuber应用监听的ip和端口',
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                )

        mapping["EasyAIVtuber"] = {
            "api_ip_port": (input_EasyAIVtuber_api_ip_port, 'str'),
        }

    if config.get("webui", "show_card", "visual_body", "digital_human_video_player"):
        with ui.card().style(card_css):
            ui.label("数字人视频播放器")
            with ui.row():
                select_digital_human_video_player_type = ui.select(
                    label='类型',
                    options={
                        "easy_wav2lip": "easy_wav2lip",
                        "sadtalker": "sadtalker",
                        "genefaceplusplus": "GeneFacePlusPlus",
                        "musetalk": "MuseTalk",
                        "anitalker": "AniTalker",
                    },
                    value=config.get("digital_human_video_player", "type")
                ).style("width:150px")
                input_digital_human_video_player_api_ip_port = ui.input(
                    label='API地址',
                    value=config.get("digital_human_video_player", "api_ip_port"),
                    placeholder='对接 数字人视频播放器 监听的ip和端口',
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                )

        mapping["digital_human_video_player"] = {
            "type": (select_digital_human_video_player_type, 'str'),
            "api_ip_port": (input_digital_human_video_player_api_ip_port, 'str'),
        }

    if config.get("webui", "show_card", "visual_body", "metahuman_stream"):
        with ui.card().style(card_css):
            ui.label("metahuman_stream")
            with ui.row():
                select_metahuman_stream_type = ui.select(
                    label='类型',
                    options={'ernerf': 'ernerf', 'musetalk': 'musetalk', 'wav2lip': 'wav2lip'},
                    value=config.get("metahuman_stream", "type")
                ).style("width:100px;")
                input_metahuman_stream_api_ip_port = ui.input(
                    label='API地址',
                    value=config.get("metahuman_stream", "api_ip_port"),
                    placeholder='metahuman_stream应用启动API后，监听的ip和端口',
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                )

        mapping["metahuman_stream"] = {
            "type": (select_metahuman_stream_type, 'str'),
            "api_ip_port": (input_metahuman_stream_api_ip_port, 'str'),
        }

    if config.get("webui", "show_card", "visual_body", "live2d_TTS_LLM_GPT_SoVITS_Vtuber"):
        with ui.card().style(card_css):
            ui.label("live2d_TTS_LLM_GPT_SoVITS_Vtuber")
            with ui.row():
                input_live2d_TTS_LLM_GPT_SoVITS_Vtuber_api_ip_port = ui.input(
                    label='API地址',
                    value=config.get("live2d_TTS_LLM_GPT_SoVITS_Vtuber", "api_ip_port"),
                    placeholder='live2d_TTS_LLM_GPT_SoVITS_Vtuber应用启动API后，监听的ip和端口',
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                )

        mapping["live2d_TTS_LLM_GPT_SoVITS_Vtuber"] = {
            "api_ip_port": (input_live2d_TTS_LLM_GPT_SoVITS_Vtuber_api_ip_port, 'str'),
        }

    if config.get("webui", "show_card", "visual_body", "xuniren"):
        with ui.card().style(card_css):
            ui.label("xuniren")
            with ui.row():
                input_xuniren_api_ip_port = ui.input(
                    label='API地址',
                    value=config.get("xuniren", "api_ip_port"),
                    placeholder='xuniren应用启动API后，监听的ip和端口',
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                )

        mapping["xuniren"] = {
            "api_ip_port": (input_xuniren_api_ip_port, 'str'),
        }

    if config.get("webui", "show_card", "visual_body", "unity"):
        with ui.card().style(card_css):
            ui.label("Unity")
            with ui.row():
                input_unity_api_ip_port = ui.input(
                    label='API地址',
                    value=config.get("unity", "api_ip_port"),
                    placeholder='对接Unity应用使用的HTTP中转站监听的ip和端口',
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                )
                input_unity_password = ui.input(label='密码', value=config.get("unity", "password"), placeholder='对接Unity应用使用的HTTP中转站的密码')

        mapping["unity"] = {
            "api_ip_port": (input_unity_api_ip_port, 'str'),
            "password": (input_unity_password, 'str'),
        }

    def write_live2d_model_name(config_data):
        if config.get("webui", "show_card", "visual_body", "live2d"):
            tmp_str = f"var model_name = \"{select_live2d_name.value}\";"
            common.write_content_to_file("Live2D/js/model_name.js", tmp_str)

    return PageConfig(mapping=mapping, on_save=write_live2d_model_name)
