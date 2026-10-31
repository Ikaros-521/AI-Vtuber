"""聊天页：拾音、STT、聊天框、打断与唤醒配置。"""

from nicegui import ui

from utils.my_log import logger
from webui_app.descriptions import show_card_desc
from webui_app.helpers import textarea_data_change
from webui_app.pages import PageConfig
from webui_app.theme import INK

TALK_INTERRUPT_CLEAN_TYPE_LIST = ["message_queue", "voice_tmp_path_queue", "audio_play"]
TALK_INTERRUPT_CLEAN_TYPE_MAPPING = {
    "message_queue": "待合成消息队列",
    "voice_tmp_path_queue": "待播放音频队列",
    "audio_play": "正在播放中的音频",
}
FASTER_WHISPER_LANGUAGES = [
    "自动识别",
    "af",
    "am",
    "ar",
    "as",
    "az",
    "ba",
    "be",
    "bg",
    "bn",
    "bo",
    "br",
    "bs",
    "ca",
    "cs",
    "cy",
    "da",
    "de",
    "el",
    "en",
    "es",
    "et",
    "eu",
    "fa",
    "fi",
    "fo",
    "fr",
    "gl",
    "gu",
    "ha",
    "haw",
    "he",
    "hi",
    "hr",
    "ht",
    "hu",
    "hy",
    "id",
    "is",
    "it",
    "ja",
    "jw",
    "ka",
    "kk",
    "km",
    "kn",
    "ko",
    "la",
    "lb",
    "ln",
    "lo",
    "lt",
    "lv",
    "mg",
    "mi",
    "mk",
    "ml",
    "mn",
    "mr",
    "ms",
    "mt",
    "my",
    "ne",
    "nl",
    "nn",
    "no",
    "oc",
    "pa",
    "pl",
    "ps",
    "pt",
    "ro",
    "ru",
    "sa",
    "sd",
    "si",
    "sk",
    "sl",
    "sn",
    "so",
    "sq",
    "sr",
    "su",
    "sv",
    "sw",
    "ta",
    "te",
    "tg",
    "th",
    "tk",
    "tl",
    "tr",
    "tt",
    "uk",
    "ur",
    "uz",
    "vi",
    "yi",
    "yo",
    "zh",
    "yue",
]


def build_talk_tab(
    config,
    common,
    state,
    card_css,
    switch_internal_css,
    button_internal_color=None,
    button_internal_css=None,
    chat_log=None,
):
    # 语音拾音与 STT 配置卡片
    with ui.card().style(card_css + "width:100%;"):
        ui.label("语音对话与拾音").style(f"font-size:14px;font-weight:600;color:{INK};")
        show_card_desc("语音对话与拾音")
        with ui.row():
            switch_talk_key_listener_enable = (
                ui.switch("启用按键监听", value=config.get("talk", "key_listener_enable"))
                .style(switch_internal_css)
                .tooltip("启用后，可以通过键盘单击下放配置的录音按键，启动语音识别对话功能")
            )
            switch_talk_direct_run_talk = (
                ui.switch("直接语音对话", value=config.get("talk", "direct_run_talk"))
                .style(switch_internal_css)
                .tooltip(
                    "如果启用了，将在首次运行时直接进行语音识别，而不需手动点击开始按键。针对有些系统按键无法触发的情况下，配合连续对话和唤醒词使用"
                )
            )

            # 无声卡的机器（CI、裸服务器、被禁用的音频驱动）上 PyAudio 会直接抛异常，
            # 不兜住的话整个 webui 都打不开，而不是只有这一页不能用
            try:
                audio_device_info_list = common.get_all_audio_device_info("in")
            except Exception as e:
                logger.warning(f"声卡输入设备枚举失败，声卡下拉将为空：{e}")
                audio_device_info_list = []
            logger.info(f"声卡输入设备={audio_device_info_list}")
            audio_device_info_dict = {
                str(device["device_index"]): device["device_info"] for device in audio_device_info_list
            }

            select_talk_device_index = (
                ui.select(
                    label="声卡输入设备", options=audio_device_info_dict, value=config.get("talk", "device_index")
                )
                .style("width:300px;")
                .tooltip(
                    "这就是语言对话输入的声卡（麦克风），选择你对应的麦克风即可，如果需要监听电脑声卡可以配合虚拟声卡来实现"
                )
            )

            switch_talk_no_recording_during_playback = (
                ui.switch("播放中不进行录音", value=config.get("talk", "no_recording_during_playback"))
                .style(switch_internal_css)
                .tooltip("AI在播放音频的过程中不进行录音，从而防止麦克风和扬声器太近导致的循环录音的问题")
            )
            input_talk_no_recording_during_playback_sleep_interval = (
                ui.input(
                    label="播放中不进行录音的检测间隔(秒)",
                    value=config.get("talk", "no_recording_during_playback_sleep_interval"),
                    placeholder="这个值设置正常不需要太大，因为在启用了“播放中不进行录音”时，不会出现录音到AI说的话的情况，设置太大会导致恢复录音的时间变慢",
                )
                .style("width:200px;")
                .tooltip("这个值设置正常不需要太大，因为不会出现录音到AI说的话的情况")
            )

            switch_talk_continuous_talk = (
                ui.switch("连续对话", value=config.get("talk", "continuous_talk"))
                .style(switch_internal_css)
                .tooltip("仅需按一次录音按键，后续就不需要按了，会自动根据沉默阈值切分等待后，继续录音")
            )

        with ui.row():
            data_json = {}
            for line in ["google", "baidu", "faster_whisper", "sensevoice"]:
                data_json[line] = line
            select_talk_type = (
                ui.select(label="录音类型", options=data_json, value=config.get("talk", "type"))
                .style("width:200px;")
                .tooltip("选择使用的STT类型")
            )

            with open("data/keyboard.txt") as file:
                file_content = file.read()
            lines = file_content.strip().split("\n")
            data_json = {}
            for line in lines:
                data_json[line] = line
            select_talk_trigger_key = (
                ui.select(
                    label="录音按键",
                    options=data_json,
                    value=config.get("talk", "trigger_key"),
                    with_input=True,
                    clearable=True,
                )
                .style("width:200px;")
                .tooltip("按压此按键就可以触发录音了，按一次就行了")
            )
            select_talk_stop_trigger_key = (
                ui.select(
                    label="停录按键",
                    options=data_json,
                    value=config.get("talk", "stop_trigger_key"),
                    with_input=True,
                    clearable=True,
                )
                .style("width:200px;")
                .tooltip("按压此按键就可以停止录音了，按一次就行了")
            )

            input_talk_volume_threshold = (
                ui.input(
                    label="音量阈值",
                    value=config.get("talk", "volume_threshold"),
                    placeholder="音量阈值，指的是触发录音的起始音量值，请根据自己的麦克风进行微调到最佳",
                )
                .style("width:100px;")
                .tooltip("音量阈值，指的是触发录音的起始音量值，请根据自己的麦克风进行微调到最佳")
            )
            input_talk_silence_threshold = (
                ui.input(
                    label="停录计数",
                    value=config.get("talk", "silence_threshold"),
                    placeholder="停录计数，指的是音量低于起始值的计数，这个值越大，切分音频越慢，即需要等待更长时间才会停止录音，但也不能太小，不然说一半就停了",
                )
                .style("width:100px;")
                .tooltip("沉默阈值，指的是触发停止路径的最低音量值，请根据自己的麦克风进行微调到最佳")
            )
            input_talk_silence_CHANNELS = ui.input(
                label="CHANNELS", value=config.get("talk", "CHANNELS"), placeholder="录音用的参数"
            ).style("width:100px;")
            input_talk_silence_RATE = ui.input(
                label="RATE", value=config.get("talk", "RATE"), placeholder="录音用的参数"
            ).style("width:100px;")

    with ui.expansion("对话打断", icon="settings", value=True).classes("w-2/3"):
        with ui.row():
            switch_talk_interrupt_talk_enable = ui.switch(
                "启用", value=config.get("talk", "interrupt_talk", "enable")
            ).style(switch_internal_css)
            textarea_talk_interrupt_talk_keywords = (
                ui.textarea(
                    label="打断关键词",
                    placeholder="如：等一下、住嘴 多个请换行分隔",
                    value=textarea_data_change(config.get("talk", "interrupt_talk", "keywords")),
                )
                .style("width:200px;")
                .tooltip("打断关键词，当语句中包含出现这些词时，会中断对话，具体清除内容根据清除类型自定义")
            )

            with ui.card().style(card_css):
                ui.label("清除类型")
                show_card_desc("清除类型")
                with ui.row():
                    talk_interrupt_clean_type_var = {}
                    for index, clean_type in enumerate(TALK_INTERRUPT_CLEAN_TYPE_LIST):
                        talk_interrupt_clean_type_var[str(index)] = ui.checkbox(
                            text=TALK_INTERRUPT_CLEAN_TYPE_MAPPING[clean_type],
                            value=clean_type in config.get("talk", "interrupt_talk", "clean_type"),
                        )

    with ui.expansion("语音唤醒与睡眠", icon="settings", value=True).classes("w-2/3"):
        with ui.row():
            switch_talk_wakeup_sleep_enable = ui.switch(
                "启用", value=config.get("talk", "wakeup_sleep", "enable")
            ).style(switch_internal_css)
            select_talk_wakeup_sleep_mode = (
                ui.select(
                    label="唤醒模式",
                    options={"长期唤醒": "长期唤醒", "单次唤醒": "单次唤醒"},
                    value=config.get("talk", "wakeup_sleep", "mode"),
                )
                .style("width:100px")
                .tooltip(
                    "长期唤醒：说完唤醒词后，会触发提示语，后期对话不需要唤醒词；单次唤醒：每次对话都需要携带唤醒词，否则默认保持睡眠，且不会触发提示语"
                )
            )
            textarea_talk_wakeup_sleep_wakeup_word = ui.textarea(
                label="唤醒词",
                placeholder="如：管家 多个请换行分隔",
                value=textarea_data_change(config.get("talk", "wakeup_sleep", "wakeup_word")),
            ).style("width:200px;")
            textarea_talk_wakeup_sleep_sleep_word = ui.textarea(
                label="睡眠词",
                placeholder="如：关机 多个请换行分隔",
                value=textarea_data_change(config.get("talk", "wakeup_sleep", "sleep_word")),
            ).style("width:200px;")
            textarea_talk_wakeup_sleep_wakeup_copywriting = ui.textarea(
                label="唤醒提示语",
                placeholder="如：在的 多个请换行分隔",
                value=textarea_data_change(config.get("talk", "wakeup_sleep", "wakeup_copywriting")),
            ).style("width:300px;")
            textarea_talk_wakeup_sleep_sleep_copywriting = ui.textarea(
                label="睡眠提示语",
                placeholder="如：晚安 多个请换行分隔",
                value=textarea_data_change(config.get("talk", "wakeup_sleep", "sleep_copywriting")),
            ).style("width:300px;")

    with ui.expansion("谷歌", icon="settings", value=False).classes("w-2/3"):
        with ui.grid(columns=1):
            data_json = {}
            for line in ["zh-CN", "en-US", "ja-JP"]:
                data_json[line] = line
            select_talk_google_tgt_lang = ui.select(
                label="目标翻译语言", options=data_json, value=config.get("talk", "google", "tgt_lang")
            ).style("width:200px")

    with ui.expansion("百度", icon="settings", value=False).classes("w-2/3"):
        with ui.grid(columns=3):
            input_talk_baidu_app_id = ui.input(
                label="AppID", value=config.get("talk", "baidu", "app_id"), placeholder="百度云 语音识别应用的 AppID"
            )
            input_talk_baidu_api_key = ui.input(
                label="API Key",
                value=config.get("talk", "baidu", "api_key"),
                placeholder="百度云 语音识别应用的 API Key",
            )
            input_talk_baidu_secret_key = ui.input(
                label="Secret Key",
                value=config.get("talk", "baidu", "secret_key"),
                placeholder="百度云 语音识别应用的 Secret Key",
            )

    with ui.expansion("faster_whisper", icon="settings", value=False).classes("w-2/3"):
        with ui.row():
            input_faster_whisper_model_size = ui.input(
                label="model_size",
                value=config.get("talk", "faster_whisper", "model_size"),
                placeholder="Size of the model to use",
            )
            data_json = {}
            for line in FASTER_WHISPER_LANGUAGES:
                data_json[line] = line
            select_faster_whisper_language = ui.select(
                label="识别语言", options=data_json, value=config.get("talk", "faster_whisper", "language")
            ).style("width:200px")
            data_json = {}
            for line in ["cuda", "cpu", "auto"]:
                data_json[line] = line
            select_faster_whisper_device = ui.select(
                label="device", options=data_json, value=config.get("talk", "faster_whisper", "device")
            ).style("width:200px")
            data_json = {}
            for line in ["float16", "int8_float16", "int8"]:
                data_json[line] = line
            select_faster_whisper_compute_type = ui.select(
                label="compute_type", options=data_json, value=config.get("talk", "faster_whisper", "compute_type")
            ).style("width:200px")
            input_faster_whisper_download_root = ui.input(
                label="download_root",
                value=config.get("talk", "faster_whisper", "download_root"),
                placeholder="模型下载路径",
            )
            input_faster_whisper_beam_size = ui.input(
                label="beam_size",
                value=config.get("talk", "faster_whisper", "beam_size"),
                placeholder="系统在每个步骤中要考虑的最可能的候选序列数。具有较大的beam_size将使系统产生更准确的结果，但可能需要更多的计算资源；较小的beam_size会减少计算需求，但可能降低结果的准确性。",
            )

    with ui.expansion("SenseVoice", icon="settings", value=False).classes("w-2/3"):
        with ui.row():
            input_sensevoice_asr_model_path = ui.input(
                label="ASR 模型路径",
                value=config.get("talk", "sensevoice", "asr_model_path"),
                placeholder="ASR模型路径",
            ).tooltip("ASR模型路径")
            input_sensevoice_vad_model_path = ui.input(
                label="VAD 模型路径",
                value=config.get("talk", "sensevoice", "vad_model_path"),
                placeholder="VAD模型路径",
            ).tooltip("VAD模型路径")
            input_sensevoice_vad_max_single_segment_time = ui.input(
                label="VAD 模型路径",
                value=config.get("talk", "sensevoice", "vad_max_single_segment_time"),
                placeholder="VAD单段最大语音时间",
            ).tooltip("VAD单段最大语音时间")
            input_sensevoice_vad_device = ui.input(
                label="device", value=config.get("talk", "sensevoice", "device"), placeholder="使用设备device"
            ).tooltip("使用设备device")

            data_json = {}
            for line in ["zh", "en", "jp"]:
                data_json[line] = line
            select_sensevoice_language = ui.select(
                label="识别语言", options=data_json, value=config.get("talk", "sensevoice", "language")
            ).style("width:100px")
            input_sensevoice_text_norm = (
                ui.input(
                    label="text_norm", value=config.get("talk", "sensevoice", "text_norm"), placeholder="text_norm"
                )
                .style("width:100px")
                .tooltip("text_norm")
            )
            input_sensevoice_batch_size_s = (
                ui.input(
                    label="batch_size_s",
                    value=config.get("talk", "sensevoice", "batch_size_s"),
                    placeholder="batch_size_s",
                )
                .style("width:100px")
                .tooltip("batch_size_s")
            )
            input_sensevoice_batch_size = (
                ui.input(
                    label="batch_size", value=config.get("talk", "sensevoice", "batch_size"), placeholder="batch_size"
                )
                .style("width:100px")
                .tooltip("batch_size")
            )

    def save_clean_types(config_data):
        clean_types = []
        for index in range(len(talk_interrupt_clean_type_var)):
            checkbox = talk_interrupt_clean_type_var[str(index)]
            if checkbox.value:
                clean_types.append(common.find_keys_by_value(TALK_INTERRUPT_CLEAN_TYPE_MAPPING, checkbox.text)[0])
        config_data.setdefault("talk", {}).setdefault("interrupt_talk", {})["clean_type"] = clean_types

    return PageConfig(
        mapping={
            "talk": {
                "key_listener_enable": (switch_talk_key_listener_enable, "bool"),
                "direct_run_talk": (switch_talk_direct_run_talk, "bool"),
                "device_index": (select_talk_device_index, "str"),
                "no_recording_during_playback": (switch_talk_no_recording_during_playback, "bool"),
                "no_recording_during_playback_sleep_interval": (
                    input_talk_no_recording_during_playback_sleep_interval,
                    "float",
                ),
                "continuous_talk": (switch_talk_continuous_talk, "bool"),
                "trigger_key": (select_talk_trigger_key, "str"),
                "stop_trigger_key": (select_talk_stop_trigger_key, "str"),
                "volume_threshold": (input_talk_volume_threshold, "float"),
                "silence_threshold": (input_talk_silence_threshold, "float"),
                "CHANNELS": (input_talk_silence_CHANNELS, "int"),
                "RATE": (input_talk_silence_RATE, "int"),
                "interrupt_talk": {
                    "enable": (switch_talk_interrupt_talk_enable, "bool"),
                    "keywords": (textarea_talk_interrupt_talk_keywords, "textarea"),
                },
                "wakeup_sleep": {
                    "enable": (switch_talk_wakeup_sleep_enable, "bool"),
                    "mode": (select_talk_wakeup_sleep_mode, "str"),
                    "wakeup_word": (textarea_talk_wakeup_sleep_wakeup_word, "textarea"),
                    "sleep_word": (textarea_talk_wakeup_sleep_sleep_word, "textarea"),
                    "wakeup_copywriting": (textarea_talk_wakeup_sleep_wakeup_copywriting, "textarea"),
                    "sleep_copywriting": (textarea_talk_wakeup_sleep_sleep_copywriting, "textarea"),
                },
                "type": (select_talk_type, "str"),
                "google": {
                    "tgt_lang": (select_talk_google_tgt_lang, "str"),
                },
                "baidu": {
                    "app_id": (input_talk_baidu_app_id, "str"),
                    "api_key": (input_talk_baidu_api_key, "str"),
                    "secret_key": (input_talk_baidu_secret_key, "str"),
                },
                "faster_whisper": {
                    "model_size": (input_faster_whisper_model_size, "str"),
                    "language": (select_faster_whisper_language, "str"),
                    "device": (select_faster_whisper_device, "str"),
                    "compute_type": (select_faster_whisper_compute_type, "str"),
                    "download_root": (input_faster_whisper_download_root, "str"),
                    "beam_size": (input_faster_whisper_beam_size, "int"),
                },
                "sensevoice": {
                    "asr_model_path": (input_sensevoice_asr_model_path, "str"),
                    "vad_model_path": (input_sensevoice_vad_model_path, "str"),
                    "vad_max_single_segment_time": (input_sensevoice_vad_max_single_segment_time, "int"),
                    "device": (input_sensevoice_vad_device, "str"),
                    "language": (select_sensevoice_language, "str"),
                    "text_norm": (input_sensevoice_text_norm, "str"),
                    "batch_size_s": (input_sensevoice_batch_size_s, "int"),
                    "batch_size": (input_sensevoice_batch_size, "int"),
                },
            }
        },
        on_save=save_clean_types,
    )
