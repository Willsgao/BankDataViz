# -*- coding:utf-8 -*-
import os
import hashlib
import base64
from typing import List
import fitz  # PyMuPDF


class TableImageUtils:
    @staticmethod
    def generate_image_id(file_path: str) -> str:
        """生成图片唯一ID"""
        file_hash = hashlib.md5(file_path.encode()).hexdigest()[:12]
        return f"img_{file_hash}"

    @staticmethod
    def encode_image_to_base64(image_path: str) -> str:
        """图片转base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    @staticmethod
    def pdf_to_images(pdf_path: str, output_dir: str, dpi: int = 150) -> List[str]:
        """PDF转图片"""
        os.makedirs(output_dir, exist_ok=True)
        image_paths = []

        pdf_document = fitz.open(pdf_path)
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            pix = page.get_pixmap(dpi=dpi)
            image_path = os.path.join(output_dir, f"page_{page_num + 1}.png")
            pix.save(image_path)
            image_paths.append(image_path)

        pdf_document.close()
        return image_paths