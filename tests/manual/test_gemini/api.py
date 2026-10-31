import google.generativeai as genai
import vertexai
from vertexai.generative_models import GenerativeModel, Part, Image
import os
import logging
import traceback

class Gemini:
    def __init__(self, data):
        try:
            self.config_data = data

            self.history = []
            # 设置代理
            if self.config_data["http_proxy"]:
                os.environ['http_proxy'] = self.config_data["http_proxy"]
            if self.config_data["https_proxy"]:
                os.environ['https_proxy'] = self.config_data["https_proxy"]

            genai.configure(api_key=self.config_data["api_key"])
            self.model = genai.GenerativeModel(model_name = self.config_data["model"])

            vertexai.init(project=self.config_data["project_id"], location="us-central1")
        except Exception as e:
            logging.error(traceback.format_exc())
            
    def list_models(self):
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                logging.info(m.name)

    def get_resp_with_img(self, prompt, img_data):
        try:
            img = Image.load_from_file(img_data)

            image_file = Part.from_image(img)

            model = GenerativeModel(model_name="gemini-1.0-pro-vision-001")
            response = model.generate_content(
                [
                    image_file,
                    prompt,
                ]
            )

            logging.warning(f"{response}")

            resp_content = response.text.strip()

            logging.debug(f"resp_content={resp_content}")

            return resp_content
        except Exception as e:
            logging.error(traceback.format_exc())
            return None
        
    def get_resp_with_img_old(self, prompt, img_data):
        try:
            import PIL.Image

            # 检查 img_data 的类型
            if isinstance(img_data, str):  # 如果是字符串，假定为文件路径
                # 使用 PIL.Image.open() 打开图片文件
                img = PIL.Image.open(img_data)
            elif isinstance(img_data, PIL.Image.Image):  # 如果已经是 PIL.Image.Image 对象
                # 直接返回这个图像对象
                img = img_data
            else:
                img = img_data

            model = genai.GenerativeModel('gemini-pro-vision')

            response = model.generate_content(
                [
                    prompt, 
                    img
                ],
                stream=False
            )

            resp_content = response.text.strip()
        
            logging.debug(f"resp_content={resp_content}")

            return resp_content
        except Exception as e:
            logging.error(traceback.format_exc())
            return None

    def get_resp(self, prompt):
        """请求对应接口，获取返回值

        Args:
            prompt (str): 你的提问

        Returns:
            str: 返回的文本回答
        """
        try:
            messages = []

            # 载入上下文
            for history in self.history:
                messages.append(
                    {
                        'role':history["role"],
                        'parts': history["parts"]
                    }
                )

            messages.append(
                {
                    'role': 'user',
                    'parts': prompt
                }
            )

            response = self.model.generate_content(
                messages, 
                generation_config = genai.types.GenerationConfig(
                    max_output_tokens = self.config_data["max_output_tokens"], 
                    temperature = self.config_data["temperature"], 
                    top_p = self.config_data["top_p"],
                    top_k = self.config_data["top_k"])
                ,
                stream = False
            )
            resp_content = response.text

            # 启用历史就给我记住！
            if self.config_data["history_enable"]:
                while True:
                    # 获取嵌套列表中所有字符串的字符数
                    total_chars = sum(len(string) for sublist in self.history for string in sublist)
                    # 如果大于限定最大历史数，就剔除第一个元素
                    if total_chars > self.config_data["history_max_len"]:
                        self.history.pop(0)
                        self.history.pop(0)
                    else:
                        self.history.append({"role": "user", "parts": [prompt]})
                        self.history.append({"role": "model", "parts": [resp_content]})
                        break

            return resp_content
        except Exception as e:
            logging.error(traceback.format_exc())
            return None
        

if __name__ == '__main__':
    # 配置日志输出格式
    logging.basicConfig(
        level=logging.DEBUG,  # 设置日志级别，可以根据需求调整
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    data = {
        "api_key": "",
        "project_id": "avian-current-437112-a3",
        "model": "gemini-pro",
        "max_output_tokens": 100, 
        "temperature": 1.0, 
        "top_p": 0.7,
        "top_k": 40,
        "http_proxy": "http://127.0.0.1:10809",
        "https_proxy": "http://127.0.0.1:10809",
        "history_enable": True,
        "history_max_len": 300
    }

    gemini = Gemini(data)

    # logging.info(gemini.get_resp("你可以扮演猫娘吗，每句话后面加个喵"))
    # logging.info(gemini.get_resp("早上好"))
    # logging.info(gemini.get_resp("我的眼睛好酸"))

    logging.info(gemini.get_resp_with_img("根据图片内容，猜猜我吃的什么", "1.png"))
    