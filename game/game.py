import pyautogui
import time
import importlib
import traceback
import logging

from utils.common import Common
from utils.config import Config


class Game:
    def __init__(self, config_path, data):
        self.config = Config(config_path)
        self.common = Common()

        try:
            self.module_name = importlib.import_module(data["module_name"])
        except Exception as e:
            logging.error(traceback.format_exc())
            raise e


    # 解析字符串，模拟按键/鼠标按压
    def parse_key_and_simulate_key_mouse_press(self, key):
        self.module_name.parse_key_and_simulate_key_mouse_press(key)


    # 解析字符串数组，根据字符串第一位判断是否需要转换按键后，按压按键
    def parse_keys_and_simulate_keys_press(self, keys):
        self.module_name.parse_keys_and_simulate_keys_press(keys)


    # 模拟按键按下后释放，传入字符串数组
    def simulate_key_press(self, keys):
        # 模拟按下释放按键
        for key in keys:
            pyautogui.keyDown(key)
            time.sleep(0.1)
            pyautogui.keyUp(key)


    # 解析字符串数组，根据字符串第一位判断是否需要转换按键后，按压按键
    def parse_keys_and_simulate_key_press(self, keys):
        # 删除数组中非 w a s d 1 2 3 的其他字符串
        def remove_needless(keys):
            for i in range(len(keys)):
                if keys[i] not in ['w', 'a', 's', 'd', '1', '2', '3']:
                    keys.pop(i)
            return keys
        
        if keys[0] == '1':
            keys = keys[1:]

            keys = remove_needless(keys)

            # 遍历数组，将123改为yui
            for i in range(len(keys)):
                if keys[i] == '1':
                    keys[i] = 'y'
                elif keys[i] == '2':
                    keys[i] = 'u'
                elif keys[i] == '3':
                    keys[i] = 'i'
        elif keys[0] == '2':
            keys = keys[1:]

            keys = remove_needless(keys)
            
            # 遍历数组，将wsad改为上下左右，123改为789
            for i in range(len(keys)):
                if keys[i] == 'w':
                    keys[i] = 'up'
                elif keys[i] == 's':
                    keys[i] = 'down'
                elif keys[i] == 'a':
                    keys[i] = 'left'
                elif keys[i] == 'd':
                    keys[i] = 'right'
                elif keys[i] == '1':
                    keys[i] = '7'
                elif keys[i] == '2':
                    keys[i] = '8'
                elif keys[i] == '3':
                    keys[i] = '9'

        self.simulate_key_press(keys)