"""变声页：DDSP-SVC 与 SO-VITS-SVC 参数。"""
from nicegui import ui

from webui_app.pages import PageConfig


def build_svc_tab(config, common, card_css, switch_internal_css):
    mapping = {}

    if config.get("webui", "show_card", "svc", "ddsp_svc"):
        with ui.card().style(card_css):
            ui.label("DDSP-SVC")
            with ui.row():
                switch_ddsp_svc_enable = ui.switch('启用', value=config.get("ddsp_svc", "enable")).style(switch_internal_css)
                input_ddsp_svc_config_path = ui.input(label='配置文件路径', placeholder='模型配置文件config.yaml的路径(此处可以不配置，暂时没有用到)', value=config.get("ddsp_svc", "config_path"))
                input_ddsp_svc_config_path.style("width:400px")

                input_ddsp_svc_api_ip_port = ui.input(
                    label='API地址',
                    placeholder='flask_api服务运行的ip端口，例如：http://127.0.0.1:6844',
                    value=config.get("ddsp_svc", "api_ip_port"),
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                )
                input_ddsp_svc_api_ip_port.style("width:400px")
                input_ddsp_svc_fSafePrefixPadLength = ui.input(label='安全前缀填充长度', placeholder='安全前缀填充长度，不知道干啥用，默认为0', value=config.get("ddsp_svc", "fSafePrefixPadLength"))
                input_ddsp_svc_fSafePrefixPadLength.style("width:300px")
            with ui.row():
                input_ddsp_svc_fPitchChange = ui.input(label='变调', placeholder='音调设置，默认为0', value=config.get("ddsp_svc", "fPitchChange"))
                input_ddsp_svc_fPitchChange.style("width:300px")
                input_ddsp_svc_sSpeakId = ui.input(label='说话人ID', placeholder='说话人ID，需要和模型数据对应，默认为0', value=config.get("ddsp_svc", "sSpeakId"))
                input_ddsp_svc_sSpeakId.style("width:400px")

                input_ddsp_svc_sampleRate = ui.input(label='采样率', placeholder='DAW所需的采样率，默认为44100', value=config.get("ddsp_svc", "sampleRate"))
                input_ddsp_svc_sampleRate.style("width:300px")

        mapping["ddsp_svc"] = {
            "enable": (switch_ddsp_svc_enable, 'bool'),
            "config_path": (input_ddsp_svc_config_path, 'str'),
            "api_ip_port": (input_ddsp_svc_api_ip_port, 'str'),
            "fSafePrefixPadLength": (input_ddsp_svc_fSafePrefixPadLength, 'float'),
            "fPitchChange": (input_ddsp_svc_fPitchChange, 'float'),
            "sSpeakId": (input_ddsp_svc_sSpeakId, 'int'),
            "sampleRate": (input_ddsp_svc_sampleRate, 'int'),
        }

    if config.get("webui", "show_card", "svc", "so_vits_svc"):
        with ui.card().style(card_css):
            ui.label("SO-VITS-SVC")
            with ui.row():
                switch_so_vits_svc_enable = ui.switch('启用', value=config.get("so_vits_svc", "enable")).style(switch_internal_css)
                input_so_vits_svc_config_path = ui.input(label='配置文件路径', placeholder='模型配置文件config.json的路径', value=config.get("so_vits_svc", "config_path"))
                input_so_vits_svc_config_path.style("width:400px")
            with ui.grid(columns=2):
                input_so_vits_svc_api_ip_port = ui.input(
                    label='API地址',
                    placeholder='flask_api_full_song服务运行的ip端口，例如：http://127.0.0.1:1145',
                    value=config.get("so_vits_svc", "api_ip_port"),
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                )
                input_so_vits_svc_api_ip_port.style("width:400px")
                input_so_vits_svc_spk = ui.input(label='说话人', placeholder='说话人，需要和配置文件内容对应', value=config.get("so_vits_svc", "spk"))
                input_so_vits_svc_spk.style("width:400px")
                input_so_vits_svc_tran = ui.input(label='音调', placeholder='音调设置，默认为1', value=config.get("so_vits_svc", "tran"))
                input_so_vits_svc_tran.style("width:300px")
                input_so_vits_svc_wav_format = ui.input(label='输出音频格式', placeholder='音频合成后输出的格式', value=config.get("so_vits_svc", "wav_format"))
                input_so_vits_svc_wav_format.style("width:300px")

        mapping["so_vits_svc"] = {
            "enable": (switch_so_vits_svc_enable, 'bool'),
            "config_path": (input_so_vits_svc_config_path, 'str'),
            "api_ip_port": (input_so_vits_svc_api_ip_port, 'str'),
            "spk": (input_so_vits_svc_spk, 'str'),
            "tran": (input_so_vits_svc_tran, 'float'),
            "wav_format": (input_so_vits_svc_wav_format, 'str'),
        }

    return PageConfig(mapping=mapping)
