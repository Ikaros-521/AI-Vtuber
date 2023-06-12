import gradio as gr
import importlib
from utils import common
from utils import logger

# TODO：gradio的TextBox不能用dict接收（user_config["platform"]获取会返回TextBox而不是string），暂时没有好的解决方法

def start_server(*inputs):
    # 构建json数据
    user_config = common.build_user_config(inputs)

    # 根据直播平台类型不同启动不同的Server
    platform = user_config["platform"]
    if len(platform) > 0:
        importlib.import_module(platform).start_server(user_config)
    else:
        exit(0)


# 配置窗口
with gr.Blocks() as config:
    # 输入列表
    input = []

    # 严格按照config_list.txt的顺序
    with gr.Row():
        with gr.Tab("基础信息输入"):
            input.append(gr.Dropdown(label="直播平台类型", choices=common.get_support_platform()))
            input.append(gr.Textbox(label="直播间房间号"))
            input.append(gr.Dropdown(label="聊天模式",choices=['chatterbot', 'gpt', 'claude', 'langchain_pdf', 'langchain_pdf+gpt', 'none']))
            input.append(gr.Dropdown(label="弹幕语言筛选", choices=['none', 'en', 'jp', 'zh']))
            input.append(gr.Textbox(label="前提限制prompt"))
            input.append(gr.Textbox(label="后置限制prompt"))
            input.append(gr.Textbox(label="最长阅读的英文单词数（空格分隔）"))
            input.append(gr.Textbox(label="最长阅读的字符数，双重过滤，避免溢出"))

    button = gr.Button("确认")
    button.click(
        fn=start_server, inputs=input
    )

    logs = gr.Textbox()

    with gr.Row():
        config.load(logger.read_logs, None, logs, every=1)

config.queue().launch()

