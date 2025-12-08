# file name: ocr_adapter.py
# -*- coding:utf-8 -*-
"""
OCR适配器层 - 统一不同OCR接口的数据格式
转换各种OCR结果到统一格式
"""
import json
from typing import Dict, Any, List
from backend.table_processor.table_image_utils import ImageUtils



class OCRAdapter:
    """OCR适配器 - 将不同OCR提供商的响应转换为统一格式"""

    # 在 ocr_adapter.py 的 OCRAdapter 类中修改：
    @staticmethod
    def adapt_baidu_response(baidu_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        适配百度OCR响应 - 修正版，支持真实百度格式
        """
        print("🔍 开始适配百度OCR响应...")
        print(f"[DEBUG] 百度OCR原始响应结构: {list(baidu_result.keys())}")

        unified_result = {
            "tables_result": [],
            "image_info": baidu_result.get("image_info", {}),
            "log_id": baidu_result.get("log_id", "")
        }

        # 🔥 关键：百度真实格式检查
        if "tables_result" in baidu_result:
            print(f"🔍 检测到百度tables_result字段，表格数: {len(baidu_result['tables_result'])}")
            tables_data = baidu_result["tables_result"]
        elif "forms_result" in baidu_result:
            print(f"🔍 检测到百度forms_result字段，表格数: {len(baidu_result['forms_result'])}")
            tables_data = baidu_result["forms_result"]
        else:
            print("⚠️ 百度OCR响应中没有表格数据字段")
            return unified_result

        # 处理每个表格
        for table_idx, table_data in enumerate(tables_data):
            print(f"🔍 处理表格 {table_idx}")

            unified_table = {"body": []}

            # 🔥 关键：检查body字段
            if "body" not in table_data:
                print(f"⚠️ 表格{table_idx}没有body字段，字段: {list(table_data.keys())}")
                unified_result["tables_result"].append(unified_table)
                continue

            body_cells = table_data.get("body", [])
            print(f"🔍 表格 {table_idx} 有 {len(body_cells)} 个body单元格")

            for cell in body_cells:
                # 🔥 关键：百度真实格式的字段名
                row_start = cell.get("row_start", cell.get("RowTl", 0))
                col_start = cell.get("col_start", cell.get("ColTl", 0))
                row_end = cell.get("row_end", cell.get("RowBr", 0))
                col_end = cell.get("col_end", cell.get("ColBr", 0))
                words = cell.get("words", cell.get("Text", cell.get("content", "")))
                confidence = cell.get("confidence", 1.0)

                # 调试输出
                if table_idx == 0 and len(unified_table["body"]) < 3:
                    print(f"  [DEBUG] 单元格格式: row_start={row_start}, col_start={col_start}, "
                          f"row_end={row_end}, col_end={col_end}, words='{words[:20]}...'")

                unified_cell = {
                    "row_start": row_start,
                    "col_start": col_start,
                    "row_end": row_end,
                    "col_end": col_end,
                    "words": words,
                    "confidence": confidence,
                    "type": "body"
                }

                unified_table["body"].append(unified_cell)

            unified_result["tables_result"].append(unified_table)

        print(f"✅ 百度OCR适配完成，共 {len(unified_result['tables_result'])} 个表格")
        return unified_result

    @staticmethod
    def adapt_tencent_response(tencent_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        适配腾讯OCR响应 - 修正版，支持真实腾讯格式
        """
        print("🔍 开始适配腾讯OCR响应...")

        unified_result = {
            "tables_result": [],
            "image_info": {},
            "log_id": tencent_result.get("RequestId", "")
        }

        # 🔥 关键：提取腾讯OCR的真实数据
        response_data = tencent_result.get("Response", {})
        if not response_data:
            print("⚠️ 腾讯OCR响应中没有Response字段")
            return unified_result

        # 查找真正的表格数据
        table_detections = None

        # 检查多个可能的字段
        if "TableDetections" in response_data:
            table_detections = response_data["TableDetections"]
            print(f"🔍 使用TableDetections字段，表格数: {len(table_detections)}")
        elif "Data" in response_data:
            # 如果数据在Data字段中（可能是base64编码的）
            data_str = response_data.get("Data", "")
            if data_str:
                try:
                    # 尝试解析base64数据
                    import base64
                    data_json = json.loads(base64.b64decode(data_str).decode('utf-8'))
                    if "TableDetections" in data_json:
                        table_detections = data_json["TableDetections"]
                        print(f"🔍 从Data字段解析TableDetections，表格数: {len(table_detections)}")
                except:
                    pass

        if not table_detections:
            print("⚠️ 腾讯OCR没有找到表格数据")
            return unified_result

        # 处理每个表格
        for table_idx, table_data in enumerate(table_detections):
            print(f"🔍 处理腾讯表格 {table_idx}")

            unified_table = {"body": []}

            # 提取单元格
            cells = table_data.get("Cells", [])
            print(f"🔍 腾讯表格 {table_idx} 有 {len(cells)} 个单元格")

            # 统计body类型单元格
            body_cells = [cell for cell in cells if cell.get("Type") == "body"]
            print(f"🔍 腾讯表格 {table_idx} 有 {len(body_cells)} 个body单元格")

            for cell in body_cells:
                # 🔥 关键：腾讯OCR的真实格式
                # 注意：腾讯使用 RowTl, ColTl, RowBr, ColBr
                row_tl = cell.get("RowTl", -1)
                col_tl = cell.get("ColTl", -1)
                row_br = cell.get("RowBr", -1)
                col_br = cell.get("ColBr", -1)

                # 如果上面字段不存在，尝试 Row, Col
                if row_tl == -1 or col_tl == -1:
                    row = cell.get("Row", 0)
                    col = cell.get("Col", 0)
                    row_span = cell.get("RowSpan", 1)
                    col_span = cell.get("ColSpan", 1)
                    row_tl = row
                    col_tl = col
                    row_br = row + row_span - 1
                    col_br = col + col_span - 1

                words = cell.get("Text", cell.get("Content", ""))
                confidence = cell.get("Confidence", 0) / 100.0

                # 调试输出
                if table_idx == 0 and len(unified_table["body"]) < 3:
                    print(f"  [DEBUG] 腾讯单元格: row_tl={row_tl}, col_tl={col_tl}, "
                          f"row_br={row_br}, col_br={col_br}, words='{words[:20]}...'")

                unified_cell = {
                    "row_start": row_tl,
                    "col_start": col_tl,
                    "row_end": row_br,
                    "col_end": col_br,
                    "words": words,
                    "confidence": confidence,
                    "type": "body"
                }

                unified_table["body"].append(unified_cell)

            unified_result["tables_result"].append(unified_table)

        print(f"✅ 腾讯OCR适配完成，共 {len(unified_result['tables_result'])} 个表格")
        return unified_result

    @staticmethod
    def validate_and_adapt(ocr_result: Dict[str, Any], provider: str) -> Dict[str, Any]:
        """
        智能验证和适配OCR结果 - 增强版，支持已适配的格式
        """
        print(f"🔍 开始智能适配 {provider} OCR结果")
        print(f"[DEBUG] {provider} OCR原始结果类型: {type(ocr_result)}")
        print(f"[DEBUG] {provider} OCR原始结果键: {list(ocr_result.keys())}")

        if not ocr_result:
            print("⚠️ OCR结果为空")
            return {"tables_result": [], "image_info": {}, "log_id": ""}

        # 🔥 关键：首先检查是否已经是适配后的格式
        if "tables_result" in ocr_result:
            print(f"🔍 检测到已适配的格式（有tables_result字段）")

            # 已经是统一格式，直接返回（但确保格式完整）
            unified_result = ocr_result.copy()

            # 确保必需字段存在
            if "image_info" not in unified_result:
                unified_result["image_info"] = {}

            if "log_id" not in unified_result:
                unified_result["log_id"] = ""

            print(f"✅ 直接使用已适配格式，有 {len(unified_result.get('tables_result', []))} 个表格")
            return unified_result

        # 🔥 如果不是已适配格式，才进行转换
        if provider == "baidu":
            # 检查百度原始格式
            if "tables_result" in ocr_result or "forms_result" in ocr_result:
                result = OCRAdapter.adapt_baidu_response(ocr_result)
            else:
                print(f"⚠️ 百度OCR没有表格数据，检查结构: {list(ocr_result.keys())}")
                result = {"tables_result": [], "image_info": {}, "log_id": ""}

        elif provider == "tencent":
            # 检查腾讯原始格式
            if "Response" in ocr_result:
                response_data = ocr_result["Response"]
                if "TableDetections" in response_data or "Data" in response_data:
                    result = OCRAdapter.adapt_tencent_response(ocr_result)
                else:
                    print(f"⚠️ 腾讯OCR Response中没有表格数据字段")
                    result = {"tables_result": [], "image_info": {}, "log_id": ""}
            elif "TableDetections" in ocr_result:
                # 🔥 新情况：直接有TableDetections字段（没有Response包装）
                print(f"🔍 检测到腾讯OCR直接TableDetections格式")
                # 包装成Response格式进行适配
                wrapped_result = {"Response": ocr_result}
                result = OCRAdapter.adapt_tencent_response(wrapped_result)
            else:
                print(f"⚠️ 腾讯OCR格式无法识别")
                result = {"tables_result": [], "image_info": {}, "log_id": ""}

        else:
            raise ValueError(f"不支持的OCR提供商: {provider}")

        # 确保必需字段存在
        if "tables_result" not in result:
            print("⚠️ 适配后添加缺失的tables_result字段")
            result["tables_result"] = []

        if "image_info" not in result:
            print("⚠️ 适配后添加缺失的image_info字段")
            result["image_info"] = {}

        if "log_id" not in result:
            result["log_id"] = ""

        print(f"✅ {provider} OCR适配完成，有 {len(result.get('tables_result', []))} 个表格")

        # 调试输出
        for i, table in enumerate(result.get("tables_result", [])):
            cells = table.get("body", [])
            print(f"  表格{i}: {len(cells)}个单元格")

        return result


class OCRProviderFactory:
    """OCR提供商工厂"""

    @staticmethod
    def create_provider(provider_type: str, config: Any):
        """
        创建OCR服务提供商
        """
        if provider_type == "baidu":
            return BaiduOCRProvider(config)
        elif provider_type == "tencent":
            return TencentOCRProvider(config)
        else:
            raise ValueError(f"不支持的OCR提供商: {provider_type}")


class BaseOCRProvider:
    """OCR提供商基类"""

    def __init__(self, config):
        self.config = config
        self.timeout = config.ocr_timeout

    def recognize(self, image_path: str) -> Dict[str, Any]:
        """识别表格 - 子类必须实现"""
        raise NotImplementedError


class BaiduOCRProvider(BaseOCRProvider):
    """百度OCR提供商"""

    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.ocr_api_key
        self.secret_key = config.ocr_secret_key
        self.access_token = None
        self.session = None
        # 移除原有的导入依赖，改为直接实现

    # 修改 BaiduOCRProvider 类的 _baidu_ocr_logic 方法
    def _baidu_ocr_logic(self, image_path: str) -> Dict[str, Any]:
        """独立的百度OCR逻辑 - 修正版"""
        import os
        import time
        import requests
        import base64
        import urllib.parse

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片不存在: {image_path}")

        # 1. 获取access_token
        def get_token():
            url = "https://aip.baidubce.com/oauth/2.0/token"
            params = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key
            }

            session = requests.Session()
            response = session.post(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return data.get("access_token")

        # 2. 图片转base64
        def image_to_base64(file_path: str, urlencoded: bool = True) -> str:
            with open(file_path, "rb") as f:
                content = base64.b64encode(f.read()).decode("utf8")
                if urlencoded:
                    content = urllib.parse.quote_plus(content)
            return content

        # 3. 调用百度OCR API - 修正为正确的表格OCR API
        try:
            access_token = get_token()
            if not access_token:
                raise Exception("获取token失败")

            image_content = image_to_base64(image_path)

            # 使用正确的表格OCR API
            url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/table?access_token={access_token}"
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }

            # 简化payload
            payload = f'image={image_content}'

            start_time = time.time()
            response = requests.post(url, headers=headers, data=payload, timeout=self.timeout)
            elapsed_time = time.time() - start_time

            if response.status_code != 200:
                raise Exception(f"百度OCR请求失败: {response.status_code}")

            result = response.json()

            # 检查错误
            if 'error_code' in result:
                error_msg = result.get('error_msg', '未知错误')
                raise Exception(f"百度OCR识别错误: {error_msg}")

            # 4. 确保结果格式正确
            # 添加统计信息
            if 'orc_statistics' not in result:
                result['orc_statistics'] = {
                    'processing_time': elapsed_time,
                    'tables_count': len(result.get('forms_result', [])),
                    'cells_count': sum(len(form.get('body', [])) for form in result.get('forms_result', []))
                }

            # 确保有forms_result字段
            if 'forms_result' not in result:
                result['forms_result'] = []

            return result

        except Exception as e:
            raise Exception(f"百度OCR识别失败: {str(e)}")


    def recognize(self, image_path: str) -> Dict[str, Any]:
        """百度OCR识别实现"""
        # 调用独立逻辑
        raw_result = self._baidu_ocr_logic(image_path)



        # 适配器处理
        adapter = OCRAdapter()
        print("baidu--------------->>>:")
        print("raw_result:", raw_result)
        return adapter.adapt_baidu_response(raw_result)



class TencentOCRProvider(BaseOCRProvider):
    """腾讯OCR提供商 - 完整实现"""

    def __init__(self, config):
        super().__init__(config)
        self.secret_id = config.tencent_secret_id
        self.secret_key = config.tencent_secret_key
        self.region = config.tencent_region

        if not self.secret_id or not self.secret_key:
            raise ValueError("腾讯OCR配置缺失: secret_id 或 secret_key")

        # 初始化腾讯云客户端
        self.client = self._init_tencent_client()

    def _init_tencent_client(self):
        """初始化腾讯云OCR客户端"""
        try:
            # 动态导入，避免没有安装tencentcloud包时报错
            from tencentcloud.common import credential
            from tencentcloud.common.profile.client_profile import ClientProfile
            from tencentcloud.common.profile.http_profile import HttpProfile
            from tencentcloud.ocr.v20181119 import ocr_client

            # 创建凭证对象
            cred = credential.Credential(self.secret_id, self.secret_key)

            # 创建HTTP配置
            httpProfile = HttpProfile()
            httpProfile.endpoint = "ocr.tencentcloudapi.com"

            # 创建客户端配置
            clientProfile = ClientProfile()
            clientProfile.httpProfile = httpProfile

            # 创建OCR客户端
            client = ocr_client.OcrClient(cred, self.region, clientProfile)
            return client

        except ImportError:
            raise ImportError("请安装腾讯云SDK: pip install tencentcloud-sdk-python")
        except Exception as e:
            raise Exception(f"初始化腾讯云客户端失败: {e}")

    def _generate_image_id(self, file_path: str) -> str:
        """生成图片ID - 独立实现"""
        import hashlib
        file_hash = hashlib.md5(file_path.encode()).hexdigest()[:12]
        return f"img_{file_hash}"

    def recognize(self, image_path: str) -> Dict[str, Any]:
        """腾讯OCR识别实现"""
        import base64
        import os
        import time
        from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
        from tencentcloud.ocr.v20181119 import models

        print(f"[TencentOCR] 开始识别表格: {image_path}")

        try:
            # 将图片转换为base64
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')

            # 构建请求参数
            req_params = {
                "ImageBase64": image_base64,
                "TableOptions": {
                    "ReturnExcel": False,
                    "ReturnImage": False
                }
            }

            # 发送请求
            req = models.RecognizeTableOCRRequest()
            req.from_json_string(json.dumps(req_params))

            start_time = time.time()
            resp = self.client.RecognizeTableOCR(req)
            elapsed_time = time.time() - start_time

            print(f"[TencentOCR] 识别完成，耗时: {elapsed_time:.2f}秒")

            # 转换为字典
            raw_result = json.loads(resp.to_json_string())

            # 🔥 添加调试输出
            print("=" * 50)
            print("[DEBUG] 腾讯OCR原始响应结构:")
            print(f"Response 字段: {'Response' in raw_result}")
            if 'Response' in raw_result:
                response_data = raw_result['Response']
                print(f"TableDetections 字段: {'TableDetections' in response_data}")
                if 'TableDetections' in response_data:
                    tables = response_data['TableDetections']
                    print(f"表格数量: {len(tables)}")
                    for i, table in enumerate(tables):
                        cells = table.get('Cells', [])
                        print(f"  表格{i}: {len(cells)}个单元格")
                        if cells:
                            print(f"    第一个单元格: {cells[0]}")
            print("=" * 50)

            # 使用适配器转换为统一格式
            adapter = OCRAdapter()
            unified_result = adapter.validate_and_adapt(raw_result, "tencent")

            # 确保包含图片信息
            unified_result["image_info"] = {
                "image_path": image_path,
                "image_id": self._generate_image_id(image_path)
            }

            # 添加统计信息
            if "orc_statistics" not in unified_result:
                unified_result["orc_statistics"] = {
                    "processing_time": elapsed_time,
                    "tables_count": len(unified_result.get("tables_result", [])),
                    "cells_count": sum(len(table.get("body", [])) for table in unified_result.get("tables_result", []))
                }

            return unified_result

        except TencentCloudSDKException as e:
            print(f"[TencentOCR] SDK异常: {e}")
            raise Exception(f"腾讯OCR识别失败: {e}")
        except Exception as e:
            print(f"[TencentOCR] 其他异常: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"腾讯OCR处理失败: {e}")

