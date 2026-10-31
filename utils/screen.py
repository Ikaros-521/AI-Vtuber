"""屏幕与摄像头采集：自 utils/common.py 拆分。

依赖说明：pygetwindow/pyautogui/cv2 都属于 visual 可选依赖组
（requirements/visual.txt），沿用原实现的函数内按需 import，
缺失时降级返回空列表/None，不炸导入。
"""

import os
import tempfile
import traceback

from utils.my_log import logger


def _common():
    """复用 Common 的文件工具与系统判定（函数内导入避免与 common.py 循环依赖）。"""
    from utils.common import Common

    return Common()


def list_visible_windows():
    """获取所有有标题的窗口对象

    Returns:
        list: 获取所有有标题的窗口名列表
    """
    if _common().detect_os() == "Windows":
        try:
            import pygetwindow as gw
        except ImportError:
            logger.warning("未安装 pygetwindow（见 requirements/visual.txt），窗口列表暂时为空")
            return []

        windows = gw.getWindowsWithTitle("")

        window_titles = []

        # 打印每个窗口的标题
        for win in windows:
            if win.title:  # 确保窗口有标题
                window_titles.append(win.title)
    else:
        return []

    return window_titles


def capture_window_by_title(img_save_path: str, window_title: str):
    """根据窗口名截图（截图窗口不能被遮挡，必须前置窗口）

    Args:
        img_save_path (str): 图片保存路径
        window_title (str): 窗口标题

    Returns:
        str: 图片保存路径含文件名
    """
    try:
        if _common().detect_os() == "Windows":
            import pyautogui
            import pygetwindow as gw

            # 使用窗口标题查找窗口
            win = gw.getWindowsWithTitle(window_title)[0]  # 获取第一个匹配的窗口
            if win:
                # 获取窗口的位置和大小
                left, top = win.left, win.top
                width, height = win.width, win.height

                # 使用pyautogui捕获指定区域的截图
                screenshot = pyautogui.screenshot(region=(left, top, width, height))

                # 判断路径存在，不存在就创建
                _common().ensure_directory_exists(img_save_path)

                # logger.debug(f"img_save_path={img_save_path}")
                destination_directory = os.path.abspath(img_save_path)
                logger.debug(f"destination_directory={destination_directory}")

                # 获取图片路径含文件名
                destination_path = os.path.join(destination_directory, f"{window_title}.png")
                logger.debug(f"destination_path={destination_path}")

                screenshot.save(destination_path)

                logger.info(f"截图已保存到：{destination_path}")

                return destination_path
            else:
                logger.error(f"未找到指定的窗口：{window_title}")
        else:
            return None
    except IndexError:
        logger.error(f"未找到指定的窗口：{window_title}")
    except Exception:
        logger.error(traceback.format_exc())

    return None


def list_cameras(max_tested=5):
    """获取所有可用摄像头的索引

    Args:
        max_tested (int, optional): 最大检索摄像头数. Defaults to 5.

    Returns:
        list: 可用摄像头的索引列表
    """
    try:
        import cv2

        available_cameras = []
        for i in range(max_tested):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # 尝试打开摄像头
            if cap.isOpened():  # 检查摄像头是否成功打开
                available_cameras.append(i)
                cap.release()  # 释放摄像头
            else:
                break  # 如果一个摄像头索引打不开，假设后面的都不可用
        return available_cameras
    except Exception:
        logger.error(traceback.format_exc())

    return []


def capture_image(img_save_path="./out/图像识别", camera_index=0):
    try:
        import cv2

        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)

        # 检查摄像头是否成功打开
        if not cap.isOpened():
            logger.info(f"无法打开摄像头 索引={camera_index}")
            return None

        # 读取一帧图像
        ret, frame = cap.read()
        if not ret:
            logger.error("无法获取摄像头流数据")
            return None
        cap.release()  # 释放摄像头

        common = _common()
        # 判断路径存在，不存在就创建
        common.ensure_directory_exists(img_save_path)

        # logger.debug(f"img_save_path={img_save_path}")
        destination_directory = os.path.abspath(img_save_path)
        logger.debug(f"destination_directory={destination_directory}")

        # 构造文件名和保存路径
        destination_path = os.path.join(destination_directory, f"camera_{camera_index}_{cv2.getTickCount()}")
        logger.debug(f"destination_path={destination_path}")

        # 在系统临时目录中创建一个临时文件
        temp_dir = tempfile.gettempdir()
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png", dir=temp_dir)
        temp_path = temp_file.name
        temp_file.close()  # 关闭文件，确保可以被其他进程使用

        # 保存图像
        save_ret = cv2.imwrite(temp_path, frame)
        if save_ret:
            logger.info(f"图像已保存到：{temp_path}")
        else:
            logger.error(f"图像保存失败：{temp_path}")
            return None

        # 将文件从临时路径移动到目标路径
        final_path = common.move_file(temp_path, destination_path, f"camera_{camera_index}_{cv2.getTickCount()}", "png")

        return final_path
    except Exception:
        logger.error(traceback.format_exc())

    return None
