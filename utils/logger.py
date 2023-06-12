import gradio as gr
import sys


# 将运行结果实时输出到gradio的textBox中

class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def isatty(self):
        return False


terminal_log = "log/terminal.log"
sys.stdout = Logger(terminal_log)


def read_logs():
    sys.stdout.flush()
    with open(terminal_log, "r") as f:
        return f.read()
