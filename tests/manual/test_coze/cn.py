import json
import logging
import requests

api_url = "https://api.coze.cn/v3/chat"
authorization_token = "Bearer "

def print_unicode(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            print(f"{key}: ", end='')
            print_unicode(value)
    elif isinstance(obj, list):
        for item in obj:
            print_unicode(item)
    else:
        print(ensure_unicode(obj))

def ensure_unicode(text):
    if isinstance(text, str):
        return text
    elif isinstance(text, bytes):
        return text.decode('utf-8', errors='replace')
    else:
        return str(text)

def get_chat_response():
    # 文档：https://www.coze.cn/docs/developer_guides/chat_v3
    headers = {
        "Authorization": authorization_token,
        "Content-Type": "application/json"
    }

    data_json = {
        "bot_id": "7392993441015332874",
        "user_id": "1",
        # 是否启用流式返回
        "stream": True,
        # 是否保存本次对话记录
        "auto_save_history": True,
        "additional_messages": [
            {
                "role": "user",
                "content": "早上好",
                "content_type": "text"
            }
        ],
    }

    try:
        with requests.post(url=api_url, headers=headers, json=data_json) as response:
            response.raise_for_status()  # 检查响应的状态码
            
            # 检查并设置响应编码
            if response.encoding is None:
                response.encoding = 'utf-8'  # 如果未指定编码，手动设置为 utf-8

            # 遍历流式响应
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    # line = line.encode('utf-8').decode('utf-8')  # 确保解码是以utf-8进行的
                    # 处理事件和数据部分
                    if line.startswith("data:"):
                        data = line[5:].strip()  # 去掉前缀 "data:" 并去除多余空白
                        try:
                            # decoded_data = data.decode('utf-8')
                            json_data = json.loads(data)
                            #print_unicode(json_data)
                            print(json_data)  # 解析并打印JSON数据
                        except json.JSONDecodeError:
                            print(f"Received non-JSON data: {data}")
                    else:
                        print(line)  # 打印事件部分或其他非数据行

    except Exception as e:
        logging.error(e)
        return None

# 调用函数并打印返回的响应内容
get_chat_response()
