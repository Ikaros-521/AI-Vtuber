from typing import Iterator
import time
import requests
import numpy as np
import resampy
import pyaudio

class VitsTTS:
    audio = None
    stream = None
    sample_rate = 16000  # Set the desired sample rate for playback

    def __init__(self, config_json):
        self.config_json = config_json

        # Initialize PyAudio and stream if not already done
        if VitsTTS.audio is None:
            VitsTTS.audio = pyaudio.PyAudio()
        if VitsTTS.stream is None or not VitsTTS.stream.is_active():
            VitsTTS.stream = VitsTTS.audio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=VitsTTS.sample_rate,
                output=True
            )

    def txt_to_audio(self, msg): 
        self.stream_tts(
            self.gpt_sovits(
                msg,
                self.config_json["ref_file"],  
                self.config_json["ref_text"],
                "zh",  # Language (can be "en" or other supported languages)
                self.config_json["server_url"]
            )
        )

    def gpt_sovits(self, text, reffile, reftext, language, server_url) -> Iterator[bytes]:
        start = time.perf_counter()
        req = {
            'text': text,
            'text_lang': language,
            'ref_audio_path': reffile,
            'prompt_text': reftext,
            'prompt_lang': language,
            'media_type': 'raw',
            'streaming_mode': True,
        }
        
        res = requests.post(
            f"{server_url}/tts",
            json=req,
            stream=True,
        )
        end = time.perf_counter()
        print(f"gpt_sovits Time to make POST: {end-start}s")

        if res.status_code != 200:
            print("Error:", res.text)
            return
            
        first = True
        for chunk in res.iter_content(chunk_size=32000):  # 32K*20ms*2
            if first:
                end = time.perf_counter()
                print(f"gpt_sovits Time to first chunk: {end-start}s")
                first = False
            if chunk:
                yield chunk

        print("gpt_sovits response.elapsed:", res.elapsed)

    def stream_tts(self, audio_stream):
        for chunk in audio_stream:
            if chunk is not None and len(chunk) > 0:
                stream = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32767
                stream = resampy.resample(x=stream, sr_orig=32000, sr_new=VitsTTS.sample_rate)
                VitsTTS.stream.write(stream.tobytes())

    @classmethod
    def close_audio(cls):
        if cls.stream is not None:
            cls.stream.stop_stream()
            cls.stream.close()
            cls.audio.terminate()
            cls.stream = None
            cls.audio = None


if __name__ == "__main__":
    config_json = {
        "server_url": "http://127.0.0.1:9880",
        "ref_file": "E:\\GitHub_pro\\AI-Vtuber\\out\\edge_tts_3.mp3",
        "ref_text": "就送个人气票，看不起谁呢",
    }
    vits_tts = VitsTTS(config_json)
    vits_tts.txt_to_audio("你好，我是AI")
    vits_tts.txt_to_audio("我的声音如何")
    vits_tts.txt_to_audio("床前明月光，疑是地上霜。举头望明月，低头思故乡。")
