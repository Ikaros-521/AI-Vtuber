import pygetwindow as gw
import pyautogui

def capture_window_by_title(window_title):
    try:
        # 使用窗口标题查找窗口
        win = gw.getWindowsWithTitle(window_title)[0]  # 获取第一个匹配的窗口
        if win:
            # 获取窗口的位置和大小
            left, top = win.left, win.top
            width, height = win.width, win.height

            # 使用pyautogui捕获指定区域的截图
            screenshot = pyautogui.screenshot(region=(left, top, width, height))
            screenshot.save(f'{window_title}.png')
            print(f"截图已保存为 {window_title}.png")
        else:
            print("未找到指定的窗口")
    except IndexError:
        print("未找到指定的窗口")


# 获取所有有标题的窗口对象
def list_visible_windows():
    """获取所有有标题的窗口对象

    Returns:
        list: 获取所有有标题的窗口名列表
    """
    windows = gw.getWindowsWithTitle('')
    
    window_titles = []

    # 打印每个窗口的标题
    for win in windows:
        if win.title:  # 确保窗口有标题
            window_titles.append(win.title)

    return window_titles

# 调用函数，列出所有可见窗口的标题
list_visible_windows()
    
# 调用函数，替换"Your Window Title Here"为你想要捕获的窗口的标题
capture_window_by_title("伊卡酱 fans群等3个会话")
