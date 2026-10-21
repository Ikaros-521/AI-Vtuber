"""数据分析页：弹幕词云与积分/礼物榜单。"""
from nicegui import ui

from utils.data_analysis import Data_Analysis
from webui_app.pages import PageConfig


def build_data_analysis_tab(config, config_path, echart_css):
    data_analysis = Data_Analysis(config_path)

    data_analysis_comment_word_cloud_card = ui.card()
    with data_analysis_comment_word_cloud_card.style("width:100%;"):
        echart_comment_word_cloud = ui.echart(data_analysis.get_comment_word_cloud_option(
            int(config.get("data_analysis", "comment_word_cloud", "top_num")))
        ).style(echart_css)

        with ui.row():
            input_data_analysis_comment_word_cloud_top_num = ui.input(label='前N个关键词', value=config.get("data_analysis", "comment_word_cloud", "top_num"), placeholder='筛选前N个弹幕关键词做为词云数据')

            def update_echart_comment_word_cloud():
                data_analysis_comment_word_cloud_card.remove(0)
                echart = ui.echart(data_analysis.get_comment_word_cloud_option(
                    int(input_data_analysis_comment_word_cloud_top_num.value))
                ).style(echart_css)
                echart.move(data_analysis_comment_word_cloud_card, 0)

            ui.button('更新数据', on_click=lambda: update_echart_comment_word_cloud())

    data_analysis_integral_card = ui.card()
    with data_analysis_integral_card.style("width:100%;"):
        echart_integral = ui.echart(data_analysis.get_integral_option(
            "integral", int(config.get("data_analysis", "integral", "top_num")))
        ).style(echart_css)

        with ui.row():
            input_data_analysis_integral_top_num = ui.input(label='Top N个数据', value=config.get("data_analysis", "integral", "top_num"), placeholder='筛选Top N个数据')

            def update_echart_integral(type):
                data_analysis_integral_card.remove(0)
                echart = ui.echart(data_analysis.get_integral_option(
                    type,
                    int(input_data_analysis_integral_top_num.value))
                ).style(echart_css)
                echart.move(data_analysis_integral_card, 0)

            ui.button('获取积分榜', on_click=lambda: update_echart_integral('integral'))
            ui.button('获取观看榜', on_click=lambda: update_echart_integral('view_num'))
            ui.button('获取签到榜', on_click=lambda: update_echart_integral('sign_num'))
            ui.button('获取金额榜', on_click=lambda: update_echart_integral('total_price'))

    data_analysis_gift_card = ui.card()
    with data_analysis_gift_card.style("width:100%;"):
        echart_gift = ui.echart(data_analysis.get_gift_option(int(config.get("data_analysis", "gift", "top_num")))).style(echart_css)

        with ui.row():
            input_data_analysis_gift_top_num = ui.input(label='Top N个数据', value=config.get("data_analysis", "gift", "top_num"), placeholder='筛选Top N个数据')

            def update_echart_gift():
                data_analysis_gift_card.remove(0)
                echart = ui.echart(data_analysis.get_gift_option(
                    int(input_data_analysis_gift_top_num.value))
                ).style(echart_css)
                echart.move(data_analysis_gift_card, 0)

            ui.button('更新数据', on_click=lambda: update_echart_gift())

    return PageConfig(mapping={
        "data_analysis": {
            "comment_word_cloud": {
                "top_num": (input_data_analysis_comment_word_cloud_top_num, 'int'),
            },
            "integral": {
                "top_num": (input_data_analysis_integral_top_num, 'int'),
            },
            "gift": {
                "top_num": (input_data_analysis_gift_top_num, 'int'),
            },
        }
    })
