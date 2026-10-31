"""WebUI v3 的运行态：配置文件读写、子进程控制。

逻辑取自 v2 的 webui_app/processes.py，去掉 NiceGUI 依赖（ui.notify 改为返回消息，
由前端决定怎么展示）。
"""

import hashlib
import json
import os
import signal
import subprocess
import sys
import traceback
from pathlib import Path
from threading import Lock

from utils.common import Common
from utils.my_log import logger

# 项目根目录（webui_server/ 的上一级）
ROOT_DIR = Path(__file__).resolve().parent.parent


class Runtime:
    def __init__(self):
        # 与 webui.py 一致：LUNA_CONFIG_PATH 供多实例与自动化测试覆盖配置路径
        self.config_path = os.environ.get("LUNA_CONFIG_PATH") or str(ROOT_DIR / "config.json")
        self.common = Common()
        self.running_flag = False
        self.subprocesses = {}
        self._lock = Lock()
        self._audio = None

    # ---------- 配置 ----------

    def read_config(self):
        """读一份最新配置；文件读不动时抛 OSError，由 API 层翻译。"""
        with open(self.config_path, encoding="utf-8") as f:
            return json.load(f)

    def file_sha256(self):
        with open(self.config_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def write_config(self, data):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()

    def get(self, *keys, default=None):
        result = self.read_config()
        for key in keys:
            if not isinstance(result, dict):
                return default
            result = result.get(key)
            if result is None:
                return default
        return result

    # ---------- 音频（懒加载：utils.audio 会拉起一串音频依赖，没用到就别 import） ----------

    @property
    def audio(self):
        if self._audio is None:
            from utils.audio import Audio

            self._audio = Audio(self.config_path, type=2)
        return self._audio

    # ---------- 子进程 ----------

    def start_programs(self, config):
        for program in config.get("coordination_program") or []:
            if not program["enable"]:
                continue
            name = program["name"]
            executable = program["executable"]
            app_path = program["parameters"][0]
            app_dir = os.path.dirname(app_path)
            logger.info(f"运行程序: {name} 位于: {app_dir}")
            self.subprocesses[name] = subprocess.Popen([executable, app_path], cwd=app_dir, shell=True)

        # 用当前解释器启动 main.py，避免走上 PATH 里的 python
        logger.info("运行程序: main")
        self.subprocesses["main"] = subprocess.Popen([sys.executable, "main.py"], cwd=str(ROOT_DIR))

    def stop_program(self, name):
        if name not in self.subprocesses:
            logger.warning(f"程序 {name} 没有在运行.")
            return
        pid = self.subprocesses[name].pid
        logger.info(f"停止程序和它所有的子进程: {name} with PID {pid}")
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], check=True)
            else:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            logger.info(f"程序 {name} 和 它所有的子进程都被终止.")
        except Exception as e:
            logger.error(f"终止程序 {name} 失败: {e}")
        del self.subprocesses[name]

    def stop_programs(self, config=None):
        for program in (config or self.read_config()).get("coordination_program") or []:
            if program["enable"]:
                self.stop_program(program["name"])
        self.stop_program("main")

    # ---------- 一键操作（消息由调用方展示） ----------

    def run(self):
        with self._lock:
            if self.running_flag:
                return False, "运行中，请勿重复运行"
            try:
                self.running_flag = True
                self.start_programs(self.read_config())
                logger.info("程序开始运行")
                return True, "程序开始运行"
            except Exception as e:
                logger.error(traceback.format_exc())
                self.running_flag = False
                return False, f"运行失败！{e}"

    def stop(self):
        if not self.running_flag:
            return True, "程序没有在运行"
        try:
            self.stop_programs()
            self.running_flag = False
            logger.info("程序已停止")
            return True, "程序已停止"
        except Exception as e:
            logger.error(f"停止错误: {e}")
            return False, f"停止失败！{e}"

    def restart(self):
        """停止运行后用当前解释器重新拉起 webui_server。"""
        self.stop()
        logger.info("重启 webui_server")
        os.execl(sys.executable, sys.executable, "-m", "webui_server", *sys.argv[1:])

    def factory(self, src_path="config.json.bak", dst_path=None):
        try:
            dst = dst_path or self.config_path
            with open(src_path, encoding="utf-8") as source, open(dst, "w", encoding="utf-8") as destination:
                destination.write(source.read())
            logger.info("恢复出厂配置成功！")
            return True, "恢复出厂配置成功，即将重启"
        except Exception as e:
            logger.error(f"恢复出厂配置失败！\n{e}")
            return False, f"恢复出厂配置失败！{e}"


runtime = Runtime()
