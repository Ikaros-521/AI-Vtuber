import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
import io
import soundfile as sf

model_size = "large-v3"
model = WhisperModel(model_size, device="cuda", compute_type="float16", download_root="E:\\GitHub_pro\\AI-Vtuber\\models")
samplerate = 16000  # Whisper 支持的采样率
channels = 1  # 单声道录音

def callback(indata, frames, time, status):
    global samplerate
    
    if status:
        print(status)

    # 将捕获的 NumPy 音频数据转换为音频文件所需的字节流格式
    with io.BytesIO() as buffer:
        sf.write(buffer, indata, samplerate, format='WAV')
        buffer.seek(0)
        
        # 使用 Whisper 模型进行实时音频转录
        segments, info = model.transcribe(buffer, beam_size=5, vad_filter=True)
        
        if segments:
            print("Detected language '%s' with probability %f" % (info.language, info.language_probability))
            for segment in segments:
                print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))

def list_input_devices():
    devices = sd.query_devices()  # 查询所有设备
    print("输入麦克风设备列表:")
    for idx, device in enumerate(devices):
        # 如果 max_input_channels 大于 0，则为输入设备
        if device['max_input_channels'] > 0:
            print(f"设备索引: {idx}, 设备名称: {device['name']}, 输入通道数: {device['max_input_channels']}")

            # 获取设备的默认采样率
            default_samplerate = int(device['default_samplerate'])
            print(f"Default sample rate: {default_samplerate}")

list_input_devices()

# 开始录音并实时处理
with sd.InputStream(device=3, callback=callback, channels=channels, samplerate=samplerate, dtype='float32'):
    print("Recording... Press Ctrl+C to stop.")
    sd.sleep(10000)  # 记录 10 秒，您可以根据需要调整
