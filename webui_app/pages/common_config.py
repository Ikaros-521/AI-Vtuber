"""通用配置（tab 现名「平台接入」）：这里仍然一次性建出全部控件，
由 webui_app/repage.py 把各区块整块改挂到 播报与输出 / 念弹幕与答谢 / 定时与闲时 … 等页面。
控件与 save_common 留在本模块，搬的只是 DOM 归属。"""
import json
import traceback

from nicegui import ui

from utils.my_log import logger
from webui_app.config_store import update_config
from webui_app.confirm import confirm_delete_group, delete_button
from webui_app.errors import explain
from webui_app.helpers import AUDIO_SYNTHESIS_TYPE_OPTIONS, common_textarea_handle, textarea_data_change
from webui_app.options import (
    CHAT_TYPE_OPTIONS,
    LIVE_MONITOR_PLATFORM_KEYS,
    VISUAL_BODY_OPTIONS,
    platform_options,
)
from webui_app.pages import PageConfig

_validator = None
_writer = None


def validate_config():
    """None = 可以保存；(提示语, 控件或 None) = 拦下来，并把用户带到那个控件。"""
    return _validator() if _validator is not None else None


def write_local_qa_file():
    return _writer() if _writer is not None else True


def build_common_config_tab(config, common, card_css, switch_internal_css, button_internal_color, button_internal_css):
    global _validator, _writer

    # -增加
    def schedule_add():
        data_len = len(schedule_var)
        tmp_config = {
            "enable": False,
            "time_min": 60,
            "time_max": 120,
            "copy": []
        }

        with schedule_config_card.style(card_css):
            with ui.row():
                schedule_var[str(data_len)] = ui.switch(text=f"启用任务#{int(data_len / 4) + 1}", value=tmp_config["enable"]).style(switch_internal_css)
                schedule_var[str(data_len + 1)] = ui.input(label=f"最小循环周期#{int(data_len / 4) + 1}", value=tmp_config["time_min"], placeholder='定时任务循环的周期最小时长（秒），即每间隔这个周期就会执行一次').style("width:100px;")
                schedule_var[str(data_len + 2)] = ui.input(label=f"最大循环周期#{int(data_len / 4) + 1}", value=tmp_config["time_max"], placeholder='定时任务循环的周期最大时长（秒），即每间隔这个周期就会执行一次').style("width:100px;")
                schedule_var[str(data_len + 3)] = ui.textarea(label=f"文案列表#{int(data_len / 4) + 1}", value=textarea_data_change(tmp_config["copy"]), placeholder='存放文案的列表，通过空格或换行分割，通过{变量}来替换关键数据，可修改源码自定义功能').style("width:500px;")


    # -删除
    def schedule_del(index):
        try:
            schedule_config_card.remove(int(index) - 1)
            # 删除操作
            keys_to_delete = [str(4 * (int(index) - 1) + i) for i in range(4)]
            for key in keys_to_delete:
                if key in schedule_var:
                    del schedule_var[key]

            # 重新编号剩余的键
            updates = {}
            for key in sorted(schedule_var.keys(), key=int):
                new_key = str(int(key) - 4 if int(key) > int(keys_to_delete[-1]) else key)
                updates[new_key] = schedule_var[key]

            # 应用更新
            schedule_var.clear()
            schedule_var.update(updates)
        except Exception as e:
            ui.notify(position="top", type="negative", message=f"错误，索引值配置有误：{e}")
            logger.error(traceback.format_exc())



    """
    动态文案
    """
    # 动态文案-增加
    def trends_copywriting_add():
        data_len = len(trends_copywriting_copywriting_var)
        tmp_config = {
            "folder_path": "",
            "prompt_change_enable": False,
            "prompt_change_content": ""
        }

        with trends_copywriting_config_card.style(card_css):
            with ui.row():
                trends_copywriting_copywriting_var[str(data_len)] = ui.input(label=f"文案路径#{int(data_len / 3) + 1}", value=tmp_config["folder_path"], placeholder='文案文件存储的文件夹路径').style("width:200px;")
                trends_copywriting_copywriting_var[str(data_len + 1)] = ui.switch(text=f"提示词转换#{int(data_len / 3) + 1}", value=tmp_config["prompt_change_enable"])
                trends_copywriting_copywriting_var[str(data_len + 2)] = ui.input(label=f"提示词转换内容#{int(data_len / 3) + 1}", value=tmp_config["prompt_change_content"], placeholder='使用此提示词内容对文案内容进行转换后再进行合成，使用的LLM为聊天类型配置').style("width:500px;")


    # 动态文案-删除
    def trends_copywriting_del(index):
        try:
            trends_copywriting_config_card.remove(int(index) - 1)
            # 删除操作
            keys_to_delete = [str(3 * (int(index) - 1) + i) for i in range(3)]
            for key in keys_to_delete:
                if key in trends_copywriting_copywriting_var:
                    del trends_copywriting_copywriting_var[key]

            # 重新编号剩余的键
            updates = {}
            for key in sorted(trends_copywriting_copywriting_var.keys(), key=int):
                new_key = str(int(key) - 3 if int(key) > int(keys_to_delete[-1]) else key)
                updates[new_key] = trends_copywriting_copywriting_var[key]

            # 应用更新
            trends_copywriting_copywriting_var.clear()
            trends_copywriting_copywriting_var.update(updates)
        except Exception as e:
            ui.notify(position="top", type="negative", message=f"错误，索引值配置有误：{e}")
            logger.error(traceback.format_exc())

    
    """
    联动程序
    """
    # 联动程序-增加
    def coordination_program_add():
        data_len = len(coordination_program_var)
        tmp_config = {
            "enable": True,
            "name": "",
            "executable": "",
            "parameters": []
        }

        with coordination_program_config_card.style(card_css):
            with ui.row():
                coordination_program_var[str(data_len)] = ui.switch(f'启用#{int(data_len / 4) + 1}', value=tmp_config["enable"]).style(switch_internal_css)
                coordination_program_var[str(data_len + 1)] = ui.input(label=f"程序名#{int(data_len / 4) + 1}", value=tmp_config["name"], placeholder='给你的程序取个名字，别整特殊符号！').style("width:200px;")
                coordination_program_var[str(data_len + 2)] = ui.input(label=f"可执行程序#{int(data_len / 4) + 1}", value=tmp_config["executable"], placeholder='可执行程序的路径，最好是绝对路径，如python的程序').style("width:400px;")
                coordination_program_var[str(data_len + 3)] = ui.textarea(label=f'参数#{int(data_len / 4) + 1}', value=textarea_data_change(tmp_config["parameters"]), placeholder='参数，可以传入多个参数，换行分隔。如启动的程序的路径，命令携带的传参等').style("width:500px;")


    # 联动程序-删除
    def coordination_program_del(index):
        try:
            coordination_program_config_card.remove(int(index) - 1)
            # 删除操作
            keys_to_delete = [str(4 * (int(index) - 1) + i) for i in range(4)]
            for key in keys_to_delete:
                if key in coordination_program_var:
                    del coordination_program_var[key]

            # 重新编号剩余的键
            updates = {}
            for key in sorted(coordination_program_var.keys(), key=int):
                new_key = str(int(key) - 4 if int(key) > int(keys_to_delete[-1]) else key)
                updates[new_key] = coordination_program_var[key]

            # 应用更新
            coordination_program_var.clear()
            coordination_program_var.update(updates)
        except Exception as e:
            ui.notify(position="top", type="negative", message=f"错误，索引值配置有误：{e}")
            logger.error(traceback.format_exc())


    """
    按键/文案映射
    """
    def key_mapping_add():
        data_len = len(key_mapping_config_var)
        tmp_config = {
            "keywords": [],
            "gift": [],
            "keys": [],
            "similarity": 1,
            "copywriting": [],
            "local_audio": [],
            "serial_name": "",
            "serial_send_data": [],
            "img_path": []
        }

        with key_mapping_config_card.style(card_css):
            with ui.row():
                num = int(data_len / 9) + 1
                key_mapping_config_var[str(data_len)] = ui.textarea(label=f"关键词#{num}", value=textarea_data_change(tmp_config["keywords"]), placeholder='此处输入触发的关键词，多个请以换行分隔').style("width:100px;")
                key_mapping_config_var[str(data_len + 1)] = ui.textarea(label=f"礼物#{num}", value=textarea_data_change(tmp_config["gift"]), placeholder='此处输入触发的礼物名，多个请以换行分隔').style("width:100px;")
                key_mapping_config_var[str(data_len + 2)] = ui.textarea(label=f"按键#{num}", value=textarea_data_change(tmp_config["keys"]), placeholder='此处输入你要映射的按键，多个按键请以换行分隔（按键名参考pyautogui规则）').style("width:100px;")
                key_mapping_config_var[str(data_len + 3)] = ui.input(label=f"相似度#{num}", value=tmp_config["similarity"], placeholder='关键词与用户输入的相似度，默认1即100%').style("width:50px;")
                key_mapping_config_var[str(data_len + 4)] = ui.textarea(label=f"文案#{num}", value=textarea_data_change(tmp_config["copywriting"]), placeholder='此处输入触发后合成的文案内容，多个请以换行分隔').style("width:300px;")
                key_mapping_config_var[str(data_len + 5)] = ui.textarea(label=f"本地音频#{num}", value=textarea_data_change(tmp_config["local_audio"]), placeholder='此处输入触发后播放的本地音频路径，多个请以换行分隔').style("width:300px;").tooltip('此处输入触发后播放的本地音频路径，多个请以换行分隔')
                key_mapping_config_var[str(data_len + 6)] = ui.input(label=f"串口名#{num}", value=tmp_config["serial_name"], placeholder='例如：COM1').style("width:100px;").tooltip('串口页配置的串口名，例如：COM1')
                key_mapping_config_var[str(data_len + 7)] = ui.textarea(label=f"串口发送内容#{num}", value=textarea_data_change(tmp_config["serial_send_data"]), placeholder='多个请以换行分隔，ASCII例如：open led\nHEX例如（2个字符的十六进制字符）：313233').style("width:300px;").tooltip('此处输入发送到串口的数据内容，数据类型根据串口页设置决定，多个请以换行分隔')
                key_mapping_config_var[str(data_len + 8)] = ui.textarea(label=f"图片路径#{num}", value=textarea_data_change(tmp_config["img_path"]), placeholder='多个请以换行分隔，支持绝对路径或相对路径，需要注意路径的斜杠哈').style("width:300px;").tooltip('此处输入图片路径，多个请以换行分隔。默认随机显示')
                          
    
    def key_mapping_del(index):
        try:
            num = 9
            key_mapping_config_card.remove(int(index) - 1)
            # 删除操作
            keys_to_delete = [str(num * (int(index) - 1) + i) for i in range(num)]
            for key in keys_to_delete:
                if key in key_mapping_config_var:
                    del key_mapping_config_var[key]

            # 重新编号剩余的键
            updates = {}
            for key in sorted(key_mapping_config_var.keys(), key=int):
                new_key = str(int(key) - num if int(key) > int(keys_to_delete[-1]) else key)
                updates[new_key] = key_mapping_config_var[key]

            # 应用更新
            key_mapping_config_var.clear()
            key_mapping_config_var.update(updates)
        except Exception as e:
            ui.notify(position="top", type="negative", message=f"错误，索引值配置有误：{e}")
            logger.error(traceback.format_exc())


    """
    自定义命令
    """
    
    # 自定义命令-增加
    def custom_cmd_add():
        data_len = len(custom_cmd_config_var)

        tmp_config = {
            "keywords": [],
            "similarity": 1,
            "api_url": "",
            "api_type": "",
            "resp_data_type": "",
            "data_analysis": "",
            "resp_template": ""
        }

        with custom_cmd_config_card.style(card_css):
            with ui.row():
                custom_cmd_config_var[str(data_len)] = ui.textarea(label=f"关键词#{int(data_len / 7) + 1}", value=textarea_data_change(tmp_config["keywords"]), placeholder='此处输入触发的关键词，多个请以换行分隔').style("width:200px;")
                custom_cmd_config_var[str(data_len + 1)] = ui.input(label=f"相似度#{int(data_len / 7) + 1}", value=tmp_config["similarity"], placeholder='关键词与用户输入的相似度，默认1即100%').style("width:100px;")
                custom_cmd_config_var[str(data_len + 2)] = ui.textarea(label=f"API URL#{int(data_len / 7) + 1}", value=tmp_config["api_url"], placeholder='发送HTTP请求的API链接', validation={'请输入正确格式的URL': lambda value: common.is_url_check(value),}).style("width:300px;")
                custom_cmd_config_var[str(data_len + 3)] = ui.select(label=f"API类型#{int(data_len / 7) + 1}", value=tmp_config["api_type"], options={"GET": "GET"}).style("width:100px;")
                custom_cmd_config_var[str(data_len + 4)] = ui.select(label=f"请求返回数据类型#{int(data_len / 7) + 1}", value=tmp_config["resp_data_type"], options={"json": "json", "content": "content"}).style("width:150px;")
                custom_cmd_config_var[str(data_len + 5)] = ui.textarea(label=f"数据解析（eval执行）#{int(data_len / 7) + 1}", value=tmp_config["data_analysis"], placeholder='数据解析，请不要随意修改resp变量，会被用于最后返回数据内容的解析').style("width:200px;")
                custom_cmd_config_var[str(data_len + 6)] = ui.textarea(label=f"返回内容模板#{int(data_len / 7) + 1}", value=tmp_config["resp_template"], placeholder='请不要随意删除data变量，支持动态变量，最终会合并成完成内容进行音频合成').style("width:300px;")


    # 自定义命令-删除
    def custom_cmd_del(index):
        try:
            custom_cmd_config_card.remove(int(index) - 1)
            # 删除操作
            keys_to_delete = [str(7 * (int(index) - 1) + i) for i in range(7)]
            for key in keys_to_delete:
                if key in custom_cmd_config_var:
                    del custom_cmd_config_var[key]

            # 重新编号剩余的键
            updates = {}
            for key in sorted(custom_cmd_config_var.keys(), key=int):
                new_key = str(int(key) - 7 if int(key) > int(keys_to_delete[-1]) else key)
                updates[new_key] = custom_cmd_config_var[key]

            # 应用更新
            custom_cmd_config_var.clear()
            custom_cmd_config_var.update(updates)
        except Exception as e:
            ui.notify(position="top", type="negative", message=f"错误，索引值配置有误：{e}")
            logger.error(traceback.format_exc())

    # -增加

    with ui.row():
        
        select_platform = ui.select(
            label='平台', 
            options=platform_options(config.get("platform")), 
            value=config.get("platform")
        ).style("width:200px;")

        input_room_display_id = ui.input(label='直播间号', placeholder='一般为直播间URL最后/后面的字母或数字', value=config.get("room_display_id")).style("width:200px;").tooltip('一般为直播间URL最后/后面的字母或数字')

        select_chat_type = ui.select(
            label='大语言模型', 
            options=CHAT_TYPE_OPTIONS, 
            value=config.get("chat_type")
        ).style("width:200px;").tooltip('选用的LLM类型。相关的弹幕信息等会传递给此LLM进行推理，获取回答')

        select_visual_body = ui.select(
            label='虚拟身体', 
            options=VISUAL_BODY_OPTIONS, 
            value=config.get("visual_body")
        ).style("width:200px;").tooltip('选用的虚拟身体类型。如果使用VTS对接，就选其他，用什么展示身体就选什么，大部分对接的选项需要单独启动对应的服务端程序，请勿随便选择。')

        select_audio_synthesis_type = ui.select(
            label='语音合成', 
            options=AUDIO_SYNTHESIS_TYPE_OPTIONS, 
            value=config.get("audio_synthesis_type")
        ).style("width:200px;").tooltip('选用的TTS类型，所有的文本内容最终都将通过此TTS进行语音合成')

    with ui.row():
        select_need_lang = ui.select(
            label='回复语言', 
            options={'none': '所有', 'zh': '中文', 'en': '英文', 'jp': '日文'}, 
            value=config.get("need_lang")
        ).style("width:200px;").tooltip('限制回复的语言，如：选中中文，则只会回复中文提问，其他语言将被跳过')

        input_before_prompt = ui.input(label='提示词前缀', placeholder='此配置会追加在弹幕前，再发送给LLM处理', value=config.get("before_prompt")).style("width:200px;").tooltip('此配置会追加在弹幕前，再发送给LLM处理')
        input_after_prompt = ui.input(label='提示词后缀', placeholder='此配置会追加在弹幕后，再发送给LLM处理', value=config.get("after_prompt")).style("width:200px;").tooltip('此配置会追加在弹幕后，再发送给LLM处理')
        switch_comment_template_enable = ui.switch('启用弹幕模板', value=config.get("comment_template", "enable")).style(switch_internal_css).tooltip('此配置会追加在弹幕后，再发送给LLM处理')
        input_comment_template_copywriting = ui.input(label='弹幕模板', value=config.get("comment_template", "copywriting"), placeholder='此配置会对弹幕内容进行修改，{}内为变量，会被替换为指定内容，请勿随意删除变量').style("width:200px;").tooltip('此配置会对弹幕内容进行修改，{}内为变量，会被替换为指定内容，请勿随意删除变量')
        switch_reply_template_enable = ui.switch('启用回复模板', value=config.get("reply_template", "enable")).style(switch_internal_css).tooltip('此配置会在LLM输出的答案中进行回复内容的重新构建')
        input_reply_template_username_max_len = ui.input(label='回复用户名的最大长度', value=config.get("reply_template", "username_max_len"), placeholder='回复用户名的最大长度').style("width:200px;").tooltip('回复用户名的最大长度')
        textarea_reply_template_copywriting = ui.textarea(
            label='回复模板', 
            placeholder='此配置会对LLM回复内容进行修改，{}内为变量，会被替换为指定内容，请勿随意删除变量', 
            value=textarea_data_change(config.get("reply_template", "copywriting"))
        ).style("width:500px;").tooltip('此配置会对LLM回复内容进行修改，{}内为变量，会被替换为指定内容，请勿随意删除变量')

    with ui.expansion('功能管理', icon="settings", value=True).classes('w-full'):

        with ui.card().style(card_css):
            ui.label('平台相关')
            with ui.card().style(card_css):
                ui.label('哔哩哔哩')
                with ui.row():
                    select_bilibili_login_type = ui.select(
                        label='登录方式',
                        options={'cookie': 'cookie', '手机扫码': '手机扫码', '手机扫码-终端': '手机扫码-终端', 'open_live': '开放平台', '不登录': '不登录'},
                        value=config.get("bilibili", "login_type")
                    ).style("width:100px")
                    input_bilibili_cookie = ui.input(label='cookie', placeholder='b站登录后F12抓网络包获取cookie，强烈建议使用小号！有封号风险，虽然实际上没听说有人被封过', value=config.get("bilibili", "cookie")).style("width:500px;").tooltip('b站登录后F12抓网络包获取cookie，强烈建议使用小号！有封号风险，虽然实际上没听说有人被封过')
                    input_bilibili_ac_time_value = ui.input(label='ac_time_value', placeholder='b站登录后，F12控制台，输入window.localStorage.ac_time_value获取(如果没有，请重新登录)', value=config.get("bilibili", "ac_time_value")).style("width:500px;").tooltip('仅在平台：哔哩哔哩，情况下可选填写。b站登录后，F12控制台，输入window.localStorage.ac_time_value获取(如果没有，请重新登录)')
                with ui.row():
                    with ui.card().style(card_css):
                        ui.label('开放平台')
                        with ui.row():
                            input_bilibili_open_live_ACCESS_KEY_ID = ui.input(label='ACCESS_KEY_ID', value=config.get("bilibili", "open_live", "ACCESS_KEY_ID"), placeholder='开放平台ACCESS_KEY_ID').style("width:160px;").tooltip('仅在平台：哔哩哔哩2，登录方式：开放平台，情况下填写。开放平台ACCESS_KEY_ID')
                            input_bilibili_open_live_ACCESS_KEY_SECRET = ui.input(label='ACCESS_KEY_SECRET', value=config.get("bilibili", "open_live", "ACCESS_KEY_SECRET"), placeholder='开放平台ACCESS_KEY_SECRET').style("width:200px;").tooltip('仅在平台：哔哩哔哩2，登录方式：开放平台，情况下填写。开放平台ACCESS_KEY_SECRET')
                            input_bilibili_open_live_APP_ID = ui.input(label='项目ID', value=config.get("bilibili", "open_live", "APP_ID"), placeholder='开放平台 创作者服务中心 项目ID').style("width:100px;").tooltip('仅在平台：哔哩哔哩2，登录方式：开放平台，情况下填写。开放平台 创作者服务中心 项目ID')
                            input_bilibili_open_live_ROOM_OWNER_AUTH_CODE = ui.input(label='身份码', value=config.get("bilibili", "open_live", "ROOM_OWNER_AUTH_CODE"), placeholder='直播中心用户 身份码').style("width:100px;").tooltip('仅在平台：哔哩哔哩2，登录方式：开放平台，情况下填写。直播中心用户 身份码')
            with ui.card().style(card_css):
                ui.label('twitch')
                with ui.row():
                    input_twitch_token = ui.input(label='token', value=config.get("twitch", "token"), placeholder='访问 https://twitchapps.com/tmi/ 获取，格式为：oauth:xxx').style("width:300px;")
                    input_twitch_user = ui.input(label='用户名', value=config.get("twitch", "user"), placeholder='你的twitch账号用户名').style("width:300px;")
                    input_twitch_proxy_server = ui.input(label='HTTP代理IP地址', value=config.get("twitch", "proxy_server"), placeholder='代理软件，http协议监听的ip地址，一般为：127.0.0.1').style("width:200px;")
                    input_twitch_proxy_port = ui.input(label='HTTP代理端口', value=config.get("twitch", "proxy_port"), placeholder='代理软件，http协议监听的端口，一般为：1080').style("width:200px;")
            with ui.card().style(card_css):
                ui.label('直播弹幕监听助手')
                with ui.row():
                    input_live_monitor_assistant_ws_ip = ui.input(label='监听IP', value=config.get("live_monitor_assistant", "ws_ip") or '127.0.0.1', placeholder='本机监听地址，一般为：127.0.0.1').style("width:200px;").tooltip('快手2、拼多多、斗鱼、1688、淘宝这些平台的弹幕，是由「直播弹幕监听助手」(游猴) 通过 websocket 推给本机的，本机就监听这个地址。助手和本程序在同一台电脑就填 127.0.0.1；助手在别的设备上就填这台设备对内开放的地址')
                    input_live_monitor_assistant_ws_port = ui.input(label='监听端口', value=config.get("live_monitor_assistant", "ws_port") or 5001, placeholder='默认 5001').style("width:120px;").tooltip('助手侧要连接的端口，必须和这里一致。端口填得不合法时，程序会退回默认端口 5001 并在日志里报错')

        if config.get("webui", "show_card", "common_config", "play_audio"):
            with ui.card().style(card_css):
                ui.label('音频播放')
                with ui.row():
                    switch_play_audio_enable = ui.switch('启用', value=config.get("play_audio", "enable")).style(switch_internal_css)
                    switch_play_audio_text_split_enable = ui.switch('启用文本切分', value=config.get("play_audio", "text_split_enable")).style(switch_internal_css).tooltip('启用后会将LLM等待合成音频的消息根据内部切分算法切分成多个短句，以便TTS快速合成')
                    switch_play_audio_info_to_callback = ui.switch('音频信息回传给内部接口', value=config.get("play_audio", "info_to_callback")).style(switch_internal_css).tooltip('启用后，会在当前音频播放完毕后，将程序中等待播放的音频信息传递给内部接口，用于闲时任务的闲时清零功能。\n不过这个功能会一定程度的拖慢程序运行，如果你不需要闲时清零，可以关闭此功能来提高响应速度')
                    
                with ui.row():
                    input_play_audio_interval_num_min = ui.input(label='间隔时间重复次数最小值', value=config.get("play_audio", "interval_num_min"), placeholder='普通音频播放间隔时间，重复睡眠次数最小值。会在最大最小值之间随机生成一个重复次数，就是 次数 x 时间 = 最终间隔时间').tooltip('普通音频播放间隔时间重复睡眠次数最小值。会在最大最小值之间随机生成一个重复次数，就是 次数 x 时间 = 最终间隔时间')
                    input_play_audio_interval_num_max = ui.input(label='间隔时间重复次数最大值', value=config.get("play_audio", "interval_num_max"), placeholder='普通音频播放间隔时间，重复睡眠次数最大值。会在最大最小值之间随机生成一个重复次数，就是 次数 x 时间 = 最终间隔时间').tooltip('普通音频播放间隔时间重复睡眠次数最大值。会在最大最小值之间随机生成一个重复次数，就是 次数 x 时间 = 最终间隔时间')
                    input_play_audio_normal_interval_min = ui.input(label='普通音频播放间隔最小值', value=config.get("play_audio", "normal_interval_min"), placeholder='就是弹幕回复、唱歌等音频播放结束后到播放下一个音频之间的一个间隔时间，单位：秒').tooltip('就是弹幕回复、唱歌等音频播放结束后到播放下一个音频之间的一个间隔时间，单位：秒。次数 x 时间 = 最终间隔时间')
                    input_play_audio_normal_interval_max = ui.input(label='普通音频播放间隔最大值', value=config.get("play_audio", "normal_interval_max"), placeholder='就是弹幕回复、唱歌等音频播放结束后到播放下一个音频之间的一个间隔时间，单位：秒').tooltip('就是弹幕回复、唱歌等音频播放结束后到播放下一个音频之间的一个间隔时间，单位：秒。次数 x 时间 = 最终间隔时间')
                    
                    input_play_audio_out_path = ui.input(label='音频输出路径', placeholder='音频文件合成后存储的路径，支持相对路径或绝对路径', value=config.get("play_audio", "out_path")).tooltip('音频文件合成后存储的路径，支持相对路径或绝对路径')
                    select_play_audio_player = ui.select(
                        label='音频播放器',
                        options={'pygame': 'pygame', 'audio_player_v2': 'audio_player_v2', 'audio_player': 'audio_player'},
                        value=config.get("play_audio", "player")
                    ).style("width:200px").tooltip('选用的音频播放器，默认pygame不需要再安装其他程序。audio player需要单独安装对接，详情看视频教程')
            
                with ui.card().style(card_css):
                    ui.label('audio_player')
                    with ui.row():
                        input_audio_player_api_ip_port = ui.input(
                            label='API地址', 
                            value=config.get("audio_player", "api_ip_port"), 
                            placeholder='audio_player的API地址，只需要 http://ip:端口 即可',
                            validation={
                                '请输入正确格式的URL': lambda value: common.is_url_check(value),
                            }
                        ).style("width:200px;").tooltip('仅在 音频播放器：audio_player等，情况下填写。audio_player的API地址，只需要 http://ip:端口 即可')

                with ui.card().style(card_css):
                    ui.label('音频随机变速')     
                    with ui.grid(columns=3):
                        switch_audio_random_speed_normal_enable = ui.switch('普通音频变速', value=config.get("audio_random_speed", "normal", "enable")).style(switch_internal_css).tooltip('是否启用 针对 普通音频的音频变速功能。此功能需要安装配置ffmpeg才能使用')
                        input_audio_random_speed_normal_speed_min = ui.input(label='速度下限', value=config.get("audio_random_speed", "normal", "speed_min")).style("width:200px;").tooltip('音频变速的下限，最终速度会在上下限之间随机一个值进行变速')
                        input_audio_random_speed_normal_speed_max = ui.input(label='速度上限', value=config.get("audio_random_speed", "normal", "speed_max")).style("width:200px;").tooltip('音频变速的上限，最终速度会在上下限之间随机一个值进行变速')
                    with ui.grid(columns=3):
                        switch_audio_random_speed_copywriting_enable = ui.switch('文案音频变速', value=config.get("audio_random_speed", "copywriting", "enable")).style(switch_internal_css).tooltip('是否启用 针对 文案页音频的音频变速功能。此功能需要安装配置ffmpeg才能使用')
                        input_audio_random_speed_copywriting_speed_min = ui.input(label='速度下限', value=config.get("audio_random_speed", "copywriting", "speed_min")).style("width:200px;").tooltip('音频变速的下限，最终速度会在上下限之间随机一个值进行变速')
                        input_audio_random_speed_copywriting_speed_max = ui.input(label='速度上限', value=config.get("audio_random_speed", "copywriting", "speed_max")).style("width:200px;").tooltip('音频变速的上限，最终速度会在上下限之间随机一个值进行变速')

    with ui.expansion('互动功能', icon="question_answer", value=True).classes('w-full'):

        if config.get("webui", "show_card", "common_config", "read_comment"):
            with ui.card().style(card_css):
                ui.label('念弹幕')
                with ui.grid(columns=4):
                    switch_read_comment_enable = ui.switch('启用', value=config.get("read_comment", "enable")).style(switch_internal_css)
                    switch_read_comment_read_username_enable = ui.switch('念用户名', value=config.get("read_comment", "read_username_enable")).style(switch_internal_css)
                    input_read_comment_username_max_len = ui.input(label='用户名最大长度', value=config.get("read_comment", "username_max_len"), placeholder='需要保留的用户名的最大长度，超出部分将被丢弃').style("width:100px;").tooltip('需要保留的用户名的最大长度，超出部分将被丢弃')
                    switch_read_comment_voice_change = ui.switch('变声', value=config.get("read_comment", "voice_change")).style(switch_internal_css)
                with ui.grid(columns=2):
                    textarea_read_comment_read_username_copywriting = ui.textarea(
                        label='念用户名文案', 
                        placeholder='念用户名时使用的文案，可以自定义编辑多个（换行分隔），实际中会随机一个使用', 
                        value=textarea_data_change(config.get("read_comment", "read_username_copywriting"))
                    ).style("width:500px;").tooltip('念用户名时使用的文案，可以自定义编辑多个（换行分隔），实际中会随机一个使用')
                with ui.row():
                    switch_read_comment_periodic_trigger_enable = ui.switch('周期性触发启用', value=config.get("read_comment", "periodic_trigger", "enable")).style(switch_internal_css)
                    input_read_comment_periodic_trigger_periodic_time_min = ui.input(
                        label='触发周期最小值', 
                        value=config.get("read_comment", "periodic_trigger", "periodic_time_min"), 
                        placeholder='例如：5'
                    ).style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                    input_read_comment_periodic_trigger_periodic_time_max = ui.input(
                        label='触发周期最大值', 
                        value=config.get("read_comment", "periodic_trigger", "periodic_time_max"), 
                        placeholder='例如：10'
                    ).style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                    input_read_comment_periodic_trigger_trigger_num_min = ui.input(
                        label='触发次数最小值', 
                        value=config.get("read_comment", "periodic_trigger", "trigger_num_min"), 
                        placeholder='例如：0'
                    ).style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成')
                    input_read_comment_periodic_trigger_trigger_num_max = ui.input(
                        label='触发次数最大值', 
                        value=config.get("read_comment", "periodic_trigger", "trigger_num_max"), 
                        placeholder='例如：1'
                    ).style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成')
        
        if config.get("webui", "show_card", "common_config", "local_qa"):
            with ui.card().style(card_css):
                ui.label('本地问答')
                with ui.row():
                    switch_local_qa_periodic_trigger_enable = ui.switch('周期性触发启用', value=config.get("local_qa", "periodic_trigger", "enable")).style(switch_internal_css)
                    input_local_qa_periodic_trigger_periodic_time_min = ui.input(label='触发周期最小值', value=config.get("local_qa", "periodic_trigger", "periodic_time_min"), placeholder='每隔这个周期的时间会触发n次此功能').style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                    input_local_qa_periodic_trigger_periodic_time_max = ui.input(label='触发周期最大值', value=config.get("local_qa", "periodic_trigger", "periodic_time_max"), placeholder='每隔这个周期的时间会触发n次此功能').style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                    input_local_qa_periodic_trigger_trigger_num_min = ui.input(label='触发次数最小值', value=config.get("local_qa", "periodic_trigger", "trigger_num_min"), placeholder='周期到后，会触发n次此功能').style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成') 
                    input_local_qa_periodic_trigger_trigger_num_max = ui.input(label='触发次数最大值', value=config.get("local_qa", "periodic_trigger", "trigger_num_max"), placeholder='周期到后，会触发n次此功能').style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成') 
                    
                with ui.grid(columns=5):
                    switch_local_qa_text_enable = ui.switch('启用文本匹配', value=config.get("local_qa", "text", "enable")).style(switch_internal_css)
                    select_local_qa_text_type = ui.select(
                        label='弹幕日志类型',
                        options={'json': '自定义json', 'text': '一问一答'},
                        value=config.get("local_qa", "text", "type")
                    )
                    input_local_qa_text_file_path = ui.input(label='文本问答数据路径', placeholder='本地问答文本数据存储路径', value=config.get("local_qa", "text", "file_path")).style("width:200px;")
                    input_local_qa_text_similarity = ui.input(label='文本最低相似度', placeholder='最低文本匹配相似度，就是说用户发送的内容和本地问答库中设定的内容的最低相似度。\n低了就会被当做一般弹幕处理', value=config.get("local_qa", "text", "similarity")).style("width:200px;")
                    input_local_qa_text_username_max_len = ui.input(label='用户名最大长度', value=config.get("local_qa", "text", "username_max_len"), placeholder='需要保留的用户名的最大长度，超出部分将被丢弃').style("width:100px;")       
                with ui.grid(columns=4):
                    switch_local_qa_audio_enable = ui.switch('启用音频匹配', value=config.get("local_qa", "audio", "enable")).style(switch_internal_css)
                    input_local_qa_audio_file_path = ui.input(label='音频存储路径', placeholder='本地问答音频文件存储路径', value=config.get("local_qa", "audio", "file_path")).style("width:200px;")
                    input_local_qa_audio_similarity = ui.input(label='音频最低相似度', placeholder='最低音频匹配相似度，就是说用户发送的内容和本地音频库中音频文件名的最低相似度。\n低了就会被当做一般弹幕处理', value=config.get("local_qa", "audio", "similarity")).style("width:200px;")
                with ui.row():
                    input_local_qa_text_json_file_path = ui.input(label='json文件路径', placeholder='填写json文件路径，默认为本地问答文本数据存储路径', value=config.get("local_qa", "text", "file_path")).style("width:200px;").tooltip("填写json文件路径，默认为本地问答文本数据存储路径")

                    def local_qa_text_json_file_reload():
                        try:
                            # 只做了个判空 所以别乱填
                            if input_local_qa_text_json_file_path.value != "":
                                textarea_local_qa_text_json_file_content.value = json.dumps(common.read_file(input_local_qa_text_json_file_path.value, "dict"), ensure_ascii=False, indent=3)
                        except Exception as e:
                            logger.error(traceback.format_exc())
                            ui.notify(f"读这个路径读不了：{explain(e)}", position="top", type="negative")

                    button_local_qa_text_json_file_reload = ui.button('加载文件', on_click=lambda: local_qa_text_json_file_reload(), color=button_internal_color).style(button_internal_css)

                    textarea_local_qa_text_json_file_content = ui.textarea(label='JSON文件内容', placeholder='注意格式！').style("width:700px;")

                    local_qa_text_json_file_reload()
        
        if config.get("webui", "show_card", "common_config", "thanks"):
            with ui.card().style(card_css):
                ui.label('答谢')  
                with ui.row():
                    input_thanks_username_max_len = ui.input(label='用户名最大长度', value=config.get("thanks", "username_max_len"), placeholder='需要保留的用户名的最大长度，超出部分将被丢弃').style("width:100px;")       
                with ui.expansion('入场设置', icon="settings", value=True).classes('w-full'):
                    with ui.row():
                        switch_thanks_entrance_enable = ui.switch('启用入场欢迎', value=config.get("thanks", "entrance_enable")).style(switch_internal_css)
                        switch_thanks_entrance_random = ui.switch('随机选取', value=config.get("thanks", "entrance_random")).style(switch_internal_css)
                        textarea_thanks_entrance_copy = ui.textarea(label='入场文案', value=textarea_data_change(config.get("thanks", "entrance_copy")), placeholder='用户进入直播间的相关文案，请勿动 {username}，此字符串用于替换用户名').style("width:500px;")

                    with ui.row():
                        switch_thanks_entrance_periodic_trigger_enable = ui.switch('周期性触发启用', value=config.get("thanks", "entrance", "periodic_trigger", "enable")).style(switch_internal_css)
                        input_thanks_entrance_periodic_trigger_periodic_time_min = ui.input(label='触发周期最小值', value=config.get("thanks", "entrance", "periodic_trigger", "periodic_time_min"), placeholder='每隔这个周期的时间会触发n次此功能').style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                        input_thanks_entrance_periodic_trigger_periodic_time_max = ui.input(label='触发周期最大值', value=config.get("thanks", "entrance", "periodic_trigger", "periodic_time_max"), placeholder='每隔这个周期的时间会触发n次此功能').style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                        input_thanks_entrance_periodic_trigger_trigger_num_min = ui.input(label='触发次数最小值', value=config.get("thanks", "entrance", "periodic_trigger", "trigger_num_min"), placeholder='周期到后，会触发n次此功能').style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成') 
                        input_thanks_entrance_periodic_trigger_trigger_num_max = ui.input(label='触发次数最大值', value=config.get("thanks", "entrance", "periodic_trigger", "trigger_num_max"), placeholder='周期到后，会触发n次此功能').style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成') 
                with ui.expansion('礼物设置', icon="settings", value=True).classes('w-full'):
                    with ui.row():
                        switch_thanks_gift_enable = ui.switch('启用礼物答谢', value=config.get("thanks", "gift_enable")).style(switch_internal_css)
                        switch_thanks_gift_random = ui.switch('随机选取', value=config.get("thanks", "gift_random")).style(switch_internal_css)
                        textarea_thanks_gift_copy = ui.textarea(label='礼物文案', value=textarea_data_change(config.get("thanks", "gift_copy")), placeholder='用户赠送礼物的相关文案，请勿动 {username} 和 {gift_name}，此字符串用于替换用户名和礼物名').style("width:500px;")
                        input_thanks_lowest_price = ui.input(label='最低答谢礼物价格', value=config.get("thanks", "lowest_price"), placeholder='设置最低答谢礼物的价格（元），低于这个设置的礼物不会触发答谢').style("width:100px;")
                    with ui.row():
                        switch_thanks_gift_periodic_trigger_enable = ui.switch('周期性触发启用', value=config.get("thanks", "gift", "periodic_trigger", "enable")).style(switch_internal_css)
                        input_thanks_gift_periodic_trigger_periodic_time_min = ui.input(label='触发周期最小值', value=config.get("thanks", "gift", "periodic_trigger", "periodic_time_min"), placeholder='每隔这个周期的时间会触发n次此功能').style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                        input_thanks_gift_periodic_trigger_periodic_time_max = ui.input(label='触发周期最大值', value=config.get("thanks", "gift", "periodic_trigger", "periodic_time_max"), placeholder='每隔这个周期的时间会触发n次此功能').style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                        input_thanks_gift_periodic_trigger_trigger_num_min = ui.input(label='触发次数最小值', value=config.get("thanks", "gift", "periodic_trigger", "trigger_num_min"), placeholder='周期到后，会触发n次此功能').style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成') 
                        input_thanks_gift_periodic_trigger_trigger_num_max = ui.input(label='触发次数最大值', value=config.get("thanks", "gift", "periodic_trigger", "trigger_num_max"), placeholder='周期到后，会触发n次此功能').style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成') 
                with ui.expansion('关注设置', icon="settings", value=True).classes('w-full'):
                    with ui.row():
                        switch_thanks_follow_enable = ui.switch('启用关注答谢', value=config.get("thanks", "follow_enable")).style(switch_internal_css)
                        switch_thanks_follow_random = ui.switch('随机选取', value=config.get("thanks", "follow_random")).style(switch_internal_css)
                        textarea_thanks_follow_copy = ui.textarea(label='关注文案', value=textarea_data_change(config.get("thanks", "follow_copy")), placeholder='用户关注时的相关文案，请勿动 {username}，此字符串用于替换用户名').style("width:500px;")
                    with ui.row():
                        switch_thanks_follow_periodic_trigger_enable = ui.switch(
                            '周期性触发启用', 
                            value=config.get("thanks", "follow", "periodic_trigger", "enable")
                        ).style(switch_internal_css)
                        input_thanks_follow_periodic_trigger_periodic_time_min = ui.input(
                            label='触发周期最小值', 
                            value=config.get("thanks", "follow", "periodic_trigger", "periodic_time_min"), 
                            placeholder='每隔这个周期的时间会触发n次此功能'
                        ).style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                        input_thanks_follow_periodic_trigger_periodic_time_max = ui.input(
                            label='触发周期最大值', 
                            value=config.get("thanks", "follow", "periodic_trigger", "periodic_time_max"), 
                            placeholder='每隔这个周期的时间会触发n次此功能'
                        ).style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                        input_thanks_follow_periodic_trigger_trigger_num_min = ui.input(
                            label='触发次数最小值', 
                            value=config.get("thanks", "follow", "periodic_trigger", "trigger_num_min"), 
                            placeholder='周期到后，会触发n次此功能'
                        ).style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成') 
                        input_thanks_follow_periodic_trigger_trigger_num_max = ui.input(
                            label='触发次数最大值', 
                            value=config.get("thanks", "follow", "periodic_trigger", "trigger_num_max"), 
                            placeholder='周期到后，会触发n次此功能'
                        ).style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成') 
                
        if config.get("webui", "show_card", "common_config", "choose_song"): 
            with ui.card().style(card_css):
                ui.label('点歌模式') 
                with ui.row():
                    switch_choose_song_enable = ui.switch('启用', value=config.get("choose_song", "enable")).style(switch_internal_css)
                    textarea_choose_song_start_cmd = ui.textarea(
                        label='点歌触发命令', 
                        value=textarea_data_change(config.get("choose_song", "start_cmd")), 
                        placeholder='点歌触发命令，换行分隔，支持多个命令，弹幕发送触发（完全匹配才行）'
                    ).style("width:200px;").tooltip('点歌触发命令，换行分隔，支持多个命令，弹幕发送触发（完全匹配才行）')
                    textarea_choose_song_stop_cmd = ui.textarea(
                        label='取消点歌命令', 
                        value=textarea_data_change(config.get("choose_song", "stop_cmd")), 
                        placeholder='停止点歌命令，换行分隔，支持多个命令，弹幕发送触发（完全匹配才行）'
                    ).style("width:200px;").tooltip('停止点歌命令，换行分隔，支持多个命令，弹幕发送触发（完全匹配才行）')
                    textarea_choose_song_random_cmd = ui.textarea(
                        label='随机点歌命令', 
                        value=textarea_data_change(config.get("choose_song", "random_cmd")), 
                        placeholder='随机点歌命令，换行分隔，支持多个命令，弹幕发送触发（完全匹配才行）'
                    ).style("width:200px;").tooltip('随机点歌命令，换行分隔，支持多个命令，弹幕发送触发（完全匹配才行）')
                with ui.row():
                    input_choose_song_song_path = ui.input(
                        label='歌曲路径', 
                        value=config.get("choose_song", "song_path"), 
                        placeholder='歌曲音频存放的路径，会自动读取音频文件'
                    ).style("width:200px;").tooltip('歌曲音频存放的路径，会自动读取音频文件')
                    input_choose_song_match_fail_copy = ui.input(
                        label='匹配失败文案', 
                        value=config.get("choose_song", "match_fail_copy"), 
                        placeholder='匹配失败返回的音频文案 注意 {content} 这个是用于替换用户发送的歌名的，请务必不要乱删！影响使用！'
                    ).style("width:300px;").tooltip('匹配失败返回的音频文案 注意 {content} 这个是用于替换用户发送的歌名的，请务必不要乱删！影响使用！')
                    input_choose_song_similarity = ui.input(
                        label='匹配最低相似度', 
                        value=config.get("choose_song", "similarity"), 
                        placeholder='最低音频匹配相似度，就是说用户发送的内容和本地音频库中音频文件名的最低相似度。\n低了就会被当做一般弹幕处理'
                    ).style("width:200px;").tooltip('最低音频匹配相似度，就是说用户发送的内容和本地音频库中音频文件名的最低相似度。\n低了就会被当做一般弹幕处理')
        
        if config.get("webui", "show_card", "common_config", "schedule"): 
            with ui.card().style(card_css):
                ui.label('定时任务')
                with ui.row():
                    input_schedule_index = ui.input(label='任务索引', value="", placeholder='任务组的排序号，就是说第一个组是1，第二个组是2，以此类推。请填写纯正整数')
                    button_schedule_add = ui.button('增加任务组', on_click=schedule_add, color=button_internal_color).style(button_internal_css)
                    button_schedule_del = delete_button('删除任务组', lambda: confirm_delete_group('定时任务', input_schedule_index.value, schedule_del)).style(button_internal_css)
                
                schedule_var = {}
                schedule_config_card = ui.card()
                for index, schedule in enumerate(config.get("schedule")):
                    with schedule_config_card.style(card_css):
                        with ui.row():
                            schedule_var[str(4 * index)] = ui.switch(text=f"启用任务#{index}", value=schedule["enable"]).style(switch_internal_css)
                            schedule_var[str(4 * index + 1)] = ui.input(label=f"最小循环周期#{index}", value=schedule["time_min"], placeholder='定时任务循环的周期最小时长（秒），即每间隔这个周期就会执行一次').style("width:100px;").tooltip('定时任务循环的周期最小时长（秒），最终周期会从最大最小之间随机生成，即每间隔这个周期就会执行一次')
                            schedule_var[str(4 * index + 2)] = ui.input(label=f"最大循环周期#{index}", value=schedule["time_max"], placeholder='定时任务循环的周期最大时长（秒），即每间隔这个周期就会执行一次').style("width:100px;").tooltip('定时任务循环的周期最小时长（秒），最终周期会从最大最小之间随机生成，即每间隔这个周期就会执行一次')
                            schedule_var[str(4 * index + 3)] = ui.textarea(label=f"文案列表#{index}", value=textarea_data_change(schedule["copy"]), placeholder='存放文案的列表，通过空格或换行分割，通过{变量}来替换关键数据，可修改源码自定义功能').style("width:500px;").tooltip('存放文案的列表，通过空格或换行分割，通过{变量}来替换关键数据，可修改源码自定义功能')
            
        if config.get("webui", "show_card", "common_config", "idle_time_task"): 
            with ui.card().style(card_css):
                ui.label('闲时任务')
                with ui.row():
                    switch_idle_time_task_enable = ui.switch('启用', value=config.get("idle_time_task", "enable")).style(switch_internal_css)
                    select_idle_time_task_type = ui.select(
                        label='机制类型',
                        options={
                            '待合成消息队列更新闲时': '待合成消息队列更新闲时', 
                            '待播放音频队列更新闲时': '待播放音频队列更新闲时', 
                            '直播间无消息更新闲时': '直播间无消息更新闲时',
                        },
                        value=config.get("idle_time_task", "type")
                    ).tooltip('闲时任务执行的逻辑，在不同逻辑下可以实现不同的触发效果。\n如果是用于带货，可以选用 待播放音频队列更新闲时，然后把触发值设为1，从而在音频数少于1的情况下才会触发闲时任务，有效抑制大量任务产生。\n如果用于不需要一直说话的场景，推荐使用：直播间无消息更新闲时，然后把间隔设大点，隔一段时间触发一次。')
                with ui.row():
                    input_idle_time_task_idle_min_msg_queue_len_to_trigger = ui.input(
                        label='待合成消息队列个数小于此值时触发', 
                        value=config.get("idle_time_task", "min_msg_queue_len_to_trigger"), 
                        placeholder='待合成消息队列个数小于此值时，才会触发闲时任务'
                    ).style("width:250px;").tooltip('待合成消息队列个数小于此值时，才会触发闲时任务')
                    input_idle_time_task_idle_min_audio_queue_len_to_trigger = ui.input(
                        label='待播放音频队列个数小于此值时触发', 
                        value=config.get("idle_time_task", "min_audio_queue_len_to_trigger"), 
                        placeholder='待播放音频队列个数小于此值时，才会触发闲时任务'
                    ).style("width:250px;").tooltip('待播放音频队列个数小于此值时，才会触发闲时任务')
                    
                with ui.row():
                    input_idle_time_task_idle_time_min = ui.input(
                        label='最小闲时时间', 
                        value=config.get("idle_time_task", "idle_time_min"), 
                        placeholder='最小闲时间隔时间（正整数，单位：秒），就是在没有弹幕情况下经过的时间'
                    ).style("width:150px;").tooltip('最小闲时间隔时间（正整数，单位：秒），就是在没有弹幕情况下经过的时间')
                    input_idle_time_task_idle_time_max = ui.input(
                        label='最大闲时时间', 
                        value=config.get("idle_time_task", "idle_time_max"), 
                        placeholder='最大闲时间隔时间（正整数，单位：秒），就是在没有弹幕情况下经过的时间'
                    ).style("width:150px;").tooltip('最大闲时间隔时间（正整数，单位：秒），就是在没有弹幕情况下经过的时间')
                    input_idle_time_task_wait_play_audio_num_threshold = ui.input(
                        label='等待播放音频数量阈值', 
                        value=config.get("idle_time_task", "wait_play_audio_num_threshold"), 
                        placeholder='当等待播放音频数量超过这个阈值，将会在音频播放完毕后触发闲时时间减少到设定的缩减值，旨在控制闲时任务触发总量'
                    ).style("width:150px;").tooltip('当等待播放音频数量超过这个阈值，将会在音频播放完毕后触发闲时时间减少到设定的缩减值，旨在控制闲时任务触发总量')
                    input_idle_time_task_idle_time_reduce_to = ui.input(label='闲时计时减小到', value=config.get("idle_time_task", "idle_time_reduce_to"), placeholder='达到阈值情况下，闲时计时缩减到的数值').style("width:150px;").tooltip('达到阈值情况下，闲时计时缩减到的数值')
                    
                with ui.row():
                    ui.label('刷新闲时计时的消息类型')
                    # 类型列表
                    idle_time_task_trigger_type_list = ["comment", "gift", "entrance", "follow"]
                    idle_time_task_trigger_type_mapping = {
                        "comment": "弹幕",
                        "gift": "礼物",
                        "entrance": "入场",
                        "follow": "关注",
                    }
                    idle_time_task_trigger_type_var = {}
                    
                    for index, idle_time_task_trigger_type in enumerate(idle_time_task_trigger_type_list):
                        if idle_time_task_trigger_type in config.get("idle_time_task", "trigger_type"):
                            idle_time_task_trigger_type_var[str(index)] = ui.checkbox(text=idle_time_task_trigger_type_mapping[idle_time_task_trigger_type], value=True)
                        else:
                            idle_time_task_trigger_type_var[str(index)] = ui.checkbox(text=idle_time_task_trigger_type_mapping[idle_time_task_trigger_type], value=False)
            

                with ui.row():
                    switch_idle_time_task_copywriting_enable = ui.switch('文案模式', value=config.get("idle_time_task", "copywriting", "enable")).style(switch_internal_css)
                    switch_idle_time_task_copywriting_random = ui.switch('随机文案', value=config.get("idle_time_task", "copywriting", "random")).style(switch_internal_css)
                    textarea_idle_time_task_copywriting_copy = ui.textarea(
                        label='文案列表', 
                        value=textarea_data_change(config.get("idle_time_task", "copywriting", "copy")), 
                        placeholder='文案列表，文案之间用换行分隔，文案会丢LLM进行处理后直接合成返回的结果'
                    ).style("width:800px;").tooltip('文案列表，文案之间用换行分隔，文案会丢LLM进行处理后直接合成返回的结果')
                
                with ui.row():
                    switch_idle_time_task_comment_enable = ui.switch('弹幕触发LLM模式', value=config.get("idle_time_task", "comment", "enable")).style(switch_internal_css)
                    switch_idle_time_task_comment_random = ui.switch('随机弹幕', value=config.get("idle_time_task", "comment", "random")).style(switch_internal_css)
                    textarea_idle_time_task_comment_copy = ui.textarea(
                        label='弹幕列表', 
                        value=textarea_data_change(config.get("idle_time_task", "comment", "copy")), 
                        placeholder='弹幕列表，弹幕之间用换行分隔，文案会丢LLM进行处理后直接合成返回的结果'
                    ).style("width:800px;").tooltip('弹幕列表，弹幕之间用换行分隔，文案会丢LLM进行处理后直接合成返回的结果')
                with ui.row():
                    switch_idle_time_task_local_audio_enable = ui.switch('本地音频模式', value=config.get("idle_time_task", "local_audio", "enable")).style(switch_internal_css)
                    switch_idle_time_task_local_audio_random = ui.switch('随机本地音频', value=config.get("idle_time_task", "local_audio", "random")).style(switch_internal_css)
                    textarea_idle_time_task_local_audio_path = ui.textarea(
                        label='本地音频路径列表', 
                        value=textarea_data_change(config.get("idle_time_task", "local_audio", "path")), 
                        placeholder='本地音频路径列表，相对/绝对路径之间用换行分隔，音频文件会直接丢进音频播放队列'
                    ).style("width:800px;").tooltip('本地音频路径列表，相对/绝对路径之间用换行分隔，音频文件会直接丢进音频播放队列')

        if config.get("webui", "show_card", "common_config", "search_online"):      
            with ui.card().style(card_css):
                ui.label('联网搜索')
                with ui.row():
                    switch_search_online_enable = ui.switch('启用', value=config.get("search_online", "enable")).style(switch_internal_css) 
                    switch_search_online_keyword_enable = ui.switch('关键词触发', value=config.get("search_online", "keyword_enable")).style(switch_internal_css) 
                    textarea_search_online_before_keyword = ui.textarea(
                        label='关键词前缀', 
                        placeholder='前缀必须携带其中任一字符串才能触发联网搜索\n例如：配置 【联网：】那么这个会触发：联网：杭州天气', 
                        value=textarea_data_change(config.get("search_online", "before_keyword"))
                    ).style("width:200px;").tooltip('前缀必须携带其中任一字符串才能触发联网搜索\n例如：配置 【联网：】那么这个会触发：联网：杭州天气')
                    
                    select_search_online_engine = ui.select(
                        label='搜索引擎',
                        options={'baidu': '百度搜索', 'google': '谷歌搜索'},
                        value=config.get("search_online", "engine")
                    ).style("width:100px;").tooltip('使用的搜索引擎')
                    input_search_online_engine_id = ui.input(label='引擎ID', value=config.get("search_online", "engine_id"), placeholder='默认：1，不建议修改').style("width:100px;").tooltip('就是单个引擎可能会有多种搜索方式，目前仅谷歌有2种，默认不建议修改')
                    input_search_online_count = ui.input(label='检索的文章数', value=config.get("search_online", "count"), placeholder='默认为：1，但有时候可能文章内容解析出来是空的，可以适当扩大检索数').style("width:100px;").tooltip('默认为：1，但有时候可能文章内容解析出来是空的，可以适当扩大检索数')
                    input_search_online_resp_template = ui.input(label='结果模板', value=config.get("search_online", "resp_template"), placeholder='检索后数据会以这个模板格式生成问题，请不要删除{}的两个变量，会导致无法运行').style("width:500px;").tooltip('检索后数据会以这个模板格式生成问题，请不要删除{}的两个变量，会导致无法运行')
                    input_search_online_http_proxy = ui.input(
                        label='HTTP代理地址', 
                        value=config.get("search_online", "http_proxy"), 
                        placeholder='http代理地址，需要走代理时配置此项。',
                        validation={
                            '请输入正确格式的URL': lambda value: common.is_url_check(value),
                        }
                    ).style("width:200px;").tooltip('http代理地址，需要走代理时配置此项。')
                    input_search_online_https_proxy = ui.input(
                        label='HTTPS代理地址', 
                        value=config.get("search_online", "https_proxy"), 
                        placeholder='https代理地址，需要走代理时配置此项。',
                        validation={
                            '请输入正确格式的URL': lambda value: common.is_url_check(value),
                        }
                    ).style("width:200px;").tooltip('https代理地址，需要走代理时配置此项。')
                
        if config.get("webui", "show_card", "common_config", "trends_copywriting"):        
            with ui.card().style(card_css):
                ui.label('动态文案')
                with ui.row():
                    switch_trends_copywriting_enable = ui.switch('启用', value=config.get("trends_copywriting", "enable")).style(switch_internal_css)
                    select_trends_copywriting_llm_type = ui.select(
                        label='LLM类型',
                        options=CHAT_TYPE_OPTIONS,
                        value=config.get("trends_copywriting", "llm_type")
                    ).style("width:200px;")
                    switch_trends_copywriting_random_play = ui.switch('随机播放', value=config.get("trends_copywriting", "random_play")).style(switch_internal_css)
                    input_trends_copywriting_play_interval = ui.input(label='文案播放间隔', value=config.get("trends_copywriting", "play_interval"), placeholder='文案于文案之间的播放间隔时间（秒）').style("width:200px;").tooltip('文案于文案之间的播放间隔时间（秒）')
                
                with ui.row():
                    input_trends_copywriting_index = ui.input(label='文案索引', value="", placeholder='文案组的排序号，就是说第一个组是1，第二个组是2，以此类推。请填写纯正整数').tooltip('文案组的排序号，就是说第一个组是1，第二个组是2，以此类推。请填写纯正整数')
                    button_trends_copywriting_add = ui.button('增加文案组', on_click=trends_copywriting_add, color=button_internal_color).style(button_internal_css)
                    button_trends_copywriting_del = delete_button('删除文案组', lambda: confirm_delete_group('动态文案', input_trends_copywriting_index.value, trends_copywriting_del)).style(button_internal_css)
                
                trends_copywriting_copywriting_var = {}
                trends_copywriting_config_card = ui.card()
                for index, trends_copywriting_copywriting in enumerate(config.get("trends_copywriting", "copywriting")):
                    with trends_copywriting_config_card.style(card_css):
                        with ui.row():
                            trends_copywriting_copywriting_var[str(3 * index)] = ui.input(label=f"文案路径#{index + 1}", value=trends_copywriting_copywriting["folder_path"], placeholder='文案文件存储的文件夹路径').style("width:200px;").tooltip('文案文件存储的文件夹路径')
                            trends_copywriting_copywriting_var[str(3 * index + 1)] = ui.switch(text=f"提示词转换#{index + 1}", value=trends_copywriting_copywriting["prompt_change_enable"])
                            trends_copywriting_copywriting_var[str(3 * index + 2)] = ui.input(label=f"提示词转换内容#{index + 1}", value=trends_copywriting_copywriting["prompt_change_content"], placeholder='使用此提示词内容对文案内容进行转换后再进行合成，使用的LLM为聊天类型配置').style("width:500px;").tooltip('使用此提示词内容对文案内容进行转换后再进行合成，使用的LLM为聊天类型配置')
        
        if config.get("webui", "show_card", "common_config", "key_mapping"):  
            with ui.card().style(card_css):
                ui.label('按键/文案/音频/串口/图片 映射')
                with ui.row():
                    switch_key_mapping_enable = ui.switch('启用', value=config.get("key_mapping", "enable")).style(switch_internal_css)
                    input_key_mapping_start_cmd = ui.input(
                        label='命令前缀', 
                        value=config.get("key_mapping", "start_cmd"), 
                        placeholder='想要触发此功能必须以这个字符串做为命令起始，不然将不会被解析为按键映射命令'
                    ).style("width:200px;").tooltip('想要触发此功能必须以这个字符串做为命令起始，不然将不会被解析为按键映射命令')
                    select_key_mapping_type = ui.select(
                        label='捕获类型',
                        options={'弹幕': '弹幕', '回复': '回复', '弹幕+回复': '弹幕+回复'},
                        value=config.get("key_mapping", "type")
                    ).style("width:200px").tooltip('什么类型的数据会触发这个板块的功能')
                with ui.row():
                    
                    select_key_mapping_key_trigger_type = ui.select(
                        label='按键触发类型',
                        options={'不启用': '不启用', '关键词': '关键词', '礼物': '礼物', '关键词+礼物': '关键词+礼物'},
                        value=config.get("key_mapping", "key_trigger_type")
                    ).style("width:120px").tooltip('什么类型的数据会触发按键映射')
                    switch_key_mapping_key_single_sentence_trigger_once_enable = ui.switch('单句仅触发一次（按键）', value=config.get("key_mapping", "key_single_sentence_trigger_once")).style(switch_internal_css).tooltip('一句话的数据，是否只让这句话触发一次按键映射，因为一句话中可能会有多个关键词，触发多次')
                    select_key_mapping_copywriting_trigger_type = ui.select(
                        label='文案触发类型',
                        options={'不启用': '不启用', '关键词': '关键词', '礼物': '礼物', '关键词+礼物': '关键词+礼物'},
                        value=config.get("key_mapping", "copywriting_trigger_type")
                    ).style("width:120px").tooltip('什么类型的数据会触发文案映射')
                    switch_key_mapping_copywriting_single_sentence_trigger_once_enable = ui.switch('单句仅触发一次（文案）', value=config.get("key_mapping", "copywriting_single_sentence_trigger_once")).style(switch_internal_css).tooltip('一句话的数据，是否只让这句话触发一次文案映射，因为一句话中可能会有多个关键词，触发多次')
                    select_key_mapping_local_audio_trigger_type = ui.select(
                        label='本地音频触发类型',
                        options={'不启用': '不启用', '关键词': '关键词', '礼物': '礼物', '关键词+礼物': '关键词+礼物'},
                        value=config.get("key_mapping", "local_audio_trigger_type")
                    ).style("width:120px").tooltip('什么类型的数据会触发本地音频映射')
                    switch_key_mapping_local_audio_single_sentence_trigger_once_enable = ui.switch('单句仅触发一次（文案）', value=config.get("key_mapping", "local_audio_single_sentence_trigger_once")).style(switch_internal_css).tooltip('一句话的数据，是否只让这句话触发一次本地音频映射，因为一句话中可能会有多个关键词，触发多次')
                    select_key_mapping_serial_trigger_type = ui.select(
                        label='串口触发类型',
                        options={'不启用': '不启用', '关键词': '关键词', '礼物': '礼物', '关键词+礼物': '关键词+礼物'},
                        value=config.get("key_mapping", "serial_trigger_type")
                    ).style("width:120px").tooltip('什么类型的数据会触发文案映射')
                    switch_key_mapping_serial_single_sentence_trigger_once_enable = ui.switch('单句仅触发一次（串口）', value=config.get("key_mapping", "serial_single_sentence_trigger_once")).style(switch_internal_css).tooltip('一句话的数据，是否只让这句话触发一次文案映射，因为一句话中可能会有多个关键词，触发多次')
                    select_key_mapping_img_path_trigger_type = ui.select(
                        label='图片触发类型',
                        options={'不启用': '不启用', '关键词': '关键词', '礼物': '礼物', '关键词+礼物': '关键词+礼物'},
                        value=config.get("key_mapping", "img_path_trigger_type")
                    ).style("width:120px").tooltip('什么类型的数据会触发文案映射')
                    switch_key_mapping_img_path_single_sentence_trigger_once_enable = ui.switch('单句仅触发一次（图片显示）', value=config.get("key_mapping", "img_path_single_sentence_trigger_once")).style(switch_internal_css).tooltip('一句话的数据，是否只让这句话触发一次文案映射，因为一句话中可能会有多个关键词，触发多次')
                    
                with ui.row():
                    input_key_mapping_index = ui.input(label='配置索引', value="", placeholder='配置组的排序号，就是说第一个组是1，第二个组是2，以此类推。请填写纯正整数').tooltip('配置组的排序号，就是说第一个组是1，第二个组是2，以此类推。请填写纯正整数')
                    button_key_mapping_add = ui.button('增加配置组', on_click=key_mapping_add, color=button_internal_color).style(button_internal_css)
                    button_key_mapping_del = delete_button('删除配置组', lambda: confirm_delete_group('按键/文案映射', input_key_mapping_index.value, key_mapping_del)).style(button_internal_css)
                
                
                key_mapping_config_var = {}
                key_mapping_config_card = ui.card()
                for index, key_mapping_config in enumerate(config.get("key_mapping", "config")):
                    with key_mapping_config_card.style(card_css):
                        with ui.row():
                            num = 9
                            key_mapping_config_var[str(num * index)] = ui.textarea(label=f"关键词#{index + 1}", value=textarea_data_change(key_mapping_config["keywords"]), placeholder='此处输入触发的关键词，多个请以换行分隔').style("width:100px;").tooltip('此处输入触发的关键词，多个请以换行分隔')
                            key_mapping_config_var[str(num * index + 1)] = ui.textarea(label=f"礼物#{index + 1}", value=textarea_data_change(key_mapping_config["gift"]), placeholder='此处输入触发的礼物名，多个请以换行分隔').style("width:100px;").tooltip('此处输入触发的礼物名，多个请以换行分隔')
                            key_mapping_config_var[str(num * index + 2)] = ui.textarea(label=f"按键#{index + 1}", value=textarea_data_change(key_mapping_config["keys"]), placeholder='此处输入你要映射的按键，多个按键请以换行分隔（按键名参考pyautogui规则）').style("width:100px;").tooltip('此处输入你要映射的按键，多个按键请以换行分隔（按键名参考pyautogui规则）')
                            key_mapping_config_var[str(num * index + 3)] = ui.input(label=f"相似度#{index + 1}", value=key_mapping_config["similarity"], placeholder='关键词与用户输入的相似度，默认1即100%').style("width:50px;").tooltip('关键词与用户输入的相似度，默认1即100%')
                            key_mapping_config_var[str(num * index + 4)] = ui.textarea(label=f"文案#{index + 1}", value=textarea_data_change(key_mapping_config["copywriting"]), placeholder='此处输入触发后合成的文案内容，多个请以换行分隔').style("width:300px;").tooltip('此处输入触发后合成的文案内容，多个请以换行分隔')
                            key_mapping_config_var[str(num * index + 5)] = ui.textarea(label=f"本地音频#{index + 1}", value=textarea_data_change(key_mapping_config["local_audio"]), placeholder='此处输入触发后播放的本地音频路径，多个请以换行分隔').style("width:300px;").tooltip('此处输入触发后播放的本地音频路径，多个请以换行分隔')
                            key_mapping_config_var[str(num * index + 6)] = ui.input(label=f"串口名#{index + 1}", value=key_mapping_config["serial_name"], placeholder='例如：COM1').style("width:100px;").tooltip('串口页配置的串口名，例如：COM1')
                            key_mapping_config_var[str(num * index + 7)] = ui.textarea(label=f"串口发送内容#{index + 1}", value=textarea_data_change(key_mapping_config["serial_send_data"]), placeholder='多个请以换行分隔，ASCII例如：open led\nHEX例如（2个字符的十六进制字符）：313233').style("width:300px;").tooltip('此处输入发送到串口的数据内容，数据类型根据串口页设置决定，多个请以换行分隔')
                            key_mapping_config_var[str(num * index + 8)] = ui.textarea(label=f"图片路径#{index + 1}", value=textarea_data_change(key_mapping_config["img_path"]), placeholder='多个请以换行分隔，支持绝对路径或相对路径，需要注意路径的斜杠哈').style("width:300px;").tooltip('此处输入图片路径，多个请以换行分隔。默认随机显示')
                            
                            # with ui.card().style(card_css):
                            #     key_mapping_config_var[str(6 * index + 5)] = ui.textarea(label=f"串口号#{index + 1}", value=textarea_data_change(key_mapping_config["serial_name"]), placeholder='例如：COM1').style("width:100px;").tooltip('发送的串口名')
                            #     key_mapping_config_var[str(6 * index + 5)] = ui.textarea(label=f"发送数据#{index + 1}", value=key_mapping_config["serial_data"], placeholder='根据类型填写，多个请以换行分隔').style("width:300px;").tooltip('根据类型填写，多个请以换行分隔')
        
    with ui.expansion('辅助软件对接', icon="extension", value=True).classes('w-full'):

        with ui.card().style(card_css):
            ui.label("洛曦 直播弹幕助手")
            with ui.row():
                switch_luoxi_project_Live_Comment_Assistant_enable = ui.switch('启用', value=config.get("luoxi_project", "Live_Comment_Assistant", "enable")).style(switch_internal_css)
                select_luoxi_project_Live_Comment_Assistant_version = ui.select(
                    label='对接版本',
                    options={'V0.1.x': 'V0.1.x'},
                    value=config.get("luoxi_project", "Live_Comment_Assistant", "version")
                ).style("width:100px;").tooltip('版本，因为不同版本可能会有接口上的改动')
                input_luoxi_project_Live_Comment_Assistant_api_ip_port = ui.input(
                    label='API地址', 
                    value=config.get("luoxi_project", "Live_Comment_Assistant", "api_ip_port"), 
                    placeholder='洛曦 直播弹幕助手 API地址'
                ).style("width:200px;").tooltip('洛曦 直播弹幕助手 API地址')
        
            with ui.card().style(card_css):
                ui.label("触发类型")
                with ui.row():    
                    # 类型列表源自 音频合成的所支持的type值
                    luoxi_project_Live_Comment_Assistant_type_list = [
                        "comment",
                        "comment_reply", 
                        "idle_time_task", 
                        "entrance_reply", 
                        "follow_reply", 
                        "gift_reply", 
                        "reread", 
                        "schedule",
                        "integral",
                        "key_mapping_copywriting"
                    ]
                    luoxi_project_Live_Comment_Assistant_type_mapping = {
                        "comment": "弹幕消息",
                        "comment_reply": "弹幕回复",
                        "idle_time_task": "闲时任务",
                        "entrance_reply": "入场回复",
                        "follow_reply": "关注回复",
                        "gift_reply": "礼物回复",
                        "reread": "复读",
                        "schedule": "定时任务",
                        "integral": "积分消息",
                        "key_mapping_copywriting": "按键映射-文案"
                    }
                    luoxi_project_Live_Comment_Assistant_type_var = {}
                    
                    for index, luoxi_project_Live_Comment_Assistant_type in enumerate(luoxi_project_Live_Comment_Assistant_type_list):
                        if luoxi_project_Live_Comment_Assistant_type in config.get("luoxi_project", "Live_Comment_Assistant", "type"):
                            luoxi_project_Live_Comment_Assistant_type_var[str(index)] = ui.checkbox(
                                text=luoxi_project_Live_Comment_Assistant_type_mapping[luoxi_project_Live_Comment_Assistant_type], 
                                value=True
                            )
                        else:
                            luoxi_project_Live_Comment_Assistant_type_var[str(index)] = ui.checkbox(
                                text=luoxi_project_Live_Comment_Assistant_type_mapping[luoxi_project_Live_Comment_Assistant_type], 
                                value=False
                            )
            with ui.card().style(card_css):
                ui.label("触发位置")
                with ui.row(): 
                    luoxi_project_Live_Comment_Assistant_trigger_position_list = [
                        "消息产生时", 
                        "音频播放时",
                    ]
                    luoxi_project_Live_Comment_Assistant_trigger_position_mapping = {
                        "消息产生时": "消息产生时",
                        "音频播放时": "音频播放时",
                    }
                    luoxi_project_Live_Comment_Assistant_trigger_position_var = {}
                    
                    for index, luoxi_project_Live_Comment_Assistant_trigger_position in enumerate(luoxi_project_Live_Comment_Assistant_trigger_position_list):
                        if luoxi_project_Live_Comment_Assistant_trigger_position in config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                            luoxi_project_Live_Comment_Assistant_trigger_position_var[str(index)] = ui.checkbox(
                                text=luoxi_project_Live_Comment_Assistant_trigger_position_mapping[luoxi_project_Live_Comment_Assistant_trigger_position], 
                                value=True
                            )
                        else:
                            luoxi_project_Live_Comment_Assistant_trigger_position_var[str(index)] = ui.checkbox(
                                text=luoxi_project_Live_Comment_Assistant_trigger_position_mapping[luoxi_project_Live_Comment_Assistant_trigger_position], 
                                value=False
                            )        
        

        if config.get("webui", "show_card", "common_config", "sd"):      
            with ui.card().style(card_css):
                ui.label('Stable Diffusion')
                with ui.row():
                    switch_sd_enable = ui.switch('启用', value=config.get("sd", "enable")).style(switch_internal_css) 
                    select_sd_translate_type = ui.select(
                        label='翻译类型',
                        options={'none': '不启用', 'baidu': '百度翻译', 'google': '谷歌翻译'},
                        value=config.get("sd", "translate_type")
                    ).style("width:100px;").tooltip('针对触发的画图命令使用翻译页的配置，进行翻译后再丢给SD画图')
                    select_sd_prompt_llm_type = ui.select(
                        label='LLM类型',
                        options=CHAT_TYPE_OPTIONS,
                        value=config.get("sd", "prompt_llm", "type")
                    ).style("width:100px;")
                    input_sd_prompt_llm_before_prompt = ui.input(label='提示词前缀', value=config.get("sd", "prompt_llm", "before_prompt"), placeholder='LLM提示词前缀').style("width:300px;")
                    input_sd_prompt_llm_after_prompt = ui.input(label='提示词后缀', value=config.get("sd", "prompt_llm", "after_prompt"), placeholder='LLM提示词后缀').style("width:300px;")
                with ui.row(): 
                    input_sd_trigger = ui.input(label='弹幕触发前缀', value=config.get("sd", "trigger"), placeholder='触发的关键词（弹幕头部触发）').style("width:200px;")
                    input_sd_ip = ui.input(label='IP地址', value=config.get("sd", "ip"), placeholder='服务运行的IP地址').style("width:200px;")
                    input_sd_port = ui.input(label='端口', value=config.get("sd", "port"), placeholder='服务运行的端口').style("width:100px;")
                    input_sd_negative_prompt = ui.input(label='负面提示词', value=config.get("sd", "negative_prompt"), placeholder='负面文本提示，用于指定与生成图像相矛盾或相反的内容').style("width:200px;")
                    input_sd_seed = ui.input(label='随机种子', value=config.get("sd", "seed"), placeholder='随机种子，用于控制生成过程的随机性。可以设置一个整数值，以获得可重复的结果。').style("width:100px;")
                    textarea_sd_styles = ui.textarea(label='图像风格', placeholder='样式列表，用于指定生成图像的风格。可以包含多个风格，例如 ["anime", "portrait"]', value=textarea_data_change(config.get("sd", "styles"))).style("width:200px;")
                with ui.row():
                    input_sd_cfg_scale = ui.input(label='提示词相关性', value=config.get("sd", "cfg_scale"), placeholder='提示词相关性，无分类器指导信息影响尺度(Classifier Free Guidance Scale) -图像应在多大程度上服从提示词-较低的值会产生更有创意的结果。').style("width:100px;")
                    input_sd_steps = ui.input(label='生成图像步数', value=config.get("sd", "steps"), placeholder='生成图像的步数，用于控制生成的精确程度。').style("width:100px;") 
                    input_sd_hr_resize_x = ui.input(label='图像水平像素', value=config.get("sd", "hr_resize_x"), placeholder='生成图像的水平尺寸。').style("width:100px;")
                    input_sd_hr_resize_y = ui.input(label='图像垂直像素', value=config.get("sd", "hr_resize_y"), placeholder='生成图像的垂直尺寸。').style("width:100px;")
                    input_sd_denoising_strength = ui.input(label='去噪强度', value=config.get("sd", "denoising_strength"), placeholder='去噪强度，用于控制生成图像中的噪点。').style("width:100px;")
                with ui.row():
                    switch_sd_enable_hr = ui.switch('高分辨率生成', value=config.get("sd", "enable_hr")).style(switch_internal_css)
                    input_sd_hr_scale = ui.input(label='高分辨率缩放因子', value=config.get("sd", "hr_scale"), placeholder='高分辨率缩放因子，用于指定生成图像的高分辨率缩放级别。').style("width:200px;")
                    input_sd_hr_second_pass_steps = ui.input(label='高分生二次传递步数', value=config.get("sd", "hr_second_pass_steps"), placeholder='高分辨率生成的第二次传递步数。').style("width:200px;")
                    switch_sd_save_enable = ui.switch('保存图片到本地', value=config.get("sd", "save_enable")).style(switch_internal_css)
                    switch_sd_loop_cover = ui.switch('本地图片循环覆盖', value=config.get("sd", "loop_cover")).style(switch_internal_css)
                    input_sd_save_path = ui.input(label='图片保存路径', value=config.get("sd", "save_path"), placeholder='生成图片存储路径，不建议修改').style("width:200px;")
        
        if config.get("webui", "show_card", "common_config", "web_captions_printer"):
            with ui.card().style(card_css):
                ui.label('web字幕打印机')
                with ui.grid(columns=2):
                    switch_web_captions_printer_enable = ui.switch('启用', value=config.get("web_captions_printer", "enable")).style(switch_internal_css).tooltip("如果您使用了audio player来做音频播放，并开启了其web字幕打印机功能,\n那请勿启动此功能，因为这样就重复惹")
                    input_web_captions_printer_api_ip_port = ui.input(
                        label='API地址', 
                        value=config.get("web_captions_printer", "api_ip_port"), 
                        placeholder='web字幕打印机的API地址，只需要 http://ip:端口 即可',
                        validation={
                            '请输入正确格式的URL': lambda value: common.is_url_check(value),
                        }
                    ).style("width:200px;").tooltip('web字幕打印机的API地址，只需要 http://ip:端口 即可')


    with ui.expansion('高级功能', icon="view_in_ar", value=True).classes('w-full'):
        if config.get("webui", "show_card", "common_config", "log"):
            with ui.card().style(card_css):
                ui.label('日志')
                with ui.grid(columns=4):
                    switch_captions_enable = ui.switch('启用', value=config.get("captions", "enable")).style(switch_internal_css)

                    select_comment_log_type = ui.select(
                        label='弹幕日志类型',
                        options={'问答': '问答', '问题': '问题', '回答': '回答', '不记录': '不记录'},
                        value=config.get("comment_log_type")
                    )

                    input_captions_file_path = ui.input(label='字幕日志路径', value=config.get("captions", "file_path"), placeholder='字幕日志存储路径').style("width:200px;")
                    input_captions_raw_file_path = ui.input(label='原文字幕日志路径', placeholder='原文字幕日志存储路径',
                                                        value=config.get("captions", "raw_file_path")).style("width:200px;")

        if config.get("webui", "show_card", "common_config", "database"):  
            with ui.card().style(card_css):
                ui.label('数据库')
                with ui.grid(columns=4):
                    switch_database_comment_enable = ui.switch('弹幕日志', value=config.get("database", "comment_enable")).style(switch_internal_css)
                    switch_database_entrance_enable = ui.switch('入场日志', value=config.get("database", "entrance_enable")).style(switch_internal_css)
                    switch_database_gift_enable = ui.switch('礼物日志', value=config.get("database", "gift_enable")).style(switch_internal_css)
                    input_database_path = ui.input(label='数据库路径', value=config.get("database", "path"), placeholder='数据库文件存储路径').style("width:200px;")
                    
                      
        if config.get("webui", "show_card", "common_config", "custom_cmd"):  
            with ui.card().style(card_css):
                ui.label('自定义命令')
                with ui.row():
                    switch_custom_cmd_enable = ui.switch('启用', value=config.get("custom_cmd", "enable")).style(switch_internal_css)
                    select_custom_cmd_type = ui.select(
                        label='类型',
                        options={'弹幕': '弹幕'},
                        value=config.get("custom_cmd", "type")
                    ).style("width:200px")
                with ui.row():
                    input_custom_cmd_index = ui.input(label='配置索引', value="", placeholder='配置组的排序号，就是说第一个组是1，第二个组是2，以此类推。请填写纯正整数')
                    button_custom_cmd_add = ui.button('增加配置组', on_click=custom_cmd_add, color=button_internal_color).style(button_internal_css)
                    button_custom_cmd_del = delete_button('删除配置组', lambda: confirm_delete_group('自定义命令', input_custom_cmd_index.value, custom_cmd_del)).style(button_internal_css)
                
                custom_cmd_config_var = {}
                custom_cmd_config_card = ui.card()
                for index, custom_cmd_config in enumerate(config.get("custom_cmd", "config")):
                    with custom_cmd_config_card.style(card_css):
                        with ui.row():
                            custom_cmd_config_var[str(7 * index)] = ui.textarea(label=f"关键词#{index + 1}", value=textarea_data_change(custom_cmd_config["keywords"]), placeholder='此处输入触发的关键词，多个请以换行分隔').style("width:200px;")
                            custom_cmd_config_var[str(7 * index + 1)] = ui.input(label=f"相似度#{index + 1}", value=custom_cmd_config["similarity"], placeholder='关键词与用户输入的相似度，默认1即100%').style("width:100px;")
                            custom_cmd_config_var[str(7 * index + 2)] = ui.textarea(
                                label=f"API URL#{index + 1}", 
                                value=custom_cmd_config["api_url"], 
                                placeholder='发送HTTP请求的API链接', 
                                validation={
                                    '请输入正确格式的URL': lambda value: common.is_url_check(value),
                                }
                            ).style("width:300px;").tooltip('发送HTTP请求的API链接')
                            custom_cmd_config_var[str(7 * index + 3)] = ui.select(label=f"API类型#{index + 1}", value=custom_cmd_config["api_type"], options={"GET": "GET"}).style("width:100px;")
                            custom_cmd_config_var[str(7 * index + 4)] = ui.select(label=f"请求返回数据类型#{index + 1}", value=custom_cmd_config["resp_data_type"], options={"json": "json", "content": "content"}).style("width:150px;")
                            custom_cmd_config_var[str(7 * index + 5)] = ui.textarea(label=f"数据解析（eval执行）#{index + 1}", value=custom_cmd_config["data_analysis"], placeholder='数据解析，请不要随意修改resp变量，会被用于最后返回数据内容的解析').style("width:200px;").tooltip('数据解析，请不要随意修改resp变量，会被用于最后返回数据内容的解析')
                            custom_cmd_config_var[str(7 * index + 6)] = ui.textarea(label=f"返回内容模板#{index + 1}", value=custom_cmd_config["resp_template"], placeholder='请不要随意删除data变量，支持动态变量，最终会合并成完成内容进行音频合成').style("width:300px;").tooltip("请不要随意删除data变量，支持动态变量，最终会合并成完成内容进行音频合成")


        if config.get("webui", "show_card", "common_config", "trends_config"):  
            with ui.card().style(card_css):
                ui.label('动态配置')
                with ui.row():
                    switch_trends_config_enable = ui.switch('启用', value=config.get("trends_config", "enable")).style(switch_internal_css)
                trends_config_path_var = {}
                for index, trends_config_path in enumerate(config.get("trends_config", "path")):
                    with ui.grid(columns=2):
                        trends_config_path_var[str(2 * index)] = ui.input(label="在线人数范围", value=trends_config_path["online_num"], placeholder='在线人数范围，用减号-分隔，例如：0-10').style("width:200px;").tooltip("在线人数范围，用减号-分隔，例如：0-10")
                        trends_config_path_var[str(2 * index + 1)] = ui.input(label="配置路径", value=trends_config_path["path"], placeholder='此处输入加载的配置文件的路径').style("width:200px;").tooltip("此处输入加载的配置文件的路径")
        
        if config.get("webui", "show_card", "common_config", "abnormal_alarm"): 
            with ui.card().style(card_css):
                ui.label('异常报警')
                with ui.row():
                    switch_abnormal_alarm_platform_enable = ui.switch('启用平台报警', value=config.get("abnormal_alarm", "platform", "enable")).style(switch_internal_css)
                    select_abnormal_alarm_platform_type = ui.select(
                        label='类型',
                        options={'local_audio': '本地音频'},
                        value=config.get("abnormal_alarm", "platform", "type")
                    )
                    input_abnormal_alarm_platform_start_alarm_error_num = ui.input(label='开始报警错误数', value=config.get("abnormal_alarm", "platform", "start_alarm_error_num"), placeholder='开始异常报警的错误数，超过这个数后就会报警').style("width:100px;")
                    input_abnormal_alarm_platform_auto_restart_error_num = ui.input(label='自动重启错误数', value=config.get("abnormal_alarm", "platform", "auto_restart_error_num"), placeholder='记得先启用“自动运行”功能。自动重启的错误数，超过这个数后就会自动重启webui。').style("width:100px;")
                    input_abnormal_alarm_platform_local_audio_path = ui.input(label='本地音频路径', value=config.get("abnormal_alarm", "platform", "local_audio_path"), placeholder='本地音频存储的文件路径（可以是多个音频，随机一个）').style("width:300px;")
                with ui.row():
                    switch_abnormal_alarm_llm_enable = ui.switch('启用LLM报警', value=config.get("abnormal_alarm", "llm", "enable")).style(switch_internal_css)
                    select_abnormal_alarm_llm_type = ui.select(
                        label='类型',
                        options={'local_audio': '本地音频'},
                        value=config.get("abnormal_alarm", "llm", "type")
                    )
                    input_abnormal_alarm_llm_start_alarm_error_num = ui.input(label='开始报警错误数', value=config.get("abnormal_alarm", "llm", "start_alarm_error_num"), placeholder='开始异常报警的错误数，超过这个数后就会报警').style("width:100px;")
                    input_abnormal_alarm_llm_auto_restart_error_num = ui.input(label='自动重启错误数', value=config.get("abnormal_alarm", "llm", "auto_restart_error_num"), placeholder='记得先启用“自动运行”功能。自动重启的错误数，超过这个数后就会自动重启webui。').style("width:100px;")
                    input_abnormal_alarm_llm_local_audio_path = ui.input(label='本地音频路径', value=config.get("abnormal_alarm", "llm", "local_audio_path"), placeholder='本地音频存储的文件路径（可以是多个音频，随机一个）').style("width:300px;")
                with ui.row():
                    switch_abnormal_alarm_tts_enable = ui.switch('启用TTS报警', value=config.get("abnormal_alarm", "tts", "enable")).style(switch_internal_css)
                    select_abnormal_alarm_tts_type = ui.select(
                        label='类型',
                        options={'local_audio': '本地音频'},
                        value=config.get("abnormal_alarm", "tts", "type")
                    )
                    input_abnormal_alarm_tts_start_alarm_error_num = ui.input(label='开始报警错误数', value=config.get("abnormal_alarm", "tts", "start_alarm_error_num"), placeholder='开始异常报警的错误数，超过这个数后就会报警').style("width:100px;")
                    input_abnormal_alarm_tts_auto_restart_error_num = ui.input(label='自动重启错误数', value=config.get("abnormal_alarm", "tts", "auto_restart_error_num"), placeholder='记得先启用“自动运行”功能。自动重启的错误数，超过这个数后就会自动重启webui。').style("width:100px;")
                    input_abnormal_alarm_tts_local_audio_path = ui.input(label='本地音频路径', value=config.get("abnormal_alarm", "tts", "local_audio_path"), placeholder='本地音频存储的文件路径（可以是多个音频，随机一个）').style("width:300px;")
                with ui.row():
                    switch_abnormal_alarm_svc_enable = ui.switch('启用SVC报警', value=config.get("abnormal_alarm", "svc", "enable")).style(switch_internal_css)
                    select_abnormal_alarm_svc_type = ui.select(
                        label='类型',
                        options={'local_audio': '本地音频'},
                        value=config.get("abnormal_alarm", "svc", "type")
                    )
                    input_abnormal_alarm_svc_start_alarm_error_num = ui.input(label='开始报警错误数', value=config.get("abnormal_alarm", "svc", "start_alarm_error_num"), placeholder='开始异常报警的错误数，超过这个数后就会报警').style("width:100px;")
                    input_abnormal_alarm_svc_auto_restart_error_num = ui.input(label='自动重启错误数', value=config.get("abnormal_alarm", "svc", "auto_restart_error_num"), placeholder='记得先启用“自动运行”功能。自动重启的错误数，超过这个数后就会自动重启webui。').style("width:100px;")
                    input_abnormal_alarm_svc_local_audio_path = ui.input(label='本地音频路径', value=config.get("abnormal_alarm", "svc", "local_audio_path"), placeholder='本地音频存储的文件路径（可以是多个音频，随机一个）').style("width:300px;")
                with ui.row():
                    switch_abnormal_alarm_visual_body_enable = ui.switch('启用虚拟身体报警', value=config.get("abnormal_alarm", "visual_body", "enable")).style(switch_internal_css)
                    select_abnormal_alarm_visual_body_type = ui.select(
                        label='类型',
                        options={'local_audio': '本地音频'},
                        value=config.get("abnormal_alarm", "visual_body", "type")
                    )
                    input_abnormal_alarm_visual_body_start_alarm_error_num = ui.input(label='开始报警错误数', value=config.get("abnormal_alarm", "visual_body", "start_alarm_error_num"), placeholder='开始异常报警的错误数，超过这个数后就会报警').style("width:100px;")
                    input_abnormal_alarm_visual_body_auto_restart_error_num = ui.input(label='自动重启错误数', value=config.get("abnormal_alarm", "visual_body", "auto_restart_error_num"), placeholder='记得先启用“自动运行”功能。自动重启的错误数，超过这个数后就会自动重启webui。').style("width:100px;")
                    input_abnormal_alarm_visual_body_local_audio_path = ui.input(label='本地音频路径', value=config.get("abnormal_alarm", "visual_body", "local_audio_path"), placeholder='本地音频存储的文件路径（可以是多个音频，随机一个）').style("width:300px;")
                with ui.row():
                    switch_abnormal_alarm_other_enable = ui.switch('启用其他报警', value=config.get("abnormal_alarm", "other", "enable")).style(switch_internal_css)
                    select_abnormal_alarm_other_type = ui.select(
                        label='类型',
                        options={'local_audio': '本地音频'},
                        value=config.get("abnormal_alarm", "other", "type")
                    )
                    input_abnormal_alarm_other_start_alarm_error_num = ui.input(label='开始报警错误数', value=config.get("abnormal_alarm", "other", "start_alarm_error_num"), placeholder='开始异常报警的错误数，超过这个数后就会报警').style("width:100px;")
                    input_abnormal_alarm_other_auto_restart_error_num = ui.input(label='自动重启错误数', value=config.get("abnormal_alarm", "other", "auto_restart_error_num"), placeholder='记得先启用“自动运行”功能。自动重启的错误数，超过这个数后就会自动重启webui。').style("width:100px;")
                    input_abnormal_alarm_other_local_audio_path = ui.input(label='本地音频路径', value=config.get("abnormal_alarm", "other", "local_audio_path"), placeholder='本地音频存储的文件路径（可以是多个音频，随机一个）').style("width:300px;")
                
        if config.get("webui", "show_card", "common_config", "coordination_program"):
            with ui.expansion('联动程序', icon="settings", value=True).classes('w-full'):
                with ui.row():
                    input_coordination_program_index = ui.input(label='配置索引', value="", placeholder='配置组的排序号，就是说第一个组是1，第二个组是2，以此类推。请填写纯正整数')
                    button_coordination_program_add = ui.button('增加配置组', on_click=coordination_program_add, color=button_internal_color).style(button_internal_css)
                    button_coordination_program_del = delete_button('删除配置组', lambda: confirm_delete_group('联动程序', input_coordination_program_index.value, coordination_program_del)).style(button_internal_css)
                
                coordination_program_var = {}
                coordination_program_config_card = ui.card()
                for index, coordination_program in enumerate(config.get("coordination_program")):
                    with coordination_program_config_card.style(card_css):
                        with ui.row():
                            coordination_program_var[str(4 * index)] = ui.switch(f'启用#{index + 1}', value=coordination_program["enable"]).style(switch_internal_css)
                            coordination_program_var[str(4 * index + 1)] = ui.input(label=f"程序名#{index + 1}", value=coordination_program["name"], placeholder='给你的程序取个名字，别整特殊符号！').style("width:200px;")
                            coordination_program_var[str(4 * index + 2)] = ui.input(label=f"可执行程序#{index + 1}", value=coordination_program["executable"], placeholder='可执行程序的路径，最好是绝对路径，如python的程序').style("width:400px;")
                            coordination_program_var[str(4 * index + 3)] = ui.textarea(label=f'参数#{index + 1}', value=textarea_data_change(coordination_program["parameters"]), placeholder='参数，可以传入多个参数，换行分隔。如启动的程序的路径，命令携带的传参等').style("width:500px;")
        


    def check_config():
        """通用配置页的保存前校验。

        返回 None 表示可以写盘，否则返回 (提示语, 该跳到哪个框)。校验失败原先只丢一条
        会自己消失的 toast，用户还得自己在 850 个控件里找那个框（走查 audit-20）。
        """
        try:
            # 通用配置 页面 配置正确性校验
            if select_platform.value == 'bilibili2' and select_bilibili_login_type.value == 'cookie' and input_bilibili_cookie.value == '':
                return 'B站登录方式选的是 cookie，但 cookie 还空着', input_bilibili_cookie
            elif select_platform.value == 'bilibili2' and select_bilibili_login_type.value == 'open_live' and \
                (input_bilibili_open_live_ACCESS_KEY_ID.value == '' or input_bilibili_open_live_ACCESS_KEY_SECRET.value == '' or \
                input_bilibili_open_live_APP_ID.value == '' or input_bilibili_open_live_ROOM_OWNER_AUTH_CODE.value == ''):
                return 'B站开放平台四项（ACCESS_KEY_ID / ACCESS_KEY_SECRET / 项目ID / 身份码）还没填全', \
                    input_bilibili_open_live_ACCESS_KEY_ID


            """
            针对配置情况进行提示
            """
            tip_config = f'平台：{select_platform.options[select_platform.value]} | ' +\
                f'大语言模型：{CHAT_TYPE_OPTIONS[select_chat_type.value]} | ' +\
                f'语音合成：{AUDIO_SYNTHESIS_TYPE_OPTIONS[select_audio_synthesis_type.value]} | ' +\
                f'虚拟身体：{VISUAL_BODY_OPTIONS[select_visual_body.value]}'
            ui.notify(position="top", type="info", message=tip_config)

            # 检测平台配置，进行提示
            if select_platform.value == "dy":
                ui.notify(position="top", type="warning", message="对接抖音平台时，请先开启抖音弹幕监听程序！直播间号不需要填写")
            elif select_platform.value in LIVE_MONITOR_PLATFORM_KEYS:
                ui.notify(position="top", type="warning", message=(
                    f'走「直播弹幕监听助手」接入：请先让助手把弹幕推送到 ws://'
                    f'{input_live_monitor_assistant_ws_ip.value}:{input_live_monitor_assistant_ws_port.value}，'
                    '监听哪个直播间由助手那边决定，直播间号不需要填写'))
            elif select_platform.value == "bilibili":
                ui.notify(position="top", type="info", message="哔哩哔哩1 监听不是很稳定，推荐使用 哔哩哔哩2")
            elif select_platform.value == "bilibili2":
                if select_bilibili_login_type.value == "不登录":
                    ui.notify(position="top", type="warning", message="哔哩哔哩2 在不登录的情况下，无法获取用户完整的用户名")

            if select_visual_body.value == "metahuman_stream":
                ui.notify(position="top", type="warning", message="对接metahuman_stream时，语音合成由metahuman_stream托管，不受AI Vtuber控制，请自行参考官方文档对接TTS")

            if config.get("webui", "show_card", "common_config", "local_qa"):
                if not common.is_json_convertible(textarea_local_qa_text_json_file_content.value):
                    return '本地问答 json 数据格式不正确，请检查 JSON 语法', textarea_local_qa_text_json_file_content

            return None
        except Exception as e:
            return f'配置错误：{e}', None


    _validator = check_config

    def write_local_qa_file_impl():
        if not config.get("webui", "show_card", "common_config", "local_qa"):
            return True
        try:
            ret = common.write_content_to_file(
                input_local_qa_text_json_file_path.value,
                textarea_local_qa_text_json_file_content.value,
                write_log=False,
            )
            if not ret:
                ui.notify(position="top", type="negative", message="无法写入本地问答json数据到文件！" + chr(10) + "详细报错见日志")
                return False
            return True
        except Exception as e:
            logger.error("无法写入本地问答json数据到文件！" + chr(10) + str(e))
            ui.notify(position="top", type="negative", message="无法写入本地问答json数据到文件！" + chr(10) + str(e))
            return False

    _writer = write_local_qa_file_impl

    def save_common(config_data):
        config_data["platform"] = select_platform.value
        config_data["room_display_id"] = input_room_display_id.value
        config_data["chat_type"] = select_chat_type.value
        config_data["visual_body"] = select_visual_body.value
        config_data["need_lang"] = select_need_lang.value
        config_data["before_prompt"] = input_before_prompt.value
        config_data["after_prompt"] = input_after_prompt.value
        config_data["audio_synthesis_type"] = select_audio_synthesis_type.value

        config_mapping = {
            "comment_template": {
                "enable": (switch_comment_template_enable, 'bool'),
                "copywriting": (input_comment_template_copywriting, 'str'),
            },
            "reply_template": {
                "enable": (switch_reply_template_enable, 'bool'),
                "username_max_len": (input_reply_template_username_max_len, 'int'),
                "copywriting": (textarea_reply_template_copywriting, 'textarea'),
            },
            "bilibili": {
                "login_type": (select_bilibili_login_type, 'str'),
                "cookie": (input_bilibili_cookie, 'str'),
                "ac_time_value": (input_bilibili_ac_time_value, 'str'),
                "open_live": {
                    "ACCESS_KEY_ID": (input_bilibili_open_live_ACCESS_KEY_ID, 'str'),
                    "ACCESS_KEY_SECRET": (input_bilibili_open_live_ACCESS_KEY_SECRET, 'str'),
                    "APP_ID": (input_bilibili_open_live_APP_ID, 'int'),
                    "ROOM_OWNER_AUTH_CODE": (input_bilibili_open_live_ROOM_OWNER_AUTH_CODE, 'str'),
                },
            },
            "twitch": {
                "token": (input_twitch_token, 'str'),
                "user": (input_twitch_user, 'str'),
                "proxy_server": (input_twitch_proxy_server, 'str'),
                "proxy_port": (input_twitch_proxy_port, 'str'),
            },
            "live_monitor_assistant": {
                "ws_ip": (input_live_monitor_assistant_ws_ip, 'str'),
                "ws_port": (input_live_monitor_assistant_ws_port, 'int'),
            },
        }
        config_data = update_config(config_mapping, config, config_data, None)
        
        config_mapping = {}
        # 日志
        if config.get("webui", "show_card", "common_config", "log"):
            config_data["comment_log_type"] = select_comment_log_type.value
            config_data["captions"]["enable"] = switch_captions_enable.value
            config_data["captions"]["file_path"] = input_captions_file_path.value
            config_data["captions"]["raw_file_path"] = input_captions_raw_file_path.value

    
        # 音频播放
        if config.get("webui", "show_card", "common_config", "play_audio"):
            # audio_player
            config_data["audio_player"]["api_ip_port"] = input_audio_player_api_ip_port.value

            config_mapping = {
                "play_audio": {
                    "enable": (switch_play_audio_enable, 'bool'),
                    "text_split_enable": (switch_play_audio_text_split_enable, 'bool'),
                    "info_to_callback": (switch_play_audio_info_to_callback, 'bool'),
                    "interval_num_min": (input_play_audio_interval_num_min, 'int'),
                    "interval_num_max": (input_play_audio_interval_num_max, 'int'),
                    "normal_interval_min": (input_play_audio_normal_interval_min, 'float'),
                    "normal_interval_max": (input_play_audio_normal_interval_max, 'float'),
                    "out_path": (input_play_audio_out_path,'str'),
                    "player": (select_play_audio_player,'str'),
                }
            }

        if config.get("webui", "show_card", "common_config", "read_comment"):
            config_mapping["read_comment"] = {
                "enable": (switch_read_comment_enable, 'bool'),
                "read_username_enable": (switch_read_comment_read_username_enable, 'bool'),
                "username_max_len": (input_read_comment_username_max_len, 'int'),
                "voice_change": (switch_read_comment_voice_change, 'bool'),
                "read_username_copywriting": (textarea_read_comment_read_username_copywriting, 'textarea'),
                "periodic_trigger": {
                    "enable": (switch_read_comment_periodic_trigger_enable, 'bool'),
                    "periodic_time_min": (input_read_comment_periodic_trigger_periodic_time_min, 'int'),
                    "periodic_time_max": (input_read_comment_periodic_trigger_periodic_time_max, 'int'),
                    "trigger_num_min": (input_read_comment_periodic_trigger_trigger_num_min, 'int'),
                    "trigger_num_max": (input_read_comment_periodic_trigger_trigger_num_max, 'int'),
                },
            }

        if config.get("webui", "show_card", "common_config", "local_qa"):
            config_mapping["local_qa"] = {
                "periodic_trigger": {
                    "enable": (switch_local_qa_periodic_trigger_enable, 'bool'),
                    "periodic_time_min": (input_local_qa_periodic_trigger_periodic_time_min, 'int'),
                    "periodic_time_max": (input_local_qa_periodic_trigger_periodic_time_max, 'int'),
                    "trigger_num_min": (input_local_qa_periodic_trigger_trigger_num_min, 'int'),
                    "trigger_num_max": (input_local_qa_periodic_trigger_trigger_num_max, 'int'),
                },
                "text": {
                    "enable": (switch_local_qa_text_enable, 'bool'),
                    "type": (select_local_qa_text_type, 'str'),
                    "file_path": (input_local_qa_text_file_path, 'str'),
                    "similarity": (input_local_qa_text_similarity, 'float'),
                    "username_max_len": (input_local_qa_text_username_max_len, 'int'),
                },
                "audio": {
                    "enable": (switch_local_qa_audio_enable, 'bool'),
                    "file_path": (input_local_qa_audio_file_path, 'str'),
                    "similarity": (input_local_qa_audio_similarity, 'float'),
                },
            }

        if config.get("webui", "show_card", "common_config", "thanks"):
            config_mapping["thanks"] = {
                "username_max_len": (input_thanks_username_max_len, 'int'),
                "entrance_enable": (switch_thanks_entrance_enable, 'bool'),
                "entrance_random": (switch_thanks_entrance_random, 'bool'),
                "entrance_copy": (textarea_thanks_entrance_copy, 'textarea'),
                "entrance": {
                    "periodic_trigger": {
                        "enable": (switch_thanks_entrance_periodic_trigger_enable, 'bool'),
                        "periodic_time_min": (input_thanks_entrance_periodic_trigger_periodic_time_min, 'int'),
                        "periodic_time_max": (input_thanks_entrance_periodic_trigger_periodic_time_max, 'int'),
                        "trigger_num_min": (input_thanks_entrance_periodic_trigger_trigger_num_min, 'int'),
                        "trigger_num_max": (input_thanks_entrance_periodic_trigger_trigger_num_max, 'int'),
                    }
                },
                "gift_enable": (switch_thanks_gift_enable, 'bool'),
                "gift_random": (switch_thanks_gift_random, 'bool'),
                "gift_copy": (textarea_thanks_gift_copy, 'textarea'),
                "gift": {
                    "periodic_trigger": {
                        "enable": (switch_thanks_gift_periodic_trigger_enable, 'bool'),
                        "periodic_time_min": (input_thanks_gift_periodic_trigger_periodic_time_min, 'int'),
                        "periodic_time_max": (input_thanks_gift_periodic_trigger_periodic_time_max, 'int'),
                        "trigger_num_min": (input_thanks_gift_periodic_trigger_trigger_num_min, 'int'),
                        "trigger_num_max": (input_thanks_gift_periodic_trigger_trigger_num_max, 'int'),
                    }
                },
                "follow_enable": (switch_thanks_follow_enable, 'bool'),
                "follow_random": (switch_thanks_follow_random, 'bool'),
                "follow_copy": (textarea_thanks_follow_copy, 'textarea'),
                "follow": {
                    "periodic_trigger": {
                        "enable": (switch_thanks_follow_periodic_trigger_enable, 'bool'),
                        "periodic_time_min": (input_thanks_follow_periodic_trigger_periodic_time_min, 'int'),
                        "periodic_time_max": (input_thanks_follow_periodic_trigger_periodic_time_max, 'int'),
                        "trigger_num_min": (input_thanks_follow_periodic_trigger_trigger_num_min, 'int'),
                        "trigger_num_max": (input_thanks_follow_periodic_trigger_trigger_num_max, 'int'),
                    }
                },
                "lowest_price": (input_thanks_lowest_price, 'float')
            }

        if config.get("webui", "show_card", "common_config", "audio_random_speed"):
            config_mapping["audio_random_speed"] = {
                "normal": {
                    "enable": (switch_audio_random_speed_normal_enable, 'bool'),
                    "speed_min": (input_audio_random_speed_normal_speed_min, 'float'),
                    "speed_max": (input_audio_random_speed_normal_speed_max, 'float'),
                },
                "copywriting": {
                    "enable": (switch_audio_random_speed_copywriting_enable, 'bool'),
                    "speed_min": (input_audio_random_speed_copywriting_speed_min, 'float'),
                    "speed_max": (input_audio_random_speed_copywriting_speed_max, 'float'),
                },
            }
        if config.get("webui", "show_card", "common_config", "choose_song"):
            config_mapping["choose_song"] = {
                "enable": (switch_choose_song_enable, 'bool'),
                "start_cmd": (textarea_choose_song_start_cmd,'textarea'),
                "stop_cmd": (textarea_choose_song_stop_cmd,'textarea'),
                "random_cmd": (textarea_choose_song_random_cmd,'textarea'),
                "song_path": (input_choose_song_song_path,'str'),
                "match_fail_copy": (input_choose_song_match_fail_copy,'str'),
                "similarity": (input_choose_song_similarity,'float'),
            }
        if config.get("webui", "show_card", "common_config", "sd"):
            config_mapping["sd"] = {
                "enable": (switch_sd_enable, 'bool'),
                "translate_type": (select_sd_translate_type, 'str'),
                "prompt_llm": {
                    "type": (select_sd_prompt_llm_type, 'str'),
                    "before_prompt": (input_sd_prompt_llm_before_prompt, 'str'),
                    "after_prompt": (input_sd_prompt_llm_after_prompt, 'str'),
                },
                "trigger": (input_sd_trigger, 'str'),
                "ip": (input_sd_ip, 'str'),
                "port": (input_sd_port, 'int'),
                "negative_prompt": (input_sd_negative_prompt, 'str'),
                "seed": (input_sd_seed, 'float'),
                "styles": (textarea_sd_styles, 'textarea'),
                "cfg_scale": (input_sd_cfg_scale, 'int'),
                "steps": (input_sd_steps, 'int'),
                "hr_resize_x": (input_sd_hr_resize_x, 'int'),
                "hr_resize_y": (input_sd_hr_resize_y, 'int'),
                "enable_hr": (switch_sd_enable_hr, 'bool'),
                "hr_scale": (input_sd_hr_scale, 'int'),
                "hr_second_pass_steps": (input_sd_hr_second_pass_steps, 'int'),
                "denoising_strength": (input_sd_denoising_strength, 'float'),
                "save_enable": (switch_sd_save_enable, 'bool'),
                "loop_cover": (switch_sd_loop_cover, 'bool'),
                "save_path": (input_sd_save_path, 'str'),
            }
        if config.get("webui", "show_card", "common_config", "search_online"):
            config_mapping["search_online"] = {
                "enable": (switch_search_online_enable, 'bool'),
                "keyword_enable": (switch_search_online_keyword_enable, 'bool'),
                "before_keyword": (textarea_search_online_before_keyword, 'textarea'),
                "engine": (select_search_online_engine, 'str'),
                "engine_id": (input_search_online_engine_id, 'int'),
                "count": (input_search_online_count, 'int'),
                "resp_template": (input_search_online_resp_template, 'str'),
                "http_proxy": (input_search_online_http_proxy, 'str'),
                "https_proxy": (input_search_online_https_proxy, 'str'),
            }
        if config.get("webui", "show_card", "common_config", "web_captions_printer"):
            config_mapping["web_captions_printer"] = {
                "enable": (switch_web_captions_printer_enable, 'bool'),
                "api_ip_port": (input_web_captions_printer_api_ip_port, 'str'),
            }
        if config.get("webui", "show_card", "common_config", "database"):
            config_mapping["database"] = {
                "path": (input_database_path, 'str'),
                "comment_enable": (switch_database_comment_enable, 'bool'),
                "entrance_enable": (switch_database_entrance_enable, 'bool'),
                "gift_enable": (switch_database_gift_enable, 'bool'),
            }
        if config.get("webui", "show_card", "common_config", "abnormal_alarm"):
            config_mapping["abnormal_alarm"] = {
                "platform": {
                    "enable": (switch_abnormal_alarm_platform_enable, 'bool'),
                    "type": (select_abnormal_alarm_platform_type, 'str'),
                    "start_alarm_error_num": (input_abnormal_alarm_platform_start_alarm_error_num, 'int'),
                    "auto_restart_error_num": (input_abnormal_alarm_platform_auto_restart_error_num, 'int'),
                    "local_audio_path": (input_abnormal_alarm_platform_local_audio_path, 'str'),
                },
                "llm": {
                    "enable": (switch_abnormal_alarm_llm_enable, 'bool'),
                    "type": (select_abnormal_alarm_llm_type, 'str'),
                    "start_alarm_error_num": (input_abnormal_alarm_llm_start_alarm_error_num, 'int'),
                    "auto_restart_error_num": (input_abnormal_alarm_llm_auto_restart_error_num, 'int'),
                    "local_audio_path": (input_abnormal_alarm_llm_local_audio_path, 'str'),
                },
                "tts": {
                    "enable": (switch_abnormal_alarm_tts_enable, 'bool'),
                    "type": (select_abnormal_alarm_tts_type, 'str'),
                    "start_alarm_error_num": (input_abnormal_alarm_tts_start_alarm_error_num, 'int'),
                    "auto_restart_error_num": (input_abnormal_alarm_tts_auto_restart_error_num, 'int'),
                    "local_audio_path": (input_abnormal_alarm_tts_local_audio_path, 'str'),
                },
                "svc": {
                    "enable": (switch_abnormal_alarm_svc_enable, 'bool'),
                    "type": (select_abnormal_alarm_svc_type, 'str'),
                    "start_alarm_error_num": (input_abnormal_alarm_svc_start_alarm_error_num, 'int'),
                    "auto_restart_error_num": (input_abnormal_alarm_svc_auto_restart_error_num, 'int'),
                    "local_audio_path": (input_abnormal_alarm_svc_local_audio_path, 'str'),
                },
                "visual_body": {
                    "enable": (switch_abnormal_alarm_visual_body_enable, 'bool'),
                    "type": (select_abnormal_alarm_visual_body_type, 'str'),
                    "start_alarm_error_num": (input_abnormal_alarm_visual_body_start_alarm_error_num, 'int'),
                    "auto_restart_error_num": (input_abnormal_alarm_visual_body_auto_restart_error_num, 'int'),
                    "local_audio_path": (input_abnormal_alarm_visual_body_local_audio_path, 'str'),
                },
                "other": {
                    "enable": (switch_abnormal_alarm_other_enable, 'bool'),
                    "type": (select_abnormal_alarm_other_type, 'str'),
                    "start_alarm_error_num": (input_abnormal_alarm_other_start_alarm_error_num, 'int'),
                    "auto_restart_error_num": (input_abnormal_alarm_other_auto_restart_error_num, 'int'),
                    "local_audio_path": (input_abnormal_alarm_other_local_audio_path, 'str'),
                },
            }

        config_data = update_config(config_mapping, config, config_data, "common_config")
        
        # 定时任务
        if config.get("webui", "show_card", "common_config", "schedule"):
            tmp_arr = []
            # logger.info(schedule_var)
            for index in range(len(schedule_var) // 4):
                tmp_json = {
                    "enable": False,
                    "time_min": 60,
                    "time_max": 120,
                    "copy": []
                }
                tmp_json["enable"] = schedule_var[str(4 * index)].value
                tmp_json["time_min"] = round(float(schedule_var[str(4 * index + 1)].value), 1)
                tmp_json["time_max"] = round(float(schedule_var[str(4 * index + 2)].value), 1)
                tmp_json["copy"] = common_textarea_handle(schedule_var[str(4 * index + 3)].value)

                tmp_arr.append(tmp_json)
            # logger.info(tmp_arr)
            config_data["schedule"] = tmp_arr

        # 闲时任务
        if config.get("webui", "show_card", "common_config", "idle_time_task"):
            config_data["idle_time_task"]["enable"] = switch_idle_time_task_enable.value
            config_data["idle_time_task"]["type"] = select_idle_time_task_type.value

            config_data["idle_time_task"]["min_msg_queue_len_to_trigger"] = int(input_idle_time_task_idle_min_msg_queue_len_to_trigger.value)
            config_data["idle_time_task"]["min_audio_queue_len_to_trigger"] = int(input_idle_time_task_idle_min_audio_queue_len_to_trigger.value)

            config_data["idle_time_task"]["idle_time_min"] = int(input_idle_time_task_idle_time_min.value)
            config_data["idle_time_task"]["idle_time_max"] = int(input_idle_time_task_idle_time_max.value)
            config_data["idle_time_task"]["wait_play_audio_num_threshold"] = int(input_idle_time_task_wait_play_audio_num_threshold.value)
            config_data["idle_time_task"]["idle_time_reduce_to"] = int(input_idle_time_task_idle_time_reduce_to.value)

            tmp_arr = []
            for index in range(len(idle_time_task_trigger_type_var)):
                if idle_time_task_trigger_type_var[str(index)].value:
                    tmp_arr.append(common.find_keys_by_value(idle_time_task_trigger_type_mapping, idle_time_task_trigger_type_var[str(index)].text)[0])
            # logger.info(tmp_arr)
            config_data["idle_time_task"]["trigger_type"] = tmp_arr

            config_data["idle_time_task"]["comment"]["enable"] = switch_idle_time_task_comment_enable.value
            config_data["idle_time_task"]["comment"]["random"] = switch_idle_time_task_comment_random.value
            config_data["idle_time_task"]["copywriting"]["copy"] = common_textarea_handle(textarea_idle_time_task_copywriting_copy.value)
            config_data["idle_time_task"]["copywriting"]["enable"] = switch_idle_time_task_copywriting_enable.value
            config_data["idle_time_task"]["copywriting"]["random"] = switch_idle_time_task_copywriting_random.value
            config_data["idle_time_task"]["comment"]["copy"] = common_textarea_handle(textarea_idle_time_task_comment_copy.value)
            config_data["idle_time_task"]["local_audio"]["enable"] = switch_idle_time_task_local_audio_enable.value
            config_data["idle_time_task"]["local_audio"]["random"] = switch_idle_time_task_local_audio_random.value
            config_data["idle_time_task"]["local_audio"]["path"] = common_textarea_handle(textarea_idle_time_task_local_audio_path.value)


        # 动态文案
        if config.get("webui", "show_card", "common_config", "trends_copywriting"):
            config_data["trends_copywriting"]["enable"] = switch_trends_copywriting_enable.value
            config_data["trends_copywriting"]["llm_type"] = select_trends_copywriting_llm_type.value
            config_data["trends_copywriting"]["random_play"] = switch_trends_copywriting_random_play.value
            config_data["trends_copywriting"]["play_interval"] = int(input_trends_copywriting_play_interval.value)
            tmp_arr = []
            for index in range(len(trends_copywriting_copywriting_var) // 3):
                tmp_json = {
                    "folder_path": "",
                    "prompt_change_enable": False,
                    "prompt_change_content": ""
                }
                tmp_json["folder_path"] = trends_copywriting_copywriting_var[str(3 * index)].value
                tmp_json["prompt_change_enable"] = trends_copywriting_copywriting_var[str(3 * index + 1)].value
                tmp_json["prompt_change_content"] = trends_copywriting_copywriting_var[str(3 * index + 2)].value

                tmp_arr.append(tmp_json)
            # logger.info(tmp_arr)
            config_data["trends_copywriting"]["copywriting"] = tmp_arr

        
        # 按键映射
        if config.get("webui", "show_card", "common_config", "key_mapping"):
            config_data["key_mapping"]["enable"] = switch_key_mapping_enable.value
            config_data["key_mapping"]["type"] = select_key_mapping_type.value
            config_data["key_mapping"]["key_trigger_type"] = select_key_mapping_key_trigger_type.value
            config_data["key_mapping"]["key_single_sentence_trigger_once"] = switch_key_mapping_key_single_sentence_trigger_once_enable.value
            config_data["key_mapping"]["copywriting_trigger_type"] = select_key_mapping_copywriting_trigger_type.value
            config_data["key_mapping"]["copywriting_single_sentence_trigger_once"] = switch_key_mapping_copywriting_single_sentence_trigger_once_enable.value
            config_data["key_mapping"]["local_audio_trigger_type"] = select_key_mapping_local_audio_trigger_type.value
            config_data["key_mapping"]["local_audio_single_sentence_trigger_once"] = switch_key_mapping_local_audio_single_sentence_trigger_once_enable.value
            config_data["key_mapping"]["serial_trigger_type"] = select_key_mapping_serial_trigger_type.value
            config_data["key_mapping"]["serial_single_sentence_trigger_once"] = switch_key_mapping_serial_single_sentence_trigger_once_enable.value
            config_data["key_mapping"]["img_path_trigger_type"] = select_key_mapping_img_path_trigger_type.value
            config_data["key_mapping"]["img_path_single_sentence_trigger_once"] = switch_key_mapping_img_path_single_sentence_trigger_once_enable.value
            

            config_data["key_mapping"]["start_cmd"] = input_key_mapping_start_cmd.value
            tmp_arr = []
            # logger.info(key_mapping_config_var)

            num = 9

            for index in range(len(key_mapping_config_var) // num):
                tmp_json = {
                    "keywords": [],
                    "gift": [],
                    "keys": [],
                    "similarity": 0.8,
                    "copywriting": [],
                    "serial_name": "",
                    "serial_send_data": [],
                    "img_path": []
                }
                tmp_json["keywords"] = common_textarea_handle(key_mapping_config_var[str(num * index)].value)
                tmp_json["gift"] = common_textarea_handle(key_mapping_config_var[str(num * index + 1)].value)
                tmp_json["keys"] = common_textarea_handle(key_mapping_config_var[str(num * index + 2)].value)
                tmp_json["similarity"] = key_mapping_config_var[str(num * index + 3)].value
                tmp_json["copywriting"] = common_textarea_handle(key_mapping_config_var[str(num * index + 4)].value)
                tmp_json["local_audio"] = common_textarea_handle(key_mapping_config_var[str(num * index + 5)].value)
                tmp_json["serial_name"] = key_mapping_config_var[str(num * index + 6)].value
                tmp_json["serial_send_data"] = common_textarea_handle(key_mapping_config_var[str(num * index + 7)].value)
                tmp_json["img_path"] = common_textarea_handle(key_mapping_config_var[str(num * index + 8)].value)

                tmp_arr.append(tmp_json)
            # logger.info(tmp_arr)
            config_data["key_mapping"]["config"] = tmp_arr

        # 自定义命令
        if config.get("webui", "show_card", "common_config", "custom_cmd"):
            config_data["custom_cmd"]["enable"] = switch_custom_cmd_enable.value
            config_data["custom_cmd"]["type"] = select_custom_cmd_type.value
            tmp_arr = []
            # logger.info(custom_cmd_config_var)
            for index in range(len(custom_cmd_config_var) // 7):
                tmp_json = {
                    "keywords": [],
                    "similarity": 1,
                    "api_url": "",
                    "api_type": "",
                    "resp_data_type": "",
                    "data_analysis": "",
                    "resp_template": ""
                }
                tmp_json["keywords"] = common_textarea_handle(custom_cmd_config_var[str(7 * index)].value)
                tmp_json["similarity"] = float(custom_cmd_config_var[str(7 * index + 1)].value)
                tmp_json["api_url"] = custom_cmd_config_var[str(7 * index + 2)].value
                tmp_json["api_type"] = custom_cmd_config_var[str(7 * index + 3)].value
                tmp_json["resp_data_type"] = custom_cmd_config_var[str(7 * index + 4)].value
                tmp_json["data_analysis"] = custom_cmd_config_var[str(7 * index + 5)].value
                tmp_json["resp_template"] = custom_cmd_config_var[str(7 * index + 6)].value

                tmp_arr.append(tmp_json)
            # logger.info(tmp_arr)
            config_data["custom_cmd"]["config"] = tmp_arr

        # 动态配置
        if config.get("webui", "show_card", "common_config", "trends_config"):
            config_data["trends_config"]["enable"] = switch_trends_config_enable.value
            tmp_arr = []
            # logger.info(trends_config_path_var)
            for index in range(len(trends_config_path_var) // 2):
                tmp_json = {
                    "online_num": "0-999999999",
                    "path": "config.json"
                }
                tmp_json["online_num"] = trends_config_path_var[str(2 * index)].value
                tmp_json["path"] = trends_config_path_var[str(2 * index + 1)].value

                tmp_arr.append(tmp_json)
            # logger.info(tmp_arr)
            config_data["trends_config"]["path"] = tmp_arr

        
        # 联动程序
        if config.get("webui", "show_card", "common_config", "coordination_program"):
            tmp_arr = []
            for index in range(len(coordination_program_var) // 4):
                tmp_json = {
                    "enable": True,
                    "name": "",
                    "executable": "",
                    "parameters": []
                }
                tmp_json["enable"] = coordination_program_var[str(4 * index)].value
                tmp_json["name"] = coordination_program_var[str(4 * index + 1)].value
                tmp_json["executable"] = coordination_program_var[str(4 * index + 2)].value
                tmp_json["parameters"] = common_textarea_handle(coordination_program_var[str(4 * index + 3)].value)

                tmp_arr.append(tmp_json)
            # logger.info(tmp_arr)
            config_data["coordination_program"] = tmp_arr
        
        tmp_arr = []
        for index in range(len(luoxi_project_Live_Comment_Assistant_type_var)):
            if luoxi_project_Live_Comment_Assistant_type_var[str(index)].value:
                tmp_arr.append(
                    common.find_keys_by_value(
                        luoxi_project_Live_Comment_Assistant_type_mapping, 
                        luoxi_project_Live_Comment_Assistant_type_var[str(index)].text
                    )[0]
                )
        # logger.info(tmp_arr)
        config_data["luoxi_project"]["Live_Comment_Assistant"]["type"] = tmp_arr

        tmp_arr = []
        for index in range(len(luoxi_project_Live_Comment_Assistant_trigger_position_var)):
            if luoxi_project_Live_Comment_Assistant_trigger_position_var[str(index)].value:
                tmp_arr.append(
                    common.find_keys_by_value(
                        luoxi_project_Live_Comment_Assistant_trigger_position_mapping, 
                        luoxi_project_Live_Comment_Assistant_trigger_position_var[str(index)].text
                    )[0]
                )
        # logger.info(tmp_arr)
        config_data["luoxi_project"]["Live_Comment_Assistant"]["trigger_position"] = tmp_arr

        config_mapping = {
            "luoxi_project": {
                "Live_Comment_Assistant": {
                    "enable": (switch_luoxi_project_Live_Comment_Assistant_enable, 'bool'),
                    "version": (select_luoxi_project_Live_Comment_Assistant_version, 'str'),
                    "api_ip_port": (input_luoxi_project_Live_Comment_Assistant_api_ip_port, 'str'),
                }
            }
        }

        config_data = update_config(config_mapping, config, config_data, None)


    return PageConfig(on_save=save_common)
