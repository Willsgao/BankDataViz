# -*- coding:utf-8 -*-
import os
import re
import time
import json
from typing import List, Dict, Any
from openai import OpenAI

from backend.services.table_processor import ImageUtils
from test_codes.enhanced_table_analyzer.utils.ocr_processor import OCRProcessor
from backend.services.table_processor._config_shim import settings
from backend.services.table_processor import TableOCRService


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

    def _build_system_prompt(self, ocr_data: Dict[str, Any]) -> str:
        """构建系统提示词 - 增强版本，包含表头关联信息"""
        dimensions = ocr_data.get("dimensions", {})
        rows, cols = dimensions.get("rows", 0), dimensions.get("cols", 0)

        # 格式化OCR数据样本
        top_rows = ocr_data.get("extracted_data", {}).get("top_rows_all_cols", [])
        left_cols = ocr_data.get("extracted_data", {}).get("left_cols_all_rows", [])

        # 简单标记缺失数据
        top_sample = []
        for i, row in enumerate(top_rows[:3]):
            marked_row = [cell if cell and str(cell).strip() else "[空]" for cell in row[:5]]
            top_sample.append(f"行{i}: {' | '.join(marked_row)}")

        left_sample = []
        for i, row in enumerate(left_cols[:5]):
            left_val = row[0] if row and len(row) > 0 else "[空]"
            left_sample.append(f"行{i}: {left_val}")

        return f"""
    你是专业的金融表格分析师。请分析图片中的表格：

    【表格信息】
    尺寸：{rows}行 × {cols}列
    OCR提取了前{self.extract_rows}行所有列 + 前{self.extract_cols}列所有行。

    【OCR数据样本】
    前{min(3, len(top_rows))}行前5列：
    {chr(10).join(top_sample)}

    前{min(5, len(left_cols))}行第一列：
    {chr(10).join(left_sample)}

    【核心任务】
    1. 识别图片中的实际表格数量和表头结构
    2. 识别行表头和列表头之间的关联关系
    3. 特别注意交叉表头（既是行表头又是列表头的情况）
    4. 将识别的表头与OCR数据进行映射

    【表格结构类型说明】
    1. 简单表格：行表头和列表头完全独立，无交叉
    2. 分层表格：有多级表头（使用"|→"表示层级）
    3. 交叉表格：存在公共表头，既是行表头又是列表头

    【输出要求】
    只输出JSON，格式如下：
    {{
      "tables_count": 2,
      "tables": [
        {{
          "id": 0,
          "header_structure": {{
            "type": "simple",  // "simple", "hierarchical", "cross"
            "common_headers": [  // 公共表头列表（交叉表格时使用）
              {{
                "name": "经营活动",
                "source": {{"ocr_table": 0, "ocr_row": 0, "ocr_column": 0}}
              }}
            ],
            "row_to_column_map": [  // 行表头对应的列表头索引
              {{"row_index": 0, "column_indices": [0, 1, 2]}},
              {{"row_index": 1, "column_indices": [0, 1, 2]}}
            ],
            "column_to_row_map": [  // 列表头对应的行表头索引
              {{"column_index": 0, "row_indices": [0, 1]}},
              {{"column_index": 1, "row_indices": [0, 1]}}
            ]
          }},
          "column_headers": [
            {{"name": "利润表|→2024年度", "source": {{"ocr_table": 1, "ocr_column": 0}}}},
            {{"name": "利润表|→2023年度", "source": {{"ocr_table": 1, "ocr_column": 1}}}}
          ],
          "row_headers": [
            {{"name": "收入类|→营业收入", "source": {{"ocr_table": 1, "ocr_row": 2}}}},
            {{"name": "成本类|→主营业务成本", "source": {{"ocr_table": 1, "ocr_row": 3}}}}
          ],
          "data_mapping": [  // 数据单元格的完整映射
            {{
              "row_index": 0,
              "column_index": 0,
              "source": {{"ocr_table": 1, "ocr_row": 2, "ocr_column": 0}}
            }}
          ],
          "data_start": {{"row": 2, "column": 1}}
        }}
      ]
    }}

    【重要说明】
    1. 以图片视觉为准，OCR可能不完整
    2. name字段使用"|→"作为层级分隔符
    3. source中的索引从0开始
    4. 对于交叉表格，公共表头放在common_headers中
    5. 确保映射关系准确，特别是行表头和列表头的对应关系
    6. 如果无法确定关联关系，row_to_column_map和column_to_row_map可以为空数组
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
        """解析LLM响应 - 简洁版本"""
        try:
            # 清理JSON标记
            cleaned = re.sub(r'^```json\s*|\s*```$', '', response_text.strip())


            print("&&&&&&&&&&&&cleaned&&&&&&&&&&&&&&&&&&&")
            print(cleaned)


            data = json.loads(cleaned)

            # 简单验证必要字段
            if "tables" not in data:
                raise ValueError("缺少tables字段")

            return data

        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {e}")
        except Exception as e:
            raise ValueError(f"响应解析失败: {e}")

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

        try:
            analysis_result = self._parse_llm_response(llm_response)
        except ValueError as e:
            return {"success": False, "error": str(e)}

        # 构建结果
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
            }
        }

    def analyze_image(self, image_path: str, ocr_service: TableOCRService = None, ocr_save_path="") -> Dict[str, Any]:
        """分析单张图片"""
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

        # 汇总
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