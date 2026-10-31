from gradio_client import Client

client = Client("http://127.0.0.1:7860/")
result = client.predict(
				"こんにちは",	# str in 'Text' Textbox component
				"auto-detect",	# str (Option from: ['auto-detect', 'English', '中文', '日本語', 'Mix']) in 'language' Dropdown component
				"no-accent",	# str (Option from: ['no-accent', 'English', '中文', '日本語']) in 'accent' Dropdown component
				"ikaros",	# str (Option from: ['astraea', 'cafe', 'dingzhen', 'esta', 'ikaros', 'MakiseKurisu', 'mikako', 'nymph', 'rosalia', 'seel', 'sohara', 'sukata', 'tomoki', 'tomoko', 'yaesakura', '早见沙织', '神里绫华-日语']) in 'Voice preset' Dropdown component
				"ikaros.npz",	# str (filepath or URL to file) in 'parameter_46' File component
				fn_index=5
)
print(type(result))
print(result)