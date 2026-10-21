"""助播页：助播名、触发类型与本地问答匹配配置。"""
from nicegui import ui

from webui_app.pages import PageConfig

ASSISTANT_ANCHOR_TYPE_LIST = [
    "comment", "local_qa_audio", "song", "reread", "read_comment", "gift",
    "entrance", "follow", "idle_time_task", "reread_top_priority", "schedule",
    "image_recognition_schedule", "key_mapping", "integral",
]
ASSISTANT_ANCHOR_TYPE_MAPPING = {
    "comment": "弹幕",
    "local_qa_audio": "本地问答-音频",
    "song": "点歌",
    "reread": "复读",
    "read_comment": "念弹幕",
    "gift": "礼物",
    "entrance": "入场",
    "follow": "关注",
    "idle_time_task": "闲时任务",
    "reread_top_priority": "最高优先级-复读",
    "schedule": "定时任务",
    "image_recognition_schedule": "图像识别定时任务",
    "key_mapping": "按键映射",
    "integral": "积分",
}


def build_assistant_anchor_tab(config, common, audio_synthesis_type_options, card_css, switch_internal_css):
    with ui.row():
        switch_assistant_anchor_enable = ui.switch('启用', value=config.get("assistant_anchor", "enable")).style(switch_internal_css)
        input_assistant_anchor_username = ui.input(label='助播名', value=config.get("assistant_anchor", "username"), placeholder='助播的用户名，暂时没啥用')
        select_assistant_anchor_audio_synthesis_type = ui.select(
            label='语音合成',
            options=audio_synthesis_type_options,
            value=config.get("assistant_anchor", "audio_synthesis_type")
        ).style("width:200px;")

    with ui.card().style(card_css):
        ui.label("触发类型")
        with ui.row():
            assistant_anchor_type_var = {}
            for index, assistant_anchor_type in enumerate(ASSISTANT_ANCHOR_TYPE_LIST):
                assistant_anchor_type_var[str(index)] = ui.checkbox(
                    text=ASSISTANT_ANCHOR_TYPE_MAPPING[assistant_anchor_type],
                    value=assistant_anchor_type in config.get("assistant_anchor", "type"),
                )

    with ui.grid(columns=4):
        switch_assistant_anchor_local_qa_text_enable = ui.switch('启用文本匹配', value=config.get("assistant_anchor", "local_qa", "text", "enable")).style(switch_internal_css)
        select_assistant_anchor_local_qa_text_format = ui.select(
            label='存储格式',
            options={'json': '自定义json', 'text': '一问一答'},
            value=config.get("assistant_anchor", "local_qa", "text", "format")
        )
        input_assistant_anchor_local_qa_text_file_path = ui.input(label='文本问答数据路径', value=config.get("assistant_anchor", "local_qa", "text", "file_path"), placeholder='本地问答文本数据存储路径').style("width:200px;")
        input_assistant_anchor_local_qa_text_similarity = ui.input(label='文本最低相似度', value=config.get("assistant_anchor", "local_qa", "text", "similarity"), placeholder='最低文本匹配相似度，就是说用户发送的内容和本地问答库中设定的内容的最低相似度。\n低了就会被当做一般弹幕处理').style("width:200px;")

    with ui.grid(columns=4):
        switch_assistant_anchor_local_qa_audio_enable = ui.switch('启用音频匹配', value=config.get("assistant_anchor", "local_qa", "audio", "enable")).style(switch_internal_css)
        select_assistant_anchor_local_qa_audio_type = ui.select(
            label='匹配算法',
            options={'包含关系': '包含关系', '相似度匹配': '相似度匹配'},
            value=config.get("assistant_anchor", "local_qa", "audio", "type")
        )
        input_assistant_anchor_local_qa_audio_file_path = ui.input(label='音频存储路径', value=config.get("assistant_anchor", "local_qa", "audio", "file_path"), placeholder='本地问答音频文件存储路径').style("width:200px;")
        input_assistant_anchor_local_qa_audio_similarity = ui.input(label='音频最低相似度', value=config.get("assistant_anchor", "local_qa", "audio", "similarity"), placeholder='最低音频匹配相似度，就是说用户发送的内容和本地音频库中音频文件名的最低相似度。\n低了就会被当做一般弹幕处理').style("width:200px;")

    def save_types(config_data):
        types = []
        for index in range(len(assistant_anchor_type_var)):
            checkbox = assistant_anchor_type_var[str(index)]
            if checkbox.value:
                types.append(common.find_keys_by_value(ASSISTANT_ANCHOR_TYPE_MAPPING, checkbox.text)[0])
        config_data.setdefault("assistant_anchor", {})["type"] = types

    return PageConfig(
        mapping={
            "assistant_anchor": {
                "enable": (switch_assistant_anchor_enable, 'bool'),
                "username": (input_assistant_anchor_username, 'str'),
                "audio_synthesis_type": (select_assistant_anchor_audio_synthesis_type, 'str'),
                "local_qa": {
                    "text": {
                        "enable": (switch_assistant_anchor_local_qa_text_enable, 'bool'),
                        "format": (select_assistant_anchor_local_qa_text_format, 'str'),
                        "file_path": (input_assistant_anchor_local_qa_text_file_path, 'str'),
                        "similarity": (input_assistant_anchor_local_qa_text_similarity, 'float'),
                    },
                    "audio": {
                        "enable": (switch_assistant_anchor_local_qa_audio_enable, 'bool'),
                        "type": (select_assistant_anchor_local_qa_audio_type, 'str'),
                        "file_path": (input_assistant_anchor_local_qa_audio_file_path, 'str'),
                        "similarity": (input_assistant_anchor_local_qa_audio_similarity, 'float'),
                    },
                },
            }
        },
        on_save=save_types,
    )
