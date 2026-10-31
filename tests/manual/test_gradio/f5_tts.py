from gradio_client import Client, handle_file

client = Client("http://127.0.0.1:7860/")
result = client.predict(
		ref_audio_orig=handle_file('F:\\GPT-SoVITS-0304\\output\\slicer_opt\\smoke1.wav'),
		ref_text="整整策划了半年了，终于现在有结果了",
		gen_text="你好",
		model="F5-TTS",
		remove_silence=False,
		cross_fade_duration=0.15,
		speed=1,
		api_name="/infer"
)
print(result)