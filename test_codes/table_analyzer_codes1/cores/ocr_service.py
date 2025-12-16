# -*- coding:utf-8 -*-

import os
import requests
import base64
import urllib.parse
from typing import Dict, Any, List

from backend.services.table_processor import ImageUtils
from backend.services.table_processor._config_shim import settings


class TableOCRService:
    def __init__(self):
        self.image_utils = ImageUtils()
        self.api_key = settings.ocr_api_key
        self.secret_key = settings.ocr_secret_key
        self.timeout = settings.ocr_timeout

        if not self.api_key or not self.secret_key:
            raise ValueError("OCR API配置错误")

        self.access_token = None
        self.session = requests.Session()

    def _get_access_token(self) -> str:
        if self.access_token:
            return self.access_token

        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }

        response = self.session.post(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        self.access_token = data.get("access_token")

        if not self.access_token:
            raise Exception("获取token失败")

        return self.access_token

    def _image_to_base64(self, file_path: str, urlencoded: bool = True) -> str:
        with open(file_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf8")
            if urlencoded:
                content = urllib.parse.quote_plus(content)
        return content

    def recognize_table(self, image_path: str) -> Dict[str, Any]:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片不存在: {image_path}")

        image_base64 = self._image_to_base64(image_path)
        token = self._get_access_token()

        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/table?access_token={token}"
        payload = f'image={image_base64}'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        response = self.session.post(url, headers=headers, data=payload.encode("utf-8"), timeout=self.timeout)
        response.encoding = "utf-8"
        response.raise_for_status()

        result = response.json()
        result["image_info"] = {
            "image_path": image_path,
            "image_id": self.image_utils.generate_image_id(image_path)
        }

        return result

    def batch_recognize(self, image_paths: List[str]) -> Dict[str, Any]:
        results = {
            "total_images": len(image_paths),
            "success_count": 0,
            "failed_count": 0,
            "image_results": []
        }

        for img_path in image_paths:
            try:
                ocr_result = self.recognize_table(img_path)
                results["image_results"].append({
                    "success": True,
                    "image_path": img_path,
                    "ocr_result": ocr_result
                })
                results["success_count"] += 1
            except Exception as e:
                results["image_results"].append({
                    "success": False,
                    "image_path": img_path,
                    "error": str(e)
                })
                results["failed_count"] += 1

        return results