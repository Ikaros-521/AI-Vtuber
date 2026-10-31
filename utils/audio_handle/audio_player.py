import requests
import traceback

from utils.my_log import logger

# 对接AUDIO_PLAYER 音频播放器项目
class AUDIO_PLAYER:
    def __init__(self, data):
        try:
            self.api_ip_port = data["api_ip_port"]
        except Exception:
            logger.error(traceback.format_exc())
            return None

    def play(self, data):
        try:
            url = f"{self.api_ip_port}/play"

            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=data, headers=headers, timeout=(10, 300))

            if response.status_code == 200:
                data_json = response.json()
                # logger.info(data_json)
                if data_json["code"] != 200:
                    logger.error(data_json["message"])
                    return False
                    
                return True
            else:
                logger.error(response.text)
                return False
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def pause_stream(self):
        try:
            url = f"{self.api_ip_port}/pause_stream"
            response = requests.get(url, timeout=(10, 300))

            if response.status_code == 200:
                data = response.json()
                if data["code"] != 200:
                    logger.error(data["message"])
                    return False
                    
                return True
            else:
                logger.error(response.text)
                return False
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def resume_stream(self):
        try:
            url = f"{self.api_ip_port}/resume_stream"
            response = requests.get(url, timeout=(10, 300))

            if response.status_code == 200:
                data = response.json()
                if data["code"] != 200:
                    logger.error(data["message"])
                    return False
                    
                return True
            else:
                logger.error(response.text)
                return False
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def skip_current_stream(self):
        """
        跳过当前播放音频
        """
        try:
            url = f"{self.api_ip_port}/skip_current_stream"
            response = requests.get(url, timeout=(10, 300))

            if response.status_code == 200:
                data = response.json()
                if data["code"] != 200:
                    logger.error(data["message"])
                    return False
                    
                return True
            else:
                logger.error(response.text)
                return False
        except Exception:
            logger.error(traceback.format_exc())
            return False

    def get_list(self):
        """
        获取音频播放队列列表
        """
        try:
            url = f"{self.api_ip_port}/get_list"
            response = requests.get(url, timeout=(10, 300))

            if response.status_code == 200:
                data = response.json()
                if data["code"] != 200:
                    logger.error(data["message"])
                    return None
                
                return data["message"]
            else:
                logger.error(response.text)
                return None
        except Exception:
            logger.error(traceback.format_exc())
            return None

    def clear(self):
        """
        清空播放队列
        """
        try:
            url = f"{self.api_ip_port}/clear"
            response = requests.get(url, timeout=(10, 300))

            if response.status_code == 200:
                data = response.json()
                if data["code"] != 200:
                    logger.error(data["message"])
                    return False

                return True
            else:
                logger.error(response.text)
                return False
        except Exception:
            logger.error(traceback.format_exc())
            return False
        