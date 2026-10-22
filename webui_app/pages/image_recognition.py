"""图像识别页：截图/摄像头取图后交给 Gemini 或智谱分析。"""
import asyncio
import traceback

from nicegui import ui

from utils.my_log import logger
from webui_app.helpers import select_value_or_none
from webui_app.pages import PageConfig


def build_image_recognition_tab(config, common, state, card_css, switch_internal_css,
                                button_internal_color, button_internal_css):
    with ui.card().style(card_css):
        async def get_llm_resp(screenshot_path: str, send_to_all: bool = True):
            try:
                prompt = input_image_recognition_prompt.value

                if select_image_recognition_model.value == "gemini":
                    from utils.gpt_model.gemini import Gemini

                    gemini = Gemini(config.get("image_recognition", "gemini"))

                    resp_content = gemini.get_resp_with_img(prompt, screenshot_path)

                    data = {
                        "type": "reread",
                        "username": config.get("talk", "username"),
                        "content": resp_content,
                        "insert_index": -1
                    }
                elif select_image_recognition_model.value == "zhipu":
                    from utils.gpt_model.zhipu import Zhipu

                    zhipu = Zhipu(config.get("image_recognition", "zhipu"))

                    resp_content = zhipu.get_resp_with_img(prompt, screenshot_path)

                    data = {
                        "type": "reread",
                        "data": {
                            "username": config.get("talk", "username"),
                            "content": resp_content,
                            "insert_index": -1
                        }
                    }

                if send_to_all:
                    if data is not None:
                        main_api_ip = "127.0.0.1" if config.get("api_ip") == "0.0.0.0" else config.get("api_ip")
                        await common.send_async_request(f'http://{main_api_ip}:{config.get("api_port")}/send', "POST", data)

                return data
            except Exception:
                logger.error(traceback.format_exc())
                return None

        async def loop_screenshot_toggle_timer(interval_time: float):
            async def image_recognition_screenshot_and_send():
                if state.running_flag != 1:
                    ui.notify(position="top", type="warning", message="请先点击“一键运行”，然后再进行截图识别")
                    return

                logger.info(f"触发截图识别")
                screenshot_path = common.capture_window_by_title(input_image_recognition_img_save_path.value, select_image_recognition_screenshot_window_title.value)
                await get_llm_resp(screenshot_path)

            if state.loop_screenshot_timer_running:
                state.loop_screenshot_timer.cancel()
            else:
                state.loop_screenshot_timer = ui.timer(interval=interval_time, callback=lambda: image_recognition_screenshot_and_send())
                state.loop_screenshot_timer.activate()
            state.loop_screenshot_timer_running = not state.loop_screenshot_timer_running

        async def image_recognition_screenshot_and_send(sleep_time: float):
            if state.running_flag != 1:
                ui.notify(position="top", type="warning", message="请先点击“一键运行”，然后再进行截图识别")
                return

            logger.info(f"{input_image_recognition_screenshot_delay.value}后触发截图识别")
            ui.notify(position="top", type="positive", message=f"{input_image_recognition_screenshot_delay.value}后触发截图识别")

            await asyncio.sleep(sleep_time)

            screenshot_path = common.capture_window_by_title(input_image_recognition_img_save_path.value, select_image_recognition_screenshot_window_title.value)
            await get_llm_resp(screenshot_path)

        async def image_recognition_cam_screenshot_and_send(sleep_time: float):
            if state.running_flag != 1:
                ui.notify(position="top", type="warning", message="请先点击“一键运行”，然后再进行截图识别")
                return

            logger.info(f"{input_image_recognition_cam_screenshot_delay.value}后触发摄像头截图识别")
            ui.notify(position="top", type="positive", message=f"{input_image_recognition_screenshot_delay.value}后触发截图识别")

            await asyncio.sleep(sleep_time)

            screenshot_path = common.capture_image(input_image_recognition_img_save_path.value, int(select_image_recognition_cam_index.value))
            await get_llm_resp(screenshot_path)

        ui.label("通用")
        with ui.row():
            button_image_recognition_enable = ui.switch('启用', value=config.get("image_recognition", "enable")).style(switch_internal_css)
            select_image_recognition_model = ui.select(
                label='模型',
                options={'gemini': 'gemini', 'zhipu': '智谱AI'},
                value=config.get("image_recognition", "model")
            ).style("width:150px")

            input_image_recognition_img_save_path = ui.input(label='截图保存路径', value=config.get("image_recognition", "img_save_path"), placeholder='截图保存路径，支持绝对或相对路径')
            input_image_recognition_prompt = ui.input(label='携带的提示词', value=config.get("image_recognition", "prompt"), placeholder='图片识别时附带的提示词，协同图片获取回答')

        with ui.card().style(card_css):
            ui.label("电脑截图")
            with ui.row():
                window_titles = common.list_visible_windows()
                data_json = {}
                for line in window_titles:
                    data_json[line] = line
                select_image_recognition_screenshot_window_title = ui.select(
                    label='截图窗口标题',
                    options=data_json,
                    value=select_value_or_none(config.get("image_recognition", "screenshot_window_title"), data_json)
                ).style("width:300px")
                input_image_recognition_screenshot_delay = ui.input(label='N秒后进行截图', value=config.get("image_recognition", "screenshot_delay"), placeholder='截图延迟，方便用户打开对应窗口').style("width:100px")
                button_image_recognition_screenshot_and_send = ui.button('截图并发送', on_click=lambda: image_recognition_screenshot_and_send(float(input_image_recognition_screenshot_delay.value)), color=button_internal_color).style(button_internal_css)

                switch_image_recognition_loop_screenshot_enable = ui.switch('循环截图并发送', value=config.get("image_recognition", "loop_screenshot_enable")).style(switch_internal_css)
                input_image_recognition_loop_screenshot_delay = ui.input(label='N秒后自动截图', value=config.get("image_recognition", "loop_screenshot_delay"), placeholder='自动截图延迟，用户在玩游戏或者看视频等情况下，可以自动触发图像识别').style("width:100px")

        with ui.card().style(card_css):
            ui.label("摄像头截图")
            with ui.row():
                switch_image_recognition_cam_screenshot_enable = ui.switch('启用', value=config.get("image_recognition", "cam_screenshot_enable")).style(switch_internal_css)

                if config.get("image_recognition", "cam_screenshot_enable"):
                    cam_indexs = common.list_cameras()
                else:
                    cam_indexs = []
                data_json = {}
                for line in cam_indexs:
                    data_json[line] = line
                select_image_recognition_cam_index = ui.select(
                    label='摄像头索引',
                    options=data_json,
                    value=select_value_or_none(config.get("image_recognition", "cam_index"), data_json)
                ).style("width:100px")
                input_image_recognition_cam_screenshot_delay = ui.input(label='N秒后进行截图', value=config.get("image_recognition", "cam_screenshot_delay"), placeholder='截图延迟，方便用户调整摄像头').style("width:100px")
                button_image_recognition_cam_screenshot_and_send = ui.button('截图并发送', on_click=lambda: image_recognition_cam_screenshot_and_send(float(input_image_recognition_cam_screenshot_delay.value)), color=button_internal_color).style(button_internal_css)

                switch_image_recognition_loop_cam_screenshot_enable = ui.switch('循环截图并发送', value=config.get("image_recognition", "loop_cam_screenshot_enable")).style(switch_internal_css)
                input_image_recognition_loop_cam_screenshot_delay = ui.input(label='N秒后自动截图', value=config.get("image_recognition", "loop_cam_screenshot_delay"), placeholder='自动截图延迟，可以自动触发图像识别').style("width:100px")

    with ui.card().style(card_css):
        ui.label("Gemini")
        with ui.row():
            select_image_recognition_gemini_model = ui.select(
                label='模型',
                options={'gemini-pro-vision': 'gemini-pro-vision'},
                value=config.get("image_recognition", "gemini", "model")
            ).style("width:150px")
            input_image_recognition_gemini_api_key = ui.input(label='API Key', value=config.get("image_recognition", "gemini", "api_key"), placeholder='Gemini API KEY')
            input_image_recognition_gemini_http_proxy = ui.input(label='HTTP代理地址', value=config.get("image_recognition", "gemini", "http_proxy"), placeholder='http代理地址，需要魔法才能使用，所以需要配置此项。').style("width:200px;")
            input_image_recognition_gemini_https_proxy = ui.input(label='HTTPS代理地址', value=config.get("image_recognition", "gemini", "https_proxy"), placeholder='https代理地址，需要魔法才能使用，所以需要配置此项。').style("width:200px;")

    with ui.card().style(card_css):
        ui.label("智谱AI")
        with ui.row():
            select_image_recognition_zhipu_model = ui.select(
                label='模型',
                options={'glm-4v': 'glm-4v'},
                value=config.get("image_recognition", "zhipu", "model")
            ).style("width:150px")
            input_image_recognition_zhipu_api_key = ui.input(label='API Key', value=config.get("image_recognition", "zhipu", "api_key"), placeholder='智谱 API KEY')

    return PageConfig(mapping={
        "image_recognition": {
            "enable": (button_image_recognition_enable, 'bool'),
            "model": (select_image_recognition_model, 'str'),
            "img_save_path": (input_image_recognition_img_save_path, 'str'),
            "prompt": (input_image_recognition_prompt, 'str'),
            "screenshot_window_title": (select_image_recognition_screenshot_window_title, 'str'),
            "screenshot_delay": (input_image_recognition_screenshot_delay, 'float'),
            "loop_screenshot_enable": (switch_image_recognition_loop_screenshot_enable, 'bool'),
            "loop_screenshot_delay": (input_image_recognition_loop_screenshot_delay, 'int'),
            "cam_screenshot_enable": (switch_image_recognition_cam_screenshot_enable, 'bool'),
            "cam_index": (select_image_recognition_cam_index, 'int'),
            "cam_screenshot_delay": (input_image_recognition_cam_screenshot_delay, 'float'),
            "loop_cam_screenshot_enable": (switch_image_recognition_loop_cam_screenshot_enable, 'bool'),
            "loop_cam_screenshot_delay": (input_image_recognition_loop_cam_screenshot_delay, 'int'),
            "gemini": {
                "model": (select_image_recognition_gemini_model, 'str'),
                "api_key": (input_image_recognition_gemini_api_key, 'str'),
                "http_proxy": (input_image_recognition_gemini_http_proxy, 'str'),
                "https_proxy": (input_image_recognition_gemini_https_proxy, 'str'),
            },
            "zhipu": {
                "model": (select_image_recognition_zhipu_model, 'str'),
                "api_key": (input_image_recognition_zhipu_api_key, 'str'),
            },
        }
    })
