import pyautogui
import time


# 模拟按键按下后释放
def simulate_key_press(key):
    pyautogui.keyDown(key)
    time.sleep(0.1)
    pyautogui.keyUp(key)


# 模拟按键按下后释放，传入字符串数组
def simulate_keys_press(keys, re=1):
    """模拟按键按下后释放，传入字符串数组

    Args:
        keys (list): 按键数组
        re (int, optional): 按键个数. Defaults to 1.
    """
    num = 0
    # 模拟按下释放按键
    for key in keys:
        # 限制触发的次数
        if num >= re:
            break
        pyautogui.keyDown(key)
        time.sleep(0.1)
        pyautogui.keyUp(key)

        num = num + 1


# 模拟鼠标点击
def simulate_mouse_press(x=0, y=0, button="left"):
    # 模拟鼠标点击
    pyautogui.click(x=x, y=y, button=button)


# 解析字符串，模拟按键/鼠标按压
def parse_key_and_simulate_key_mouse_press(key):
    # 删除数组中不需要的其他字符串
    # def remove_needless(keys):
    #     for i in range(len(keys)):
    #         if keys[i] not in ['1', '2', 're']:
    #             keys.pop(i)
    #     return keys

    # keys = remove_needless(keys)

    if key not in ["1", "2", "re"]:
        return

    if key == "1":
        key = "w"
        simulate_key_press(key)
    elif key == "2":
        key = "up"
        simulate_key_press(key)
    elif key == "re":
        # 根据实际情况设置坐标值
        x = 1076
        y = 771
        simulate_mouse_press(x, y, "left")

        time.sleep(1)

        x = 1311
        y = 951
        simulate_mouse_press(x, y, "left")


# 解析字符串数组，根据字符串第一位判断是否需要转换按键后，按压按键
def parse_keys_and_simulate_keys_press(keys, re=1):
    # print(f"keys={keys}")

    # 删除数组中非 w a s d 1 2 3 的其他字符串
    def remove_needless(keys):
        for i in range(len(keys)):
            if keys[i] not in ["w", "a", "s", "d", "1"]:
                keys.pop(i)
        return keys

    if isinstance(keys, list) and len(keys) > 0:
        if keys[0] == "1":
            keys = keys[1:]

            keys = remove_needless(keys)

            # 遍历数组，将123改为yui
            for i in range(len(keys)):
                if keys[i] == "1":
                    keys[i] = "f"
                # elif keys[i] == '2':
                #     keys[i] = 'u'
                # elif keys[i] == '3':
                #     keys[i] = 'i'
        elif keys[0] == "2":
            keys = keys[1:]

            keys = remove_needless(keys)

            # 遍历数组，将wsad改为上下左右，123改为789
            for i in range(len(keys)):
                if keys[i] == "w":
                    keys[i] = "up"
                elif keys[i] == "s":
                    keys[i] = "down"
                elif keys[i] == "a":
                    keys[i] = "left"
                elif keys[i] == "d":
                    keys[i] = "right"
                elif keys[i] == "1":
                    keys[i] = "l"
                # elif keys[i] == '2':
                #     keys[i] = '8'
                # elif keys[i] == '3':
                #     keys[i] = '9'
        elif keys[0] == "re":
            # 鼠标按压的坐标，请手动重新校准坐标以适配
            x = 1097
            y = 779

            simulate_mouse_press(x, y)

            time.sleep(1)

            x = 1314
            y = 957

            simulate_mouse_press(x, y)

            return

        simulate_keys_press(keys, re)


if __name__ == "__main__":
    # 测试游戏：醉酒拔河 https://www.4399.com/flash/221542_1.htm

    # 循环获取鼠标当前坐标
    def get_mouse_pos():
        # 定时获取鼠标坐标的时间间隔（秒）
        interval = 1

        try:
            while True:
                # 获取鼠标当前的坐标
                x, y = pyautogui.position()

                # 打印坐标信息
                print(f"当前鼠标坐标：x={x}, y={y}")

                # 等待一段时间后再次获取坐标
                time.sleep(interval)

        except KeyboardInterrupt:
            print("获取鼠标坐标的程序已结束。")

    get_mouse_pos()

    # game1 = Game1()
    # time.sleep(5)
    # game1.parse_key_and_simulate_key_mouse_press('re')
