import pytchat
import time, re

# https://www.youtube.com/watch?v=P5wlxQgYhMY
video_id = "P5wlxQgYhMY"

live = pytchat.create(video_id=video_id)
while live.is_alive():
# while True:
    try:
        for c in live.get().sync_items():
            # if not c.message.startswith("!") and c.message.startswith('#'):
            # if not c.message.startswith("!"):
            # 过滤表情包
            chat_raw = re.sub(r':[^\s]+:', '', c.message)
            chat_raw = chat_raw.replace('#', '')
            if chat_raw != '':
                # chat_author makes the chat look like this: "Nightbot: Hello". So the assistant can respond to the user's name
                chat = '[' + c.author.name + ']: ' + chat_raw
                print(chat)
                
            # time.sleep(1)
    except Exception as e:
        print("Error receiving chat: {0}".format(e))