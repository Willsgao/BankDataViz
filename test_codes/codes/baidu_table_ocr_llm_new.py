import os
import requests
import json
import hashlib
import base64
import urllib
from typing import Dict, Any, List

# from backend.utils.constants import BAIDU_OCR_CONFIG, BAIDU_APP_CONFIG
BAIDU_OCR_CONFIG = {
    "API_KEY": "Id7EZH2q6IOSlivHbwHHbWwz",
    "SECRET_KEY": "leeZiDapOBp6nGZssuuzABgSZubNgSLu"
}
# 其他应用配置
BAIDU_APP_CONFIG = {
    "TIMEOUT": 30,
    "MAX_RETRIES": 3
}


class TableOCRService:
    """表格OCR识别服务类，用于识别图片中的Excel表格数据，支持图片ID"""

    def __init__(self, api_key: str = None, secret_key: str = None, timeout: int = None, max_retries: int = None):
        # 初始化代码保持不变...
        self.api_key = api_key or BAIDU_OCR_CONFIG.get("API_KEY")
        self.secret_key = secret_key or BAIDU_OCR_CONFIG.get("SECRET_KEY")
        self.timeout = timeout or BAIDU_APP_CONFIG.get("TIMEOUT", 30)
        self.max_retries = max_retries or BAIDU_APP_CONFIG.get("MAX_RETRIES", 3)

        if not self.api_key or not self.secret_key:
            raise ValueError("API_KEY和SECRET_KEY不能为空，请检查配置文件")

        self.access_token = None
        self.session = requests.Session()

        adapter = requests.adapters.HTTPAdapter(max_retries=self.max_retries)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def _generate_image_id(self, image_path: str) -> str:
        """
        为图片生成唯一ID（与LLM分析器保持一致）
        """
        try:
            with open(image_path, "rb") as f:
                file_content = f.read()
            content_hash = hashlib.md5(file_content).hexdigest()[:16]

            file_name = os.path.basename(image_path)
            combined = f"{file_name}_{content_hash}"
            image_id = hashlib.md5(combined.encode()).hexdigest()[:16]

            return f"img_{image_id}"

        except Exception as e:
            path_hash = hashlib.md5(image_path.encode()).hexdigest()[:16]
            return f"img_{path_hash}"

    def get_access_token(self) -> str:
        """
        获取访问令牌

        Returns:
            access_token字符串

        Raises:
            Exception: 获取token失败时抛出异常
        """
        if self.access_token:
            return self.access_token

        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }

        try:
            response = self.session.post(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            self.access_token = data.get("access_token")

            if not self.access_token:
                raise Exception(f"Failed to get access token: {data}")

            return self.access_token

        except requests.exceptions.RequestException as e:
            raise Exception(f"获取access_token请求失败: {e}")

    @staticmethod
    def get_file_content_as_base64(file_path: str, urlencoded: bool = False) -> str:
        """
        获取文件base64编码

        Args:
            file_path: 文件路径
            urlencoded: 是否对结果进行urlencoded

        Returns:
            base64编码信息

        Raises:
            FileNotFoundError: 文件不存在时抛出异常
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        with open(file_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf8")
            if urlencoded:
                content = urllib.parse.quote_plus(content)
        return content

    def recognize_table_from_file(self, file_path: str, urlencoded: bool = True) -> Dict[str, Any]:
        """
        从图片文件识别表格，包含图片ID信息
        """
        image_base64 = self.get_file_content_as_base64(file_path, urlencoded)
        result = self.recognize_table_from_base64(image_base64)

        # 添加图片ID到结果中
        image_id = self._generate_image_id(file_path)
        result["image_info"] = {
            "image_path": file_path,
            "image_id": image_id
        }

        return result

    def recognize_table_from_base64(self, image_base64: str) -> Dict[str, Any]:
        """
        从base64编码识别表格

        Args:
            image_base64: 图片的base64编码

        Returns:
            识别结果字典

        Raises:
            Exception: 识别失败时抛出异常
        """
        url = "https://aip.baidubce.com/rest/2.0/ocr/v1/table?access_token=" + self.get_access_token()

        payload = f'image={image_base64}'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        try:
            response = self.session.post(url, headers=headers, data=payload.encode("utf-8"), timeout=self.timeout)
            response.encoding = "utf-8"
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            raise Exception(f"表格识别请求失败: {e}")

    def recognize_table_from_bytes(self, image_bytes: bytes, urlencoded: bool = True) -> Dict[str, Any]:
        """
        从字节数据识别表格

        Args:
            image_bytes: 图片字节数据
            urlencoded: 是否对图片进行url编码

        Returns:
            识别结果字典
        """
        content = base64.b64encode(image_bytes).decode("utf8")
        if urlencoded:
            content = urllib.parse.quote_plus(content)

        return self.recognize_table_from_base64(content)

    def batch_recognize_tables(self, image_paths: List[str]) -> Dict[str, Any]:
        """
        批量识别多张图片的表格

        Args:
            image_paths: 图片路径列表

        Returns:
            包含所有图片识别结果的字典
        """
        all_results = {
            "total_images": len(image_paths),
            "image_results": [],
            "summary": {
                "success_count": 0,
                "failed_count": 0,
                "total_tables": 0
            }
        }

        for img_path in image_paths:
            try:
                result = self.recognize_table_from_file(img_path)
                tables_count = len(result.get("tables_result", []))

                image_result = {
                    "image_path": img_path,
                    "image_id": result["image_info"]["image_id"],
                    "tables_result": result.get("tables_result", []),
                    "tables_count": tables_count,
                    "success": True
                }
                all_results["image_results"].append(image_result)

                all_results["summary"]["success_count"] += 1
                all_results["summary"]["total_tables"] += tables_count

                print(
                    f"✅ 图片 {os.path.basename(img_path)} (ID: {result['image_info']['image_id']}) 识别完成，检测到 {tables_count} 个表格")

            except Exception as e:
                print(f"❌ 图片 {os.path.basename(img_path)} 识别失败: {e}")

                # 即使失败也生成图片ID
                image_id = self._generate_image_id(img_path)
                image_result = {
                    "image_path": img_path,
                    "image_id": image_id,
                    "tables_result": [],
                    "tables_count": 0,
                    "success": False,
                    "error": str(e)
                }
                all_results["image_results"].append(image_result)
                all_results["summary"]["failed_count"] += 1

        return all_results

    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()

    def save_result_to_json(self, result: Dict[str, Any], save_path: str) -> None:
        """
        将识别结果保存为 JSON 文件
        """
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f'结果已保存至: {save_path}')


# 使用示例
if __name__ == '__main__':
    # 方式1: 使用配置文件中的默认参数
    ocr_service = TableOCRService()

    # 方式2: 覆盖部分配置参数
    # ocr_service = TableOCRService(timeout=60, max_retries=5)

    page_file = r"E:\Datas\base_pros\DocuVista\test_codes/pngs/514001_142.png"
    save_json = r"E:\Datas\base_pros\DocuVista\test_codes/data3.json"

    try:
        # 从文件识别表格
        result = ocr_service.recognize_table_from_file(page_file)
        ocr_service.save_result_to_json(result, save_json)
        print("识别结果:", result)

    except Exception as e:
        print(f"识别失败: {e}")

    finally:
        # 关闭会话
        ocr_service.close()