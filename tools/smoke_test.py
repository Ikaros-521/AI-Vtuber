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
    "luna.infra.config",
    "luna.common.helpers",
    "luna.infra.my_log",
    "luna.infra.models",
    "luna.audio.service",
    "luna.audio.audio_player",
    "luna.audio.my_tts",
    "luna.llm.gpt",
    "luna.platforms",
    "luna.infra.db",
    "luna.core.my_translate",
    "luna.core.my_handle",
    # v2 NiceGUI 前端(webui_app)已删除，改为导入 v3 后端模块
    "webui_server.app",
    "webui_server.runtime",
    "webui_server.port_guard",
    "webui_server.auth_api",
    "webui_server.config_api",
    "webui_server.compat_api",
    "webui_server.logs_api",
    "webui_server.ops_api",
    "webui_server.actions_api",
    "webui_server.chat_log",
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
    from luna.platforms import PLATFORM_LISTENERS

    failures = []
    for platform, module_name in PLATFORM_LISTENERS.items():
        path = ROOT / Path(*module_name.split(".")).with_suffix(".py")
        if not path.is_file():
            failures.append(f"{platform} -> {module_name}：文件不存在")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if not any(isinstance(node, ast.FunctionDef) and node.name == "start_listen" for node in tree.body):
            failures.append(f"{platform} -> {module_name}：没有定义 start_listen")
    print(f"  已登记平台：{', '.join(sorted(PLATFORM_LISTENERS))}")
    if failures:
        raise AssertionError("平台注册表有问题：\n  " + "\n  ".join(failures))


def check_agent_registry():
    """Agent 决策域（v5）：注册表完整性与核心类型可构造（docs/agent-upgrade-design.md）。"""
    from luna.agent.context import AgentContext, Budget
    from luna.agent.registry import TOOLS, ToolRegistry, load_tool_class

    failures = []
    for name in TOOLS:
        try:
            tool = load_tool_class(name)()
            if tool.name != name or not tool.description:
                failures.append(f"{name}：name/description 不完整")
        except Exception:
            failures.append(f"{name}：加载失败")
            traceback.print_exc()
    # ToolRegistry 走 Config 的多级链式取值，要传 Config 而不是裸 dict
    from luna.infra.config import Config

    config_path = Path(os.environ.get("LUNA_CONFIG_PATH") or ROOT / "config.json")
    registry = ToolRegistry(Config(str(config_path)))
    enabled = [spec["name"] for spec in registry.specs()]
    print(f"  已注册工具：{', '.join(sorted(TOOLS))}")
    print(f"  当前启用：{', '.join(enabled) if enabled else '（无）'}")
    if failures:
        raise AssertionError("Agent 工具注册表有问题：\n  " + "\n  ".join(failures))
    # Budget/AgentContext 只做可构造性检查（不请求 LLM、不碰 db）
    Budget(max_tool_rounds=1, timeout_seconds=1)
    assert AgentContext.__dataclass_fields__, "AgentContext 字段缺失"


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
        env["WEBUI_V3_PORT"] = str(port)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            proc = subprocess.Popen(
                [sys.executable, "-m", "webui_server"],
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

    print("[1/5] 配置检查")
    load_config()
    print("  OK   config.json")

    print("[2/5] 核心模块导入")
    check_imports()

    print("[3/5] 平台注册表")
    check_platform_registry()

    print("[4/5] Agent 决策域")
    check_agent_registry()

    if args.skip_webui:
        print("[5/5] 已跳过 WebUI 启动")
    else:
        print("[5/5] WebUI 启动")
        check_webui(args.timeout)

    print("SMOKE OK")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"\nSMOKE FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
