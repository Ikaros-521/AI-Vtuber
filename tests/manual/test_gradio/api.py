from gradio_client import Client
import json, logging
import traceback

# 配置日志输出格式
logging.basicConfig(
    level=logging.DEBUG,  # 设置日志级别，可以根据需求调整
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# 请求gradio的api
def gradio_api(data):
    def get_value_by_index(response, index):
        try:
            # 确保响应是元组或列表，并且索引在范围内
            if isinstance(response, (tuple, list)) and index < len(response):
                return response[index]
            else:
                return None
        except IndexError:
            logging.error(traceback.format_exc())
            # 索引超出范围
            return None

    def get_file_path(data):
        try:
            url = data.pop('url')  # 获取并移除URL
            fn_index = data.pop('fn_index')  # 获取并移除函数索引
            data_analysis = data.pop('data_analysis')

            client = Client(url)

            # data是一个字典，包含了所有需要的参数
            data_values = list(data.values())
            result = client.predict(fn_index=fn_index, *data_values)

            logging.info(result)

            if isinstance(result, (tuple, list)):
                # 获取索引为1的元素
                file_path = get_value_by_index(result, int(data_analysis))

            if file_path:
                logging.info(f"文件路径:{file_path}")
                return file_path
            else:
                logging.error("Invalid index or response format.")
                return None
        except Exception as e:
            logging.error(traceback.format_exc())
            # 索引超出范围
            return None

    data_str = data["request_parameters"]
    logging.info(f"data_str:{data_str}")
    formatted_data_str = data_str.format(content=data["content"])
    logging.info(f"formatted_data_str:{formatted_data_str}")
    data_json = json.loads(formatted_data_str)
    logging.info(f"data_json:{data_json}")

    return get_file_path(data_json)


    # result = client.predict(
    # 		"你好",	# str  in '输入文本内容' Textbox component
    # 		"派蒙_ZH",	# str (Option from: [('派蒙_ZH', '派蒙_ZH'), ('纳西妲_ZH', '纳西妲_ZH')]) in 'Speaker' Dropdown component
    # 		0.5,	# int | float (numeric value between 0 and 1) in 'SDP Ratio' Slider component
    # 		0.6,	# int | float (numeric value between 0.1 and 2) in 'Noise' Slider component
    # 		0.9,	# int | float (numeric value between 0.1 and 2) in 'Noise_W' Slider component
    # 		1,	# int | float (numeric value between 0.1 and 2) in 'Length' Slider component
    # 		"ZH",	# str (Option from: [('ZH', 'ZH'), ('JP', 'JP'), ('EN', 'EN'), ('mix', 'mix'), ('auto', 'auto')]) in 'Language' Dropdown component
    # 		None,	# str (filepath on your computer (or URL) of file) in 'Audio prompt' Audio component
    # 		"Happy",	# str  in 'Text prompt' Textbox component
    # 		"Text prompt",	# str  in 'Prompt Mode' Radio component
    # 		"",	# str  in '辅助文本' Textbox component
    # 		0.7,	# int | float (numeric value between 0 and 1) in 'Weight' Slider component
    # 		fn_index=fn_index
    # )
        
    # Define the JSON template string
    data_str = '{{"url": "https://v2.genshinvoice.top/", "fn_index": 0, "data_analysis": 1, "text_input": "{content}", "speaker_option": "派蒙_ZH", "sdp_ratio": 0.5, "noise": 0.6, "noise_w": 0.9, "length": 1, "language": "ZH", "audio_prompt_url": null, "text_prompt": "Happy", "prompt_mode": "Text prompt", "auxiliary_text": "", "weight": 0.7}}'

    # Insert dynamic content using format
    formatted_data_str = data_str.format(content="你好")

    data = {
        "url": "https://v2.genshinvoice.top/",
        "fn_index": 0,
        "data_analysis": 1,
        "text_input": "你好",
        "speaker_option": "派蒙_ZH",
        "sdp_ratio": 0.5,
        "noise": 0.6,
        "noise_w": 0.9,
        "length": 1,
        "language": "ZH",
        "audio_prompt_url": None,
        "text_prompt": "Happy",
        "prompt_mode": "Text prompt",
        "auxiliary_text": "",
        "weight": 0.7
    }

    # print(json.dumps(data))

    # Parse the JSON string
    data = json.loads(formatted_data_str)

    print(data)

    logging.info(get_file_path(data))

    '''
    data = {
        "url": "https://xzjosh-nana7mi-bert-vits2.hf.space/--replicas/m9qdw/",
        "fn_index": 0,
        "data_analysis": 1,
        "text_input": "你好",
        "speaker_option": "Nana7mi",
        "sdp_ratio": 0.5,
        "noise": 0.6,
        "noise_w": 0.9,
        "length": 1
    }
    print(json.dumps(data))

    data_str = "{{"url": "https://xzjosh-nana7mi-bert-vits2.hf.space/--replicas/m9qdw/", "fn_index": 0, "data_analysis": 1, "text_input": "{content}", "speaker_option": "Nana7mi", "sdp_ratio": 0.5, "noise": 0.6, "noise_w": 0.9, "length": 1}}"
    
    logging.info(get_file_path(data))

    data = {
        "url": "https://frankzxshen-vits-fast-fineturning-models-ba.hf.space/",
        "fn_index": 2,
        "data_analysis": 1,
        "text": "你好",
        "character": "果穗",
        "language": "日本語",
        "noise": 0.6,
        "noise_w": 0.6,
        "speed": 1,
        "symbol_input": False
    }
    logging.info(get_file_path(data))
    '''


# genshinvoice.top
data = {
    'content': '你好',
    'request_parameters': '{{"url": "https://v2.genshinvoice.top/", "fn_index": 0, "data_analysis": 1, "text_input": "{content}", "speaker_option": "派蒙_ZH", "sdp_ratio": 0.5, "noise": 0.6, "noise_w": 0.9, "length": 1, "language": "ZH", "audio_prompt_url": null, "text_prompt": "Happy", "prompt_mode": "Text prompt", "auxiliary_text": "", "weight": 0.7}}'
}

# openvoice
data = {
    'content': '你好',
    'request_parameters': '{{"url": "http://127.0.0.1:7860/", "fn_index": 1, "data_analysis": 1, "Text_Prompt": "{content}", "style": "default", "filepath": "F:/OpenVoice/resources/demo_speaker0.mp3", "Agree": true}}'
}

gradio_api(data)
