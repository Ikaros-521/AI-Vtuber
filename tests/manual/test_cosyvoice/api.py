import json, logging, asyncio
import aiohttp, requests, ssl
from urllib.parse import urlencode
import traceback
from urllib.parse import urljoin

async def download_audio(type: str, file_url: str, timeout: int=30, request_type: str="get", data=None, json_data=None, audio_suffix: str="wav"):
    async with aiohttp.ClientSession() as session:
        try:
            if request_type == "get":
                async with session.get(file_url, params=data, timeout=timeout) as response:
                    if response.status == 200:
                        content = await response.read()
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
            
async def cosyvoice_api(text):
    url = 'http://127.0.0.1:9880/'

    params = {
        "text": text,
        "speaker": "中文女",
        'new': 0,
        'speed': 1.0,
        'streaming': 0
    }

    logging.debug(f"params={params}")

    try:
        audio_path = await download_audio("cosyvoice", url, 30, request_type="post", json_data=params)
        print(audio_path)
        return audio_path
    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error(f'cosyvoice未知错误: {e}')
    
    return None


if __name__ == '__main__':
    asyncio.run(cosyvoice_api("你好"))
