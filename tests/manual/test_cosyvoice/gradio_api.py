from gradio_client import Client, file

client = Client("http://127.0.0.1:9886/")
result = client.predict(
    tts_text="合成能力。",
    mode_checkbox_group="预训练音色",
    sft_dropdown="中文女",
    prompt_text="",
    prompt_wav_upload=None,
    prompt_wav_record=None,
    #prompt_wav_upload=file('https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav'),
    #prompt_wav_record=file('https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav'),
    instruct_text="",
    seed=0,
    api_name="/generate_audio"
)
print(result)