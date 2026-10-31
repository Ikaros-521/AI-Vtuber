from gradio_client import Client

client = Client("http://127.0.0.1:7860/")
result = client.predict(
				True,	# bool  in 'Quick Generation' Checkbox component
				fn_index=1
)
print(result)