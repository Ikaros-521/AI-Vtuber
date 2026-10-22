"""UMS 账号登录与到期自检。

config.json 的 login.enable 打开时，webui 先渲染这张登录卡，登录成功才进入功能页；
之后每十分钟自检一次账号是否还有效，过期就停掉正在运行的程序。
"""

import traceback
from urllib.parse import urljoin

import requests
from nicegui import ui

from utils.my_log import logger
from webui_app.processes import stop_programs

# 登录成功后保存的 UMS 用户信息（含 accessToken、expiration_ts）
user_info = None


def check_expiration(config, common):
    """检查账号是否仍在有效期内，过期则停止程序。"""

    try:
        API_URL = urljoin(config.get("login", "ums_api"), '/auth/check_expiration')

        if user_info is None:
            ui.notify(position="top", type="negative", message=f"账号登录信息失效，请重新登录")
            stop_programs(config)
            return False

        if "accessToken" not in user_info:
            ui.notify(position="top", type="negative", message=f"账号登录信息失效，请重新登录")
            stop_programs(config)
            return False

        headers = {
            "Authorization": "Bearer " + user_info["accessToken"]
        }

        # 发送 POST 请求
        response = requests.post(API_URL, headers=headers, timeout=(10, 300))

        # 判断状态码
        if response.status_code == 200:
            resp_json = response.json()
            if resp_json["code"] == 0 and resp_json["success"]:
                logger.info(f'账号可用，过期时间：{resp_json["data"]["expiration_ts"]}')
                return True
            else:
                remainder = common.time_difference_in_seconds(resp_json["data"]["expiration_ts"])
                ui.notify(position="top", type="negative", message=f'账号过期时间：{resp_json["data"]["expiration_ts"]}，已过期：{remainder}秒，请联系管理员续费')
                logger.error(f'账号过期时间：{resp_json["data"]["expiration_ts"]}，已过期：{remainder}秒，请联系管理员续费')
                stop_programs(config)
                return False

        logger.error(f"自检异常！")
        return False
    except Exception as e:
        ui.notify(position="top", type="negative", message=f"错误：{e}")
        logger.error(traceback.format_exc())

        return False


def start_expiration_timer(config, common):
    """十分钟一次的账号有效期自检。"""
    ui.timer(600.0, lambda: check_expiration(config, common))


def forget_password():
    ui.notify(position="top", type="info", message="请联系管理员修改密码！")


def build_login(config, common, login_card_css, on_success):
    """渲染登录卡片，登录成功后调用 on_success 进入功能页。

    Args:
        config: 配置对象，读取 ums_api 地址。
        common: 通用工具，发起登录请求。
        login_card_css (str): 登录卡片的主题样式。
        on_success: 登录成功后的回调（构建功能页）。

    Returns:
        tuple: (login_column, login_card)。
    """

    def my_login():
        global user_info

        try:
            username = input_login_username.value
            password = input_login_password.value

            if username == "" or password == "":
                ui.notify(position="top", type="info", message="用户名或密码不能为空")
                return

            API_URL = urljoin(config.get("login", "ums_api"), '/auth/login')

            resp_json = common.check_login(API_URL, username, password)

            if resp_json is None:
                ui.notify(position="top", type="negative", message="登录失败")
                return

            if "data" not in resp_json or "success" not in resp_json:
                ui.notify(position="top", type="negative", message="用户名或密码不正确")
                return

            if not resp_json["success"]:
                ui.notify(position="top", type="warning", message=f'账号过期时间：{resp_json["data"]["expiration_ts"]}，已到期，请联系管理员续费')
                return

            user_info = resp_json["data"]
            expiration_ts = resp_json["data"]["expiration_ts"]

            remainder = common.time_difference_in_seconds(expiration_ts)
            if remainder < 0:
                ui.notify(position="top", type="warning", message=f"账号已过期：{remainder}秒，请联系管理员续费")
                return

            ui.notify(position="top", type="info", message=f'登录成功，账号到期时间：{resp_json["data"]["expiration_ts"]}，剩余时长：{remainder}秒')

            label_login.delete()
            input_login_username.delete()
            input_login_password.delete()
            button_login.delete()
            button_login_forget_password.delete()

            login_column.style("")
            login_card.style("position: unset;")

            on_success()

            return
        except Exception as e:
            logger.error(traceback.format_exc())
            return

    login_column = ui.column().style("width:100%;text-align: center;")
    with login_column:
        login_card = ui.card().style(login_card_css)
        with login_card:
            label_login = ui.label('AI    Vtuber').style("font-size: 30px;letter-spacing: 5px;color: #3b3838;")
            input_login_username = ui.input(label='用户名', placeholder='您的账号，请找管理员申请', value="").style("width:250px;")
            input_login_password = ui.input(label='密码', password=True, placeholder='您的密码，请找管理员申请', value="").style("width:250px;")
            button_login = ui.button('登录', on_click=lambda: my_login()).style("width:250px;")
            button_login_forget_password = ui.button('忘记账号/密码怎么办？', on_click=lambda: forget_password()).style("width:250px;")

    return login_column, login_card
