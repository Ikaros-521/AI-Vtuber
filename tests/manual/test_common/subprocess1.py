import subprocess
import json
import os, time, logging
import signal

config_json = '''
{
  "coordination_program": [
    {
      "name": "captions_printer",
      "path": "E://GitHub_pro//captions_printer//pkg//captions_printer-v4.1//Miniconda3//python.exe",
      "parameters": ["E://GitHub_pro//captions_printer//pkg//captions_printer-v4.1//app.py"]
    },
    {
      "name": "audio_player",
      "path": "E://GitHub_pro//audio_player//pkg//audio_player_v2-20240320//Miniconda3//python.exe",
      "parameters": ["E://GitHub_pro//audio_player//pkg//audio_player_v2-20240320//app.py"]
    }
  ]
}
'''

# 解析 JSON 配置
config = json.loads(config_json)

# 存储启动的进程
processes = {}

def start_programs(config):
    """根据配置启动所有程序。

    Args:
        config (dict): 包含程序配置的字典。
    """
    for program in config.get("programs", []):
        name = program["name"]
        python_path = program["path"]  # Python 解释器的路径
        app_path = program["parameters"][0]  # 假设第一个参数总是 app.py 的路径
        
        # 从 app.py 的路径中提取目录
        app_dir = os.path.dirname(app_path)
        
        # 使用 Python 解释器路径和 app.py 路径构建命令
        cmd = [python_path, app_path]

        logging.info(f"运行程序: {name} 位于: {app_dir}")
        
        # 在 app.py 文件所在的目录中启动程序
        process = subprocess.Popen(cmd, cwd=app_dir, shell=True)
        processes[name] = process

def stop_program(name):
    """停止一个正在运行的程序及其所有子进程，兼容 Windows、Linux 和 macOS。

    Args:
        name (str): 要停止的程序的名称。
    """
    if name in processes:
        pid = processes[name].pid  # 获取进程ID
        logging.info(f"停止程序和它所有的子进程: {name} with PID {pid}")

        try:
            if os.name == 'nt':  # Windows
                command = ["taskkill", "/F", "/T", "/PID", str(pid)]
                subprocess.run(command, check=True)
            else:  # POSIX系统，如Linux和macOS
                os.killpg(os.getpgid(pid), signal.SIGKILL)

            logging.info(f"程序 {name} 和 它所有的子进程都被终止.")
        except Exception as e:
            logging.error(f"终止程序 {name} 失败: {e}")

        del processes[name]  # 从进程字典中移除
    else:
        logging.warning(f"程序 {name} 没有在运行.")

# 启动所有配置中的程序
start_programs(config)

# ...执行其他任务...
time.sleep(10)

# 当你想要停止某个程序时
stop_program("captions_logging.infoer")
stop_program("audio_player")
