"""极简独立聊天页：即时消息视窗与复合交互坞（文本与麦克风对话）。"""
from nicegui import ui

from utils.my_log import logger
from webui_app.pages import PageConfig


def build_chat_tab(config, common, state, chat_log, card_css, switch_internal_css,
                   button_internal_color, button_internal_css):
    """构建极简独立的聊天与交互页。

    将原先混在 talk.py 大量音频底层配置中的聊天记录与发送框彻底剥离，
    为用户提供一个纯净、现代、即时响应的 AI Vtuber 对话交互工作区。
    """
    with ui.column().classes('w-full').style(
        'max-width:960px;margin:0 auto;height:calc(100vh - 170px);min-height:540px;display:flex;flex-direction:column;gap:12px;padding:4px 0;'
    ):
        # 1. 聊天记录主视窗
        with ui.card().classes('w-full flex-grow').style(
            'display:flex;flex-direction:column;padding:0;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.06);border-radius:12px;background:#ffffff;'
        ):
            # 顶栏微状态条
            with ui.row().classes('w-full items-center justify-between').style(
                'padding:10px 18px;border-bottom:1px solid #f3f4f6;background:#fafafa;'
            ):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('chat', size='20px', color='#6366f1')
                    ui.label('AI 对话与即时交互').style('font-size:14px;font-weight:600;color:#111827;')

                with ui.row().classes('items-center gap-4'):
                    # 运行态状态指示
                    is_running = (state.running_flag == 1)
                    ui.label('● 服务运行中' if is_running else '○ 核心未运行').style(
                        f'font-size:12px;font-weight:500;color:{"#16a34a" if is_running else "#6b7280"};'
                    ).tooltip('核心服务运行状态；未运行时请点击右上角「一键运行」')

                    switch_show_log = ui.switch(
                        '同步弹幕', value=config.get("talk", "show_chat_log")
                    ).props('dense').style('font-size:12px;').tooltip('开启后，直播间弹幕与 AI 回复将实时同步显示到本聊天窗口')

            # 消息滚动区
            scroll_area = ui.scroll_area().classes('w-full flex-grow').style(
                'padding:16px 20px;height:100%;'
            )
            chat_log.mount(scroll_area)

        # 2. 底部极简复合交互坞（Dock）
        with ui.card().classes('w-full').style(
            'padding:12px 16px;box-shadow:0 1px 4px rgba(0,0,0,0.06);border-radius:12px;background:#ffffff;gap:10px;'
        ):
            # 上排：身份、麦克风快速控麦与次级操作
            with ui.row().classes('w-full items-center justify-between'):
                with ui.row().classes('items-center gap-3'):
                    input_username = ui.input(
                        label='说话人昵称',
                        value=config.get("talk", "username") or "主播"
                    ).props('dense outlined').style('width:130px;font-size:13px;').tooltip('在此输入您与 AI 对话时的昵称/身份')

                    # 麦克风直接对话快捷开关
                    switch_direct_talk = ui.switch(
                        '🎤 语音对话 (直接拾音)',
                        value=config.get("talk", "direct_run_talk")
                    ).props('dense').style('font-size:13px;').tooltip('开启后无需按键，麦克风将自动监听语音并与 AI 实时对话')

                    trigger_key = config.get("talk", "trigger_key")
                    if trigger_key:
                        ui.badge(f'录音热键: {trigger_key}', color='grey-6').props('outline').tooltip('若未开启直接拾音，可在后台按此快捷键触发录音')

                with ui.row().classes('items-center gap-2'):
                    btn_reread = ui.button('直接复读', on_click=lambda: do_reread()).props(
                        'outline dense no-caps'
                    ).style('font-size:12px;padding:2px 10px;color:#4b5563;').tooltip('跳过大模型思考，让当前 TTS 语音引擎直接朗读输入框文字（声音调试）')

                    btn_tuning = ui.button('调教', on_click=lambda: do_tuning()).props(
                        'outline dense no-caps'
                    ).style('font-size:12px;padding:2px 10px;color:#4b5563;').tooltip('向 LLM 注入提示词或指导信息，不触发语音播放')

            # 下排：文本输入与发送
            with ui.row().classes('w-full items-center gap-2'):
                input_text = ui.input(
                    placeholder='输入消息与 AI 对话... (按 Enter 发送)'
                ).props('outlined dense').classes('flex-grow').style('font-size:14px;')
                input_text.is_config_field = False

                btn_send = ui.button('发送', on_click=lambda: do_send()).props('unelevated').style(
                    'padding:0 22px;height:40px;background:#6366f1;color:#ffffff;font-weight:600;border-radius:6px;'
                ).tooltip('发送消息给 AI，模拟弹幕互动并触发语音回复')

                input_text.on('keydown.enter.prevent', lambda: do_send())

    # 发送消息给核心服务
    async def do_send():
        if state.running_flag != 1:
            ui.notify(position="top", type="info", message="请先点击右上角“一键运行”启动核心服务")
            return

        username = (input_username.value or "主播").strip()
        content = (input_text.value or "").strip()
        if not content:
            return
        input_text.value = ""

        data = {
            "type": "comment",
            "data": {
                "type": "comment",
                "platform": "webui",
                "username": username,
                "content": content,
            }
        }

        logger.debug(f"chat send data={data}")
        main_api_ip = "127.0.0.1" if config.get("api_ip") == "0.0.0.0" else config.get("api_ip")
        await common.send_async_request(f'http://{main_api_ip}:{config.get("api_port")}/send', "POST", data)

    async def do_reread(insert_index=-1, reread_type="reread"):
        if state.running_flag != 1:
            ui.notify(position="top", type="warning", message="请先点击右上角“一键运行”启动核心服务")
            return

        username = (input_username.value or "主播").strip()
        content = (input_text.value or "").strip()
        if not content:
            return
        input_text.value = ""

        if insert_index == -1:
            data = {
                "type": reread_type,
                "data": {
                    "type": reread_type,
                    "username": username,
                    "content": content,
                }
            }
        else:
            data = {
                "type": reread_type,
                "data": {
                    "type": reread_type,
                    "username": username,
                    "content": content,
                    "insert_index": insert_index,
                }
            }

        if switch_show_log.value:
            show_chat_log_json = {
                "type": "llm",
                "data": {
                    "type": reread_type,
                    "username": username,
                    "content_type": "question",
                    "content": content,
                    "timestamp": common.get_bj_time(0),
                }
            }
            chat_log.add(show_chat_log_json)

        main_api_ip = "127.0.0.1" if config.get("api_ip") == "0.0.0.0" else config.get("api_ip")
        await common.send_async_request(f'http://{main_api_ip}:{config.get("api_port")}/send', "POST", data)

    async def do_tuning():
        if state.running_flag != 1:
            ui.notify(position="top", type="warning", message="请先点击右上角“一键运行”启动核心服务")
            return

        username = (input_username.value or "主播").strip()
        content = (input_text.value or "").strip()
        if not content:
            return
        input_text.value = ""

        data = {
            "type": "tuning",
            "data": {
                "type": "tuning",
                "username": username,
                "content": content,
            }
        }

        main_api_ip = "127.0.0.1" if config.get("api_ip") == "0.0.0.0" else config.get("api_ip")
        await common.send_async_request(f'http://{main_api_ip}:{config.get("api_port")}/send', "POST", data)

    return PageConfig(
        mapping={
            "talk": {
                "username": (input_username, 'str'),
                "show_chat_log": (switch_show_log, 'bool'),
                "direct_run_talk": (switch_direct_talk, 'bool'),
            }
        }
    )
