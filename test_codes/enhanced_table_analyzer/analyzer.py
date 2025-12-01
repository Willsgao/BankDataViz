# -*- coding:utf-8 -*-


import os
import re
import time
import json
from typing import List, Dict, Any, Union
from openai import OpenAI

from test_codes.enhanced_table_analyzer.utils.image_utils import ImageUtils
from test_codes.enhanced_table_analyzer.utils.ocr_processor import OCRProcessor
from test_codes.enhanced_table_analyzer.config import settings
from test_codes.enhanced_table_analyzer.ocr_service import TableOCRService


class FinancialTableAnalyzer:
    def __init__(self):
        self.image_utils = ImageUtils()
        self.client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key
        )
        self.model_name = settings.llm_model_name
        self.extract_rows = settings.extract_rows
        self.extract_cols = settings.extract_cols

    def _build_system_prompt111(self, ocr_data: Dict[str, Any]) -> str:
        """构建系统提示词"""
        dimensions = ocr_data.get("dimensions", {})
        rows, cols = dimensions.get("rows", 0), dimensions.get("cols", 0)

        top_rows = ocr_data.get("extracted_data", {}).get("top_rows_all_cols", [])
        left_cols = ocr_data.get("extracted_data", {}).get("left_cols_all_rows", [])

        # 格式化提取的数据
        top_rows_text = "\n".join([f"行{i + 1}: {' | '.join(row)}" for i, row in enumerate(top_rows)])
        left_cols_text = "\n".join([f"行{i + 1}: {' | '.join(row[:3])}" for i, row in enumerate(left_cols[:10])])
        if len(left_cols) > 10:
            left_cols_text += f"\n... (还有{len(left_cols) - 10}行)"

        return f"""
你是一名专业的金融表格分析师。请分析以下表格：

【表格信息】
表格尺寸：{rows}行 × {cols}列
OCR提取了前{self.extract_rows}行所有{cols}列 + 前{self.extract_cols}列所有{rows}行数据。

【OCR提取数据】
1. 前{self.extract_rows}行所有列：
{top_rows_text}

2. 前{self.extract_cols}列所有行：
{left_cols_text}

【次要检查】
1. OCR报告有多少个表格？图片中实际有多少个表格？
2. OCR提取的文字与图片显示是否一致？

【主要任务】
识别表格的表头层级结构，包括横向表头和纵向表头。

【输出要求】
只输出JSON，格式如下：
{{
  "table_headers": {{
    "horizontal": [{{"field_path": "层级路径", "is_statistical": bool}}],
    "vertical": [{{"field_path": "层级路径", "is_statistical": bool}}]
  }},
  "consistency_checks": {{
    "table_count": {{"ocr_reported": int, "visual_observed": int, "match": bool, "needs_human": bool}},
    "text_vs_visual": {{"match": bool, "needs_human": bool}}
  }}
}}
"""

    def _build_system_prompt(self, ocr_data: Dict[str, Any]) -> str:
        """构建系统提示词 - 修改版"""
        dimensions = ocr_data.get("dimensions", {})
        rows, cols = dimensions.get("rows", 0), dimensions.get("cols", 0)

        top_rows = ocr_data.get("extracted_data", {}).get("top_rows_all_cols", [])
        left_cols = ocr_data.get("extracted_data", {}).get("left_cols_all_rows", [])

        # 格式化提取的数据
        top_rows_text = "\n".join([f"行{i + 1}: {' | '.join(row)}" for i, row in enumerate(top_rows)])
        left_cols_text = "\n".join([f"行{i + 1}: {' | '.join(row[:3])}" for i, row in enumerate(left_cols[:10])])
        if len(left_cols) > 10:
            left_cols_text += f"\n... (还有{len(left_cols) - 10}行)"

        return f"""
    你是一名专业的金融表格分析师。请分析以下表格：

    【表格信息】
    表格尺寸：{rows}行 × {cols}列
    OCR提取了前{self.extract_rows}行所有{cols}列 + 前{self.extract_cols}列所有{rows}行数据。

    【OCR提取数据】
    1. 前{self.extract_rows}行所有列：
    {top_rows_text}

    2. 前{self.extract_cols}列所有行：
    {left_cols_text}

    【主要任务】
    1. 识别表格的表头层级结构，包括横向表头和纵向表头
    2. 明确指出哪些行是表头行（需要被删除），哪些列是表头列（需要被删除）
    3. 提供新的合并后的表头结构

    【表头特征分析要求】
    1. 横向表头行分析：前3行中哪些行是表头行？如果是多级表头，需要合并
    2. 纵向表头列分析：前3列中哪些列是表头列？
    3. 提供原始表头需要删除的行数和列数

    【输出要求】
    只输出JSON，格式如下：
    {{
      "table_headers": {{
        "horizontal": [{{"field_path": "层级路径", "is_statistical": bool, "is_header": bool}}],
        "vertical": [{{"field_path": "层级路径", "is_statistical": bool, "is_header": bool}}],
        "header_positions": {{
          "horizontal_header_rows": [行索引列表],  // 从0开始，哪些行需要被删除
          "vertical_header_cols": [列索引列表],    // 从0开始，哪些列需要被删除
          "horizontal_header_depth": int,          // 水平表头行数
          "vertical_header_depth": int            // 垂直表头列数
        }}
      }},
      "consistency_checks": {{
        "table_count": {{"ocr_reported": int, "visual_observed": int, "match": bool, "needs_human": bool}},
        "text_vs_visual": {{"match": bool, "needs_human": bool}}
      }}
    }}

    【重要说明】
    - horizontal_header_rows：指定需要被删除的原始表头行索引
    - vertical_header_cols：指定需要被删除的原始表头列索引
    - 新的表头应该替换这些被删除的原始表头
    """




    def _call_llm(self, base64_image: str, prompt: str) -> tuple[str, Dict[str, int], float]:
        """调用LLM API"""
        start_time = time.time()

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ]
            }],
            temperature=0.1
        )

        elapsed = time.time() - start_time
        content = response.choices[0].message.content.strip()

        usage = response.usage if hasattr(response, 'usage') else None
        usage_dict = {
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0
        }

        return content, usage_dict, elapsed

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            cleaned = re.sub(r'^```json\s*|\s*```$', '', response_text.strip())
            data = json.loads(cleaned)
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {e}\n响应内容: {response_text[:200]}")

    def analyze_table(self, image_path: str, ocr_result: Dict[str, Any], table_index: int = 0) -> Dict[str, Any]:
        """分析单个表格"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片不存在: {image_path}")

        tables = ocr_result.get("tables_result", [])
        if table_index >= len(tables):
            raise ValueError(f"表格索引{table_index}超出范围")

        # 提取OCR数据
        table_data = tables[table_index]
        ocr_extract = OCRProcessor.extract_for_llm(
            table_data,
            extract_rows=self.extract_rows,
            extract_cols=self.extract_cols
        )

        if not ocr_extract["success"]:
            return {"success": False, "error": ocr_extract.get("error")}

        # 调用LLM
        base64_image = self.image_utils.encode_image_to_base64(image_path)
        prompt = self._build_system_prompt(ocr_extract)
        llm_response, usage, elapsed = self._call_llm(base64_image, prompt)
        analysis_result = self._parse_llm_response(llm_response)

        # 构建完整结果
        image_info = ocr_result.get("image_info", {})
        table_count = ocr_result.get("table_num", 0)

        return {
            "success": True,
            "image_info": image_info,
            "table_info": {
                "table_id": table_index + 1,
                "table_index": table_index,
                "dimensions": ocr_extract["dimensions"],
                "ocr_reported_tables": table_count
            },
            "analysis_result": analysis_result,
            "processing_stats": {
                "analysis_time_sec": round(elapsed, 2),
                "token_usage": usage
            },
            "source_data": {
                "ocr_extract": ocr_extract,
                "raw_llm_response": llm_response
            }
        }

    def analyze_image(self, image_path: str, ocr_service: TableOCRService = None) -> Dict[str, Any]:
        """分析单张图片"""
        # 如果没有传入OCR服务，创建新的
        if ocr_service is None:
            ocr_service = TableOCRService()

        # OCR识别
        ocr_result = ocr_service.recognize_table(image_path)
        tables_count = ocr_result.get("table_num", 0)

        results = {
            "image_path": image_path,
            "image_id": ocr_result["image_info"]["image_id"],
            "tables_count": tables_count,
            "tables_analysis": []
        }

        # 分析每个表格
        for i in range(tables_count):
            try:
                table_result = self.analyze_table(image_path, ocr_result, i)
                results["tables_analysis"].append(table_result)
            except Exception as e:
                results["tables_analysis"].append({
                    "success": False,
                    "table_index": i,
                    "error": str(e)
                })

        # 汇总统计
        success_count = sum(1 for t in results["tables_analysis"] if t.get("success"))
        results["summary"] = {
            "total_tables": tables_count,
            "successfully_analyzed": success_count,
            "failed": tables_count - success_count
        }

        return results

    def analyze_batch(self, image_paths: List[str]) -> Dict[str, Any]:
        """批量分析"""
        ocr_service = TableOCRService()

        all_results = {
            "total_images": len(image_paths),
            "image_results": [],
            "summary": {
                "total_tables": 0,
                "success_tables": 0,
                "failed_tables": 0
            }
        }

        for img_path in image_paths:
            try:
                result = self.analyze_image(img_path, ocr_service)
                all_results["image_results"].append(result)

                # 更新统计
                all_results["summary"]["total_tables"] += result["tables_count"]
                all_results["summary"]["success_tables"] += result["summary"]["successfully_analyzed"]
                all_results["summary"]["failed_tables"] += result["summary"]["failed"]

            except Exception as e:
                all_results["image_results"].append({
                    "image_path": img_path,
                    "success": False,
                    "error": str(e)
                })

        return all_results