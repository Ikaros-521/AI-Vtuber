"""HTTP 客户端与 OpenAI 兼容接口探测：自 utils/common.py 拆分。

拆分原则：网络出站请求集中在一个模块，便于统一排查代理/超时/日志行为。
Common 类保留同名方法作委托门面，所有既有调用方（平台监听器、webui、
my_handle 等）不需要改动。
"""

import json
import traceback

import requests

from luna.infra.my_log import logger


def send_request(
    url: str,
    method: str = "GET",
    json_data: dict | None = None,
    resp_data_type: str = "json",
    timeout: int = 60,
    proxy: str | None = None,
):
    """
    发送 HTTP 请求并返回结果

    Parameters:
        url (str): 请求的 URL
        method (str): 请求方法，'GET' 或 'POST'
        json_data (dict): JSON 数据，用于 POST 请求
        resp_data_type (str): 返回数据的类型（json | content）
        timeout (int): 请求超时时间
        proxy (str): 代理服务器地址

    Returns:
        dict|str: 包含响应的 JSON数据 | 字符串数据
    """
    headers = {"Content-Type": "application/json"}

    # requests 的 proxies 参数要 dict；配置里存的是单个代理地址(str)。
    # 历史代码直接把 str 传给 requests（代理实际不生效），这里规范化修复。
    proxies: dict | None = None
    if isinstance(proxy, str) and proxy:
        proxies = {"http": proxy, "https": proxy}

    try:
        if method in ["GET", "get"]:
            response = requests.get(url, headers=headers, timeout=timeout, proxies=proxies)
        elif method in ["POST", "post"]:
            response = requests.post(url, headers=headers, data=json.dumps(json_data), timeout=timeout, proxies=proxies)
        else:
            raise ValueError("无效 method. 支持的 methods 为 GET 和 POST.")

        # 检查请求是否成功
        response.raise_for_status()

        if resp_data_type == "json":
            # 解析响应的 JSON 数据
            result = response.json()
        else:
            result = response.content
            # 使用 'utf-8' 编码来解码字节串
            result = result.decode("utf-8")

        return result

    except requests.exceptions.RequestException as e:
        logger.error(traceback.format_exc())
        logger.error(f"请求出错: {e}")
        return None
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"请求出错: {e}")
        return None


async def send_async_request(
    url: str,
    method: str = "GET",
    json_data: dict | None = None,
    resp_data_type: str = "json",
    timeout: int = 60,
    proxy: str | None = None,
):
    """
    发送异步 HTTP 请求并返回结果

    Parameters:
        url (str): 请求的 URL
        method (str): 请求方法，'GET' 或 'POST'
        json_data (dict): JSON 数据，用于 POST 请求
        resp_data_type (str): 返回数据的类型（json | content）
        timeout (int): 请求超时时间
        proxy (str): 代理服务器地址

    Returns:
        dict|str: 包含响应的 JSON数据 | 字符串数据
    """
    import aiohttp

    headers = {"Content-Type": "application/json"}

    try:
        # 创建 aiohttp.ClientSession
        async with aiohttp.ClientSession() as session:
            if method in ["GET", "get"]:
                async with session.get(url, headers=headers, timeout=timeout, proxy=proxy) as response:
                    # 检查请求是否成功
                    response.raise_for_status()

                    if resp_data_type == "json":
                        # 解析响应的 JSON 数据
                        result = await response.json()
                    else:
                        result = await response.read()

            elif method in ["POST", "post"]:
                async with session.post(
                    url, headers=headers, data=json.dumps(json_data), timeout=timeout, proxy=proxy
                ) as response:
                    # 检查请求是否成功
                    response.raise_for_status()

                    if resp_data_type == "json":
                        # 解析响应的 JSON 数据
                        result = await response.json()
                    else:
                        result = await response.read()

            else:
                raise ValueError("无效 method. 支持的 methods 为 GET 和 POST.")

            return result

    except aiohttp.ClientError as e:
        logger.error(traceback.format_exc())
        logger.error(f"请求出错: {e}")
        return None
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"请求出错: {e}")
        return None


# 请求web字幕打印机
async def send_to_web_captions_printer(api_ip_port, data):
    """请求web字幕打印机

    Args:
        api_ip_port (str): api请求地址
        data (dict): 包含用户名,弹幕内容

    Returns:
        bool: True/False
    """

    # username = data["username"]
    content = data["content"]

    # 记录数据库):
    try:
        # TODO: 换成异步请求
        response = requests.get(url=api_ip_port + f"/send_message?content={content}", timeout=(10, 300))
        response.raise_for_status()  # 检查响应的状态码

        result = response.content
        ret = json.loads(result)

        logger.debug(ret)

        if ret["code"] == 200:
            logger.debug(ret["message"])
            return True
        else:
            logger.error(ret["message"])
            return False
    except Exception:
        logger.error("web字幕打印机请求失败！请确认配置是否正确或者服务端是否运行！")
        logger.error(traceback.format_exc())
        return False


# openai 测试key可用性
def test_openai_key(data_json, type=1):
    if type == 1:
        from urllib.parse import urljoin

        # 检查可用性
        def check_useful(data_json):
            # 尝试调用 list engines 接口
            try:
                api_key = data_json["api_keys"].split("\n")[0].rstrip()

                url = urljoin(data_json["base_url"], "/v1/chat/completions")

                logger.debug(f"url=【{url}】, api_keys=【{api_key}】")

                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

                data = {
                    "model": data_json["model"],
                    "messages": [{"role": "user", "content": "hi"}],
                    "temperature": data_json["temperature"],
                    "max_tokens": data_json["max_tokens"],
                    "top_p": data_json["top_p"],
                    "presence_penalty": data_json["presence_penalty"],
                    "frequency_penalty": data_json["frequency_penalty"],
                }

                response = requests.post(url, headers=headers, json=data, timeout=(10, 300))
                response_data = response.json()

                logger.debug(response_data)

                # 结构探针：响应缺少 choices[0].message.content 时抛异常，走 except 判定 key 不可用
                response_data["choices"][0]["message"]["content"]

                logger.info("OpenAI API key 可用")

                return {"code": 200, "msg": "OpenAI API key 可用"}
            except Exception as e:
                logger.error(traceback.format_exc())
                logger.error(f"OpenAI API key 不可用: {e}")
                return {"code": -1, "msg": f"OpenAI API key 不可用: {e}"}
    else:
        import openai
        from packaging import version

        # os.environ['http_proxy'] = "http://127.0.0.1:10809"
        # os.environ['https_proxy'] = "http://127.0.0.1:10809"

        # 检查可用性
        def check_useful(data_json):
            # 尝试调用 list engines 接口
            try:
                api_key = data_json["api_keys"].split("\n")[0].rstrip()

                logger.info(
                    f"base_url=【{data_json['base_url']}】, api_keys=【{api_key}】, 模型=【{data_json['model']}】"
                )

                # openai.base_url = self.data_openai['api']
                # openai.api_key = self.data_openai['api_key'][0]

                logger.debug(f"openai.__version__={openai.__version__}")

                openai.api_base = data_json["base_url"]
                openai.api_key = api_key

                # 判断openai库版本，1.x.x和0.x.x有破坏性更新
                if version.parse(openai.__version__) < version.parse("1.0.0"):
                    # 调用 ChatGPT 接口生成回复消息
                    resp = openai.ChatCompletion.create(
                        model=data_json["model"],
                        messages=[{"role": "user", "content": "Hi"}],
                        temperature=data_json["temperature"],
                        max_tokens=data_json["max_tokens"],
                        top_p=data_json["top_p"],
                        presence_penalty=data_json["presence_penalty"],
                        frequency_penalty=data_json["frequency_penalty"],
                        timeout=30,
                    )

                    resp = resp["choices"][0]["message"]["content"]
                else:
                    client = openai.OpenAI(base_url=openai.api_base, api_key=openai.api_key)
                    # 调用 ChatGPT 接口生成回复消息
                    resp = client.chat.completions.create(
                        model=data_json["model"],
                        messages=[{"role": "user", "content": "Hi"}],
                        temperature=data_json["temperature"],
                        max_tokens=data_json["max_tokens"],
                        top_p=data_json["top_p"],
                        presence_penalty=data_json["presence_penalty"],
                        frequency_penalty=data_json["frequency_penalty"],
                        timeout=30,
                    )

                    resp = resp.choices[0].message.content

                logger.debug(resp)
                logger.info("OpenAI API key 可用（如需使用此配置，请保存后重新运行）")

                return {"code": 200, "msg": "OpenAI API key 可用（如需使用此配置，请保存后重新运行）"}
            except openai.OpenAIError as e:
                logger.error(f"OpenAI API key 不可用: {e}")
                return {"code": -1, "msg": f"OpenAI API key 不可用: {e}"}
            except Exception as e:
                logger.error(traceback.format_exc())
                logger.error(f"OpenAI API key 不可用: {e}")
                return {"code": -1, "msg": f"OpenAI API key 不可用: {e}"}

    return check_useful(data_json)


# 取 OpenAI 兼容接口下面的模型列表
def get_openai_models(base_url: str, api_keys: str):
    """请求 ``{base_url}/v1/models``，把这把 key 能用的模型名列出来。

    地址拼法与 test_openai_key 一致（都 urljoin 到 /v1/xxx），所以那边能通的
    网关这里也能通。密钥取文本框第一行，多 key 时搜的是第一个 key 的可见模型。

    Returns:
        dict: {"code": 200, "models": [模型名...]}，或 {"code": -1, "msg": 原因}
    """
    from urllib.parse import urljoin

    try:
        api_key = (api_keys or "").split("\n")[0].strip()

        url = urljoin(base_url, "/v1/models")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        logger.debug(f"url=【{url}】")

        response = requests.get(url, headers=headers, timeout=(10, 30))
        response.raise_for_status()
        response_data = response.json()

        # OpenAI 是 {"data":[{"id":...}]}，one-api、lmstudio、ollama 这些各家不一样，
        # 三种常见形状都兜一下
        if isinstance(response_data, list):
            items = response_data
        else:
            items = response_data.get("data") or response_data.get("models") or []

        models = []
        for item in items:
            name: str | None
            if isinstance(item, str):
                name = item
            elif isinstance(item, dict):
                name = item.get("id") or item.get("name")
            else:
                name = None
            if name and name not in models:
                models.append(name)

        if not models:
            return {"code": -1, "msg": f"接口没有返回任何模型名：{url}"}

        models.sort()
        logger.info(f"从 {url} 取到 {len(models)} 个模型")
        return {"code": 200, "models": models}
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"获取模型列表失败: {e}")
        return {"code": -1, "msg": f"获取模型列表失败: {e}"}
