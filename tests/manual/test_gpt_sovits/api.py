import logging, json, aiohttp, os, traceback
import base64
import mimetypes
import websockets
import asyncio

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
            async with websockets.connect(data["ws_ip_port"]) as websocket:
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
                    response = json.dumps({"session_hash":"3obpzfqql7f","fn_index":3})
                    await websocket.send(response)
                    logging.debug(f"Sent message: {response}")
                elif data["msg"] == "send_data":
                    # audio_path = "F:\\GPT-SoVITS\\raws\\ikaros\\1.wav"
                    audio_path = data_json["ref_audio_path"]

                    # 发送响应消息
                    response = json.dumps(
                        {
                            "session_hash":"3obpzfqql7f",
                            "fn_index":3,
                            "data":[
                                {
                                    "data": file_to_data_url(audio_path),
                                    "name": os.path.basename(audio_path)
                                },
                                data_json["prompt_text"], 
                                data_json["prompt_language"], 
                                data_json["content"], 
                                data_json["language"],
                                data_json["cut"]
                            ]
                        }
                    )
                    await websocket.send(response)
                    logging.debug(f"Sent message: {response}")
                elif data["msg"] == "process_completed":
                    return data["output"]["data"][0]["name"]
                
    try:
        logging.debug(f"data={data}")
        
        if data["type"] == "gradio":
            # 调用函数并等待结果
            voice_tmp_path = await websocket_client(data)

            # if voice_tmp_path:
            #     new_file_path = self.common.move_file(voice_tmp_path, os.path.join(self.audio_out_path, 'gpt_sovits_' + self.common.get_bj_time(4)), 'gpt_sovits_' + self.common.get_bj_time(4))

            new_file_path = 'gpt_sovits_.wav'

            return new_file_path
        elif data["type"] == "api":
            try:
                data_json = {
                    "refer_wav_path": data["ref_audio_path"],
                    "prompt_text": data["prompt_text"],
                    "prompt_language": data["prompt_language"],
                    "text": data["content"],
                    "text_language": data["language"]
                }
                                    
                async with aiohttp.ClientSession() as session:
                    async with session.post(data["api_ip_port"], json=data_json, timeout=30) as response:
                        response = await response.read()
                        
                        file_name = 'gpt_sovits_.wav'

                        voice_tmp_path = file_name

                        # voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)

                        with open(voice_tmp_path, 'wb') as f:
                            f.write(response)

                        return voice_tmp_path
            except aiohttp.ClientError as e:
                logging.error(traceback.format_exc())
                logging.error(f'gpt_sovits请求失败: {e}')
            except Exception as e:
                logging.error(traceback.format_exc())
                logging.error(f'gpt_sovits未知错误: {e}')
        elif data["type"] == "webtts":
            try:
                # 使用字典推导式构建 params 字典，只包含非空字符串的值
                params = {
                    key: value
                    for key, value in data["webtts"].items()
                    if value != ""
                    if key != "api_ip_port"
                }

                # params["speed"] = self.get_random_float(params["speed"])
                params["text"] = data["content"]
                                    
                async with aiohttp.ClientSession() as session:
                    async with session.get(data["webtts"]["api_ip_port"], params=params, timeout=30) as response:
                        response = await response.read()
                        
                        file_name = 'gpt_sovits_.wav'

                        voice_tmp_path = file_name

                        # voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)

                        with open(voice_tmp_path, 'wb') as f:
                            f.write(response)

                        return voice_tmp_path
            except aiohttp.ClientError as e:
                logging.error(traceback.format_exc())
                logging.error(f'gpt_sovits请求失败: {e}')
            except Exception as e:
                logging.error(traceback.format_exc())
                logging.error(f'gpt_sovits未知错误: {e}')
    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error(f'gpt_sovits未知错误，请检查您的gpt_sovits推理是否启动/配置是否正确，报错内容: {e}')
    
    return None


async def gpt_sovits_set_model(data):
    from urllib.parse import urljoin

    if data["type"] == "api":
        try:
            data_json = {
                "gpt_model_path": data["gpt_model_path"],
                "sovits_model_path": data["sovits_model_path"]
            }

            API_URL = urljoin(data["api_ip_port"], '/set_model')
                                
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, json=data_json, timeout=30) as response:
                    response = await response.read()
                    
                    print(response)

                    return response
        except aiohttp.ClientError as e:
            logging.error(traceback.format_exc())
            logging.error(f'gpt_sovits请求失败: {e}')
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(f'gpt_sovits未知错误: {e}')


if __name__ == '__main__':
    # 配置日志输出格式
    logging.basicConfig(
        level=logging.DEBUG,  # 设置日志级别，可以根据需求调整
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    data = {
        "type": "api",
        "api_ip_port": "http://127.0.0.1:9880",
        "gpt_model_path": "F:\GPT-SoVITS\GPT_weights\ikaros-e15.ckpt",
        "sovits_model_path": "F:\GPT-SoVITS\SoVITS_weights\ikaros_e8_s280.pth"
    }
    
    asyncio.run(gpt_sovits_set_model(data))
