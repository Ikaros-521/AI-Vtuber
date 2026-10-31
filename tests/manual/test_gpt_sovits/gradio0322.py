from gradio_client import Client

client = Client("http://127.0.0.1:9872/")
result = client.predict(
    "你好，Hello!!",	# str  in '需要合成的文本' Textbox component
    "中英混合",	# Literal['中文', '英文', '日文', '中英混合', '日英混合', '多语种混合']  in '需要合成的语种' Dropdown component
    "F:\\GPT-SoVITS\\raws\\ikaros\\21.wav",	# filepath  in '请上传3~10秒内参考音频，超过会报错！' Audio component
    "マスター、どうりょくろか、いいえ、なんでもありません",	# str  in '参考音频的文本' Textbox component
    "日文",	# Literal['中文', '英文', '日文', '中英混合', '日英混合', '多语种混合']  in '参考音频的语种' Dropdown component
    1,	# float (numeric value between 1 and 100) in 'top_k' Slider component
    0.8,	# float (numeric value between 0 and 1) in 'top_p' Slider component
    0.8,	# float (numeric value between 0 and 1) in 'temperature' Slider component
    "按标点符号切",	# Literal['不切', '凑四句一切', '凑50字一切', '按中文句号。切', '按英文句号.切', '按标点符号切']  in '怎么切' Radio component
    20,	# float (numeric value between 1 and 200) in 'batch_size' Slider component
    1,	# float (numeric value between 0.25 and 4) in 'speed_factor' Slider component
    False,	# bool  in '开启无参考文本模式。不填参考文本亦相当于开启。' Checkbox component
    True,	# bool  in '数据分桶(可能会降低一点计算量,选就对了)' Checkbox component
    0.3,	# float (numeric value between 0.01 and 1) in '分段间隔(秒)' Slider component
    api_name="/inference"
)
print(result)