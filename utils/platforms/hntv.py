import requests
import time
import traceback

from utils.my_log import logger

def start_listen(config, common, my_handle, platform: str):
    # 初始化已获取的commentId集合
    comment_set = set()

    def fetch_comments():
        try:
            url = f"https://pubmod.hntv.tv/dx-bridge/get-comment-with-article-super-v2?limit=40&typeId=1&appFusionId=1390195608019869697&page=1&objectId={my_handle.get_room_id()}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                items = data.get("result", {}).get("items", [])
                for item in items:
                    comment_id = item.get("commentId")
                    if comment_id not in comment_set:
                        comment_set.add(comment_id)
                        username = item.get("commentUserNickname", "")
                        content = item.get("content", "")

                        logger.info(f"[{username}]: {content}")

                        data = {
                            "platform": platform,
                            "username": username,
                            "content": content,
                        }

                        my_handle.process_data(data, "comment")
            else:
                logger.error("获取弹幕数据失败。。。")
        except Exception as e:
            logger.error(traceback.format_exc())
            my_handle.abnormal_alarm_handle("platform")

    while True:
        fetch_comments()
        time.sleep(3)  # 每隔3秒轮询一次