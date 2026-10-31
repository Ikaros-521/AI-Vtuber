from gradio_client import Client

client = Client("https://v2.genshinvoice.top/")
result = client.predict(
		"Howdy!",	# str  in '输入文本内容' Textbox component
		fn_index=1
)
print(result)