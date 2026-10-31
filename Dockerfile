FROM docker.io/library/python:3.10

# 设置工作目录
WORKDIR .

# 复制应用程序文件到容器中
COPY . .


# 安装应用程序依赖项
RUN apt-get update && \
    apt-get install -y portaudio19-dev ffmpeg libasound2-dev

RUN pip install requests

# docker跑ai vtb不太行，声卡加载有问题，pyautogui加载也有问题（模拟键鼠）
RUN pip install -r requirements.txt -i https://pypi.org/simple/ 

# 设置环境变量（如果需要）

# 暴露应用程序的端口（如果需要）
EXPOSE 8081
EXPOSE 8082

# 启动应用程序
# v3 起 WebUI 入口是 webui_server（v2 的 webui.py 已删除）
CMD ["python", "-m", "webui_server"]