import logging, asyncio, aiohttp, traceback, os
from aiohttp import FormData
from urllib.parse import urlencode, urljoin

class TTS:
    def __init__(self):
        self.timeout = 60

    # 请求vits_simple_api的api gpt_sovits
    async def vits_simple_api_gpt_sovits_api(self, data):
        try:
            logging.debug(f"data={data}")
            # API地址 "http://127.0.0.1:5000/voice"
            API_URL = urljoin(data["api_ip_port"], '/voice/gpt-sovits')

            data_json = {
                "text": data["content"],
                "id": data["id"],
                "format": data["format"],
                "lang": data["lang"],
                "segment_size": data["segment_size"],
                "prompt_text": data["prompt_text"],
                "prompt_lang": data["prompt_lang"],
                "preset": data["preset"],
                "top_k": data["top_k"],
                "top_p": data["top_p"],
                "temperature": data["temperature"]
            }

            # 创建 FormData 对象
            form_data = FormData()
            # 添加文本字段
            for key, value in data_json.items():
                form_data.add_field(key, str(value))

            # 以二进制读取模式打开音频文件，并添加到表单数据中
            # 'reference_audio' 是字段名称，应与服务器端接收的名称一致
            form_data.add_field('reference_audio',
                        open(data["reference_audio"], 'rb'),
                        content_type='audio/mpeg')  # 内容类型根据文件类型修改
                
            logging.info(f"data_json={data_json}")
            # logging.info(f"data={data}")

            logging.info(f"API_URL={API_URL}")

            # url = f"{API_URL}?{urlencode(data_json)}"

            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, data=form_data, timeout=self.timeout) as response:
                    response = await response.read()
                    # print(response)
                    # file_name = 'vits_simple_api_gpt_sovits_' + self.common.get_bj_time(4) + '.wav'
                    # voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)
                    voice_tmp_path = '1.wav'
                    with open(voice_tmp_path, 'wb') as f:
                        f.write(response)
                    
                    return voice_tmp_path
        except aiohttp.ClientError as e:
            logging.error(traceback.format_exc())
            logging.error(f'vits_simple_api gpt_sovits请求失败，请检查您的vits_simple_api是否启动/配置是否正确，报错内容: {e}')
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error(f'vits_simple_api gpt_sovits未知错误，请检查您的vits_simple_api是否启动/配置是否正确，报错内容: {e}')
        
        return None

if __name__ == '__main__':
    # 配置日志输出格式
    logging.basicConfig(
        level=logging.DEBUG,  # 设置日志级别，可以根据需求调整
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    data = {
        "api_ip_port": "http://127.0.0.1:23456/",
        "content": "你好,你在说什么玩意，啊啊啊啊",
        "id": 0,
        "format": "wav",
        "lang": "auto",
        "segment_size": 30,
        "reference_audio": "E:\\GitHub_pro\\AI-Vtuber\\out\\gpt_sovits_67.wav",
        "prompt_text": "所有拍到的姐妹一定不要划走",
        "prompt_lang": "auto",
        "preset": "default",
        "top_k": 5,
        "top_p": 1,
        "temperature": 1
    }
    asyncio.run(TTS().vits_simple_api_gpt_sovits_api(data))


    