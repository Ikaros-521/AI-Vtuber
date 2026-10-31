import json, logging
import aiohttp, asyncio


async def reecho_ai_api(text):
    url = 'https://v1.reecho.ai/api/tts/simple-generate'

    # reecho_ai = self.config.get("reecho_ai")
    
    reecho_ai = {
        "Authorization": "sk-xxx",
        "model": "reecho-neural-voice-001",
        "randomness": 97,
        "stability_boost": 40,
        "voiceId": "b4b885c3-89a7-46d4-badb-015a55bb3a91",
        "text": "你好"
    }
    
    headers = {  
        "Authorization": f"Bearer {reecho_ai['Authorization']}",  
        "Content-Type": "application/json"
    }

    params = {
        "model": reecho_ai['model'],
        'randomness': reecho_ai['randomness'],
        'stability_boost': reecho_ai['stability_boost'],
        'voiceId': reecho_ai['voiceId'],
        'text': text
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=params) as response:
                ret = await response.json()
                print(ret)

                file_url = ret["data"]["audio"]
                
                print(file_url)
                
                return None

                async with session.get(file_url) as response:
                    if response.status == 200:
                        content = await response.read()

                        # voice_tmp_path = os.path.join(self.audio_out_path, 'reecho_ai_' + self.common.get_bj_time(4) + '.wav')
                        file_name = 'reecho_ai_' + self.common.get_bj_time(4) + '.wav'

                        voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)
                        
                        with open(voice_tmp_path, 'wb') as file:
                            file.write(content)

                        return voice_tmp_path
                    else:
                        print(f'reecho.ai下载音频失败: {response.status}')
                        return None
    except aiohttp.ClientError as e:
        print(f'reecho.ai请求失败: {e}')
    except Exception as e:
        print(f'reecho.ai未知错误: {e}')
    
    return None
    

asyncio.run(reecho_ai_api("你好"))