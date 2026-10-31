import json, logging, asyncio
import aiohttp, requests, ssl
from urllib.parse import urlencode
import traceback
from urllib.parse import urljoin

async def clone_voice_api(text):
    url = 'http://127.0.0.1:9988/tts'

    # voice=cn-nan.wav&text=%E4%BD%A0%E5%A5%BD&language=zh-cn&speed=1
    params = {
        "voice": "cn-nan.wav",
        "language": "zh-cn",
        'speed': 1,
        'text': text
    }

    print(f"params={params}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=params) as response:
                ret = await response.json()
                print(ret)

                file_path = ret["filename"]

                return file_path

    except aiohttp.ClientError as e:
        logging.error(traceback.format_exc())
        logging.error(f'clone_voice请求失败: {e}')
    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error(f'clone_voice未知错误: {e}')
    
    return None


asyncio.run(clone_voice_api("你好"))
