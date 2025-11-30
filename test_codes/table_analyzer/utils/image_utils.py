import os
import hashlib
import base64
import fitz  # PyMuPDF
from typing import List


class ImageUtils:
    """统一的图片处理工具类"""

    @staticmethod
    def generate_image_id(image_path: str) -> str:
        """统一的图片ID生成器"""
        try:
            with open(image_path, "rb") as f:
                file_content = f.read()
            content_hash = hashlib.md5(file_content).hexdigest()[:16]
            file_name = os.path.basename(image_path)
            combined = f"{file_name}_{content_hash}"
            image_id = hashlib.md5(combined.encode()).hexdigest()[:16]
            return f"img_{image_id}"
        except Exception:
            path_hash = hashlib.md5(image_path.encode()).hexdigest()[:16]
            return f"img_{path_hash}"

    @staticmethod
    def encode_image_to_base64(image_path: str) -> str:
        """图片转base64"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    @staticmethod
    def pdf_to_images(pdf_path: str, output_dir: str) -> List[str]:
        """PDF转图片"""
        os.makedirs(output_dir, exist_ok=True)
        doc = fitz.open(pdf_path)
        image_paths = []
        for i, page in enumerate(doc):
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img_path = os.path.join(output_dir, f"page_{i + 1}.png")
            pix.save(img_path)
            image_paths.append(img_path)
        doc.close()
        return image_paths