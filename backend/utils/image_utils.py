# backend/utils/image_utils.py
import base64
import io
from typing import Tuple
from PIL import Image

class ImageUtils:
    @staticmethod
    def encode_image(image_path: str) -> Tuple[str, int]:
        """编码图片为base64并返回像素总数"""
        img = Image.open(image_path)
        w, h = img.size
        pixel_count = w * h

        buffer = io.BytesIO()
        img_format = img.format or "PNG"
        img_format = img_format.upper()

        if img_format == "JPEG":
            img.save(buffer, format=img_format, quality=100, optimize=True)
        else:
            img.save(buffer, format=img_format)

        image_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return image_b64, pixel_count

    @staticmethod
    def validate_image_format(image_path: str) -> bool:
        """验证图片格式是否支持"""
        supported_formats = ['PNG', 'JPEG', 'JPG', 'BMP', 'GIF']
        try:
            img = Image.open(image_path)
            return img.format.upper() in supported_formats
        except Exception:
            return False