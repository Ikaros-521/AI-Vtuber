import asyncio
import websockets
import json, os, logging, traceback
import base64
import mimetypes

async def gpt_sovits_api(data):
    def file_to_data_url(file_path):
        # 根据文件扩展名确定 MIME 类型
        mime_type, _ = mimetypes.guess_type(file_path)

        # 读取文件内容
        with open(file_path, "rb") as file:
            file_content = file.read()

        # 转换为 Base64 编码
        base64_encoded_data = base64.b64encode(file_content).decode('utf-8')

        # 构造完整的 Data URL
        return f"data:{mime_type};base64,{base64_encoded_data}"

    async def websocket_client(data_json):
        try:
            async with websockets.connect(data["api_ip_port"]) as websocket:
                # 设置最大连接时长（例如 30 秒）
                return await asyncio.wait_for(websocket_client_logic(websocket, data_json), timeout=30)
        except asyncio.TimeoutError:
            logging.error("gpt_sovits WebSocket连接超时")
            return None

    async def websocket_client_logic(websocket, data_json):
        async for message in websocket:
            logging.debug(f"Received message: {message}")

            # 解析收到的消息
            data = json.loads(message)
            # 检查是否是预期的消息
            if "msg" in data:
                if data["msg"] == "send_hash":
                    # 发送响应消息
                    response = json.dumps({"session_hash":"3obpzfqql7f","fn_index":0})
                    await websocket.send(response)
                    logging.debug(f"Sent message: {response}")
                elif data["msg"] == "send_data":
                    # audio_path = "F:\\GPT-SoVITS\\raws\\ikaros\\1.wav"
                    audio_path = data_json["ref_audio_path"]

                    # 发送响应消息
                    response = json.dumps(
                        {
                            "session_hash":"3obpzfqql7f",
                            "fn_index":0,
                            "data":[
                                {
                                    "data": file_to_data_url(audio_path),
                                    "name": os.path.basename(audio_path)
                                },
                                data_json["prompt_text"], 
                                data_json["prompt_language"], 
                                data_json["content"], 
                                data_json["language"]
                            ]
                        }
                    )
                    await websocket.send(response)
                    logging.debug(f"Sent message: {response}")
                elif data["msg"] == "process_completed":
                    return data["output"]["data"][0]["name"]
                
    try:
        logging.debug(f"data={data}")
        
        # 调用函数并等待结果
        voice_tmp_path = await websocket_client(data)

        return voice_tmp_path
    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error(f'gpt_sovits未知错误，请检查您的gpt_sovits推理是否启动/配置是否正确，报错内容: {e}')
    
    return None

# 运行异步 WebSocket 客户端
# asyncio.get_event_loop().run_until_complete(websocket_client())

if __name__ == '__main__':
    # 配置日志输出格式
    logging.basicConfig(
        level=logging.INFO,  # 设置日志级别，可以根据需求调整
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    data = {
        "api_ip_port": "ws://localhost:9872/queue/join",
        "ref_audio_path": "F:\\GPT-SoVITS\\raws\\ikaros\\1.wav",
        "prompt_text": "そらのおとしもの、ふぉるて",
        "prompt_language": "日文",
        "content": "おはようございます",
        "language": "日文"
    }

    # 运行异步函数并获取结果
    result = asyncio.run(gpt_sovits_api(data))

    logging.info(f"result={result}")
    