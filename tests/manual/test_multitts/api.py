import logging
import asyncio
import aiohttp
import json


async def download_audio(type: str, file_url: str, timeout: int=30, request_type: str="get", data=None, json_data=None, audio_suffix: str="wav"):
    async with aiohttp.ClientSession() as session:
        try:
            if request_type == "get":
                async with session.get(file_url, params=data, timeout=timeout) as response:
                    if response.status == 200:
                        content = await response.read()
                        file_name = type + '_' + '1' + '.' + audio_suffix
                        voice_tmp_path = '1.wav'
                        with open(voice_tmp_path, 'wb') as file:
                            file.write(content)
                        return voice_tmp_path
                    else:
                        logging.error(f'{type} 下载音频失败: {response.status}')
                        return None
            else:
                async with session.post(file_url, data=data, json=json_data, timeout=timeout) as response:
                    if response.status == 200:
                        content = await response.read()
                        file_name = type + '_' + '1' + '.' + audio_suffix
                        voice_tmp_path = '1.wav'
                        with open(voice_tmp_path, 'wb') as file:
                            file.write(content)
                        return voice_tmp_path
                    else:
                        logging.error(f'{type} 下载音频失败: {response.status}')
                        return None
        except asyncio.TimeoutError:
            logging.error("{type} 下载音频超时")
            return None

async def multitts_api(data):
    from urllib.parse import urljoin

    timeout = 30

    # http://127.0.0.1:8774/forward
    API_URL = urljoin(data["multitts"]["api_ip_port"], "/forward")

    data_json = {
        "text": data["content"],
        "speed": data["multitts"]["speed"],
        "volume": int(data["multitts"]["volume"]),
        "pitch": int(data["multitts"]["pitch"])
    }

    if data["multitts"]["voice"] != "":
        data_json["voice"] = data["multitts"]["voice"]
        
    logging.debug(f"data_json={data_json}")

    logging.debug(f"url={API_URL}")

    return await download_audio("multitts", API_URL, timeout, "get", data_json)

logging.basicConfig(level=logging.DEBUG)  # 设置日志级别为INFO
data = {
    "content": "你好，欢迎使用AI Lab！",
    "multitts": {
        "api_ip_port": "http://192.168.31.180:8774",
        "speed": 1.0,
        "volume": 50,
        "pitch": 50,
        "voice": ""
    }
}
# 执行异步程序
asyncio.run(multitts_api(data))