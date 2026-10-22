"""文本转语音页：各家 TTS 参数与试听。"""
import traceback
from urllib.parse import urljoin

from nicegui import ui

from utils.my_log import logger
from webui_app.helpers import AUDIO_SYNTHESIS_TYPE_OPTIONS
from webui_app.pages import PageConfig


def build_tts_tab(config, common, audio, card_css, switch_internal_css,
                  button_internal_color, button_internal_css):
    async def gpt_sovits_set_model():
        try:
            if select_gpt_sovits_type.value == "v2_api_0821":
                async def set_gpt_weights():
                    try:

                        API_URL = urljoin(input_gpt_sovits_api_ip_port.value, '/set_gpt_weights?weights_path=' + input_gpt_sovits_gpt_model_path.value)
                        
                        # logger.debug(API_URL)

                        resp_json = await common.send_async_request(API_URL, "GET", None, resp_data_type="json")

                        if resp_json is None:
                            content = f"gpt_weights：{input_gpt_sovits_gpt_model_path.value} 加载失败，请查看双方日志排查问题"
                            logger.error(content)
                            return False
                        else:
                            if resp_json["message"] == "success":
                                content = f"gpt_weights：{input_gpt_sovits_gpt_model_path.value} 加载成功"
                                logger.info(content)
                            else:
                                content = f"gpt_weights：{input_gpt_sovits_gpt_model_path.value} 加载失败，请查看双方日志排查问题"
                                logger.error(content)
                                return False
                        
                        return True
                    except Exception as e:
                        logger.error(traceback.format_exc())
                        logger.error(f'gpt_sovits未知错误: {e}')
                        return False

                async def set_sovits_weights():
                    try:

                        API_URL = urljoin(input_gpt_sovits_api_ip_port.value, '/set_sovits_weights?weights_path=' + input_gpt_sovits_sovits_model_path.value)
                        
                        resp_json = await common.send_async_request(API_URL, "GET", None, resp_data_type="json")

                        if resp_json is None:
                            content = f"sovits_weights：{input_gpt_sovits_sovits_model_path.value} 加载失败，请查看双方日志排查问题"
                            logger.error(content)
                            return False
                        else:
                            if resp_json["message"] == "success":
                                content = f"sovits_weights：{input_gpt_sovits_sovits_model_path.value} 加载成功"
                                logger.info(content)
                            else:
                                content = f"sovits_weights：{input_gpt_sovits_sovits_model_path.value} 加载失败，请查看双方日志排查问题"
                                logger.error(content)
                                return False
                        
                        return True
                    except Exception as e:
                        logger.error(traceback.format_exc())
                        logger.error(f'sovits_weights未知错误: {e}')
                        return False
            
                if await set_gpt_weights() and await set_sovits_weights():
                    content = "gpt_sovits模型加载成功"
                    logger.info(content)
                    ui.notify(position="top", type="positive", message=content)
                else:
                    content = "gpt_sovits模型加载失败，请查看双方日志排查问题"
                    logger.error(content)
                    ui.notify(position="top", type="negative", message=content)
            else:
                API_URL = urljoin(input_gpt_sovits_api_ip_port.value, '/set_model')

                data_json = {
                    "gpt_model_path": input_gpt_sovits_gpt_model_path.value,
                    "sovits_model_path": input_gpt_sovits_sovits_model_path.value
                }
                
                resp_data = await common.send_async_request(API_URL, "POST", data_json, resp_data_type="content")

                if resp_data is None:
                    content = "gpt_sovits加载模型失败，请查看双方日志排查问题"
                    logger.error(content)
                    ui.notify(position="top", type="negative", message=content)
                else:
                    content = "gpt_sovits加载模型成功"
                    logger.info(content)
                    ui.notify(position="top", type="positive", message=content)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f'gpt_sovits未知错误: {e}')
            ui.notify(position="top", type="negative", message=f'gpt_sovits未知错误: {e}')


    # 通用-合成试听音频
    async def tts_common_audio_synthesis():
        ui.notify(position="top", type="warning", message="音频合成中，将会阻塞其他任务运行，请勿做其他操作，查看日志情况，耐心等待")
        logger.warning("音频合成中，将会阻塞其他任务运行，请勿做其他操作，查看日志情况，耐心等待")
        
        content = input_tts_common_text.value
        audio_synthesis_type = select_tts_common_audio_synthesis_type.value

        # 使用本地配置进行音频合成，返回音频路径
        file_path = await audio.audio_synthesis_use_local_config(content, audio_synthesis_type)

        if file_path:
            logger.info(f"音频合成成功，存储于：{file_path}")
            ui.notify(position="top", type="positive", message=f"音频合成成功，存储于：{file_path}")
        else:
            logger.error(f"音频合成失败！请查看日志排查问题")
            ui.notify(position="top", type="negative", message=f"音频合成失败！请查看日志排查问题")
            return

        def clear_tts_common_audio_card(file_path):
            tts_common_audio_card.clear()
            if common.del_file(file_path):
                ui.notify(position="top", type="positive", message=f"删除文件成功：{file_path}")
            else:
                ui.notify(position="top", type="negative", message=f"删除文件失败：{file_path}")
        
        # 清空card
        tts_common_audio_card.clear()
        tmp_label = ui.label(f"音频合成成功，存储于：{file_path}")
        tmp_label.move(tts_common_audio_card)
        audio_tmp = ui.audio(src=file_path)
        audio_tmp.move(tts_common_audio_card)
        button_audio_del = ui.button('删除音频', on_click=lambda: clear_tts_common_audio_card(file_path), color=button_internal_color).style(button_internal_css)
        button_audio_del.move(tts_common_audio_card)
        
        
    with ui.card().style(card_css):
        ui.label("合成测试（只是测试，若确认使用此TTS，请前往 通用配置 配置 语音合成）")
        with ui.row():
            select_tts_common_audio_synthesis_type = ui.select(
                label='语音合成', 
                options=AUDIO_SYNTHESIS_TYPE_OPTIONS, 
                value=config.get("audio_synthesis_type")
            ).style("width:200px;")
            input_tts_common_text = ui.input(label='待合成音频内容', placeholder='此处填写待合成的音频文本内容', value="此处填写待合成的音频文本内容，用于试听效果，类型切换不需要保存即可生效。").style("width:350px;")
            button_tts_common_audio_synthesis = ui.button('试听', on_click=lambda: tts_common_audio_synthesis(), color=button_internal_color).style(button_internal_css)
        tts_common_audio_card = ui.card()
        with tts_common_audio_card.style(card_css):
            with ui.row():
                ui.label("此处显示生成的音频，仅显示最新合成的音频，可以在此操作删除合成的音频")

    if config.get("webui", "show_card", "tts", "edge-tts"):
        with ui.card().style(card_css):
            ui.label("Edge-TTS")
            with ui.row():
                with open('data/edge-tts-voice-list.txt', 'r') as file:
                    file_content = file.read()
                # 按行分割内容，并去除每行末尾的换行符
                lines = file_content.strip().split('\n')
                data_json = {}
                for line in lines:
                    data_json[line] = line
                select_edge_tts_voice = ui.select(
                    label='说话人', 
                    options=data_json, 
                    value=config.get("edge-tts", "voice")
                )

                input_edge_tts_rate = ui.input(label='语速增益', placeholder='语速增益 默认是 +0%，可以增减，注意 + - %符合别搞没了，不然会影响语音合成', value=config.get("edge-tts", "rate")).style("width:150px;").tooltip("语速增益 默认是 +0%，可以增减，注意 + - %符合别搞没了，不然会影响语音合成")

                input_edge_tts_volume = ui.input(label='音量增益', placeholder='音量增益 默认是 +0%，可以增减，注意 + - %符合别搞没了，不然会影响语音合成', value=config.get("edge-tts", "volume")).style("width:150px;").tooltip("音量增益 默认是 +0%，可以增减，注意 + - %符合别搞没了，不然会影响语音合成")
                input_edge_tts_proxy = ui.input(label='HTTP代理地址', placeholder='例：http://127.0.0.1:10809', value=config.get("edge-tts", "proxy")).style("width:300px;").tooltip("根据您的实际代理配置，例：http://127.0.0.1:10809")
                
    if config.get("webui", "show_card", "tts", "vits"):
        with ui.card().style(card_css):
            ui.label("VITS-Simple-API")
            with ui.row():
                select_vits_type = ui.select(
                    label='类型', 
                    options={'vits': 'vits', 'bert_vits2': 'bert_vits2', 'gpt_sovits': 'gpt_sovits'}, 
                    value=config.get("vits", "type")
                ).style("width:200px;")
                input_vits_config_path = ui.input(label='配置文件路径', placeholder='模型配置文件存储路径', value=config.get("vits", "config_path")).style("width:200px;")

                input_vits_api_ip_port = ui.input(
                    label='API地址', 
                    placeholder='vits-simple-api启动后监听的ip端口地址', 
                    value=config.get("vits", "api_ip_port"),
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                ).style("width:300px;")
            with ui.row():
                # input_vits_id = ui.input(label='说话人ID', placeholder='API启动时会给配置文件重新划分id，一般为拼音顺序排列，从0开始', value=config.get("vits", "id")).style("width:200px;")
                select_vits_id = ui.select(
                    label='说话人ID', 
                    options={config.get("vits", "id"): config.get("vits", "id")}, 
                    value=config.get("vits", "id")
                ).style("width:200px;")

                async def vits_get_speaker_id():
                    try:
                        API_URL = urljoin(input_vits_api_ip_port.value, '/voice/speakers')

                        resp_data = await common.send_async_request(API_URL, "GET", resp_data_type="json")

                        if resp_data is None:
                            content = "vits-simple-api检索说话人失败，请查看双方日志排查问题"
                            logger.error(content)
                            ui.notify(position="top", type="negative", message=content)
                        else:
                            content = "vits-simple-api检索说话人成功"
                            logger.info(content)
                            ui.notify(position="top", type="positive", message=content)

                            data_json = {}
                            if select_vits_type.value == "vits":
                                for vits_info in resp_data["VITS"]:
                                    data_json[vits_info['id']] = vits_info['name']
                                select_vits_id.set_options(data_json, value=int(config.get("vits", "id")))
                            elif select_vits_type.value == "bert_vits2":
                                for vits_info in resp_data["BERT-VITS2"]:
                                    data_json[vits_info['id']] = vits_info['name']
                                select_vits_id.set_options(data_json, value=int(config.get("vits", "id")))
                            elif select_vits_type.value == "gpt_sovits":
                                for vits_info in resp_data["GPT-SOVITS"]:
                                    data_json[vits_info['id']] = vits_info['name']
                                select_vits_gpt_sovits_id.set_options(data_json, value=int(config.get("vits", "gpt_sovits", "id")))
                            
                    except Exception as e:
                        logger.error(traceback.format_exc())
                        logger.error(f'vits-simple-api未知错误: {e}')
                        ui.notify(position="top", type="negative", message=f'vits-simple-api未知错误: {e}')

                
                select_vits_lang = ui.select(
                    label='语言', 
                    options={'自动': '自动', '中文': '中文', '英文': '英文', '日文': '日文'}, 
                    value=config.get("vits", "lang")
                ).style("width:100px;")
                input_vits_length = ui.input(label='语音长度', placeholder='调节语音长度，相当于调节语速，该数值越大语速越慢', value=config.get("vits", "length")).style("width:200px;")

                button_vits_get_speaker_id = ui.button('检索说话人', on_click=lambda: vits_get_speaker_id(), color=button_internal_color).style(button_internal_css)
        
            with ui.row():
                input_vits_noise = ui.input(label='噪声', placeholder='控制感情变化程度', value=config.get("vits", "noise")).style("width:200px;")
            
                input_vits_noisew = ui.input(label='噪声偏差', placeholder='控制音素发音长度', value=config.get("vits", "noisew")).style("width:200px;")

                input_vits_max = ui.input(label='分段阈值', placeholder='按标点符号分段，加起来大于max时为一段文本。max<=0表示不分段。', value=config.get("vits", "max")).style("width:200px;")
                input_vits_format = ui.input(label='音频格式', placeholder='支持wav,ogg,silk,mp3,flac', value=config.get("vits", "format")).style("width:200px;")

                input_vits_sdp_radio = ui.input(label='SDP/DP混合比', placeholder='SDP/DP混合比：SDP在合成时的占比，理论上此比率越高，合成的语音语调方差越大。', value=config.get("vits", "sdp_radio")).style("width:200px;")

            with ui.expansion('GPT-SOVITS', icon="settings", value=True).classes('w-full'):
                with ui.row():
                    select_vits_gpt_sovits_id = ui.select(
                        label='说话人ID', 
                        options={config.get("vits", "gpt_sovits", "id"): config.get("vits", "gpt_sovits", "id")}, 
                        value=config.get("vits", "gpt_sovits", "id")
                    ).style("width:200px;")

                    select_vits_gpt_sovits_lang = ui.select(
                        label='语言', 
                        options={'auto': '自动', 'zh': '中文', 'jp': '英文', 'en': '日文'}, 
                        value=config.get("vits", "gpt_sovits", "lang")
                    ).style("width:100px;")
                    input_vits_gpt_sovits_format = ui.input(label='音频格式', value=config.get("vits", "gpt_sovits", "format"), placeholder='支持wav,ogg,silk,mp3,flac').style("width:100px;")
                    input_vits_gpt_sovits_segment_size = ui.input(label='segment_size', value=config.get("vits", "gpt_sovits", "segment_size"), placeholder='segment_size').style("width:100px;")
                    input_vits_gpt_sovits_reference_audio = ui.input(label='参考音频路径', value=config.get("vits", "gpt_sovits", "reference_audio"), placeholder='参考音频路径').style("width:200px;")
                    input_vits_gpt_sovits_prompt_text = ui.input(label='参考音频文本内容', value=config.get("vits", "gpt_sovits", "prompt_text"), placeholder='参考音频文本内容').style("width:200px;")
                    select_vits_gpt_sovits_prompt_lang = ui.select(
                        label='参考音频语言', 
                        options={'auto': '自动', 'zh': '中文', 'jp': '英文', 'en': '日文'}, 
                        value=config.get("vits", "gpt_sovits", "prompt_lang")
                    ).style("width:150px;")
                with ui.row():
                    input_vits_gpt_sovits_top_k = ui.input(label='top_k', value=config.get("vits", "gpt_sovits", "top_k"), placeholder='top_k').style("width:100px;")
                    input_vits_gpt_sovits_top_p = ui.input(label='top_p', value=config.get("vits", "gpt_sovits", "top_p"), placeholder='top_p').style("width:100px;")
                    input_vits_gpt_sovits_temperature = ui.input(label='temperature', value=config.get("vits", "gpt_sovits", "temperature"), placeholder='temperature').style("width:100px;")
                    input_vits_gpt_sovits_preset = ui.input(label='preset', value=config.get("vits", "gpt_sovits", "preset"), placeholder='preset').style("width:100px;")
                    

    if config.get("webui", "show_card", "tts", "bert_vits2"):
        with ui.card().style(card_css):
            ui.label("bert_vits2")
            with ui.row():
                select_bert_vits2_type = ui.select(
                    label='类型', 
                    options={'hiyori': 'hiyori', '刘悦-中文特化API': '刘悦-中文特化API'}, 
                    value=config.get("bert_vits2", "type")
                ).style("width:200px;")
                
            with ui.expansion('hiyori', icon="settings", value=True).classes('w-full'):
                with ui.row():
                    input_bert_vits2_api_ip_port = ui.input(
                        label='API地址', 
                        placeholder='bert_vits2启动后Hiyori UI后监听的ip端口地址', 
                        value=config.get("bert_vits2", "api_ip_port"),
                        validation={
                            '请输入正确格式的URL': lambda value: common.is_url_check(value),
                        }
                    ).style("width:300px;")
                    input_bert_vits2_model_id = ui.input(label='模型ID', placeholder='给配置文件重新划分id，一般为拼音顺序排列，从0开始', value=config.get("bert_vits2", "model_id")).style("width:200px;")
                    input_bert_vits2_speaker_name = ui.input(label='说话人名称', value=config.get("bert_vits2", "speaker_name"), placeholder='配置文件中，对应的说话人的名称').style("width:200px;")
                    input_bert_vits2_speaker_id = ui.input(label='说话人ID', value=config.get("bert_vits2", "speaker_id"), placeholder='给配置文件重新划分id，一般为拼音顺序排列，从0开始').style("width:200px;")
                    
                    select_bert_vits2_language = ui.select(
                        label='语言', 
                        options={'auto': '自动', 'ZH': '中文', 'JP': '日文', 'EN': '英文'}, 
                        value=config.get("bert_vits2", "language")
                    ).style("width:100px;")
                    input_bert_vits2_length = ui.input(label='语音长度', placeholder='调节语音长度，相当于调节语速，该数值越大语速越慢', value=config.get("bert_vits2", "length")).style("width:200px;")

                with ui.row():
                    input_bert_vits2_noise = ui.input(label='噪声', value=config.get("bert_vits2", "noise"), placeholder='控制感情变化程度').style("width:200px;")
                    input_bert_vits2_noisew = ui.input(label='噪声偏差', value=config.get("bert_vits2", "noisew"), placeholder='控制音素发音长度').style("width:200px;")
                    input_bert_vits2_sdp_radio = ui.input(label='SDP/DP混合比', value=config.get("bert_vits2", "sdp_radio"), placeholder='SDP/DP混合比：SDP在合成时的占比，理论上此比率越高，合成的语音语调方差越大。').style("width:200px;")
                with ui.row():
                    input_bert_vits2_emotion = ui.input(label='emotion', value=config.get("bert_vits2", "emotion"), placeholder='emotion').style("width:200px;")
                    input_bert_vits2_style_text = ui.input(label='风格文本', value=config.get("bert_vits2", "style_text"), placeholder='style_text').style("width:200px;")
                    input_bert_vits2_style_weight = ui.input(label='风格权重', value=config.get("bert_vits2", "style_weight"), placeholder='主文本和辅助文本的bert混合比率，0表示仅主文本，1表示仅辅助文本0.7').style("width:200px;")
                    switch_bert_vits2_auto_translate = ui.switch('自动翻译', value=config.get("bert_vits2", "auto_translate")).style(switch_internal_css)
                    switch_bert_vits2_auto_split = ui.switch('自动切分', value=config.get("bert_vits2", "auto_split")).style(switch_internal_css)
            with ui.expansion('刘悦-中文特化API', icon="settings", value=True).classes('w-full'):
                with ui.row():
                    input_bert_vits2_liuyue_zh_api_api_ip_port = ui.input(
                        label='API地址', 
                        placeholder='接口服务后监听的ip端口地址', 
                        value=config.get("bert_vits2", "刘悦-中文特化API", "api_ip_port"),
                        validation={
                            '请输入正确格式的URL': lambda value: common.is_url_check(value),
                        }
                    ).style("width:300px;")
                    input_bert_vits2_liuyue_zh_api_speaker = ui.input(label='说话人名称', value=config.get("bert_vits2", "刘悦-中文特化API", "speaker"), placeholder='配置文件中，对应的说话人的名称').style("width:200px;")
                    
                    select_bert_vits2_liuyue_zh_api_language = ui.select(
                        label='语言', 
                        options={'auto': '自动', 'ZH': '中文', 'JP': '日文', 'EN': '英文'}, 
                        value=config.get("bert_vits2", "刘悦-中文特化API", "language")
                    ).style("width:100px;")
                    input_bert_vits2_liuyue_zh_api_length_scale = ui.input(label='语音长度', placeholder='调节语音长度，相当于调节语速，该数值越大语速越慢', value=config.get("bert_vits2", "刘悦-中文特化API", "length_scale")).style("width:200px;")
                    
                with ui.row():
                    input_bert_vits2_liuyue_zh_api_interval_between_para = ui.input(label='interval_between_para', value=config.get("bert_vits2", "刘悦-中文特化API", "interval_between_para"), placeholder='interval_between_para').style("width:200px;")
                    input_bert_vits2_liuyue_zh_api_interval_between_sent = ui.input(label='interval_between_sent', value=config.get("bert_vits2", "刘悦-中文特化API", "interval_between_sent"), placeholder='interval_between_sent').style("width:200px;")
                   
                    input_bert_vits2_liuyue_zh_api_noise_scale = ui.input(label='噪声', value=config.get("bert_vits2", "刘悦-中文特化API", "noise_scale"), placeholder='控制感情变化程度').style("width:200px;")
                    input_bert_vits2_liuyue_zh_api_noise_scale_w = ui.input(label='噪声偏差', value=config.get("bert_vits2", "刘悦-中文特化API", "noise_scale_w"), placeholder='控制音素发音长度').style("width:200px;")
                    input_bert_vits2_liuyue_zh_api_sdp_radio = ui.input(label='SDP/DP混合比', value=config.get("bert_vits2", "刘悦-中文特化API", "sdp_radio"), placeholder='SDP/DP混合比：SDP在合成时的占比，理论上此比率越高，合成的语音语调方差越大。').style("width:200px;")
                with ui.row():
                    input_bert_vits2_liuyue_zh_api_emotion = ui.input(label='emotion', value=config.get("bert_vits2", "刘悦-中文特化API", "emotion"), placeholder='emotion').style("width:200px;")
                    input_bert_vits2_liuyue_zh_api_style_text = ui.input(label='风格文本', value=config.get("bert_vits2", "刘悦-中文特化API", "style_text"), placeholder='style_text').style("width:200px;")
                    input_bert_vits2_liuyue_zh_api_style_weight = ui.input(label='风格权重', value=config.get("bert_vits2", "刘悦-中文特化API", "style_weight"), placeholder='主文本和辅助文本的bert混合比率，0表示仅主文本，1表示仅辅助文本0.7').style("width:200px;")
                    switch_bert_vits2_cut_by_sent = ui.switch('cut_by_sent', value=config.get("bert_vits2", "刘悦-中文特化API", "cut_by_sent")).style(switch_internal_css)
                    
    if config.get("webui", "show_card", "tts", "vits_fast"):
        with ui.card().style(card_css):
            ui.label("VITS-Fast")
            with ui.row():
                input_vits_fast_config_path = ui.input(label='配置文件路径', placeholder='配置文件的路径，例如：E:\\inference\\finetune_speaker.json', value=config.get("vits_fast", "config_path"))

                input_vits_fast_api_ip_port = ui.input(
                    label='API地址', 
                    placeholder='推理服务运行的链接（需要完整的URL）', 
                    value=config.get("vits_fast", "api_ip_port"),
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                )
                input_vits_fast_character = ui.input(label='说话人', placeholder='选择的说话人，配置文件中的speaker中的其中一个', value=config.get("vits_fast", "character"))

                select_vits_fast_language = ui.select(
                    label='语言', 
                    options={'自动识别': '自动识别', '日本語': '日本語', '简体中文': '简体中文', 'English': 'English', 'Mix': 'Mix'}, 
                    value=config.get("vits_fast", "language")
                )
                input_vits_fast_speed = ui.input(label='语速', placeholder='语速，默认为1', value=config.get("vits_fast", "speed"))
    
    if config.get("webui", "show_card", "tts", "elevenlabs"):
        with ui.card().style(card_css):
            ui.label("elevenlabs")
            with ui.row():
                input_elevenlabs_api_key = ui.input(label='api密钥', placeholder='elevenlabs密钥，可以不填，默认也有一定额度的免费使用权限，具体多少不知道', value=config.get("elevenlabs", "api_key"))

                input_elevenlabs_voice = ui.input(label='说话人', placeholder='选择的说话人名', value=config.get("elevenlabs", "voice"))

                input_elevenlabs_model = ui.input(label='模型', placeholder='选择的模型', value=config.get("elevenlabs", "model"))
    
    
    if config.get("webui", "show_card", "tts", "openai_tts"): 
        with ui.card().style(card_css):
            ui.label("OpenAI TTS")
            with ui.row():
                select_openai_tts_type = ui.select(
                    label='类型', 
                    options={'api': 'api', 'huggingface': 'huggingface'}, 
                    value=config.get("openai_tts", "type")
                ).style("width:200px;")
                input_openai_tts_api_ip_port = ui.input(
                    label='API地址', 
                    value=config.get("openai_tts", "api_ip_port"), 
                    placeholder='huggingface上对应项目的API地址',
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                ).style("width:200px;")
            with ui.row():
                select_openai_tts_model = ui.select(
                    label='模型', 
                    options={'tts-1': 'tts-1', 'tts-1-hd': 'tts-1-hd'}, 
                    value=config.get("openai_tts", "model")
                ).style("width:200px;")
                select_openai_tts_voice = ui.select(
                    label='说话人', 
                    options={'alloy': 'alloy', 'echo': 'echo', 'fable': 'fable', 'onyx': 'onyx', 'nova': 'nova', 'shimmer': 'shimmer'}, 
                    value=config.get("openai_tts", "voice")
                ).style("width:200px;")
                input_openai_tts_api_key = ui.input(label='api key', value=config.get("openai_tts", "api_key"), placeholder='OpenAI API KEY').style("width:200px;")
          
    if config.get("webui", "show_card", "tts", "gradio_tts"): 
        with ui.card().style(card_css):
            ui.label("Gradio")
            with ui.row():
                textarea_gradio_tts_request_parameters = ui.textarea(label='请求参数', value=config.get("gradio_tts", "request_parameters"), placeholder='一定要注意格式啊！{content}用于替换待合成的文本。\nurl是请求地址；\nfn_index是api对应的索引；\ndata_analysis是数据解析规则，暂时只支持元组和列表数据的index索引，请参考模板进行配置\n键不影响请求，需要注意的是参数顺序需要和API请求保持一致\n那么数据可以用json库将dict转成str，这样再用来配置就可靠很多').style("width:800px;")
   
    if config.get("webui", "show_card", "tts", "gpt_sovits"): 
        with ui.card().style(card_css):
            ui.label("GPT-SoVITS")
            with ui.row():
                select_gpt_sovits_type = ui.select(
                    label='API类型', 
                    options={
                        'api':'api', 
                        'api_0322':'api_0322', 
                        'api_0706':'api_0706', 
                        'v2_api_0821': 'v2_api_0821', 
                        'webtts':'WebTTS', 
                        'gradio_0322':'gradio_0322',
                    }, 
                    value=config.get("gpt_sovits", "type")
                ).style("width:100px;")
                input_gpt_sovits_gradio_ip_port = ui.input(
                    label='Gradio API地址', 
                    value=config.get("gpt_sovits", "gradio_ip_port"), 
                    placeholder='官方webui程序启动后gradio监听的地址',
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                ).style("width:200px;")
                input_gpt_sovits_api_ip_port = ui.input(
                    label='API地址（http）', 
                    value=config.get("gpt_sovits", "api_ip_port"), 
                    placeholder='官方API程序启动后监听的地址',
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                ).style("width:200px;")
                
            
            with ui.row():
                input_gpt_sovits_gpt_model_path = ui.input(
                    label='GPT模型路径', 
                    value=config.get("gpt_sovits", "gpt_model_path"), 
                    placeholder='GPT模型路径，填绝对路径'
                ).style("width:300px;")
                input_gpt_sovits_sovits_model_path = ui.input(label='SOVITS模型路径', value=config.get("gpt_sovits", "sovits_model_path"), placeholder='SOVITS模型路径，填绝对路径').style("width:300px;")
                button_gpt_sovits_set_model = ui.button('加载模型', on_click=lambda: gpt_sovits_set_model(), color=button_internal_color).style(button_internal_css)
            
            with ui.card().style(card_css):
                ui.label("api")
                with ui.row():
                    input_gpt_sovits_ref_audio_path = ui.input(label='参考音频路径', value=config.get("gpt_sovits", "ref_audio_path"), placeholder='参考音频路径，建议填绝对路径').style("width:300px;")
                    input_gpt_sovits_prompt_text = ui.input(label='参考音频的文本', value=config.get("gpt_sovits", "prompt_text"), placeholder='参考音频的文本').style("width:200px;")
                    select_gpt_sovits_prompt_language = ui.select(
                        label='参考音频的语种', 
                        options={'中文':'中文', '日文':'日文', '英文':'英文'}, 
                        value=config.get("gpt_sovits", "prompt_language")
                    ).style("width:150px;")
                    select_gpt_sovits_language = ui.select(
                        label='需要合成的语种', 
                        options={'自动识别':'自动识别', '中文':'中文', '日文':'日文', '英文':'英文'}, 
                        value=config.get("gpt_sovits", "language")
                    ).style("width:150px;")
                    select_gpt_sovits_cut = ui.select(
                        label='语句切分', 
                        options={
                            '不切':'不切', 
                            '凑四句一切':'凑四句一切', 
                            '凑50字一切':'凑50字一切', 
                            '按中文句号。切':'按中文句号。切', 
                            '按英文句号.切':'按英文句号.切',
                            '按标点符号切':'按标点符号切'
                        }, 
                        value=config.get("gpt_sovits", "cut")
                    ).style("width:200px;")
            
            with ui.card().style(card_css):
                ui.label("api_0322 | gradio_0322")
                with ui.row():
                    input_gpt_sovits_api_0322_ref_audio_path = ui.input(label='参考音频路径', value=config.get("gpt_sovits", "api_0322", "ref_audio_path"), placeholder='参考音频路径，建议填绝对路径').style("width:300px;")
                    input_gpt_sovits_api_0322_prompt_text = ui.input(label='参考音频的文本', value=config.get("gpt_sovits", "api_0322", "prompt_text"), placeholder='参考音频的文本').style("width:200px;")
                    select_gpt_sovits_api_0322_prompt_lang = ui.select(
                        label='参考音频的语种', 
                        options={'中文':'中文', '日文':'日文', '英文':'英文'}, 
                        value=config.get("gpt_sovits", "api_0322", "prompt_lang")
                    ).style("width:150px;")
                    select_gpt_sovits_api_0322_text_lang = ui.select(
                        label='需要合成的语种', 
                        options={
                            '自动识别':'自动识别', 
                            '中文':'中文', 
                            '日文':'日文', 
                            '英文':'英文', 
                            '中英混合': '中英混合',
                            '日英混合': '日英混合',
                            '多语种混合': '多语种混合',
                        }, 
                        value=config.get("gpt_sovits", "api_0322", "text_lang")
                    ).style("width:150px;")
                    select_gpt_sovits_api_0322_text_split_method = ui.select(
                        label='语句切分', 
                        options={
                            '不切':'不切', 
                            '凑四句一切':'凑四句一切', 
                            '凑50字一切':'凑50字一切', 
                            '按中文句号。切':'按中文句号。切', 
                            '按英文句号.切':'按英文句号.切',
                            '按标点符号切':'按标点符号切'
                        }, 
                        value=config.get("gpt_sovits", "api_0322", "text_split_method")
                    ).style("width:200px;")
                with ui.row():
                    input_gpt_sovits_api_0322_top_k = ui.input(label='top_k', value=config.get("gpt_sovits", "api_0322", "top_k"), placeholder='top_k').style("width:100px;")
                    input_gpt_sovits_api_0322_top_p = ui.input(label='top_p', value=config.get("gpt_sovits", "api_0322", "top_p"), placeholder='top_p').style("width:100px;")
                    input_gpt_sovits_api_0322_temperature = ui.input(label='temperature', value=config.get("gpt_sovits", "api_0322", "temperature"), placeholder='temperature').style("width:100px;")
                    input_gpt_sovits_api_0322_batch_size = ui.input(label='batch_size', value=config.get("gpt_sovits", "api_0322", "batch_size"), placeholder='batch_size').style("width:100px;")
                    input_gpt_sovits_api_0322_speed_factor = ui.input(label='speed_factor', value=config.get("gpt_sovits", "api_0322", "speed_factor"), placeholder='speed_factor').style("width:100px;")
                    input_gpt_sovits_api_0322_fragment_interval = ui.input(label='分段间隔(秒)', value=config.get("gpt_sovits", "api_0322", "fragment_interval"), placeholder='fragment_interval').style("width:100px;")
                    switch_gpt_sovits_api_0322_split_bucket = ui.switch('split_bucket', value=config.get("gpt_sovits", "api_0322", "split_bucket")).style(switch_internal_css)
                    switch_gpt_sovits_api_0322_return_fragment = ui.switch('return_fragment', value=config.get("gpt_sovits", "api_0322", "return_fragment")).style(switch_internal_css)
            
            with ui.card().style(card_css):
                ui.label("api_0706")
                with ui.row():
                    input_gpt_sovits_api_0706_refer_wav_path = ui.input(label='参考音频路径', value=config.get("gpt_sovits", "api_0706", "refer_wav_path"), placeholder='参考音频路径，建议填绝对路径').style("width:300px;")
                    input_gpt_sovits_api_0706_prompt_text = ui.input(label='参考音频的文本', value=config.get("gpt_sovits", "api_0706", "prompt_text"), placeholder='参考音频的文本').style("width:200px;")
                    select_gpt_sovits_api_0706_prompt_language = ui.select(
                        label='参考音频的语种', 
                        options={'中文':'中文', '日文':'日文', '英文':'英文'}, 
                        value=config.get("gpt_sovits", "api_0706", "prompt_language")
                    ).style("width:150px;")
                    select_gpt_sovits_api_0706_text_language = ui.select(
                        label='需要合成的语种', 
                        options={
                            '自动识别':'自动识别', 
                            '中文':'中文', 
                            '日文':'日文', 
                            '英文':'英文', 
                            '中英混合': '中英混合',
                            '日英混合': '日英混合',
                            '多语种混合': '多语种混合',
                        }, 
                        value=config.get("gpt_sovits", "api_0706", "text_language")
                    ).style("width:150px;")
                    input_gpt_sovits_api_0706_cut_punc = ui.input(label='文本切分', value=config.get("gpt_sovits", "api_0706", "cut_punc"), placeholder='文本切分符号设定, 符号范围,.;?!、，。？！；：…').style("width:200px;")
            
            with ui.card().style(card_css):
                ui.label("v2_api_0821")
                with ui.row():
                    input_gpt_sovits_v2_api_0821_ref_audio_path = ui.input(label='参考音频路径', value=config.get("gpt_sovits", "v2_api_0821", "ref_audio_path"), placeholder='参考音频路径，建议填绝对路径').style("width:300px;")
                    input_gpt_sovits_v2_api_0821_prompt_text = ui.input(label='参考音频的文本', value=config.get("gpt_sovits", "v2_api_0821", "prompt_text"), placeholder='参考音频的文本').style("width:200px;")
                    select_gpt_sovits_v2_api_0821_prompt_lang = ui.select(
                        label='参考音频的语种', 
                        options={'zh':'中文', 'ja':'日文', 'en':'英文'}, 
                        value=config.get("gpt_sovits", "v2_api_0821", "prompt_lang")
                    ).style("width:150px;")
                    select_gpt_sovits_v2_api_0821_text_lang = ui.select(
                        label='需要合成的语种', 
                        options={
                            "all_zh": "中文",
                            "all_yue": "粤语",
                            "en": "英文",
                            "all_ja": "日文",
                            "all_ko": "韩文",
                            "zh": "中英混合",
                            "yue": "粤英混合",
                            "ja": "日英混合",
                            "ko": "韩英混合",
                            "auto": "多语种混合",    #多语种启动切分识别语种
                            "auto_yue": "多语种混合(粤语)",
                        }, 
                        value=config.get("gpt_sovits", "v2_api_0821", "text_lang")
                    ).style("width:150px;")
                    select_gpt_sovits_v2_api_0821_text_split_method = ui.select(
                        label='语句切分', 
                        options={
                            'cut0':'不切', 
                            'cut1':'凑四句一切', 
                            'cut2':'凑50字一切', 
                            'cut3':'按中文句号。切', 
                            'cut4':'按英文句号.切',
                            'cut5':'按标点符号切'
                        }, 
                        value=config.get("gpt_sovits", "v2_api_0821", "text_split_method")
                    ).style("width:200px;")
                with ui.row():
                    input_gpt_sovits_v2_api_0821_top_k = ui.input(label='top_k', value=config.get("gpt_sovits", "v2_api_0821", "top_k"), placeholder='top_k').style("width:100px;")
                    input_gpt_sovits_v2_api_0821_top_p = ui.input(label='top_p', value=config.get("gpt_sovits", "v2_api_0821", "top_p"), placeholder='top_p').style("width:100px;")
                    input_gpt_sovits_v2_api_0821_temperature = ui.input(label='temperature', value=config.get("gpt_sovits", "v2_api_0821", "temperature"), placeholder='temperature').style("width:100px;")
                    input_gpt_sovits_v2_api_0821_batch_size = ui.input(label='batch_size', value=config.get("gpt_sovits", "v2_api_0821", "batch_size"), placeholder='batch_size').style("width:100px;")
                    input_gpt_sovits_v2_api_0821_batch_threshold = ui.input(label='batch_threshold', value=config.get("gpt_sovits", "v2_api_0821", "batch_threshold"), placeholder='batch_threshold').style("width:100px;")
                    switch_gpt_sovits_v2_api_0821_split_bucket = ui.switch('split_bucket', value=config.get("gpt_sovits", "v2_api_0821", "split_bucket")).style(switch_internal_css)
                    input_gpt_sovits_v2_api_0821_speed_factor = ui.input(label='speed_factor', value=config.get("gpt_sovits", "v2_api_0821", "speed_factor"), placeholder='speed_factor').style("width:100px;")
                    input_gpt_sovits_v2_api_0821_fragment_interval = ui.input(label='分段间隔(秒)', value=config.get("gpt_sovits", "v2_api_0821", "fragment_interval"), placeholder='fragment_interval').style("width:100px;")
                    input_gpt_sovits_v2_api_0821_seed = ui.input(label='seed', value=config.get("gpt_sovits", "v2_api_0821", "seed"), placeholder='seed').style("width:100px;")
                    input_gpt_sovits_v2_api_0821_media_type = ui.input(label='media_type', value=config.get("gpt_sovits", "v2_api_0821", "media_type"), placeholder='media_type').style("width:100px;")
                    switch_gpt_sovits_v2_api_0821_parallel_infer = ui.switch('parallel_infer', value=config.get("gpt_sovits", "v2_api_0821", "parallel_infer")).style(switch_internal_css)
                    input_gpt_sovits_v2_api_0821_repetition_penalty = ui.input(label='repetition_penalty', value=config.get("gpt_sovits", "v2_api_0821", "repetition_penalty"), placeholder='repetition_penalty').style("width:100px;")
                    

            with ui.card().style(card_css):
                ui.label("WebTTS相关配置")
                with ui.row():
                    select_gpt_sovits_webtts_version = ui.select(
                        label='版本', 
                        options={
                            '1':'1', 
                            '1.4':'1.4', 
                            '2':'2'
                        }, 
                        value=config.get("gpt_sovits", "webtts", "version")
                    ).style("width:80px;")
                    input_gpt_sovits_webtts_api_ip_port = ui.input(label='API地址', value=config.get("gpt_sovits", "webtts", "api_ip_port"), placeholder='API监听地址').style("width:200px;")
                    input_gpt_sovits_webtts_spk = ui.input(label='音色', value=config.get("gpt_sovits", "webtts", "spk"), placeholder='音色').style("width:100px;")
                    select_gpt_sovits_webtts_lang = ui.select(
                        label='语言', 
                        options={
                            'zh':'中文', 
                            'en':'英文', 
                            'jp':'日文'
                        }, 
                        value=config.get("gpt_sovits", "webtts", "lang")
                    ).style("width:100px;")
                    input_gpt_sovits_webtts_speed = ui.input(label='语速', value=config.get("gpt_sovits", "webtts", "speed"), placeholder='语速').style("width:100px;")
                    input_gpt_sovits_webtts_emotion = ui.input(label='情感', value=config.get("gpt_sovits", "webtts", "emotion"), placeholder='情感').style("width:100px;")

    
    if config.get("webui", "show_card", "tts", "azure_tts"): 
        with ui.card().style(card_css):
            ui.label("azure_tts")
            with ui.row():
                input_azure_tts_subscription_key = ui.input(label='密钥', value=config.get("azure_tts", "subscription_key"), placeholder='申请开通服务后，自然就看见了').style("width:200px;")
                input_azure_tts_region = ui.input(label='区域', value=config.get("azure_tts", "region"), placeholder='申请开通服务后，自然就看见了').style("width:200px;")
                input_azure_tts_voice_name = ui.input(label='说话人名', value=config.get("azure_tts", "voice_name"), placeholder='Speech Studio平台试听获取说话人名').style("width:200px;")
    
    
    if config.get("webui", "show_card", "tts", "cosyvoice"): 
        with ui.card().style(card_css):
            ui.label("CosyVoice")
            with ui.row():
                select_cosyvoice_type = ui.select(
                    label='类型', 
                    options={"api_0819": "api_0819", "gradio_0707": "gradio_0707"}, 
                    value=config.get("cosyvoice", "type")
                ).style("width:150px").tooltip("对接的API类型")
                input_cosyvoice_gradio_ip_port = ui.input(
                    label='Gradio API地址', 
                    value=config.get("cosyvoice", "gradio_ip_port"), 
                    placeholder='官方webui程序启动后gradio监听的地址',
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                ).style("width:200px;").tooltip("对接webui的gradio接口，填webui的地址")
                input_cosyvoice_api_ip_port = ui.input(
                    label='HTTP API地址', 
                    value=config.get("cosyvoice", "api_ip_port"), 
                    placeholder='API程序启动后，API请求地址',
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                ).style("width:200px;").tooltip("对接api接口，填api端点地址")
            
            with ui.row():
                with ui.card().style(card_css):
                    ui.label("gradio_0707")
                    with ui.row():
                        select_cosyvoice_gradio_0707_mode_checkbox_group = ui.select(
                            label='推理模式', 
                            options={'预训练音色': '预训练音色', '3s极速复刻': '3s极速复刻', '跨语种复刻': '跨语种复刻', '自然语言控制': '自然语言控制'}, 
                            value=config.get("cosyvoice", "gradio_0707", "mode_checkbox_group")
                        ).style("width:200px;")
                        select_cosyvoice_gradio_0707_sft_dropdown = ui.select(
                            label='预训练音色', 
                            options={'中文女': '中文女', '中文男': '中文男', '日语男': '日语男', '粤语女': '粤语女', '英文女': '英文女', '英文男': '英文男', '韩语女': '韩语女'}, 
                            value=config.get("cosyvoice", "gradio_0707", "sft_dropdown")
                        ).style("width:100px;")
                        input_cosyvoice_gradio_0707_prompt_text = ui.input(label='prompt文本', value=config.get("cosyvoice", "gradio_0707", "prompt_text"), placeholder='').style("width:200px;").tooltip("不用就留空")
                        input_cosyvoice_gradio_0707_prompt_wav_upload = ui.input(label='prompt音频路径', value=config.get("cosyvoice", "gradio_0707", "prompt_wav_upload"), placeholder='例如：E:\\1.wav').style("width:200px;").tooltip("不用就留空，例如：E:\\1.wav")
                        input_cosyvoice_gradio_0707_instruct_text = ui.input(label='instruct文本', value=config.get("cosyvoice", "gradio_0707", "instruct_text"), placeholder='').style("width:200px;").tooltip("不用就留空")
                        input_cosyvoice_gradio_0707_seed = ui.input(label='随机推理种子', value=config.get("cosyvoice", "gradio_0707", "seed"), placeholder='默认：0').style("width:100px;").tooltip("随机推理种子")
            with ui.row():
                with ui.card().style(card_css):
                    ui.label("api_0819")
                    with ui.row():
                        input_cosyvoice_api_0819_speaker = ui.input(label='说话人', value=config.get("cosyvoice", "api_0819", "speaker"), placeholder='').style("width:200px;").tooltip("自行查看")
                        input_cosyvoice_api_0819_new = ui.input(label='new', value=config.get("cosyvoice", "api_0819", "new"), placeholder='0').style("width:200px;").tooltip("自行查看")
                        input_cosyvoice_api_0819_speed = ui.input(label='语速', value=config.get("cosyvoice", "api_0819", "speed"), placeholder='1').style("width:200px;").tooltip("语速")
    
    if config.get("webui", "show_card", "tts", "f5_tts"): 
        with ui.card().style(card_css):
            ui.label("F5-TTS")
            with ui.row():
                select_f5_tts_type = ui.select(
                    label='类型', 
                    options={"gradio_1023": "gradio_1023"}, 
                    value=config.get("f5_tts", "type")
                ).style("width:150px").tooltip("对接的API类型")
                input_f5_tts_gradio_ip_port = ui.input(
                    label='Gradio API地址', 
                    value=config.get("f5_tts", "gradio_ip_port"), 
                    placeholder='官方webui程序启动后gradio监听的地址',
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                ).style("width:200px;").tooltip("对接webui的gradio接口，填webui的地址")

                select_f5_tts_model = ui.select(
                    label='模型', 
                    options={'F5-TTS': 'F5-TTS', 'E2-TTS': 'E2-TTS'}, 
                    value=config.get("f5_tts", "model")
                ).style("width:100px;")
                input_f5_tts_ref_audio_orig = ui.input(label='参考音频路径', value=config.get("f5_tts", "ref_audio_orig"), placeholder='例如：E:\\1.wav').style("width:200px;").tooltip("参考音频路径")
                input_f5_tts_ref_text = ui.input(label='参考文本', value=config.get("f5_tts", "ref_text"), placeholder='音频的文本').style("width:200px;").tooltip("参考文本，例如：E:\\1.wav")
                switch_f5_tts_remove_silence = ui.switch('remove_silence', value=config.get("f5_tts", "remove_silence")).style(switch_internal_css)
                input_f5_tts_cross_fade_duration = ui.input(label='cross_fade_duration', value=config.get("f5_tts", "cross_fade_duration"), placeholder='0.15').style("width:100px;").tooltip("cross_fade_duration")
                input_f5_tts_speed = ui.input(label='语速', value=config.get("f5_tts", "speed"), placeholder='语速').style("width:100px;").tooltip("语速，默认：1")

    if config.get("webui", "show_card", "tts", "multitts"): 
        with ui.card().style(card_css):
            ui.label("MultiTTS")
            with ui.row():
                input_multitts_api_ip_port = ui.input(
                    label='API地址', 
                    value=config.get("multitts", "api_ip_port"), 
                    placeholder='MultiTTS所在设备的IP地址以及端口号',
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                ).style("width:200px;").tooltip("MultiTTS所在设备的IP地址以及端口号")
                input_multitts_speed = ui.input(label='语速', value=config.get("multitts", "speed"), placeholder='0-100').style("width:100px;").tooltip("语速，默认：1")
                input_multitts_volume = ui.input(label='音量', value=config.get("multitts", "volume"), placeholder='0-100').style("width:100px;").tooltip("音量：默认50")
                input_multitts_pitch = ui.input(label='音调', value=config.get("multitts", "pitch"), placeholder='0-100').style("width:100px;").tooltip("音调：默认50")
                input_multitts_voice = ui.input(label='声音ID', value=config.get("multitts", "voice"), placeholder='默认不填就是默认选中的发言人').style("width:200px;").tooltip("默认不填就是默认选中的发言人")
    if config.get("webui", "show_card", "tts", "melotts"): 
        with ui.card().style(card_css):
            ui.label("MeloTTS")
            with ui.row():
                input_melotts_api_ip_port = ui.input(
                    label='API地址', 
                    value=config.get("melotts", "api_ip_port"), 
                    placeholder='MeloTTS API程序所在设备的IP地址以及端口号',
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                ).style("width:200px;").tooltip("MeloTTS API程序所在设备的IP地址以及端口号")
                input_melotts_language = ui.input(label='语言', value=config.get("melotts", "language"), placeholder='0-100').style("width:100px;").tooltip("语速，默认：1")
                select_melotts_device = ui.select(
                    label='device', 
                    options={'auto': 'auto', 'cuda': 'cuda', 'cpu': 'cpu'}, 
                    value=config.get("melotts", "device")
                ).style("width:100px;")
                switch_melotts_use_hf = ui.switch('使用HF默认模型', value=config.get("melotts", "use_hf")).style(switch_internal_css)
                input_melotts_config_path = ui.input(label='配置文件路径', value=config.get("melotts", "config_path"), placeholder='config.json路径').style("width:200px;").tooltip("config.json路径")
                input_melotts_ckpt_path = ui.input(label='模型路径', value=config.get("melotts", "ckpt_path"), placeholder='G_*.pth模型路径').style("width:200px;").tooltip("G_*.pth模型路径")
                
                async def melotts_load_model(data):
                    import aiohttp

                    ui.notify(position="top", type="info", message='MeloTTS 准备加载模型')

                    API_URL = urljoin(data["api_ip_port"], '/init')

                    if "use_hf" in data and data["use_hf"]:
                        del data["config_path"]
                        del data["ckpt_path"]

                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.post(API_URL, json=data) as response:
                                if response.status == 200:
                                    ret = await response.json()
                                    logger.debug(ret)

                                    logger.info('MeloTTS模型加载成功')
                                    ui.notify(position="top", type="positive", message='MeloTTS模型加载成功')
                                    return ret
                                else: 
                                    logger.error('MeloTTS模型加载失败')
                                    ui.notify(position="top", type="negative", message='MeloTTS模型加载失败')
                                    return None

                    except aiohttp.ClientError as e:
                        logger.error(f'MeloTTS请求失败: {e}')
                        ui.notify(position="top", type="negative", message=f'MeloTTS请求失败: {e}')
                    except Exception as e:
                        logger.error(f'MeloTTS未知错误: {e}')
                        ui.notify(position="top", type="negative", message=f'MeloTTS未知错误: {e}')
                    
                    return None

                button_melotts_load_model = ui.button('加载模型', on_click=lambda: melotts_load_model(config.get("melotts")), color=button_internal_color).style(button_internal_css)
            
            with ui.row():
                input_melotts_speaker_id = ui.input(label='说话人ID', value=config.get("melotts", "speaker_id"), placeholder='从0开始的整数，默认为0').style("width:100px;").tooltip("从0开始的整数，默认为0")
                input_melotts_sdp_ratio = ui.input(label='sdp_ratio', value=config.get("melotts", "sdp_ratio"), placeholder='sdp_ratio').style("width:100px;").tooltip("sdp_ratio")
                input_melotts_noise_scale = ui.input(label='noise_scale', value=config.get("melotts", "noise_scale"), placeholder='noise_scale').style("width:100px;").tooltip("noise_scale")
                input_melotts_noise_scale_w = ui.input(label='noise_scale_w', value=config.get("melotts", "noise_scale_w"), placeholder='noise_scale_w').style("width:100px;").tooltip("noise_scale_w")
                input_melotts_speed = ui.input(label='语速', value=config.get("melotts", "speed"), placeholder='0-10，默认：1').style("width:100px;").tooltip("语速，默认：1")
    if config.get("webui", "show_card", "tts", "index_tts"): 
        with ui.card().style(card_css):
            ui.label("Index-TTS")
            with ui.row():
                input_index_tts_api_ip_port = ui.input(
                    label='API地址', 
                    value=config.get("index_tts", "api_ip_port"), 
                    placeholder='Index-TTS API程序所在设备的IP地址以及端口号',
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                ).style("width:200px;").tooltip("Index-TTS API程序所在设备的IP地址以及端口号")
                input_index_tts_prompt_audio = ui.input(label='prompt音频路径', value=config.get("index_tts", "prompt_audio"), placeholder='例如：E:\\1.wav').style("width:200px;").tooltip("prompt音频路径")
                input_index_tts_temperature = ui.input(label='temperature', value=config.get("index_tts", "temperature"), placeholder='temperature').style("width:200px;").tooltip("temperature")
                

    mapping = {}

    if config.get("webui", "show_card", "tts", "edge-tts"):
        mapping["edge-tts"] = {
            "voice": (select_edge_tts_voice, 'str'),
            "rate": (input_edge_tts_rate, 'str'),
            "volume": (input_edge_tts_volume, 'str'),
            "proxy": (input_edge_tts_proxy, 'str'),
        }
    if config.get("webui", "show_card", "tts", "vits"):
        mapping["vits"] = {
            "type": (select_vits_type, 'str'),
            "config_path": (input_vits_config_path, 'str'),
            "api_ip_port": (input_vits_api_ip_port, 'str'),
            "id": (select_vits_id, 'str'),
            "lang": (select_vits_lang, 'str'),
            "length": (input_vits_length, 'str'),
            "noise": (input_vits_noise, 'str'),
            "noisew": (input_vits_noisew, 'str'),
            "max": (input_vits_max, 'str'),
            "format": (input_vits_format, 'str'),
            "sdp_radio": (input_vits_sdp_radio, 'str'),
            "gpt_sovits": {
                "id": (select_vits_gpt_sovits_id, 'str'),
                "lang": (select_vits_gpt_sovits_lang, 'str'),
                "format": (input_vits_gpt_sovits_format, 'str'),
                "segment_size": (input_vits_gpt_sovits_segment_size, 'str'),
                "reference_audio": (input_vits_gpt_sovits_reference_audio, 'str'),
                "prompt_text": (input_vits_gpt_sovits_prompt_text, 'str'),
                "prompt_lang": (select_vits_gpt_sovits_prompt_lang, 'str'),
                "top_k": (input_vits_gpt_sovits_top_k, 'str'),
                "top_p": (input_vits_gpt_sovits_top_p, 'str'),
                "temperature": (input_vits_gpt_sovits_temperature, 'str'),
                "preset": (input_vits_gpt_sovits_preset, 'str'),
            }
        }
    if config.get("webui", "show_card", "tts", "bert_vits2"):
        mapping["bert_vits2"] = {
            "type": (select_bert_vits2_type, 'str'),
            "api_ip_port": (input_bert_vits2_api_ip_port, 'str'),
            "model_id": (input_bert_vits2_model_id, 'int'),
            "speaker_name": (input_bert_vits2_speaker_name, 'str'),
            "speaker_id": (input_bert_vits2_speaker_id, 'int'),
            "language": (select_bert_vits2_language, 'str'),
            "length": (input_bert_vits2_length, 'int'),
            "noise": (input_bert_vits2_noise, 'float'),
            "noisew": (input_bert_vits2_noisew, 'float'),
            "sdp_radio": (input_bert_vits2_sdp_radio, 'float'),
            "emotion": (input_bert_vits2_emotion, 'str'),
            "style_text": (input_bert_vits2_style_text, 'str'),
            "style_weight": (input_bert_vits2_style_weight, 'float'),
            "auto_translate": (switch_bert_vits2_auto_translate, 'bool'),
            "auto_split": (switch_bert_vits2_auto_split, 'bool'),
            "刘悦-中文特化API": {
                "api_ip_port": (input_bert_vits2_liuyue_zh_api_api_ip_port, 'str'),
                "speaker": (input_bert_vits2_liuyue_zh_api_speaker, 'str'),
                "language": (select_bert_vits2_liuyue_zh_api_language, 'str'),
                "length_scale": (input_bert_vits2_liuyue_zh_api_length_scale, 'str'),
                "interval_between_para": (input_bert_vits2_liuyue_zh_api_interval_between_para, 'str'),
                "interval_between_sent": (input_bert_vits2_liuyue_zh_api_interval_between_sent, 'str'),
                "noise_scale": (input_bert_vits2_liuyue_zh_api_noise_scale, 'str'),
                "noise_scale_w": (input_bert_vits2_liuyue_zh_api_noise_scale_w, 'str'),
                "sdp_radio": (input_bert_vits2_liuyue_zh_api_sdp_radio, 'str'),
                "emotion": (input_bert_vits2_liuyue_zh_api_emotion, 'str'),
                "style_text": (input_bert_vits2_liuyue_zh_api_style_text, 'str'),
                "style_weight": (input_bert_vits2_liuyue_zh_api_style_weight, 'str'),
                "cut_by_sent": (switch_bert_vits2_cut_by_sent, 'bool'),
            }
        }
    if config.get("webui", "show_card", "tts", "vits_fast"):
        mapping["vits_fast"] = {
            "config_path": (input_vits_fast_config_path, 'str'),
            "api_ip_port": (input_vits_fast_api_ip_port, 'str'),
            "character": (input_vits_fast_character, 'str'),
            "language": (select_vits_fast_language, 'str'),
            "speed": (input_vits_fast_speed, 'float'),
        }
    if config.get("webui", "show_card", "tts", "elevenlabs"):
        mapping["elevenlabs"] = {
            "api_key": (input_elevenlabs_api_key, 'str'),
            "voice": (input_elevenlabs_voice, 'str'),
            "model": (input_elevenlabs_model, 'str'),
        }
    
    if config.get("webui", "show_card", "tts", "openai_tts"):
        mapping["openai_tts"] = {
            "type": (select_openai_tts_type, 'str'),
            "api_ip_port": (input_openai_tts_api_ip_port, 'str'),
            "model": (select_openai_tts_model, 'str'),
            "voice": (select_openai_tts_voice, 'str'),
            "api_key": (input_openai_tts_api_key, 'str'),
        }
    
    if config.get("webui", "show_card", "tts", "gradio_tts"):
        mapping["gradio_tts"] = {
            "request_parameters": (textarea_gradio_tts_request_parameters, 'str'),
        }
    if config.get("webui", "show_card", "tts", "gpt_sovits"):
        mapping["gpt_sovits"] = {
            "type": (select_gpt_sovits_type, 'str'),
            "gradio_ip_port": (input_gpt_sovits_gradio_ip_port, 'str'),
            "api_ip_port": (input_gpt_sovits_api_ip_port, 'str'),
            "ref_audio_path": (input_gpt_sovits_ref_audio_path, 'str'),
            "prompt_text": (input_gpt_sovits_prompt_text, 'str'),
            "prompt_language": (select_gpt_sovits_prompt_language, 'str'),
            "language": (select_gpt_sovits_language, 'str'),
            "cut": (select_gpt_sovits_cut, 'str'),
            "gpt_model_path": (input_gpt_sovits_gpt_model_path, 'str'),
            "sovits_model_path": (input_gpt_sovits_sovits_model_path, 'str'),
            "api_0322": {
                "ref_audio_path": (input_gpt_sovits_api_0322_ref_audio_path, 'str'),
                "prompt_text": (input_gpt_sovits_api_0322_prompt_text, 'str'),
                "prompt_lang": (select_gpt_sovits_api_0322_prompt_lang, 'str'),
                "text_lang": (select_gpt_sovits_api_0322_text_lang, 'str'),
                "text_split_method": (select_gpt_sovits_api_0322_text_split_method, 'str'),
                "top_k": (input_gpt_sovits_api_0322_top_k, 'int'),
                "top_p": (input_gpt_sovits_api_0322_top_p, 'float'),
                "temperature": (input_gpt_sovits_api_0322_temperature, 'float'),
                "batch_size": (input_gpt_sovits_api_0322_batch_size, 'int'),
                "speed_factor": (input_gpt_sovits_api_0322_speed_factor, 'float'),
                "fragment_interval": (input_gpt_sovits_api_0322_fragment_interval, 'str'),
                "split_bucket": (switch_gpt_sovits_api_0322_split_bucket, 'bool'),
                "return_fragment": (switch_gpt_sovits_api_0322_return_fragment, 'bool'),
            },
            "api_0706": {
                "refer_wav_path": (input_gpt_sovits_api_0706_refer_wav_path, 'str'),
                "prompt_text": (input_gpt_sovits_api_0706_prompt_text, 'str'),
                "prompt_language": (select_gpt_sovits_api_0706_prompt_language, 'str'),
                "text_language": (select_gpt_sovits_api_0706_text_language, 'str'),
                "cut_punc": (input_gpt_sovits_api_0706_cut_punc, 'str'),
            },
            "v2_api_0821": {
                "ref_audio_path": (input_gpt_sovits_v2_api_0821_ref_audio_path, 'str'),
                "prompt_text": (input_gpt_sovits_v2_api_0821_prompt_text, 'str'),
                "prompt_lang": (select_gpt_sovits_v2_api_0821_prompt_lang, 'str'),
                "text_lang": (select_gpt_sovits_v2_api_0821_text_lang, 'str'),
                "text_split_method": (select_gpt_sovits_v2_api_0821_text_split_method, 'str'),
                "top_k": (input_gpt_sovits_v2_api_0821_top_k, 'int'),
                "top_p": (input_gpt_sovits_v2_api_0821_top_p, 'float'),
                "temperature": (input_gpt_sovits_v2_api_0821_temperature, 'float'),
                "batch_size": (input_gpt_sovits_v2_api_0821_batch_size, 'int'),
                "batch_threshold": (input_gpt_sovits_v2_api_0821_batch_threshold, 'float'),
                "split_bucket": (switch_gpt_sovits_v2_api_0821_split_bucket, 'bool'),
                "speed_factor": (input_gpt_sovits_v2_api_0821_speed_factor, 'float'),
                "fragment_interval": (input_gpt_sovits_v2_api_0821_fragment_interval, 'float'),
                "seed": (input_gpt_sovits_v2_api_0821_seed, 'int'),
                "media_type": (input_gpt_sovits_v2_api_0821_media_type, 'str'),
                "parallel_infer": (switch_gpt_sovits_v2_api_0821_parallel_infer, 'bool'),
                "repetition_penalty": (input_gpt_sovits_v2_api_0821_repetition_penalty, 'float'),
            },
            "webtts": {
                "version": (select_gpt_sovits_webtts_version, 'str'),
                "api_ip_port": (input_gpt_sovits_webtts_api_ip_port, 'str'),
                "spk": (input_gpt_sovits_webtts_spk, 'str'),
                "lang": (select_gpt_sovits_webtts_lang, 'str'),
                "speed": (input_gpt_sovits_webtts_speed, 'str'),
                "emotion": (input_gpt_sovits_webtts_emotion, 'str'),
            }
        }

    if config.get("webui", "show_card", "tts", "azure_tts"):
        mapping["azure_tts"] = {
            "subscription_key": (input_azure_tts_subscription_key, 'str'),
            "region": (input_azure_tts_region, 'str'),
            "voice_name": (input_azure_tts_voice_name, 'str'),
        }
    if config.get("webui", "show_card", "tts", "cosyvoice"):
        mapping["cosyvoice"] = {
            "type": (select_cosyvoice_type, 'str'),
            "gradio_ip_port": (input_cosyvoice_gradio_ip_port, 'str'),
            "api_ip_port": (input_cosyvoice_api_ip_port, 'str'),
            "gradio_0707": {
                "mode_checkbox_group": (select_cosyvoice_gradio_0707_mode_checkbox_group, 'str'),
                "sft_dropdown": (select_cosyvoice_gradio_0707_sft_dropdown, 'str'),
                "prompt_text": (input_cosyvoice_gradio_0707_prompt_text, 'str'),
                "prompt_wav_upload": (input_cosyvoice_gradio_0707_prompt_wav_upload, 'str'),
                "instruct_text": (input_cosyvoice_gradio_0707_instruct_text, 'str'),
                "seed": (input_cosyvoice_gradio_0707_seed, 'int'),
            },
            "api_0819": {
                "speaker": (input_cosyvoice_api_0819_speaker, 'str'),
                "new": (input_cosyvoice_api_0819_new, 'int'),
                "speed": (input_cosyvoice_api_0819_speed, 'float'),
            },
        }
    if config.get("webui", "show_card", "tts", "f5_tts"):
        mapping["f5_tts"] = {
            "type": (select_f5_tts_type, 'str'),
            "gradio_ip_port": (input_f5_tts_gradio_ip_port, 'str'),
            "ref_audio_orig": (input_f5_tts_ref_audio_orig, 'str'),
            "ref_text": (input_f5_tts_ref_text, 'str'),
            "model": (select_f5_tts_model, 'str'),
            "remove_silence": (switch_f5_tts_remove_silence, 'bool'),
            "cross_fade_duration": (input_f5_tts_cross_fade_duration, 'float'),
            "speed": (input_f5_tts_speed, 'float'),
        }
    if config.get("webui", "show_card", "tts", "multitts"):
        mapping["multitts"] = {
            "api_ip_port": (input_multitts_api_ip_port, 'str'),
            "speed": (input_multitts_speed, 'int'),
            "volume": (input_multitts_volume, 'int'),
            "pitch": (input_multitts_pitch, 'int'),
            "voice": (input_multitts_voice, 'str'),
        }
    if config.get("webui", "show_card", "tts", "melotts"):
        mapping["melotts"] = {
            "api_ip_port": (input_melotts_api_ip_port, 'str'),
            "language": (input_melotts_language, 'str'),
            "device": (select_melotts_device, 'str'),
            "use_hf": (switch_melotts_use_hf, 'bool'),
            "config_path": (input_melotts_config_path, 'str'),
            "ckpt_path": (input_melotts_ckpt_path, 'str'),
            "speaker_id": (input_melotts_speaker_id, 'int'),
            "sdp_ratio": (input_melotts_sdp_ratio, 'float'),
            "noise_scale": (input_melotts_noise_scale, 'float'),
            "noise_scale_w": (input_melotts_noise_scale_w, 'float'),
            "speed": (input_melotts_speed, 'float'),
        }
    if config.get("webui", "show_card", "tts", "index_tts"):
        mapping["index_tts"] = {
            "api_ip_port": (input_index_tts_api_ip_port, 'str'),
            "prompt_audio": (input_index_tts_prompt_audio, 'str'),
            "temperature": (input_index_tts_temperature, 'float'),
        }



    return PageConfig(mapping=mapping)
