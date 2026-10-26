"""WebUI 的子进程与程序控制。

「一键运行 / 停止 / 重启 / 恢复出厂」这几组按钮和 /sys_cmd 接口共用这里的实现。
"""

import os
import signal
import subprocess
import sys
import traceback

from nicegui import ui

from utils.my_log import logger
from webui_app.errors import explain
from webui_app.state import state

# 存储运行的子进程，key 为程序名
my_subprocesses = {}


def start_programs(config):
    """根据配置启动所有协同程序和 main.py。"""

    for program in config.get("coordination_program"):
        if not program["enable"]:
            continue

        name = program["name"]
        executable = program["executable"]  # Python 解释器的路径
        app_path = program["parameters"][0]  # 假设第一个参数总是 app.py 的路径

        # 从 app.py 的路径中提取目录
        app_dir = os.path.dirname(app_path)

        # 使用 Python 解释器路径和 app.py 路径构建命令
        cmd = [executable, app_path]

        logger.info(f"运行程序: {name} 位于: {app_dir}")

        # 在 app.py 文件所在的目录中启动程序
        process = subprocess.Popen(cmd, cwd=app_dir, shell=True)
        my_subprocesses[name] = process

    name = "main"
    # 用当前解释器启动 main.py，避免走上 PATH 里的 python（可能与 webui 所在的虚拟环境不是同一个）
    process = subprocess.Popen([sys.executable, "main.py"])
    my_subprocesses[name] = process

    logger.info(f"运行程序: {name}")


def stop_program(name):
    """停止一个正在运行的程序及其所有子进程，兼容 Windows、Linux 和 macOS。

    Args:
        name (str): 要停止的程序的名称。
    """
    if name in my_subprocesses:
        pid = my_subprocesses[name].pid  # 获取进程ID
        logger.info(f"停止程序和它所有的子进程: {name} with PID {pid}")

        try:
            if os.name == 'nt':  # Windows
                command = ["taskkill", "/F", "/T", "/PID", str(pid)]
                subprocess.run(command, check=True)
            else:  # POSIX系统，如Linux和macOS
                os.killpg(os.getpgid(pid), signal.SIGKILL)

            logger.info(f"程序 {name} 和 它所有的子进程都被终止.")
        except Exception as e:
            logger.error(f"终止程序 {name} 失败: {e}")

        del my_subprocesses[name]  # 从进程字典中移除
    else:
        logger.warning(f"程序 {name} 没有在运行.")


def stop_programs(config):
    """根据配置停止所有程序。"""

    for program in config.get("coordination_program"):
        if not program["enable"]:
            continue

        stop_program(program["name"])

    stop_program("main")


def run_external_program(config, config_path="config.json", type="webui"):
    """启动协同程序和主程序。

    Args:
        config: 配置对象。
        config_path (str): 配置文件路径，保留给 API 调用方传参。
        type (str): "webui" 时弹出提示，"api" 时静默。
    """

    if state.running_flag:
        if type == "webui":
            ui.notify(position="top", type="warning", message="运行中，请勿重复运行")
        return

    try:
        state.running_flag = True

        # 启动协同程序和主程序
        start_programs(config)

        if type == "webui":
            ui.notify(position="top", type="positive", message="程序开始运行")
        logger.info("程序开始运行")

        return {"code": 200, "msg": "程序开始运行"}
    except Exception as e:
        if type == "webui":
            ui.notify(position="top", type="negative", message=f"启动失败：{explain(e)}")
        logger.error(traceback.format_exc())
        state.running_flag = False

        return {"code": -1, "msg": f"运行失败！{e}"}


def stop_external_program(config, type="webui"):
    """停止正在运行的程序。"""

    if state.running_flag:
        try:
            # 停止协同程序
            stop_programs(config)

            state.running_flag = False
            if type == "webui":
                ui.notify(position="top", type="positive", message="程序已停止")
            logger.info("程序已停止")
        except Exception as e:
            if type == "webui":
                ui.notify(position="top", type="negative", message=f"停止错误：{e}")
            logger.error(f"停止错误：{e}")

            return {"code": -1, "msg": f"重启失败！{e}"}


def restart_application(config, type="webui"):
    """停止运行后用当前解释器重新拉起 webui。"""
    try:
        # 先停止运行
        stop_external_program(config, type)

        logger.info(f"重启webui")
        if type == "webui":
            ui.notify(position="top", type="ongoing", message=f"重启中...")
        python = sys.executable
        os.execl(python, python, *sys.argv)  # Start a new instance of the application
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"code": -1, "msg": f"重启失败！{e}"}


def factory(config, src_path='config.json.bak', dst_path='config.json', type="webui"):
    """用备份配置覆盖当前配置并重启。"""

    try:
        with open(src_path, 'r', encoding="utf-8") as source:
            with open(dst_path, 'w', encoding="utf-8") as destination:
                destination.write(source.read())
        logger.info("恢复出厂配置成功！")
        if type == "webui":
            ui.notify(position="top", type="positive", message=f"恢复出厂配置成功！")

        # 重启
        restart_application(config)

        return {"code": 200, "msg": "恢复出厂配置成功！"}
    except Exception as e:
        logger.error(f"恢复出厂配置失败！\n{e}")
        if type == "webui":
            ui.notify(position="top", type="negative", message=f"恢复出厂配置失败！\n{e}")

        return {"code": -1, "msg": f"恢复出厂配置失败！\n{e}"}


def scroll_to_top():
    """页面平滑滑到顶部"""
    # 平滑滚动到页面顶部
    ui.run_javascript("window.scrollTo({top: 0, behavior: 'smooth'});")
