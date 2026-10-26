"""串口页：串口组配置、连接测试与数据发送。"""
import traceback

from nicegui import ui

from utils.my_log import logger
from webui_app.confirm import delete_button
from webui_app.errors import notify_error
from webui_app.groups import GroupPicker
from webui_app.descriptions import show_card_desc
from webui_app.pages import PageConfig
from webui_app.theme import INK


def build_serial_tab(config, card_css, switch_internal_css, button_internal_color, button_internal_css):
    serial_config_var = {}
    serial_config_card = ui.card()

    async def refresh_serial(index: int):
        logger.warning(index)
        try:
            from utils.serial_manager_instance import get_serial_manager

            serial_manager = get_serial_manager()
            list_ports = await serial_manager.list_ports()
            logger.info(f"搜索到的串口：{list_ports}")
            ui.notify(position="top", type="positive", message=f"搜索到的串口：{list_ports}")
            serial_config_var[str(8 * index)].set_options(list_ports)
        except Exception as e:
            logger.error(traceback.format_exc())
            notify_error(e, '搜索串口')

    async def connect_serial(index: int):
        logger.warning(index)
        try:
            from utils.serial_manager_instance import get_serial_manager

            serial_manager = get_serial_manager()
            serial_name = serial_config_var[str(8 * index)].value
            baudrate = serial_config_var[str(8 * index + 1)].value
            resp_json = await serial_manager.connect(serial_name, baudrate)
            ui.notify(position="top", type="positive" if resp_json['ret'] else "negative", message=f"{resp_json['msg']}")
        except Exception as e:
            logger.error(traceback.format_exc())
            notify_error(e, '连接串口')

    async def disconnect_serial(index: int):
        logger.warning(index)
        try:
            from utils.serial_manager_instance import get_serial_manager

            serial_manager = get_serial_manager()
            serial_name = serial_config_var[str(8 * index)].value
            resp_json = await serial_manager.disconnect(serial_name)
            ui.notify(position="top", type="positive" if resp_json['ret'] else "negative", message=f"{resp_json['msg']}")
        except Exception as e:
            logger.error(traceback.format_exc())
            notify_error(e, '关闭串口')

    async def send_data_to_serial(index: int):
        try:
            from utils.serial_manager_instance import get_serial_manager

            serial_manager = get_serial_manager()
            serial_name = serial_config_var[str(8 * index)].value
            serial_data_type = serial_config_var[str(8 * index + 5)].value
            send_data = serial_config_var[str(8 * index + 6)].value
            resp_json = await serial_manager.send_data(serial_name, send_data, serial_data_type)
            ui.notify(position="top", type="positive" if resp_json['ret'] else "negative", message=f"{resp_json['msg']}")
        except Exception as e:
            logger.error(traceback.format_exc())
            notify_error(e, '发送串口数据')

    def serial_config_add():
        data_len = len(serial_config_var)
        tmp_config = {
            "serial_name": "COM1",
            "baudrate": "115200",
            "serial_data_type": "ASCII"
        }

        with serial_config_card.style(card_css):
            with ui.row():
                serial_config_var[str(data_len)] = ui.select(label=f"串口名#{int(data_len / 8) + 1}", value=tmp_config["serial_name"], options={f'{tmp_config["serial_name"]}': f'{tmp_config["serial_name"]}'}).style("width:200px;").tooltip('文案文件存储路径。不建议更改。')
                serial_config_var[str(data_len + 1)] = ui.select(
                    label=f"波特率#{int(data_len / 8) + 1}",
                    value=tmp_config["baudrate"],
                    options={'9600': '9600', '19200': '19200', '38400': '38400', '115200': '115200'}
                ).style("width:200px;").tooltip('波特率')
                serial_config_var[str(data_len + 2)] = ui.button('刷新串口', on_click=lambda: refresh_serial(int(data_len / 8)))
                serial_config_var[str(data_len + 3)] = ui.button('打开串口', on_click=lambda: connect_serial(int(data_len / 8)))
                serial_config_var[str(data_len + 4)] = ui.button('关闭串口', on_click=lambda: disconnect_serial(int(data_len / 8)))

                serial_config_var[str(data_len + 5)] = ui.select(label=f"发送数据类型#{int(data_len / 8) + 1}", value=tmp_config["serial_data_type"], options={'ASCII': 'ASCII', 'HEX': 'HEX'},).style("width:100px;").tooltip('发送的数据类型')
                serial_config_var[str(data_len + 6)] = ui.input(label=f"发送数据#{int(data_len / 8) + 1}", value="", placeholder='填要发的内容，连接后，点 发送').style("width:200px;").tooltip('填要发的内容，连接后，点 发送')
                serial_config_var[str(data_len + 7)] = ui.button('发送', on_click=lambda: send_data_to_serial(int(data_len / 8)))

    def serial_config_del(pos):
        try:
            keys_to_delete = [str(8 * pos + i) for i in range(8)]
            for key in keys_to_delete:
                if key in serial_config_var:
                    del serial_config_var[key]

            updates = {}
            for key in sorted(serial_config_var.keys(), key=int):
                new_key = str(int(key) - 8 if int(key) > int(keys_to_delete[-1]) else key)
                updates[new_key] = serial_config_var[key]

            serial_config_var.clear()
            serial_config_var.update(updates)
        except Exception as e:
            ui.notify(position="top", type="negative", message=f"错误，索引值配置有误：{e}")
            logger.error(traceback.format_exc())

    with ui.element('div').classes('tip-bar'):
        ui.label("此页完成串口配置后，可以在“按键与命令”的 串口映射配置功能\n 注意！！！此处连接测试完成后，请 关闭串口，因为程序是跨进程使用的，所以不关掉会占用串口，导致无法正常使用！")

    # 串口配置组的增删原来直接铺在渐变面板上（同页其余区块都在卡片里），包进一张卡
    with ui.card().style(card_css + 'width:100%;'):
        ui.label('串口').style(f'font-size:14px;font-weight:600;color:{INK};')
        show_card_desc('串口')
        with ui.row():
            picker_serial = GroupPicker(lambda: serial_config_card, '串口', serial_config_del, lambda: serial_config_var).build()
            button_serial_config_add = ui.button('增加串口配置组', on_click=lambda: (serial_config_add(), picker_serial.refresh()), color=button_internal_color).style(button_internal_css)
            button_serial_config_del = delete_button('删除串口配置组', picker_serial.ask_delete).style(button_internal_css)

    with serial_config_card:
        for index, serial_config in enumerate(config.get("serial", "config")):
            with serial_config_card.style(card_css):
                with ui.row():
                    serial_config_var[str(8 * index)] = ui.select(label=f"串口名#{index + 1}", value=serial_config["serial_name"], options={f'{serial_config["serial_name"]}': f'{serial_config["serial_name"]}'}).style("width:200px;").tooltip('文案文件存储路径。不建议更改。')
                    serial_config_var[str(8 * index + 1)] = ui.select(
                        label=f"波特率#{index + 1}",
                        value=serial_config["baudrate"],
                        options={'9600': '9600', '19200': '19200', '38400': '38400', '115200': '115200'}
                    ).style("width:200px;").tooltip('波特率')

                    serial_config_var[str(8 * index + 2)] = ui.button('刷新串口', on_click=lambda idx=index: refresh_serial(idx))
                    serial_config_var[str(8 * index + 3)] = ui.button('打开串口', on_click=lambda idx=index: connect_serial(idx))
                    serial_config_var[str(8 * index + 4)] = ui.button('关闭串口', on_click=lambda idx=index: disconnect_serial(idx))

                    serial_config_var[str(8 * index + 5)] = ui.select(label=f"发送数据类型#{index + 1}", value=serial_config["serial_data_type"], options={'ASCII': 'ASCII', 'HEX': 'HEX'},).style("width:100px;").tooltip('发送的数据类型')
                    serial_config_var[str(8 * index + 6)] = ui.input(label=f"发送数据#{index + 1}", value="", placeholder='填要发的内容，连接后，点 发送').style("width:200px;").tooltip('填要发的内容，连接后，点 发送')
                    serial_config_var[str(8 * index + 7)] = ui.button('发送', on_click=lambda idx=index: send_data_to_serial(idx))

    def save_serial_config(config_data):
        tmp_arr = []
        for index in range(len(serial_config_var) // 8):
            tmp_arr.append({
                "serial_name": serial_config_var[str(8 * index)].value,
                "baudrate": serial_config_var[str(8 * index + 1)].value,
                "serial_data_type": serial_config_var[str(8 * index + 5)].value,
            })
        config_data.setdefault("serial", {})["config"] = tmp_arr

    return PageConfig(on_save=save_serial_config)
