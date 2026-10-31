import threading
import webuiapi

# from PIL import Image
import pyvirtualcam
import numpy as np
import traceback
import asyncio
import os
from PIL import Image

from luna.common.helpers import Common
from luna.infra.my_log import logger


def hex_to_rgba(hex_str):
    """将十六进制颜色字符串转换为 RGBA 元组."""
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 8:
        return tuple(int(hex_str[i : i + 2], 16) for i in (0, 2, 4, 6))  # 分别提取RGBA
    elif len(hex_str) == 6:
        return tuple(int(hex_str[i : i + 2], 16) for i in (0, 2, 4)) + (255,)  # RGB + 默认不透明度
    else:
        logger.error(f"无效的颜色值: {hex_str}")
        raise ValueError(f"无效的颜色值: {hex_str}")


class SD:
    def __init__(self, data):
        self.common = Common()

        self.new_img = None
        self.sd_config = data

        try:
            if data["enable"]:
                # 创建 API 客户端
                self.api = webuiapi.WebUIApi(host=data["ip"], port=data["port"])

            self.rgba_color = hex_to_rgba(data["visual_camera"]["background_color"])

            logger.info("即将创建 虚拟摄像头线程...")
            # 在单独的线程中更新虚拟摄像头
            threading.Thread(target=lambda: asyncio.run(self.update_virtual_camera())).start()
            # threading.Thread(target=self.update_virtual_camera).start()
        except Exception:
            logger.error(traceback.format_exc())

    async def update_virtual_camera(self):
        try:
            # 固定虚拟摄像头的分辨率
            cam_width, cam_height = 1920, 1080  # 这里可以根据需要修改分辨率
            with pyvirtualcam.Camera(
                width=cam_width, height=cam_height, fps=1, fmt=pyvirtualcam.PixelFormat.RGB
            ) as cam:
                logger.info(f"虚拟摄像头已创建，分辨率：{cam_width}x{cam_height}，设备：{cam.device}")

                while True:
                    if self.new_img is not None:
                        try:
                            # 获取图片原始宽高
                            img_width, img_height = self.new_img.size

                            # 计算图片的缩放比例，确保图片按比例缩放并且适应虚拟摄像头的宽或高
                            scale = min(cam_width / img_width, cam_height / img_height)
                            new_size = (int(img_width * scale), int(img_height * scale))

                            # 调整图片大小
                            resized_img = self.new_img.resize(new_size, Image.LANCZOS)

                            # 检查是否有 Alpha 通道，如果没有则添加
                            if resized_img.mode != "RGBA":
                                resized_img = resized_img.convert("RGBA")

                            # 创建一个带自定义背景的空白图像，大小与摄像头一致
                            custom_background = Image.new("RGBA", (cam_width, cam_height), self.rgba_color)

                            # 计算居中位置
                            paste_position = ((cam_width - new_size[0]) // 2, (cam_height - new_size[1]) // 2)

                            # 将调整后的图片粘贴到自定义背景的中心
                            custom_background.paste(resized_img, paste_position, resized_img)

                            # 将图像转换为RGB（去除Alpha通道）
                            rgb_img = custom_background.convert("RGB")

                            # 将 PIL 图像转换为 numpy 数组并设置数据类型为 uint8
                            frame = np.array(rgb_img).astype(np.uint8)

                            # 将图像帧发送到虚拟摄像头
                            cam.send(frame)

                        except Exception as e:
                            logger.error(traceback.format_exc())
                            logger.error(f"更新虚拟摄像头失败：{e}")

                    # 暂停一段时间
                    await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f"更新虚拟摄像头失败：{e}")

    def save_image_locally(self, img):
        # 确保有一个用于保存图片的目录
        save_dir = self.sd_config["save_path"]
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        if self.sd_config["loop_cover"]:
            # 生成一个基于时间循环覆盖的文件名
            filename = self.common.get_bj_time(4) + ".png"
        else:
            # 生成一个基于时间的唯一文件名
            filename = self.common.get_bj_time(3) + ".png"

        # 保存图片
        img_path = os.path.join(save_dir, filename)
        img.save(img_path)
        logger.info(f"图片保存在：{img_path}")

    def process_input(self, user_input):
        # 使用用户输入的文本作为 prompt 调用 API
        """
        prompt：主要文本提示，用于指定生成图像的主题或内容。
        negative_prompt：负面文本提示，用于指定与生成图像相矛盾或相反的内容。
        seed：随机种子，用于控制生成过程的随机性。可以设置一个整数值，以获得可重复的结果。
        styles：样式列表，用于指定生成图像的风格。可以包含多个风格，例如 ["anime", "portrait"]。
        cfg_scale：提示词相关性，无分类器指导信息影响尺度(Classifier Free Guidance Scale) -图像应在多大程度上服从提示词-较低的值会产生更有创意的结果。
        sampler_index：采样器索引，用于指定生成图像时使用的采样器。默认情况下，该参数为 None。
        steps：生成图像的步数，用于控制生成的精确程度。
        enable_hr：是否启用高分辨率生成。默认为 False。
        hr_scale：高分辨率缩放因子，用于指定生成图像的高分辨率缩放级别。
        hr_upscaler：高分辨率放大器类型，用于指定高分辨率生成的放大器类型。
        hr_second_pass_steps：高分辨率生成的第二次传递步数。
        hr_resize_x：生成图像的水平尺寸。
        hr_resize_y：生成图像的垂直尺寸。
        denoising_strength：去噪强度，用于控制生成图像中的噪点。
        """
        try:
            result = self.api.txt2img(
                prompt=user_input,
                negative_prompt=self.sd_config["negative_prompt"],
                seed=self.sd_config["seed"],
                styles=self.sd_config["styles"],
                cfg_scale=self.sd_config["cfg_scale"],
                # sampler_index='DDIM',
                steps=self.sd_config["steps"],
                enable_hr=self.sd_config["enable_hr"],
                hr_scale=self.sd_config["hr_scale"],
                # hr_upscaler=webuiapi.HiResUpscaler.Latent,
                hr_second_pass_steps=self.sd_config["hr_second_pass_steps"],
                hr_resize_x=self.sd_config["hr_resize_x"],
                hr_resize_y=self.sd_config["hr_resize_y"],
                denoising_strength=self.sd_config["denoising_strength"],
            )

            # 获取返回的图像
            img = result.image
            self.new_img = img

            # 保存图片到本地
            if self.sd_config["save_enable"]:
                self.save_image_locally(img)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f"调用 SD API 失败：{e}")
            return None

    def set_new_img(self, img_path: str):
        try:
            # 读取图片
            img = Image.open(img_path)
            self.new_img = img
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f"读取图片失败：{e}")
            return None
