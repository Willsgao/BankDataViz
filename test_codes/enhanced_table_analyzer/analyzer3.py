# -*- coding:utf-8 -*-
import json
import time
from typing import Dict, Any, List
from openai import OpenAI

from backend.src.services import settings


class EnhancedFinancialTableAnalyzer:
    """增强版金融表格分析器 - 全局分析+语义对齐"""

    def __init__(self):
        self.client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key
        )
        self.model_name = settings.llm_model_name
        self.max_sample_rows = 3  # 每个表格采样前3行
        self.max_sample_cols = 3  # 每个表格采样前3列

    def _prepare_ocr_summary(self, ocr_result: Dict[str, Any]) -> str:
        """准备OCR数据摘要 - 精简版"""
        ocr_tables = ocr_result.get("tables_result", [])

        tables_info = []
        for i, table in enumerate(ocr_tables):
            # 获取表格维度
            rows = table.get("row", 0)
            cols = table.get("col", 0)

            # 提取前三行所有列
            top_rows = []
            for r in range(min(self.max_sample_rows, rows)):
                row_data = []
                for c in range(cols):
                    cell_key = f"{r}_{c}"
                    cell = table.get("cell", {}).get(cell_key, "")
                    row_data.append(cell if cell else "[空]")
                top_rows.append(row_data[:5])  # 只取前5列展示，避免过长

            # 提取前三列所有行
            left_cols = []
            for c in range(min(self.max_sample_cols, cols)):
                col_data = []
                for r in range(rows):
                    cell_key = f"{r}_{c}"
                    cell = table.get("cell", {}).get(cell_key, "")
                    col_data.append(cell if cell else "[空]")
                left_cols.append(col_data[:8])  # 只取前8行展示

            tables_info.append({
                "ocr_table_id": i,
                "dimensions": {"rows": rows, "cols": cols},
                "extracted_data": {
                    "top_rows_all_cols": top_rows,  # 前三行所有列
                    "left_cols_all_rows": left_cols  # 前三列所有行
                }
            })

        return json.dumps({"ocr_tables": tables_info}, ensure_ascii=False)

    def _build_global_analysis_prompt(self, ocr_summary: str) -> str:
        """构建全局分析prompt"""
        return f"""
【核心任务】
分析图片中的表格结构，建立表头与OCR数据的准确映射。

【OCR检测结果】
OCR系统检测到以下表格分区：
{ocr_summary}

【分析要求】
1. 判断实际有几个独立表格（OCR可能错误分割）
2. 识别每个表格的行表头和列表头
3. 将表头映射到OCR数据的具体位置

【映射规则】
- 每个表头必须指定：ocr_table_id, ocr_row, ocr_col
- 优先映射到数据直接对应的表头层级
- 对于多级表头，用"|"表示层级

【输出格式】
{{
  "visual_tables": [
    {{
      "visual_id": 0,
      "name": "表格名称",
      "contains_ocr_tables": [0, 1],  // 可能对应多个OCR分区
      "headers": {{
        "row_headers": [  // 纵向表头
          {{
            "name": "表头内容",
            "ocr_ref": {{"table_id": 0, "row": 2, "col": 0}}
          }}
        ],
        "column_headers": [  // 横向表头
          {{
            "name": "表头内容", 
            "ocr_ref": {{"table_id": 0, "row": 0, "col": 1}}
          }}
        ]
      }},
      "data_region": {{"start_row": 2, "start_col": 1}}  // 数据起始位置
    }}
  ]
}}

只输出JSON，不要其他内容。
"""

    def _call_llm_global(self, base64_image: str, prompt: str) -> Dict[str, Any]:
        """调用LLM进行全局分析"""
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

        # 提取JSON
        try:
            # 清理可能的markdown标记
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

            result = json.loads(content)

            # 简单验证
            if "visual_tables" not in result:
                raise ValueError("响应缺少visual_tables字段")

        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"LLM响应解析失败: {e}\n原始内容: {content[:200]}...")

        # 计算token消耗
        usage = response.usage if hasattr(response, 'usage') else None
        token_usage = {
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0
        }

        return {
            "analysis": result,
            "time_sec": round(elapsed, 2),
            "token_usage": token_usage
        }

    def analyze_image(self, image_path: str, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """分析单张图片中的所有表格"""
        from backend.src.services import ImageUtils

        # 1. 准备数据
        image_utils = ImageUtils()
        base64_image = image_utils.encode_image_to_base64(image_path)
        ocr_summary = self._prepare_ocr_summary(ocr_result)

        # 2. 调用LLM全局分析
        prompt = self._build_global_analysis_prompt(ocr_summary)
        llm_result = self._call_llm_global(base64_image, prompt)

        # 3. 构建最终结果
        return {
            "success": True,
            "image_info": ocr_result.get("image_info", {}),
            "global_analysis": llm_result["analysis"],
            "processing_stats": {
                "analysis_time_sec": llm_result["time_sec"],
                "ocr_tables_count": len(ocr_result.get("tables_result", [])),
                "visual_tables_count": len(llm_result["analysis"].get("visual_tables", [])),
                "token_usage": llm_result["token_usage"]  # 新增token消耗统计
            }
        }

    def batch_analyze(self, image_ocr_pairs: List[tuple]) -> Dict[str, Any]:
        """批量分析（图片路径, OCR结果）对"""
        results = []

        for img_path, ocr_result in image_ocr_pairs:
            try:
                result = self.analyze_image(img_path, ocr_result)
                results.append({
                    "image_path": img_path,
                    "success": True,
                    "result": result
                })
            except Exception as e:
                results.append({
                    "image_path": img_path,
                    "success": False,
                    "error": str(e)
                })

        # 汇总统计
        success_count = sum(1 for r in results if r["success"])

        return {
            "total_images": len(image_ocr_pairs),
            "successful": success_count,
            "failed": len(image_ocr_pairs) - success_count,
            "results": results
        }


# 使用示例
if __name__ == "__main__":
    analyzer = EnhancedFinancialTableAnalyzer()

    # 假设已有OCR服务
    from backend.src.services import TableOCRService

    ocr_service = TableOCRService()
    image_path = r"E:\Datas\base_pros\DocuVista\test_codes\pngs\514001_152.png"

    # 1. OCR识别
    ocr_result = ocr_service.recognize_table(image_path)

    # 2. 全局分析
    from pprint import pprint
    result = analyzer.analyze_image(image_path, ocr_result)

    pprint(result)

    print(f"分析完成，发现{result['processing_stats']['visual_tables_count']}个表格")

    # 3. 使用映射关系提取数据
    for table in result["global_analysis"]["visual_tables"]:
        print(f"表格: {table.get('name', '未命名')}")
        print(f"包含OCR分区: {table.get('contains_ocr_tables', [])}")
        print(f"行表头: {[h['name'] for h in table['headers']['row_headers']]}")
        print(f"列表头: {[h['name'] for h in table['headers']['column_headers']]}")