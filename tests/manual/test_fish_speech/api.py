import json, logging
import aiohttp, asyncio
from urllib.parse import urljoin

async def fish_speech_load_model(data):
    API_URL = urljoin(data["api_ip_port"], f'/v1/models/{data["model_name"]}')

    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(API_URL, json=data["model_config"]) as response:
                if response.status == 200:
                    ret = await response.json()
                    print(ret)

                    if ret["name"] == data["model_name"]:
                        print(f'fish_speech模型加载成功: {ret["name"]}')
                        return ret
                else: 
                    return None

    except aiohttp.ClientError as e:
        print(f'fish_speech请求失败: {e}')
    except Exception as e:
        print(f'fish_speech未知错误: {e}')
    
    return None

async def fish_speech_api(data):
    API_URL = urljoin(data["api_ip_port"], f'/v1/models/{data["model_name"]}/invoke')

    print(f"data={data}")

    def replace_empty_strings_with_none(input_dict):
        for key, value in input_dict.items():
            if value == "":
                input_dict[key] = None
        return input_dict

    data["tts_config"] = replace_empty_strings_with_none(data["tts_config"])

    print(f"data={data}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=data["tts_config"]) as response:
                if response.status == 200:
                    content = await response.read()

                    # voice_tmp_path = os.path.join(self.audio_out_path, '' + self.common.get_bj_time(4) + '.wav')
                    # file_name = 'fish_speech_' + self.common.get_bj_time(4) + '.wav'

                    # voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)
                    voice_tmp_path = "1.wav"
                    with open(voice_tmp_path, 'wb') as file:
                        file.write(content)

                    return voice_tmp_path
                else:
                    print(f'fish_speech下载音频失败: {response.status}')
                    return None
    except aiohttp.ClientError as e:
        print(f'fish_speech请求失败: {e}')
    except Exception as e:
        print(f'fish_speech未知错误: {e}')
    
    return None
    

data = {
    "fish_speech": {
        "api_ip_port": "http://127.0.0.1:8000",
        "model_name": "default",
        "model_config": {
            "device": "cuda",
            "llama": {
                "config_name": "text2semantic_finetune",
                "checkpoint_path": "checkpoints/text2semantic-400m-v0.2-4k.pth",
                "precision": "bfloat16",
                "tokenizer": "fishaudio/speech-lm-v1",
                "compile": True
            },
            "vqgan": {
                "config_name": "vqgan_pretrain",
                "checkpoint_path": "checkpoints/vqgan-v1.pth"
            }
        },
        "tts_config": {
            "prompt_text": "",
            "prompt_tokens": "",
            "max_new_tokens": 0,
            "top_k": 3,
            "top_p": 0.5,
            "repetition_penalty": 1.5,
            "temperature": 0.7,
            "order": "zh,jp,en",
            "use_g2p": True,
            "seed": 1,
            "speaker": ""
        }
    }
}

asyncio.run(fish_speech_load_model(data["fish_speech"]))

data["fish_speech"]["tts_config"]["text"] = "你好"
asyncio.run(fish_speech_api(data["fish_speech"]))