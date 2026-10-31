import json
import requests
from urllib.parse import urljoin

base_url = "https://chatglm.cn"

def get_assistant_api_token(api_key, api_secret):
    url = urljoin(base_url, "/chatglm/assistant-api/v1/get_token")

    data = {
        "api_key": api_key,
        "api_secret": api_secret
    }

    # print(f"url={url}, data={data}")

    # get请求
    response = requests.post(url=url, json=data)

    # 获取状态码
    status_code = response.status_code
    print(status_code)

    if status_code == 200:
        print(response.json())

        resp_json = response.json()

        access_token = resp_json["result"]["access_token"]

        return access_token
    else:
        return None

access_token = get_assistant_api_token("", "")



def get_resp(prompt):
    url = urljoin(base_url, "/chatglm/assistant-api/v1/stream_sync")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "assistant_id": "",
        "conversation_id": None,
        "prompt": prompt,
        "meta_data": None
    }

    response = requests.post(url=url, json=data, headers=headers)
    status_code = response.status_code
    print(status_code)

    if status_code == 200:
        try:
            # print(response.json())
            resp_json = response.json()
            print(json.dumps(resp_json, ensure_ascii=True, indent=4))

            conversation_id = resp_json["result"]["conversation_id"]
            resp_content = resp_json["result"]["output"][-1]["content"][0]["text"]

            print(resp_content)

            return resp_content
        except Exception as e:
            print(e)
            return None
    else:
        return None

if access_token:
    get_resp("杭州今日天气")
