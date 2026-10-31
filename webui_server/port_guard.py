"""端口占用守卫：uvicorn 起服前清掉残留的 webui_server 实例。

强退（直接关终端窗口、任务管理器杀进程）时，上一次的 python -m webui_server
可能没死透，继续占着 webui.port，下一次启动就报 [Errno 10048]。启动前先：
1. 探测 host:port 能否绑定（TIME_WAIT 不影响，只有真监听才挡）；
2. 被占则查出监听 PID（Windows 走 netstat -ano，POSIX 走 lsof）；
3. 命令行确认是 webui_server 的残留实例，才 taskkill /F /T 连子进程一起回收
   （runtime 拉起的 main.py 等协调程序都在它的进程树里，一并收掉）；
4. 别的程序占用就不动它，把 PID 和命令行报出来让人决定。

不依赖 psutil：base 环境没装，netstat/taskkill/PowerShell 都是系统自带。
"""

import os
import signal
import socket
import subprocess
import time

from luna.infra.my_log import logger

_KILL_WAIT_SEC = 3.0


def port_in_use(host: str, port: int) -> bool:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
        except OSError:
            return True
    return False


def _split_addr(addr: str):
    """netstat 的本地地址列：127.0.0.1:8081 / [::]:8081 / 0.0.0.0:8081。"""
    try:
        if addr.startswith("["):
            ip, _, port = addr[1:].partition("]:")
            return ip, int(port)
        ip, _, port = addr.rpartition(":")
        return ip, int(port)
    except ValueError:
        return "", -1


def _host_match(host: str, local_ip: str) -> bool:
    if host in ("0.0.0.0", "::", "") or local_ip in ("0.0.0.0", "::", "*"):
        return True
    return local_ip == host


def _listener_pids(host: str, port: int) -> list:
    """返回在 host:port 上处于 LISTENING 的 PID 列表。"""
    pids = set()
    if os.name == "nt":
        # 中文系统的 netstat 输出是 GBK，在 UTF-8 模式解释器下会解码失败；解析只涉及
        # ASCII 字段（地址/状态/PID），errors="replace" 足够且不会抛异常
        out = (
            subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, errors="replace").stdout
            or ""
        )
        for line in out.splitlines():
            parts = line.split()
            # TCP  本地地址  远程地址  状态  PID
            if len(parts) >= 5 and parts[3] == "LISTENING":
                local_ip, local_port = _split_addr(parts[1])
                if local_port == port and _host_match(host, local_ip):
                    pids.add(int(parts[4]))
    else:
        out = (
            subprocess.run(
                ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-Fp"],
                capture_output=True,
                text=True,
                errors="replace",
            ).stdout
            or ""
        )
        for line in out.splitlines():
            if line.startswith("p") and line[1:].isdigit():
                pids.add(int(line[1:]))
    return sorted(pids)


def _cmdline(pid: int) -> str:
    if os.name == "nt":
        try:
            out = (
                subprocess.run(
                    ["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine", "/value"],
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=10,
                ).stdout
                or ""
            )
            for line in out.splitlines():
                if line.startswith("CommandLine="):
                    return line.split("=", 1)[1]
        except Exception:
            pass
        try:
            out = (
                subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine",
                    ],
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=15,
                ).stdout
                or ""
            )
            return out.strip()
        except Exception:
            return ""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return f.read().replace(b"\x00", b" ").decode("utf-8", "replace").strip()
    except OSError:
        return ""


def _kill_tree(pid: int):
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            text=True,
            errors="replace",
        )
    else:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


def ensure_port_free(host: str, port: int) -> bool:
    """端口可用（含清掉残留实例后）返回 True；被别的程序占用返回 False。"""
    if not port_in_use(host, port):
        return True

    logger.warning(f"端口 {host}:{port} 已被占用，正在查找占用进程…")
    pids = _listener_pids(host, port)
    if not pids:
        if not port_in_use(host, port):
            return True  # 刚好自己退了
        logger.error("端口被占但定位不到监听进程，请手动检查后重试。")
        return False

    own_pid = os.getpid()
    stale = []
    for pid in pids:
        if pid in (0, 4, own_pid):
            continue
        cmdline = _cmdline(pid)
        if "webui_server" in cmdline:
            stale.append((pid, cmdline))
        else:
            logger.error(f"端口被其它进程占用：PID {pid} -> {cmdline or '（拿不到命令行）'}")
            logger.error(
                "不是 webui_server 的残留实例，不会自动处理；请换端口（--port / WEBUI_V3_PORT）或先手动结束该进程。"
            )
            return False

    if not stale:
        logger.error("找不到可回收的占用者，请手动检查后重试。")
        return False

    for pid, cmdline in stale:
        logger.warning(f"回收强退残留的 webui_server 实例：PID {pid}（{cmdline}），连同其子进程一起终止")
        _kill_tree(pid)

    deadline = time.time() + _KILL_WAIT_SEC
    while time.time() < deadline:
        if not port_in_use(host, port):
            logger.info("残留实例已回收，端口释放。")
            return True
        time.sleep(0.3)
    logger.error("回收后端口仍被占用，请手动检查。")
    return False
