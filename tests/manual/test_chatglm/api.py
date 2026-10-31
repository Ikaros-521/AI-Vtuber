import json, logging
import requests


api_ip_port = "http://127.0.0.1:8000"
max_length = 2048
top_p = 0.7
temperature = 0.95


# 调用chatglm接口，获取返回内容
def get_resp(prompt, history=[]):
    data_json = {
        "prompt": prompt, 
        "history": history,
        "max_length": max_length,
        "top_p": top_p,
        "temperature": temperature
    }

    try:
        response = requests.post(url=api_ip_port, json=data_json)
        response.raise_for_status()  # 检查响应的状态码

        result = response.content
        ret = json.loads(result)

        print(ret)

        resp_content = ret['response']

        return resp_content
    except Exception as e:
        logging.info(e)
        return None
    

print(get_resp("你好"))