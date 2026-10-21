"""文案页：文案组配置、文本加载/保存、文案音频合成与播放控制。"""
import os
import traceback

from nicegui import ui

from utils.my_log import logger
from webui_app.helpers import AUDIO_SYNTHESIS_TYPE_OPTIONS, common_textarea_handle, textarea_data_change
from webui_app.pages import PageConfig


def build_copywriting_tab(config, common, audio, card_css, switch_internal_css,
                          button_internal_color, button_internal_css):
    copywriting_config_var = {}
    copywriting_config_card = ui.card()

    def copywriting_add():
        data_len = len(copywriting_config_var)
        tmp_config = {
            "file_path": f"data/copywriting{int(data_len / 5) + 1}/",
            "audio_path": f"out/copywriting{int(data_len / 5) + 1}/",
            "continuous_play_num": 2,
            "max_play_time": 10.0,
            "play_list": []
        }

        with copywriting_config_card.style(card_css):
            with ui.row():
                copywriting_config_var[str(data_len)] = ui.input(label=f"文案存储路径#{int(data_len / 5) + 1}", value=tmp_config["file_path"], placeholder='文案文件存储路径。不建议更改。').style("width:200px;")
                copywriting_config_var[str(data_len + 1)] = ui.input(label=f"音频存储路径#{int(data_len / 5) + 1}", value=tmp_config["audio_path"], placeholder='文案音频文件存储路径。不建议更改。').style("width:200px;")
                copywriting_config_var[str(data_len + 2)] = ui.input(label=f"连续播放数#{int(data_len / 5) + 1}", value=tmp_config["continuous_play_num"], placeholder='文案播放列表中连续播放的音频文件个数，如果超过了这个个数就会切换下一个文案列表').style("width:200px;")
                copywriting_config_var[str(data_len + 3)] = ui.input(label=f"连续播放时间#{int(data_len / 5) + 1}", value=tmp_config["max_play_time"], placeholder='文案播放列表中连续播放音频的时长，如果超过了这个时长就会切换下一个文案列表').style("width:200px;")
                copywriting_config_var[str(data_len + 4)] = ui.textarea(label=f"播放列表#{int(data_len / 5) + 1}", value=textarea_data_change(tmp_config["play_list"]), placeholder='此处填写需要播放的音频文件全名，填写完毕后点击 保存配置。文件全名从音频列表中复制，换行分隔，请勿随意填写').style("width:500px;")

    def copywriting_del(index):
        try:
            copywriting_config_card.remove(int(index) - 1)
            keys_to_delete = [str(5 * (int(index) - 1) + i) for i in range(5)]
            for key in keys_to_delete:
                if key in copywriting_config_var:
                    del copywriting_config_var[key]

            updates = {}
            for key in sorted(copywriting_config_var.keys(), key=int):
                new_key = str(int(key) - 5 if int(key) > int(keys_to_delete[-1]) else key)
                updates[new_key] = copywriting_config_var[key]

            copywriting_config_var.clear()
            copywriting_config_var.update(updates)
        except Exception as e:
            ui.notify(position="top", type="negative", message=f"错误，索引值配置有误：{e}")
            logger.error(traceback.format_exc())

    def copywriting_text_load():
        copywriting_text_path = input_copywriting_text_path.value
        if "" == copywriting_text_path:
            logger.warning("请输入 文案文本路径喵~")
            ui.notify(position="top", type="warning", message="请输入 文案文本路径喵~")
            return

        logger.info(f"准备加载 文件：[{copywriting_text_path}]")
        new_file_path = os.path.join(copywriting_text_path)

        content = common.read_file_return_content(new_file_path)
        if content is None:
            logger.error("读取失败！请检测配置、文件路径、文件名")
            ui.notify(position="top", type="negative", message="读取失败！请检测配置、文件路径、文件名")
            return

        textarea_copywriting_text.value = content
        logger.info(f"成功加载文案：{copywriting_text_path}")
        ui.notify(position="top", type="positive", message=f"成功加载文案：{copywriting_text_path}")

    def copywriting_save_text():
        content = textarea_copywriting_text.value
        copywriting_text_path = input_copywriting_text_path.value
        if "" == copywriting_text_path:
            logger.warning("请输入 文案文本路径喵~")
            ui.notify(position="top", type="warning", message="请输入 文案文本路径喵~")
            return

        new_file_path = os.path.join(copywriting_text_path)
        if common.write_content_to_file(new_file_path, content):
            ui.notify(position="top", type="positive", message="保存成功~")
        else:
            ui.notify(position="top", type="negative", message="保存失败！请查看日志排查问题")

    async def copywriting_audio_synthesis():
        ui.notify(position="top", type="warning", message="文案音频合成中，将会阻塞其他任务运行，请勿做其他操作，查看日志情况，耐心等待")
        logger.warning("文案音频合成中，将会阻塞其他任务运行，请勿做其他操作，查看日志情况，耐心等待")

        copywriting_text_path = input_copywriting_text_path.value
        copywriting_audio_save_path = input_copywriting_audio_save_path.value
        audio_synthesis_type = select_copywriting_audio_synthesis_type.value

        file_path = await audio.copywriting_synthesis_audio(copywriting_text_path, copywriting_audio_save_path, audio_synthesis_type)

        if file_path:
            ui.notify(position="top", type="positive", message=f"文案音频合成成功，存储于：{file_path}")
        else:
            ui.notify(position="top", type="negative", message="文案音频合成失败！请查看日志排查问题")
            return

        def clear_copywriting_audio_card(file_path):
            copywriting_audio_card.clear()
            if common.del_file(file_path):
                ui.notify(position="top", type="positive", message=f"删除文件成功：{file_path}")
            else:
                ui.notify(position="top", type="negative", message=f"删除文件失败：{file_path}")

        copywriting_audio_card.clear()
        tmp_label = ui.label(f"文案音频合成成功，存储于：{file_path}")
        tmp_label.move(copywriting_audio_card)
        audio_copywriting = ui.audio(src=file_path)
        audio_copywriting.move(copywriting_audio_card)
        button_copywriting_audio_del = ui.button('删除音频', on_click=lambda: clear_copywriting_audio_card(file_path), color=button_internal_color).style(button_internal_css)
        button_copywriting_audio_del.move(copywriting_audio_card)

    with ui.row():
        switch_copywriting_auto_play = ui.switch('自动播放', value=config.get("copywriting", "auto_play")).style(switch_internal_css)
        switch_copywriting_random_play = ui.switch('音频随机播放', value=config.get("copywriting", "random_play")).style(switch_internal_css)
        input_copywriting_audio_interval = ui.input(label='音频播放间隔', value=config.get("copywriting", "audio_interval"), placeholder='文案音频播放之间的间隔时间。就是前一个文案播放完成后，到后一个文案开始播放之间的间隔时间。').tooltip('文案音频播放之间的间隔时间。就是前一个文案播放完成后，到后一个文案开始播放之间的间隔时间。')
        input_copywriting_switching_interval = ui.input(label='音频切换间隔', value=config.get("copywriting", "switching_interval"), placeholder='文案音频切换到弹幕音频的切换间隔时间（反之一样）。\n就是在播放文案时，有弹幕触发并合成完毕，此时会暂停文案播放，然后等待这个间隔时间后，再播放弹幕回复音频。').tooltip('n就是在播放文案时，有弹幕触发并合成完毕，此时会暂停文案播放，然后等待这个间隔时间后，再播放弹幕回复音频。')
    with ui.row():
        input_copywriting_index = ui.input(label='文案索引', value="", placeholder='文案组的排序号，就是说第一个组是1，第二个组是2，以此类推。请填写纯正整数')
        button_copywriting_add = ui.button('增加文案组', on_click=copywriting_add, color=button_internal_color).style(button_internal_css)
        button_copywriting_del = ui.button('删除文案组', on_click=lambda: copywriting_del(input_copywriting_index.value), color=button_internal_color).style(button_internal_css)

    with copywriting_config_card:
        for index, copywriting_config in enumerate(config.get("copywriting", "config")):
            with copywriting_config_card.style(card_css):
                with ui.row():
                    copywriting_config_var[str(5 * index)] = ui.input(label=f"文案存储路径#{index + 1}", value=copywriting_config["file_path"], placeholder='文案文件存储路径。不建议更改。').style("width:200px;").tooltip('文案文件存储路径。不建议更改。')
                    copywriting_config_var[str(5 * index + 1)] = ui.input(label=f"音频存储路径#{index + 1}", value=copywriting_config["audio_path"], placeholder='文案音频文件存储路径。不建议更改。').style("width:200px;").tooltip('文案音频文件存储路径。不建议更改。')
                    copywriting_config_var[str(5 * index + 2)] = ui.input(label=f"连续播放数#{index + 1}", value=copywriting_config["continuous_play_num"], placeholder='文案播放列表中连续播放的音频文件个数，如果超过了这个个数就会切换下一个文案列表').style("width:200px;").tooltip('文案播放列表中连续播放的音频文件个数，如果超过了这个个数就会切换下一个文案列表')
                    copywriting_config_var[str(5 * index + 3)] = ui.input(label=f"连续播放时间#{index + 1}", value=copywriting_config["max_play_time"], placeholder='文案播放列表中连续播放音频的时长，如果超过了这个时长就会切换下一个文案列表').style("width:200px;").tooltip('文案播放列表中连续播放音频的时长，如果超过了这个时长就会切换下一个文案列表')
                    copywriting_config_var[str(5 * index + 4)] = ui.textarea(label=f"播放列表#{index + 1}", value=textarea_data_change(copywriting_config["play_list"]), placeholder='此处填写需要播放的音频文件全名，填写完毕后点击 保存配置。文件全名从音频列表中复制，换行分隔，请勿随意填写').style("width:500px;").tooltip('此处填写需要播放的音频文件全名，填写完毕后点击 保存配置。文件全名从音频列表中复制，换行分隔，请勿随意填写')

    with ui.card().style(card_css):
        ui.label("文案音频合成")
        with ui.row():
            input_copywriting_text_path = ui.input(label='文案文本路径', value=config.get("copywriting", "text_path"), placeholder='待合成的文案文本文件的路径').style("width:250px;").tooltip('待合成的文案文本文件的路径')
            button_copywriting_text_load = ui.button('加载文本', on_click=copywriting_text_load, color=button_internal_color).style(button_internal_css)
            input_copywriting_audio_save_path = ui.input(label='音频存储路径', value=config.get("copywriting", "audio_save_path"), placeholder='音频合成后存储的路径').style("width:250px;").tooltip('音频合成后存储的路径')
            select_copywriting_audio_synthesis_type = ui.select(
                label='语音合成',
                options=AUDIO_SYNTHESIS_TYPE_OPTIONS,
                value=config.get("copywriting", "audio_synthesis_type")
            ).style("width:200px;")
        with ui.row():
            textarea_copywriting_text = ui.textarea(label='文案文本', value='', placeholder='此处对需要合成文案音频的文本内容进行编辑。文案会自动根据逻辑进行切分，然后根据配置合成完整的一个音频文件。').style("width:1000px;").tooltip('此处对需要合成文案音频的文本内容进行编辑。文案会自动根据逻辑进行切分，然后根据配置合成完整的一个音频文件。')
        with ui.row():
            button_copywriting_save_text = ui.button('保存文案', on_click=copywriting_save_text, color=button_internal_color).style(button_internal_css)
            button_copywriting_audio_synthesis = ui.button('合成音频', on_click=lambda: copywriting_audio_synthesis(), color=button_internal_color).style(button_internal_css)
        copywriting_audio_card = ui.card()
        with copywriting_audio_card.style(card_css):
            with ui.row():
                ui.label("此处显示生成的文案音频，仅显示最新合成的文案音频，可以在此操作删除合成的音频")

    def save_config_array(config_data):
        tmp_arr = []
        for index in range(len(copywriting_config_var) // 5):
            tmp_arr.append({
                "file_path": copywriting_config_var[str(5 * index)].value,
                "audio_path": copywriting_config_var[str(5 * index + 1)].value,
                "continuous_play_num": int(copywriting_config_var[str(5 * index + 2)].value),
                "max_play_time": float(copywriting_config_var[str(5 * index + 3)].value),
                "play_list": common_textarea_handle(copywriting_config_var[str(5 * index + 4)].value),
            })
        config_data.setdefault("copywriting", {})["config"] = tmp_arr

    return PageConfig(
        mapping={
            "copywriting": {
                "auto_play": (switch_copywriting_auto_play, 'bool'),
                "random_play": (switch_copywriting_random_play, 'bool'),
                "audio_interval": (input_copywriting_audio_interval, 'str'),
                "switching_interval": (input_copywriting_switching_interval, 'str'),
                "text_path": (input_copywriting_text_path, 'str'),
                "audio_save_path": (input_copywriting_audio_save_path, 'str'),
                "audio_synthesis_type": (select_copywriting_audio_synthesis_type, 'str'),
            }
        },
        on_save=save_config_array,
    )
