import json, os
import aiohttp, requests, ssl, asyncio
from urllib.parse import urlencode
import traceback
import edge_tts
from urllib.parse import urljoin
import random, copy

from utils.common import Common
from utils.my_log import logger
from utils.config import Config

class MY_TTS:
    def __init__(self, config_path):
        self.common = Common()
        self.config = Config(config_path)

        # 创建一个不执行证书验证的 SSLContext 对象
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

        # 获取 werkzeug 库的日志记录器
        # werkzeug_logger = logger.getLogger("werkzeug")
        # # 设置 httpx 日志记录器的级别为 WARNING
        # werkzeug_logger.setLevel(logger.WARNING)

        # 请求超时
        self.timeout = 60

        # 使用内部成员做配置
        self.use_class_config = False
        # 备份一下配置
        self.class_config = copy.copy(self.config)

        try:
            self.audio_out_path = self.config.get("play_audio", "out_path")

            if not os.path.isabs(self.audio_out_path):
                if not self.audio_out_path.startswith('./'):
                    self.audio_out_path = './' + self.audio_out_path
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error("请检查播放音频的音频输出路径配置！！！这将影响程序使用！")


    # 获取随机数，单数据就是原数值，有-则判断为范围性数据，随机一个数值，返回float数据
    def get_random_float(self, data):
        # 将非字符串的情况统一处理为长度相同的最小值和最大值
        if isinstance(data, str) and "-" in data:
            min, max = map(float, data.split("-"))
        else:
            min = max = float(data)
        
        # 返回指定范围内的随机浮点数
        return random.uniform(min, max)

    # 音频文件base64编码 传入文件路径
    def encode_audio_to_base64(self, file_path):
        import base64

        if file_path == "" or file_path is None:
            return None

        with open(file_path, "rb") as audio_file:
            audio_data = audio_file.read()
            encoded_audio = base64.b64encode(audio_data).decode('utf-8')
        return encoded_audio

    async def download_audio(self, type: str, file_url: str, timeout: int=30, request_type: str="get", data=None, json_data=None, audio_suffix: str="wav"):
        async with aiohttp.ClientSession() as session:
            try:
                if request_type == "get":
                    async with session.get(file_url, params=data, timeout=timeout) as response:
                        if response.status == 200:
                            content = await response.read()
                            file_name = type + '_' + self.common.get_bj_time(4) + '.' + audio_suffix
                            voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)
                            with open(voice_tmp_path, 'wb') as file:
                                file.write(content)
                            return voice_tmp_path
                        else:
                            logger.error(f'{type} 下载音频失败: {response.status}')
                            return None
                else:
                    async with session.post(file_url, data=data, json=json_data, timeout=timeout) as response:
                        if response.status == 200:
                            content = await response.read()
                            file_name = type + '_' + self.common.get_bj_time(4) + '.' + audio_suffix
                            voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)
                            with open(voice_tmp_path, 'wb') as file:
                                file.write(content)
                            return voice_tmp_path
                        else:
                            logger.error(f'{type} 下载音频失败: {response.status}')
                            return None
            except asyncio.TimeoutError:
                logger.error("{type} 下载音频超时")
                return None

    # 请求vits的api
    async def vits_api(self, data):
        try:
            logger.debug(f"data={data}")
            if data["type"] == "vits":
                # API地址 "http://127.0.0.1:23456/voice/vits"
                API_URL = urljoin(data["api_ip_port"], '/voice/vits')
                data_json = {
                    "text": data["content"],
                    "id": data["id"],
                    "format": data["format"],
                    "lang": "ja",
                    "length": data["length"],
                    "noise": data["noise"],
                    "noisew": data["noisew"],
                    "max": data["max"]
                }
                
                if data["lang"] == "中文" or data["lang"] == "汉语":
                    data_json["lang"] = "zh"
                elif data["lang"] == "英文" or data["lang"] == "英语":
                    data_json["lang"] = "en"
                elif data["lang"] == "韩文" or data["lang"] == "韩语":
                    data_json["lang"] = "ko"
                elif data["lang"] == "日文" or data["lang"] == "日语":
                    data_json["lang"] = "ja"
                elif data["lang"] == "自动":
                    data_json["lang"] = "auto"
                else:
                    data_json["lang"] = "auto"
            elif data["type"] == "bert_vits2":
                # API地址 "http://127.0.0.1:23456/voice/bert-vits2"
                API_URL = urljoin(data["api_ip_port"], '/voice/bert-vits2')

                data_json = {
                    "text": data["content"],
                    "id": data["id"],
                    "format": data["format"],
                    "lang": "ja",
                    "length": self.get_random_float(data["length"]),
                    "noise": self.get_random_float(data["noise"]),
                    "noisew": self.get_random_float(data["noisew"]),
                    "max": data["max"],
                    "sdp_radio": self.get_random_float(data["sdp_radio"])
                }
                
                if data["lang"] == "中文" or data["lang"] == "汉语":
                    data_json["lang"] = "zh"
                elif data["lang"] == "英文" or data["lang"] == "英语":
                    data_json["lang"] = "en"
                elif data["lang"] == "韩文" or data["lang"] == "韩语":
                    data_json["lang"] = "ko"
                elif data["lang"] == "日文" or data["lang"] == "日语":
                    data_json["lang"] = "ja"
                elif data["lang"] == "自动":
                    data_json["lang"] = "auto"
                else:
                    data_json["lang"] = "auto"
            elif data["type"] == "gpt_sovits":
                # 请求vits_simple_api的api gpt_sovits
                async def vits_simple_api_gpt_sovits_api(data):
                    try:
                        from aiohttp import FormData

                        logger.debug(f"data={data}")
                        url = urljoin(data["api_ip_port"], '/voice/gpt-sovits')


                        data_json = {
                            "text": data["content"],
                            "id": data["gpt_sovits"]["id"],
                            "format": data["gpt_sovits"]["format"],
                            "lang": data["gpt_sovits"]["lang"],
                            "segment_size": data["gpt_sovits"]["segment_size"],
                            "prompt_text": data["gpt_sovits"]["prompt_text"],
                            "prompt_lang": data["gpt_sovits"]["prompt_lang"],
                            "preset": data["gpt_sovits"]["preset"],
                            "top_k": data["gpt_sovits"]["top_k"],
                            "top_p": data["gpt_sovits"]["top_p"],
                            "temperature": data["gpt_sovits"]["temperature"]
                        }

                        # 创建 FormData 对象
                        form_data = FormData()
                        # 添加文本字段
                        for key, value in data_json.items():
                            form_data.add_field(key, str(value))

                        # 以二进制读取模式打开音频文件，并添加到表单数据中
                        # 'reference_audio' 是字段名称，应与服务器端接收的名称一致
                        form_data.add_field('reference_audio',
                                    open(data["gpt_sovits"]["reference_audio"], 'rb'),
                                    content_type='audio/mpeg')  # 内容类型根据文件类型修改
                            
                        logger.debug(f"data_json={data_json}")

                        logger.debug(f"url={url}")

                        return await self.download_audio("vits_simple_api", url, self.timeout, "post", form_data)
                    except aiohttp.ClientError as e:
                        logger.error(traceback.format_exc())
                        logger.error(f'vits_simple_api gpt_sovits请求失败，请检查您的vits_simple_api是否启动/配置是否正确，报错内容: {e}')
                    except Exception as e:
                        logger.error(traceback.format_exc())
                        logger.error(f'vits_simple_api gpt_sovits未知错误，请检查您的vits_simple_api是否启动/配置是否正确，报错内容: {e}')
                    
                    return None
                
                voice_tmp_path = await vits_simple_api_gpt_sovits_api(data)
                return voice_tmp_path
                
            # logger.info(f"data_json={data_json}")
            # logger.info(f"data={data}")

            logger.debug(f"API_URL={API_URL}")

            url = f"{API_URL}?{urlencode(data_json)}"

            return await self.download_audio("vits", url, self.timeout)
        except aiohttp.ClientError as e:
            logger.error(traceback.format_exc())
            logger.error(f'vits请求失败，请检查您的vits-simple-api是否启动/配置是否正确，报错内容: {e}')
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f'vits未知错误，请检查您的vits-simple-api是否启动/配置是否正确，报错内容: {e}')
        
        return None

    # 请求bert_vits2的api
    async def bert_vits2_api(self, data):
        try:
            logger.debug(f"data={data}")
            if data["type"] == "hiyori":
                # API地址 "http://127.0.0.1:5000/voice"
                API_URL = urljoin(data["api_ip_port"], '/voice')

                data_json = {
                    "text": data["content"],
                    "model_id": data["model_id"],
                    "speaker_name": data["speaker_name"],
                    "speaker_id": data["speaker_id"],
                    "language": data["language"],
                    "length": self.get_random_float(data["length"]),
                    "noise": self.get_random_float(data["noise"]),
                    "noisew": self.get_random_float(data["noisew"]),
                    "sdp_radio": self.get_random_float(data["sdp_radio"]),
                    "auto_translate": data["auto_translate"],
                    "auto_split": data["auto_split"],
                    "emotion": data["emotion"],
                    "style_text": data["style_text"],
                    "style_weight": self.get_random_float(data["style_weight"])
                }
                
                logger.debug(f"data_json={data_json}")
                # logger.info(f"data={data}")

                logger.debug(f"API_URL={API_URL}")

                url = f"{API_URL}?{urlencode(data_json)}"

                # logger.warning(f"url={url}")

                return await self.download_audio("bert_vits2", url, self.timeout)
            elif data["type"] == "刘悦-中文特化API":
                type = data["type"]
                # API地址 "http://127.0.0.1:5000/run/predict/"
                API_URL = urljoin(data[type]["api_ip_port"], '/tts_to_audio/')

                data_json = {
                    "text": data["content"],
                    "speaker": data[type]["speaker"],
                    "language": data["language"],
                    "length_scale": self.get_random_float(data[type]["length_scale"]),
                    "noise_scale": self.get_random_float(data[type]["noise_scale"]),
                    "noise_scale_w": self.get_random_float(data[type]["noise_scale_w"]),
                    "sdp_radio": self.get_random_float(data[type]["sdp_radio"]),
                    "cut_by_sent": data[type]["cut_by_sent"],
                    "interval_between_para": self.get_random_float(data[type]["interval_between_para"]),
                    "interval_between_sent": self.get_random_float(data[type]["interval_between_sent"]),
                    "emotion": data[type]["emotion"],
                    "style_text": data[type]["style_text"],
                    "style_weight": self.get_random_float(data[type]["style_weight"]),
                    "stream": data[type]["stream"]
                }

                logger.debug(f"data_json={data_json}")
                # logger.info(f"data={data}")

                logger.debug(f"API_URL={API_URL}")

                return await self.download_audio("bert_vits2", API_URL, self.timeout, "post", json_data=data_json)
        except aiohttp.ClientError as e:
            logger.error(traceback.format_exc())
            logger.error(f'bert_vits2请求失败，请检查您的bert_vits2 api是否启动/配置是否正确，报错内容: {e}')
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f'bert_vits2未知错误，请检查您的bert_vits2 api是否启动/配置是否正确，报错内容: {e}')
        
        return None
    
    # 请求VITS fast接口获取合成后的音频路径
    def vits_fast_api(self, data):
        try:
            # API地址
            API_URL = urljoin(data["api_ip_port"], '/run/predict/')

            data_json = {
                "fn_index":0,
                "data":[
                    "こんにちわ。",
                    "ikaros",
                    "日本語",
                    1
                ],
                "session_hash":"mnqeianp9th"
            }

            data_json["data"] = [data["content"], data["character"], data["language"], data["speed"]]

            logger.debug(f'data_json={data_json}')

            response = requests.post(url=API_URL, json=data_json, timeout=self.timeout)
            response.raise_for_status()  # 检查响应的状态码

            result = response.content
            ret = json.loads(result)

            file_path = ret["data"][1]["name"]

            new_file_path = self.common.move_file(file_path, os.path.join(self.audio_out_path, 'vits_fast_' + self.common.get_bj_time(4)), 'vits_fast_' + self.common.get_bj_time(4))

            return new_file_path
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f'vits-fast错误，请检查您的vits-fast推理程序是否启动/配置是否正确，报错内容: {e}')
            return None
    

    # 请求Edge-TTS接口获取合成后的音频路径
    async def edge_tts_api(self, data):
        try:
            file_name = 'edge_tts_' + self.common.get_bj_time(4) + '.mp3'
            voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)
            # voice_tmp_path = './out/' + self.common.get_bj_time(4) + '.mp3'
            # 过滤" '字符
            data["content"] = data["content"].replace('"', '').replace("'", '')

            proxy = data["edge-tts"]["proxy"] if data["edge-tts"]["proxy"] != "" else None

            # 使用 Edge TTS 生成回复消息的语音文件
            communicate = edge_tts.Communicate(
                text=data["content"], 
                voice=data["edge-tts"]["voice"], 
                rate=data["edge-tts"]["rate"], 
                volume=data["edge-tts"]["volume"], 
                proxy=proxy
            )
            await communicate.save(voice_tmp_path)

            return voice_tmp_path
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(e)
            return None
    

    # 请求OpenAI_TTS的api
    def openai_tts_api(self, data):
        try:
            if data["type"] == "huggingface":
                from gradio_client import Client

                client = Client(data["api_ip_port"])
                result = client.predict(
                    data["content"],	# str in 'Text' Textbox component
                    data["model"],	# Literal[tts-1, tts-1-hd]  in 'Model' Dropdown component
                    data["voice"],	# Literal[alloy, echo, fable, onyx, nova, shimmer]  in 'Voice Options' Dropdown component
                    data["api_key"],	# str  in 'OpenAI API Key' Textbox component
                    api_name="/tts_enter_key"
                )

                new_file_path = self.common.move_file(result, os.path.join(self.audio_out_path, 'openai_tts_' + self.common.get_bj_time(4)), 'openai_tts_' + self.common.get_bj_time(4), "mp3")

                return new_file_path
            elif data["type"] == "api":
                from openai import OpenAI
                
                client = OpenAI(api_key=data["api_key"], base_url=data['api_ip_port'])

                response = client.audio.speech.create(
                    model=data["model"],
                    voice=data["voice"],
                    input=data["content"]
                )

                file_name = 'openai_tts_' + self.common.get_bj_time(4) + '.mp3'
                voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)

                response.stream_to_file(voice_tmp_path)

                return voice_tmp_path
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f'OpenAI_TTS请求失败: {e}')
            return None

    # 请求gradio的api
    def gradio_tts_api(self, data):
        def get_value_by_index(response, index):
            try:
                # 确保响应是元组或列表，并且索引在范围内
                if isinstance(response, (tuple, list)) and index < len(response):
                    return response[index]
                else:
                    return None
            except IndexError:
                logger.error(traceback.format_exc())
                # 索引超出范围
                return None

        def get_file_path(data):
            try:
                url = data.pop('url')  # 获取并移除URL
                fn_index = data.pop('fn_index')  # 获取并移除函数索引
                data_analysis = data.pop('data_analysis')

                from gradio_client import Client
                client = Client(url)

                # data是一个字典，包含了所有需要的参数
                data_values = list(data.values())
                result = client.predict(fn_index=fn_index, *data_values)

                logger.debug(result)

                if isinstance(result, (tuple, list)):
                    # 获取索引为1的元素
                    file_path = get_value_by_index(result, int(data_analysis))

                    if file_path:
                        logger.debug(f"文件路径:{file_path}")
                        return file_path
                elif isinstance(result, str):
                    logger.debug(f"文件路径:{result}")
                    return result
                else:
                    logger.error("数据解析失败！Invalid index or response format.")
                    return None
            except Exception as e:
                logger.error(traceback.format_exc())
                # 索引超出范围
                return None

        logger.debug(f"data={data}")
        data_str = data["request_parameters"]
        formatted_data_str = data_str.format(content=data["content"])
        data_json = json.loads(formatted_data_str)

        file_path = get_file_path(data_json)

        new_file_path = self.common.move_file(file_path, os.path.join(self.audio_out_path, 'gradio_tts_' + self.common.get_bj_time(4)), 'gradio_tts_' + self.common.get_bj_time(4))

        return new_file_path


    async def gpt_sovits_api(self, data):
        import base64
        import mimetypes

        def file_to_data_url(file_path):
            # 根据文件扩展名确定 MIME 类型
            mime_type, _ = mimetypes.guess_type(file_path)

            # 读取文件内容
            with open(file_path, "rb") as file:
                file_content = file.read()

            # 转换为 Base64 编码
            base64_encoded_data = base64.b64encode(file_content).decode('utf-8')

            # 构造完整的 Data URL
            return f"data:{mime_type};base64,{base64_encoded_data}"

               
        try:
            logger.debug(f"data={data}")
            
            if data["type"] == "gradio_0322":
                from gradio_client import Client

                client = Client(data["gradio_ip_port"])
                voice_tmp_path = client.predict(
                    data["content"],	# str  in '需要合成的文本' Textbox component
                    data["api_0322"]["text_lang"],	# Literal['中文', '英文', '日文', '中英混合', '日英混合', '多语种混合']  in '需要合成的语种' Dropdown component
                    data["api_0322"]["ref_audio_path"],	# filepath  in '请上传3~10秒内参考音频，超过会报错！' Audio component
                    data["api_0322"]["prompt_text"],	# str  in '参考音频的文本' Textbox component
                    data["api_0322"]["prompt_lang"],	# Literal['中文', '英文', '日文', '中英混合', '日英混合', '多语种混合']  in '参考音频的语种' Dropdown component
                    data["api_0322"]["top_k"],	# float (numeric value between 1 and 100) in 'top_k' Slider component
                    data["api_0322"]["top_p"],	# float (numeric value between 0 and 1) in 'top_p' Slider component
                    data["api_0322"]["temperature"],	# float (numeric value between 0 and 1) in 'temperature' Slider component
                    data["api_0322"]["text_split_method"],	# Literal['不切', '凑四句一切', '凑50字一切', '按中文句号。切', '按英文句号.切', '按标点符号切']  in '怎么切' Radio component
                    int(data["api_0322"]["batch_size"]),	# float (numeric value between 1 and 200) in 'batch_size' Slider component
                    float(data["api_0322"]["speed_factor"]),	# float (numeric value between 0.25 and 4) in 'speed_factor' Slider component
                    data["api_0322"]["split_bucket"],	# bool  in '开启无参考文本模式。不填参考文本亦相当于开启。' Checkbox component
                    data["api_0322"]["return_fragment"],	# bool  in '数据分桶(可能会降低一点计算量,选就对了)' Checkbox component
                    data["api_0322"]["fragment_interval"],	# float (numeric value between 0.01 and 1) in '分段间隔(秒)' Slider component
                    api_name="/inference"
                )
                new_file_path = None

                if voice_tmp_path:
                    new_file_path = self.common.move_file(voice_tmp_path, os.path.join(self.audio_out_path, 'gpt_sovits_' + self.common.get_bj_time(4)), 'gpt_sovits_' + self.common.get_bj_time(4))

                return new_file_path
            elif data["type"] == "api":
                try:
                    data_json = {
                        "refer_wav_path": data["ref_audio_path"],
                        "prompt_text": data["prompt_text"],
                        "prompt_language": data["prompt_language"],
                        "text": data["content"],
                        "text_language": data["language"]
                    }
                                        
                    return await self.download_audio("gpt_sovits", data["api_ip_port"], self.timeout, "post", None, data_json)
                except aiohttp.ClientError as e:
                    logger.error(traceback.format_exc())
                    logger.error(f'gpt_sovits请求失败: {e}')
                except Exception as e:
                    logger.error(traceback.format_exc())
                    logger.error(f'gpt_sovits未知错误: {e}')
            elif data["type"] == "api_0322":
                try:

                    data_json = {
                        "text": data["content"],
                        "text_lang": data["api_0322"]["text_lang"],
                        "ref_audio_path": data["api_0322"]["ref_audio_path"],
                        "prompt_text": data["api_0322"]["prompt_text"],
                        "prompt_lang": data["api_0322"]["prompt_lang"],
                        "top_k": data["api_0322"]["top_k"],
                        "top_p": data["api_0322"]["top_p"],
                        "temperature": data["api_0322"]["temperature"],
                        "text_split_method": data["api_0322"]["text_split_method"],
                        "batch_size":int(data["api_0322"]["batch_size"]),
                        "speed_factor":float(data["api_0322"]["speed_factor"]),
                        "split_bucket":data["api_0322"]["split_bucket"],
                        "return_fragment":data["api_0322"]["return_fragment"],
                        "fragment_interval":data["api_0322"]["fragment_interval"],
                    }
                                        
                    return await self.download_audio("gpt_sovits", data["api_ip_port"], self.timeout, "post", None, data_json)
                except aiohttp.ClientError as e:
                    logger.error(traceback.format_exc())
                    logger.error(f'gpt_sovits请求失败: {e}')
                except Exception as e:
                    logger.error(traceback.format_exc())
                    logger.error(f'gpt_sovits未知错误: {e}')
            elif data["type"] == "api_0706":
                try:

                    data_json = {
                        "text": data["content"],
                        "refer_wav_path": data["api_0706"]["refer_wav_path"],
                        "text_language": data["api_0706"]["text_language"],
                        "prompt_text": data["api_0706"]["prompt_text"],
                        "prompt_language": data["api_0706"]["prompt_language"],
                        "cut_punc": data["api_0706"]["cut_punc"],
                    }
                                        
                    return await self.download_audio("gpt_sovits", data["api_ip_port"], self.timeout, "post", None, data_json)
                except aiohttp.ClientError as e:
                    logger.error(traceback.format_exc())
                    logger.error(f'gpt_sovits请求失败: {e}')
                except Exception as e:
                    logger.error(traceback.format_exc())
                    logger.error(f'gpt_sovits未知错误: {e}')
            elif data["type"] == "v2_api_0821":
                try:
                    data_json = {
                        "text": data["content"],
                        "text_lang": data[data["type"]]["text_lang"],
                        "ref_audio_path": data[data["type"]]["ref_audio_path"],
                        "aux_ref_audio_paths": data[data["type"]]["aux_ref_audio_paths"],
                        "prompt_text": data[data["type"]]["prompt_text"],
                        "prompt_lang": data[data["type"]]["prompt_lang"],
                        "top_k": int(data[data["type"]]["top_k"]),
                        "top_p": float(data[data["type"]]["top_p"]),
                        "temperature": float(data[data["type"]]["temperature"]),
                        "text_split_method": data[data["type"]]["text_split_method"],
                        "batch_size": int(data[data["type"]]["batch_size"]),
                        "split_bucket": data[data["type"]]["split_bucket"],
                        "speed_factor": float(data[data["type"]]["speed_factor"]),
                        "fragment_interval": float(data[data["type"]]["fragment_interval"]),
                        "seed": int(data[data["type"]]["seed"]),
                        "media_type": data[data["type"]]["media_type"],
                        "streaming_mode": data[data["type"]]["streaming_mode"],
                        "parallel_infer": data[data["type"]]["parallel_infer"],
                        "repetition_penalty": float(data[data["type"]]["repetition_penalty"]),
                    }

                    API_URL = urljoin(data["api_ip_port"], '/tts')

                    return await self.download_audio("gpt_sovits", API_URL, self.timeout, "post", None, data_json)
                except aiohttp.ClientError as e:
                    logger.error(traceback.format_exc())
                    logger.error(f'gpt_sovits请求失败: {e}')
                except Exception as e:
                    logger.error(traceback.format_exc())
                    logger.error(f'gpt_sovits未知错误: {e}')
            
            elif data["type"] == "webtts":
                try:
                    # 使用字典推导式构建 params 字典，只包含非空字符串的值
                    params = {
                        key: value
                        for key, value in data["webtts"].items()
                        if value != ""
                        if key != "api_ip_port"
                    }

                    params["speed"] = self.get_random_float(params["speed"])
                    params["text"] = data["content"]

                    if params["version"] in ["1", "2"]:
                        return await self.download_audio("gpt_sovits", data["webtts"]["api_ip_port"], self.timeout, "get", params)
                    elif params["version"] == "1.4":
                        async with aiohttp.ClientSession() as session:
                            async with session.get(data["webtts"]["api_ip_port"], params=params, timeout=self.timeout) as response:
                                resp_json = await response.json()

                                url = urljoin(data["webtts"]["api_ip_port"], resp_json['url'])

                                return await self.download_audio("gpt_sovits", url, self.timeout, "get", params)
                except aiohttp.ClientError as e:
                    logger.error(traceback.format_exc())
                    logger.error(f'gpt_sovits请求失败: {e}')
                except Exception as e:
                    logger.error(traceback.format_exc())
                    logger.error(f'gpt_sovits未知错误: {e}')
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f'gpt_sovits未知错误，请检查您的gpt_sovits推理是否启动/配置是否正确，报错内容: {e}')
        
        return None


    def azure_tts_api(self, data):
        """调用Azure TTS API合成音频返回音频路径

        Args:
            data (dict): JSON数据

        Returns:
            str: 音频路径
        """
        try:
            import azure.cognitiveservices.speech as speechsdk

            file_name = 'azure_tts_' + self.common.get_bj_time(4) + '.wav'
            voice_tmp_path = self.common.get_new_audio_path(self.audio_out_path, file_name)
            
            # 创建语音配置对象，使用Azure订阅密钥和服务区域
            speech_config = speechsdk.SpeechConfig(subscription=self.config.get("azure_tts", "subscription_key"), region=self.config.get("azure_tts", "region"))
            speech_config.speech_synthesis_voice_name = self.config.get("azure_tts", "voice_name")

            # 创建音频配置对象，指定输出音频文件路径
            audio_config = speechsdk.audio.AudioOutputConfig(filename=voice_tmp_path)

            # 创建语音合成器对象
            speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

            # 执行文本到语音的转换
            result = speech_synthesizer.speak_text_async(data["content"]).get()

            # 检查结果
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                logger.debug(f"音频已成功保存到: {voice_tmp_path}")
                return voice_tmp_path
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                logger.error(f"文本转语音取消: {str(cancellation_details.reason)}")
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    if cancellation_details.error_details:
                        logger.error(f"错误详情: {str(cancellation_details.error_details)}")

                return None
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f'azure_tts未知错误: {e}')

            return None
        

    # CosyVoice （gradio_client-0.16.4，版本太低没法用喵）
    async def cosyvoice_api(self, data):
        """CosyVoice Gradio的API对接喵

        Args:
            data (dict): 传参数据喵

        Returns:
            str: 音频路径
        """
        try:
            if data["type"] == "gradio_0707":
                from gradio_client import Client, file

                client = Client(data["gradio_ip_port"])

                if data["gradio_0707"]["prompt_wav_upload"] == "":
                    prompt_wav_upload = None
                else:
                    prompt_wav_upload = file(data["gradio_0707"]["prompt_wav_upload"])

                result = client.predict(
                    tts_text=data["content"] + "。",
                    mode_checkbox_group=data["gradio_0707"]["mode_checkbox_group"],
                    sft_dropdown=data["gradio_0707"]["sft_dropdown"],
                    prompt_text=data["gradio_0707"]["prompt_text"],
                    prompt_wav_upload=prompt_wav_upload,
                    prompt_wav_record=None,
                    instruct_text=data["gradio_0707"]["instruct_text"],
                    seed=int(data["gradio_0707"]["seed"]),
                    api_name="/generate_audio"
                )

                new_file_path = None

                if result:
                    voice_tmp_path = result
                    new_file_path = self.common.move_file(voice_tmp_path, os.path.join(self.audio_out_path, 'cosyvoice_' + self.common.get_bj_time(4)), 'cosyvoice_' + self.common.get_bj_time(4))

                return new_file_path
            elif data["type"] == "api_0819":
                url = data["api_ip_port"]

                params = {
                    "text": data["content"],
                    "speaker": data["api_0819"]["speaker"],
                    'new': int(data["api_0819"]["new"]),
                    'speed': float(data["api_0819"]["speed"]),
                    'streaming': int(data["api_0819"]["streaming"])
                }

                logger.debug(f"params={params}")

                try:
                    return await self.download_audio("cosyvoice", url, self.timeout, request_type="post", json_data=params)
                except Exception as e:
                    logger.error(traceback.format_exc())
                    logger.error(f'cosyvoice未知错误，请检查您的CosyVoice API是否启动/配置是否正确，报错内容: {e}')
                
                return None
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f'CosyVoice未知错误，请检查您的CosyVoice WebUI是否启动/配置是否正确，报错内容: {e}')
        
        return None

    # F5-TTS （gradio_client-1.4.2，版本太低没法用喵）
    async def f5_tts_api(self, data):
        """F5-TTS Gradio的API对接喵

        Args:
            data (dict): 传参数据喵

        Returns:
            str: 音频路径
        """
        try:
            if data["type"] == "gradio_1023":
                from gradio_client import Client, handle_file

                client = Client(data["gradio_ip_port"])

                result = client.predict(
                    ref_audio_orig=handle_file(data["ref_audio_orig"]),
                    ref_text=data["ref_text"],
                    gen_text=data["content"],
                    model=data["model"],
                    remove_silence=data["remove_silence"],
                    cross_fade_duration=float(data["cross_fade_duration"]),
                    speed=float(data["speed"]),
                    api_name="/infer"
                )

                new_file_path = None

                if result:
                    voice_tmp_path = result[0]
                    new_file_path = self.common.move_file(voice_tmp_path, os.path.join(self.audio_out_path, 'f5_tts_' + self.common.get_bj_time(4)), 'f5_tts_' + self.common.get_bj_time(4))

                return new_file_path
            
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f'F5-TTS未知错误，请检查您的F5-TTS WebUI是否启动/配置是否正确，报错内容: {e}')
        
        return None

    async def multitts_api(self, data):
        try:
            # http://127.0.0.1:8774/forward
            API_URL = urljoin(data["multitts"]["api_ip_port"], "/forward")

            data_json = {
                "text": data["content"],
                "speed": int(data["multitts"]["speed"]),
                "volume": int(data["multitts"]["volume"]),
                "pitch": int(data["multitts"]["pitch"])
            }

            if data["multitts"]["voice"] != "":
                data_json["voice"] = data["multitts"]["voice"]
                
            logger.debug(f"data_json={data_json}")
            logger.debug(f"url={API_URL}")

            return await self.download_audio("multitts", API_URL, self.timeout, "get", data_json)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f'MultiTTS未知错误，请检查您的MultiTTS 接口服务是否启动/配置/网络是否正确，报错内容: {e}')
        
        return None

    
    async def melotts_api(self, data):
        try:
            API_URL = urljoin(data["melotts"]["api_ip_port"], "/tts")

            data_json = {
                "text": data["content"],
                "speaker_id": int(data["melotts"]["speaker_id"]),
                "sdp_ratio": float(data["melotts"]["sdp_ratio"]),
                "noise_scale": float(data["melotts"]["noise_scale"]),
                "noise_scale_w": float(data["melotts"]["noise_scale_w"]),
                "speed": float(data["melotts"]["speed"]),
            }
                
            logger.debug(f"data_json={data_json}")
            logger.debug(f"url={API_URL}")

            return await self.download_audio("melotts", API_URL, self.timeout, "post", json_data=data_json)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f'MeloTTS未知错误，请检查您的MeloTTS 接口服务是否启动/配置/网络是否正确，报错内容: {e}')
        
        return None

    # Index-tts
    async def index_tts_api(self, data):
        """Index-tts API对接喵

        Args:
            data (dict): 传参数据喵

        Returns:
            str: 音频路径
        """
        try:
            url = f"{data['index_tts']['api_ip_port']}/tts"
            
            # 创建FormData对象用于multipart/form-data请求
            from aiohttp import FormData
            form_data = FormData()
            
            # 添加文本参数
            form_data.add_field('text', data["content"])
            
            # 添加温度参数
            form_data.add_field('temperature', str(data['index_tts']["temperature"]))
            
            # 添加音频文件
            form_data.add_field(
                'prompt_audio',
                open(data['index_tts']["prompt_audio"], 'rb'),
                filename=os.path.basename(data['index_tts']["prompt_audio"]),
                content_type='audio/wav'
            )
            
            logger.debug(f"Index-tts 请求参数: text={data['content']}, temperature={data['index_tts']['temperature']}")
            
            try:
                return await self.download_audio("index_tts", url, self.timeout, request_type="post", data=form_data)
            except Exception as e:
                logger.error(traceback.format_exc())
                logger.error(f'Index-tts API 错误，请检查您的 Index-tts API 是否启动/配置是否正确，报错内容: {e}')

            return None
            
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f'Index-tts未知错误，请检查您的Index-tts API是否启动/配置是否正确，报错内容: {e}')
        
        return None
