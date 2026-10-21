#!/usr/bin/env python
"""冒烟测试：核心模块导入、配置加载、WebUI 启动。

用法：
    python tools/smoke_test.py            # 全部检查
    python tools/smoke_test.py --skip-webui
"""
import argparse
import ast
import importlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_MODULES = [
    "utils.config",
    "utils.common",
    "utils.my_log",
    "utils.models",
    "utils.audio",
    "utils.audio_handle.audio_player",
    "utils.audio_handle.my_tts",
    "utils.gpt_model.gpt",
    "utils.platforms",
    "utils.db",
    "utils.my_translate",
    "utils.my_handle",
    "webui_app.chat_log",
    "webui_app.helpers",
    "webui_app.pages.assistant_anchor",
    "webui_app.pages.copywriting",
    "webui_app.pages.data_analysis",
    "webui_app.pages.image_recognition",
    "webui_app.pages.integral",
    "webui_app.pages.llm",
    "webui_app.pages.serial",
    "webui_app.pages.talk",
    "webui_app.pages.static_pages",
    "webui_app.pages.svc",
    "webui_app.pages.translate",
    "webui_app.pages.visual_body",
    "webui_app.state",
]
REQUIRED_CONFIG_KEYS = ["webui", "platform", "chat_type", "filter", "openai"]


def load_config():
    config_path = Path(os.environ.get("LUNA_CONFIG_PATH") or ROOT / "config.json")
    with config_path.open(encoding="utf-8") as f:
        data = json.load(f)

    missing = [key for key in REQUIRED_CONFIG_KEYS if key not in data]
    if missing:
        raise AssertionError(f"config.json 缺少顶层配置：{', '.join(missing)}")
    for key in ("ip", "port"):
        if key not in (data.get("webui") or {}):
            raise AssertionError(f"config.json 缺少 webui.{key}")
    return data


def check_imports():
    failures = []
    sys.path.insert(0, str(ROOT))
    for name in CORE_MODULES:
        try:
            importlib.import_module(name)
            print(f"  OK   {name}")
        except Exception:
            failures.append(name)
            print(f"  FAIL {name}")
            traceback.print_exc()
    if failures:
        raise AssertionError(f"核心模块导入失败：{', '.join(failures)}")


def check_platform_registry():
    """平台注册表里的每个模块都要存在且暴露 start_listen（只做静态检查，不导入平台 SDK）。"""
    from utils.platforms import PLATFORM_LISTENERS

    failures = []
    for platform, module_name in PLATFORM_LISTENERS.items():
        path = ROOT / Path(*module_name.split(".")).with_suffix(".py")
        if not path.is_file():
            failures.append(f"{platform} -> {module_name}：文件不存在")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if not any(
            isinstance(node, ast.FunctionDef) and node.name == "start_listen"
            for node in tree.body
        ):
            failures.append(f"{platform} -> {module_name}：没有定义 start_listen")
    print(f"  已登记平台：{', '.join(sorted(PLATFORM_LISTENERS))}")
    if failures:
        raise AssertionError("平台注册表有问题：\n  " + "\n  ".join(failures))


def find_free_port():
    sock = socket.socket()
    try:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


def tail(path, limit=4000):
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-limit:]


def check_webui(timeout):
    config = load_config()
    port = find_free_port()
    config.setdefault("webui", {})
    config["webui"].update({"ip": "127.0.0.1", "port": port, "auto_run": False})
    if isinstance(config.get("login"), dict):
        config["login"]["enable"] = False

    with tempfile.TemporaryDirectory(prefix="luna-smoke-") as tmp:
        tmp = Path(tmp)
        test_config = tmp / "config.json"
        test_config.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
        stdout_path = tmp / "stdout.log"
        stderr_path = tmp / "stderr.log"

        env = os.environ.copy()
        env["LUNA_CONFIG_PATH"] = str(test_config)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            proc = subprocess.Popen(
                [sys.executable, "webui.py"],
                cwd=ROOT,
                stdout=stdout,
                stderr=stderr,
                env=env,
            )
            started = time.time()
            url = f"http://127.0.0.1:{port}/"
            try:
                while time.time() - started < timeout:
                    if proc.poll() is not None:
                        raise AssertionError(
                            f"webui 提前退出，返回码 {proc.returncode}\n"
                            f"--- stdout ---\n{tail(stdout_path)}\n"
                            f"--- stderr ---\n{tail(stderr_path)}"
                        )
                    try:
                        with urllib.request.urlopen(url, timeout=2) as response:
                            if response.status == 200:
                                print(f"  OK   webui {url} ({time.time() - started:.1f}s)")
                                return
                    except OSError:
                        time.sleep(0.5)
                raise AssertionError(
                    f"webui 在 {timeout}s 内未返回 200\n"
                    f"--- stdout ---\n{tail(stdout_path)}\n"
                    f"--- stderr ---\n{tail(stderr_path)}"
                )
            finally:
                if proc.poll() is None:
                    if os.name == "nt":
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                            capture_output=True,
                        )
                    else:
                        proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()


def main():
    parser = argparse.ArgumentParser(description="Luna AI 冒烟测试")
    parser.add_argument("--skip-webui", action="store_true", help="不启动 WebUI")
    parser.add_argument("--timeout", type=float, default=60, help="WebUI 启动超时秒数")
    args = parser.parse_args()

    print("[1/4] 配置检查")
    load_config()
    print("  OK   config.json")

    print("[2/4] 核心模块导入")
    check_imports()

    print("[3/4] 平台注册表")
    check_platform_registry()

    if args.skip_webui:
        print("[4/4] 已跳过 WebUI 启动")
    else:
        print("[4/4] WebUI 启动")
        check_webui(args.timeout)

    print("SMOKE OK")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"\nSMOKE FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
