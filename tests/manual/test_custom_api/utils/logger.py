import logging
import colorlog

def Configure_logger(log_file):
    log_format = '%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'
    color_format = '%(log_color)s%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s%(reset)s'

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 创建一个处理程序
    handler = logging.FileHandler(log_file, encoding='utf-8', mode='a+')

    handlers = [handler]

    # 创建控制台处理程序并设置颜色
    console = colorlog.StreamHandler()
    console.setFormatter(colorlog.ColoredFormatter(
        color_format,
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'white', # 将INFO的颜色设置为白色
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'red,bg_white',
        }
    ))
    handlers.append(console)

    logger.handlers = handlers

    formatter = colorlog.ColoredFormatter(
        color_format,
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 将处理程序添加到记录器，并设置格式化器
    handler.setFormatter(formatter)