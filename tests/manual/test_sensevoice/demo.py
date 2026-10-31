from funasr import AutoModel
import sys
sys.path.insert(1, "../../sensevoice")


asr_model_path = "./models/iic/SenseVoiceSmall"
vad_model_path = "./models/iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
sense_voice_model = AutoModel(model=asr_model_path,
                            vad_model=vad_model_path,
                            vad_kwargs={"max_single_segment_time": 30000},
                            trust_remote_code=True, device="cuda:0", remote_code="./sensevoice/model.py")

file_path = "E:\\GitHub_pro\\AI-Vtuber\\out\\gpt_sovits_9.wav"
res = sense_voice_model.generate(
    input=file_path,
    cache={},
    language="zh",
    text_norm="woitn",
    batch_size_s=0,
    batch_size=1
)
text = res[0]['text']
res_dict = {"file_path": file_path, "text": text}
print(res_dict)
