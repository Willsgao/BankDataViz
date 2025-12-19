# backend/src/services/table_processor/ocr_gateway.py
# -*- coding:utf-8 -*-

import os
import json
import base64
import urllib.parse
import time
import hashlib
import gzip
import uuid
from io import BytesIO
from typing import Dict, Any, List
from pathlib import Path

import requests
import redis

from backend.src.services.table_processor.image_utils import TableImageUtils
from backend.utils.config import tableconfig as settings
from backend.src.services.table_processor.ocr_service import OCRProviderFactory, OCRAdapter

# 导入缓存相关模块
from .cache_gateway import ensure_table, get as cache_get, upsert as cache_upsert
from .object_store import get_object, put_object

# Redis连接 - 移到模块级别，避免重复创建
_redis = None


def get_redis_client():
    """获取Redis客户端（单例）"""
    global _redis
    if _redis is None:
        _redis = redis.Redis(
            host=os.getenv("REDIS_HOST", "127.0.0.1"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=0, decode_responses=False
        )
    return _redis


class TableOCRService:
    def __init__(self, provider_type: str = None):
        """
        初始化OCR服务
        Args:
            provider_type: OCR提供商类型，默认为配置中的设置
        """
        self.image_utils = TableImageUtils()

        # 确定使用的OCR提供商
        self.provider_type = provider_type or getattr(settings, 'ocr_provider', 'baidu')

        print(f"初始化OCR服务，使用提供商: {self.provider_type}")

        # 创建OCR提供商实例
        try:
            self.ocr_provider = OCRProviderFactory.create_provider(self.provider_type, settings)
        except Exception as e:
            print(f"⚠️ 创建OCR提供商失败: {e}，回退到百度OCR")
            # 回退到百度OCR
            self.provider_type = 'baidu'
            self.ocr_provider = OCRProviderFactory.create_provider('baidu', settings)

        # 适配器实例
        self.adapter = OCRAdapter()

        print(f"✅ OCR服务初始化完成，使用: {self.provider_type}")

    def _get_access_token(self) -> str:
        """获取百度OCR访问令牌 - 兼容原有代码"""
        # 注意：这个方法可能不再需要，因为OCR提供商已经封装了token获取
        if not hasattr(settings, 'ocr_api_key') or not hasattr(settings, 'ocr_secret_key'):
            raise ValueError("百度OCR API配置错误")

        api_key = getattr(settings, 'ocr_api_key', '')
        secret_key = getattr(settings, 'ocr_secret_key', '')

        if hasattr(self, 'access_token') and self.access_token:
            return self.access_token

        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": secret_key
        }

        session = requests.Session()
        response = session.post(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        self.access_token = data.get("access_token")

        if not self.access_token:
            raise Exception("获取token失败")

        return self.access_token

    def _image_to_base64(self, file_path: str, urlencoded: bool = True) -> str:
        """图片转base64 - 兼容原有代码"""
        with open(file_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf8")
            if urlencoded:
                content = urllib.parse.quote_plus(content)
        return content

    def batch_recognize(self, image_paths: List[str]) -> Dict[str, Any]:
        """
        批量识别 - 兼容原有接口
        """
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

    def recognize_table_baidu(self, image_path: str) -> Dict[str, Any]:
        """
        直接使用百度OCR识别（保持原有实现）
        """
        # 临时切换回百度OCR
        original_provider = self.provider_type
        self.provider_type = "baidu"
        self.ocr_provider = OCRProviderFactory.create_provider("baidu", settings)

        try:
            result = self.recognize_table(image_path)
            return result
        finally:
            # 恢复原始提供商
            self.provider_type = original_provider
            self.ocr_provider = OCRProviderFactory.create_provider(original_provider, settings)

    def recognize_table(self, image_path: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        识别表格 - 主入口方法，增强错误处理
        三级缓存：Redis → DB → 盘；成功写盘+写库+写Redis
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片不存在: {image_path}")

        print(f"使用 {self.provider_type} OCR识别: {image_path}")

        # 计算图片MD5
        with open(image_path, "rb") as f:
            md5 = hashlib.md5(f.read()).hexdigest()

        # 获取Redis客户端
        redis_client = get_redis_client()

        # ----- 1. 三级缓存命中（Redis → DB → 盘） -----
        if not (getattr(settings, 'OCR_FORCE_REFRESH', False) or force_refresh):
            # 1) Redis
            try:
                cached = redis_client.get(f"ocr:{md5}")
                if cached:
                    print("OCR Redis hit")
                    return json.loads(gzip.decompress(cached))
            except Exception as e:
                print(f"Redis读取失败: {e}，继续尝试其他缓存")

            # 2) DB + 盘存在性检查
            hit = cache_get(md5, self.provider_type)
            if hit:
                # 获取本地对象存储路径
                local_store_path = getattr(settings, 'LOCAL_OBJECT_STORE', 'data/backend/obj_cache')
                file_path = Path(local_store_path) / hit["s3_key"]
                if file_path.exists():
                    try:
                        data = json.loads(gzip.decompress(file_path.read_bytes()))
                        # 回写 Redis（24h TTL）
                        redis_client.set(f"ocr:{md5}", gzip.compress(json.dumps(data).encode()), ex=86400)
                        print("OCR cache hit, skip cost")
                        return data
                    except Exception as e:
                        print(f"缓存文件读取失败: {e}")

        # ----- 2. 真调用 -----
        try:
            ocr_result = self.ocr_provider.recognize(image_path)

            # 调试：保存原始响应到 data/backend/ocr_raw
            if getattr(settings, 'debug_ocr', False):
                raw_dir = getattr(settings, 'OCR_RAW_DIR', 'data/backend/ocr_raw')
                os.makedirs(raw_dir, exist_ok=True)

                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"{self.provider_type}_ocr_raw_{timestamp}_{uuid.uuid4().hex[:8]}.json"
                raw_path = os.path.join(raw_dir, filename)

                with open(raw_path, "w", encoding="utf-8") as f:
                    json.dump(ocr_result, f, ensure_ascii=False, indent=2)
                print(f"原始响应已保存到: {raw_path}")

            # 适配和验证结果
            ocr_result = self.adapter.validate_and_adapt(ocr_result, self.provider_type)

            if "image_info" not in ocr_result:
                ocr_result["image_info"] = {
                    "image_path": image_path,
                    "image_id": self.image_utils.generate_image_id(image_path)
                }

            if "orc_statistics" not in ocr_result:
                ocr_result["orc_statistics"] = {
                    "processing_time": 0,
                    "tables_count": len(ocr_result.get('tables_result', [])),
                    "cells_count": sum(len(table.get('body', [])) for table in ocr_result.get('tables_result', []))
                }

            print(f"✅ OCR识别成功，找到 {len(ocr_result.get('tables_result', []))} 个表格")

            # 调试：保存最终结果到 data/backend/ocr_final
            if getattr(settings, 'debug_ocr', False) and getattr(settings, 'debug_ocr_keep_mb', 0) > 0:
                final_dir = getattr(settings, 'OCR_FINAL_DIR', 'data/backend/ocr_final')
                os.makedirs(final_dir, exist_ok=True)

                timestamp = time.strftime("%Y%m%d_%H%M%S")
                final_filename = f"{self.provider_type}_ocr_final_{timestamp}_{uuid.uuid4().hex[:8]}.json"
                final_path = os.path.join(final_dir, final_filename)

                with open(final_path, "w", encoding="utf-8") as f:
                    json.dump(ocr_result, f, ensure_ascii=False, indent=2)
                print(f"最终OCR结果已保存到: {final_path}")

            # ----- 3. 成功落盘 + 写库 + 写 Redis -----
            compressed = gzip.compress(json.dumps(ocr_result).encode())
            s3_key = f"ocr/{md5}.json.gz"
            put_object(s3_key, compressed)
            cost_usd = 0.0  # 可按官方价计算
            cache_upsert(md5, self.provider_type, self.provider_type,
                         cost_usd, 0, 0, s3_key)
            redis_client.set(f"ocr:{md5}", compressed, ex=86400)  # 写内存 24h

            return ocr_result

        except Exception as e:
            print(f"❌ {self.provider_type} OCR识别失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"OCR识别失败: {str(e)}")


# 测试代码
if __name__ == '__main__':
    # 初始化缓存表
    ensure_table()

    # 测试代码
    service = TableOCRService()
    test_image = "test.png"  # 修改为你的测试图片路径

    if os.path.exists(test_image):
        try:
            result = service.recognize_table(test_image)
            print(f"OCR识别成功，表格数量: {len(result.get('tables_result', []))}")
        except Exception as e:
            print(f"OCR识别失败: {e}")
    else:
        print(f"测试图片不存在: {test_image}")