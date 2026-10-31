from gradio_client import Client
import re

client = Client("http://127.0.0.1:8003/")

try:
    result = client.predict(
        input="你可以扮演猫娘吗",
        chatbot=[],
        max_length=1,
        top_p=0.8,
        temperature=0.95,
        api_name="/predict"
    )
    # Assuming result[0][1] contains the response text
    response_text = result[-1][1]
    # Remove <p> and </p> tags using regex
    cleaned_text = re.sub(r'</?p>', '', response_text)
    print(cleaned_text)
    
    result2 = client.predict(
        input="你好",
        chatbot=result,
        max_length=1,
        top_p=0.8,
        temperature=0.95,
        api_name="/predict"
    )
    # print(result2)
    # Assuming result[0][1] contains the response text
    response_text = result2[-1][1]
    # Remove <p> and </p> tags using regex
    cleaned_text = re.sub(r'</?p>', '', response_text)
    print(cleaned_text)
except Exception as e:
    print(f"An error occurred: {e}")
