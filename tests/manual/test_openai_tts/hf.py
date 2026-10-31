from gradio_client import Client

client = Client("https://ysharma-openai-tts-new.hf.space/--replicas/zcq5n/")
result = client.predict(
		"你好",	# str  in 'Input text' Textbox component
		"tts-1",	# Literal[tts-1, tts-1-hd]  in 'Model' Dropdown component
		"nova",	# Literal[alloy, echo, fable, onyx, nova, shimmer]  in 'Voice Options' Dropdown component
		"sk-",	# str  in 'OpenAI API Key' Textbox component
		api_name="/tts_enter_key"
)
print(f"音频合成成功，输出到={result}")