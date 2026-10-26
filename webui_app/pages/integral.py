"""积分页：签到、礼物、入场与增删改查配置。"""
from nicegui import ui

from webui_app.helpers import common_textarea_handle, textarea_data_change
from webui_app.descriptions import show_card_desc
from webui_app.pages import PageConfig


def build_integral_tab(config, card_css, switch_internal_css):
    with ui.card().style(card_css):
        ui.label("积分系统")
        show_card_desc("积分系统")
        with ui.grid(columns=3):
            switch_integral_enable = ui.switch('启用', value=config.get("integral", "enable")).style(switch_internal_css)
    with ui.card().style(card_css):
        ui.label("签到")
        show_card_desc("签到")
        with ui.grid(columns=3):
            switch_integral_sign_enable = ui.switch('启用', value=config.get("integral", "sign", "enable")).style(switch_internal_css)
            input_integral_sign_get_integral = ui.input(label='获得积分数', value=config.get("integral", "sign", "get_integral"), placeholder='签到成功可以获得的积分数，请填写正整数！')
            textarea_integral_sign_cmd = ui.textarea(label='命令', value=textarea_data_change(config.get("integral", "sign", "cmd")), placeholder='弹幕发送以下命令可以触发签到功能，换行分隔命令')
        with ui.card().style(card_css):
            ui.label("文案")
            integral_sign_copywriting_var = {}
            for index, integral_sign_copywriting in enumerate(config.get("integral", "sign", "copywriting")):
                with ui.grid(columns=2):
                    integral_sign_copywriting_var[str(2 * index)] = ui.input(label=f"签到数区间#{index}", value=integral_sign_copywriting["sign_num_interval"], placeholder='限制在此区间内的签到数来触发对应的文案，用-号来进行区间划分，包含边界值')
                    integral_sign_copywriting_var[str(2 * index + 1)] = ui.textarea(label=f"文案#{index}", value=textarea_data_change(integral_sign_copywriting["copywriting"]), placeholder='在此签到区间内，触发的文案内容，换行分隔').style("width:400px;")
    with ui.card().style(card_css):
        ui.label("礼物")
        with ui.grid(columns=3):
            switch_integral_gift_enable = ui.switch('启用', value=config.get("integral", "gift", "enable")).style(switch_internal_css)
            input_integral_gift_get_integral_proportion = ui.input(label='获得积分比例', value=config.get("integral", "gift", "get_integral_proportion"), placeholder='此比例和礼物真实金额（元）挂钩，默认就是1元=10积分')
        with ui.card().style(card_css):
            ui.label("文案")
            integral_gift_copywriting_var = {}
            for index, integral_gift_copywriting in enumerate(config.get("integral", "gift", "copywriting")):
                with ui.grid(columns=2):
                    integral_gift_copywriting_var[str(2 * index)] = ui.input(label=f"礼物价格区间#{index}", value=integral_gift_copywriting["gift_price_interval"], placeholder='限制在此区间内的礼物价格来触发对应的文案，用-号来进行区间划分，包含边界值')
                    integral_gift_copywriting_var[str(2 * index + 1)] = ui.textarea(label=f"文案#{index}", value=textarea_data_change(integral_gift_copywriting["copywriting"]), placeholder='在此礼物区间内，触发的文案内容，换行分隔').style("width:400px;")
    with ui.card().style(card_css):
        ui.label("入场")
        with ui.grid(columns=3):
            switch_integral_entrance_enable = ui.switch('启用', value=config.get("integral", "entrance", "enable")).style(switch_internal_css)
            input_integral_entrance_get_integral = ui.input(label='获得积分数', value=config.get("integral", "entrance", "get_integral"), placeholder='签到成功可以获得的积分数，请填写正整数！')
        with ui.card().style(card_css):
            ui.label("文案")
            integral_entrance_copywriting_var = {}
            for index, integral_entrance_copywriting in enumerate(config.get("integral", "entrance", "copywriting")):
                with ui.grid(columns=2):
                    integral_entrance_copywriting_var[str(2 * index)] = ui.input(label=f"入场数区间#{index}", value=integral_entrance_copywriting["entrance_num_interval"], placeholder='限制在此区间内的入场数来触发对应的文案，用-号来进行区间划分，包含边界值')
                    integral_entrance_copywriting_var[str(2 * index + 1)] = ui.textarea(label=f"文案#{index}", value=textarea_data_change(integral_entrance_copywriting["copywriting"]), placeholder='在此入场区间内，触发的文案内容，换行分隔').style("width:400px;")
    with ui.card().style(card_css):
        ui.label("增删改查")
        show_card_desc("增删改查")
        with ui.card().style(card_css):
            ui.label("查询")
            with ui.grid(columns=3):
                switch_integral_crud_query_enable = ui.switch('启用', value=config.get("integral", "crud", "query", "enable")).style(switch_internal_css)
                textarea_integral_crud_query_cmd = ui.textarea(label="命令", value=textarea_data_change(config.get("integral", "crud", "query", "cmd")), placeholder='弹幕发送以下命令可以触发查询功能，换行分隔命令')
                textarea_integral_crud_query_copywriting = ui.textarea(label="文案", value=textarea_data_change(config.get("integral", "crud", "query", "copywriting")), placeholder='触发查询功能后返回的文案内容，换行分隔命令').style("width:400px;")

    def save_integral(config_data):
        integral = config_data.setdefault("integral", {})

        integral["enable"] = switch_integral_enable.value

        sign = integral.setdefault("sign", {})
        sign["enable"] = switch_integral_sign_enable.value
        sign["get_integral"] = int(input_integral_sign_get_integral.value)
        sign["cmd"] = common_textarea_handle(textarea_integral_sign_cmd.value)
        sign["copywriting"] = [
            {
                "sign_num_interval": integral_sign_copywriting_var[str(2 * index)].value,
                "copywriting": common_textarea_handle(integral_sign_copywriting_var[str(2 * index + 1)].value),
            }
            for index in range(len(integral_sign_copywriting_var) // 2)
        ]

        gift = integral.setdefault("gift", {})
        gift["enable"] = switch_integral_gift_enable.value
        gift["get_integral_proportion"] = float(input_integral_gift_get_integral_proportion.value)
        gift["copywriting"] = [
            {
                "gift_price_interval": integral_gift_copywriting_var[str(2 * index)].value,
                "copywriting": common_textarea_handle(integral_gift_copywriting_var[str(2 * index + 1)].value),
            }
            for index in range(len(integral_gift_copywriting_var) // 2)
        ]

        entrance = integral.setdefault("entrance", {})
        entrance["enable"] = switch_integral_entrance_enable.value
        entrance["get_integral"] = int(input_integral_entrance_get_integral.value)
        entrance["copywriting"] = [
            {
                "entrance_num_interval": integral_entrance_copywriting_var[str(2 * index)].value,
                "copywriting": common_textarea_handle(integral_entrance_copywriting_var[str(2 * index + 1)].value),
            }
            for index in range(len(integral_entrance_copywriting_var) // 2)
        ]

        query = integral.setdefault("crud", {}).setdefault("query", {})
        query["enable"] = switch_integral_crud_query_enable.value
        query["cmd"] = common_textarea_handle(textarea_integral_crud_query_cmd.value)
        query["copywriting"] = common_textarea_handle(textarea_integral_crud_query_copywriting.value)

    return PageConfig(on_save=save_integral)
