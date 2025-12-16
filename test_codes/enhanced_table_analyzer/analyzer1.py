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
        """构建系统提示词 - 处理OCR数据不完整的情况"""
        dimensions = ocr_data.get("dimensions", {})
        rows, cols = dimensions.get("rows", 0), dimensions.get("cols", 0)

        top_rows = ocr_data.get("extracted_data", {}).get("top_rows_all_cols", [])
        left_cols = ocr_data.get("extracted_data", {}).get("left_cols_all_rows", [])

        # 获取OCR覆盖率信息
        coverage = ocr_data.get("stats", {}).get("coverage_percentage", 100)

        # 标记OCR数据中的空单元格
        marked_top_rows = []
        for row_idx, row in enumerate(top_rows[:5]):  # 只标记前5行
            marked_row = []
            for col_idx, cell in enumerate(row):
                if cell == "" or cell is None or str(cell).strip() == "":
                    marked_row.append("[空]")
                elif len(str(cell).strip()) < 2:  # 过短的可能是识别错误
                    marked_row.append(f"[?{cell}?]")
                else:
                    marked_row.append(str(cell))
            marked_top_rows.append(marked_row)

        # 格式化标记后的数据
        top_rows_text = "\n".join([f"行{i + 1}: {' | '.join(row)}" for i, row in enumerate(marked_top_rows)])
        if len(top_rows) > 5:
            top_rows_text += f"\n... (还有{len(top_rows) - 5}行)"

        # 检查OCR数据质量
        empty_cells_count = sum(1 for row in top_rows[:3] for cell in row if not cell or str(cell).strip() == "")
        total_cells = sum(len(row) for row in top_rows[:3])
        data_quality = "差" if empty_cells_count / max(total_cells,
                                                       1) > 0.3 else "一般" if empty_cells_count > 0 else "好"

        # 提供关键匹配提示
        matching_hints = self._generate_matching_hints(ocr_data)

        return f"""
    你是一名专业的金融表格分析师。你的核心任务是：**以图片中的真实表头为准，即使OCR数据不完整**。

    ## 【重要前提：OCR数据可能不完整】

    OCR识别质量：{data_quality} (空白单元格: {empty_cells_count}/{total_cells})
    OCR覆盖率：{coverage}%

    OCR数据可能有：
    1. **单元格缺失**：[空] 标记表示OCR没识别到内容
    2. **识别错误**：[?X?] 标记表示可能识别错误
    3. **内容截断**：长文本可能被截断
    4. **格式丢失**：合并单元格可能被拆散

    ## 【核心原则：图片优先】

    你必须遵守以下原则：
    1. **表头以图片为准**：图片显示什么就是什么，不要受OCR缺失影响
    2. **结构以图片为准**：表头层级、合并单元格以图片视觉为准
    3. **尽量匹配OCR**：在图片识别的基础上，尽量在OCR中找对应位置

    ## 【三步分析流程】

    ### 第一步：从图片识别完整表头（不受OCR限制）

    仔细观察图片，识别：
    1. **横向完整表头**：不管OCR有没有识别到，图片显示的所有表头内容
    2. **纵向完整表头**：图片显示的所有行项目名称
    3. **表头结构**：合并情况、层级关系

    ### 第二步：将图片表头与OCR数据进行宽容匹配

    **关键：OCR可能不完整，匹配要宽容但准确**

    OCR数据前几行（[空]表示缺失，[?X?]表示可能错误）：
    {top_rows_text}

    {matching_hints}

    **匹配策略：**
    1. **精确匹配优先**：如果OCR内容与图片完全一致 → 直接匹配
    2. **模糊匹配**：如果OCR内容部分匹配（如"营业收"匹配"营业收入"）→ 视为匹配
    3. **位置推断**：如果OCR单元格为空但图片有内容 → 根据位置推断
    4. **模式匹配**：根据财务表格模式推断（如年份顺序、会计科目顺序）

    ### 第三步：确定OCR中的表头位置（用于数据提取）

    即使OCR不完整，也要确定：
    1. **哪些行是表头行**：对应图片表头的OCR行索引
    2. **哪些列是表头列**：对应图片行标题的OCR列索引
    3. **数据起始位置**：表头之后的数据起始点

    ## 【特殊处理：OCR缺失时的解决方案】

    ### 情况1：OCR表头行完全缺失
    - 图片：第一行"全年业绩"，第二行"2024年 2023年 变化(%) ..."
    - OCR：第一行可能全是[空]
    - **处理**：依然标记horizontal_header_rows=[0,1]，用图片识别的完整表头

    ### 情况2：OCR表头内容识别错误
    - 图片："利息净收入"
    - OCR："利息收人" 或 "利总净收入"
    - **处理**：视为匹配，使用图片的正确文本

    ### 情况3：OCR数据与图片行列数不一致
    - 图片：6列表头
    - OCR：只有5列（最后一列缺失）
    - **处理**：标记缺失，使用图片的完整表头

    ## 【输出要求 - 必须处理不完整情况】

    你的输出必须明确区分：
    1. **图片中的真实表头**（完整、准确）
    2. **OCR中的对应位置**（可能不完整）
    3. **匹配置信度**（完全匹配/部分匹配/推断匹配）

    {{
      "table_headers": {{
        // 图片中的完整表头（不受OCR影响）
        "horizontal_from_image": [
          {{"field_path": "2024年", "is_statistical": false, "is_header": true}}
        ],
        "vertical_from_image": [
          {{"field_path": "营业收入", "is_statistical": false, "is_header": true}}
        ],

        // OCR中的对应位置（可能不完整）
        "ocr_positions": {{
          "horizontal_header_rows": [0, 1],  // OCR中哪些行是表头
          "vertical_header_cols": [0],       // OCR中哪些列是表头
          "horizontal_matched_cells": [
            {{"image_text": "2024年", "ocr_text": "2024年", "ocr_position": [1, 0], "match_type": "exact"}},
            {{"image_text": "2023年", "ocr_text": "", "ocr_position": [1, 1], "match_type": "empty_but_inferred"}}
          ],
          "vertical_matched_cells": [
            {{"image_text": "营业收入", "ocr_text": "营业收", "ocr_position": [2, 0], "match_type": "partial"}}
          ],
          "data_start_row": 2,  // 数据在OCR中的起始行
          "data_start_col": 1   // 数据在OCR中的起始列
        }},

        // 用于替换的新表头（基于图片的完整表头）
        "horizontal_for_replacement": ["2024年", "2023年", "变化(%)", "2022年", "2021年", "2020年"],
        "vertical_for_replacement": ["营业收入", "利息净收入", "手续费及佣金净收入", ...]
      }},

      "ocr_data_quality": {{
        "coverage_percentage": {coverage},
        "missing_cells": {empty_cells_count},
        "data_quality": "{data_quality}",
        "notes": "OCR数据不完整，以图片识别为准"
      }},

      "matching_summary": {{
        "horizontal_match_rate": "80%",  // 横向表头匹配率
        "vertical_match_rate": "90%",    // 纵向表头匹配率
        "inferred_positions": ["[1,1] 位置为空，根据图片推断为'2023年'"],
        "confidence_level": "high"  // high/medium/low
      }},

      "data_extraction_plan": {{
        "steps": [
          "1. 删除OCR的horizontal_header_rows行(0,1)",
          "2. 删除OCR的vertical_header_cols列(0)",
          "3. 用horizontal_for_replacement作为新横向表头",
          "4. 用vertical_for_replacement作为新纵向表头",
          "5. 从OCR位置[2,1]开始提取数据"
        ],
        "expected_data_dimensions": {{
          "rows": {rows - 2},  // 减去表头行
          "cols": {cols - 1}   // 减去表头列
        }}
      }}
    }}

    ## 【重要提示】

    如果OCR数据严重不完整（匹配率<50%），请：
    1. 依然提供图片的完整表头
    2. 在`ocr_data_quality.notes`中说明问题
    3. 设置`confidence_level`为`medium`或`low`
    4. 在`data_extraction_plan`中说明风险

    **记住：你的首要任务是识别图片中的真实表头结构，其次才是匹配OCR数据。**

    现在开始分析，先看图片识别完整表头！
    """

    def _generate_matching_hints(self, ocr_data):
        """生成匹配提示，帮助LLM理解财务表格模式"""
        top_rows = ocr_data.get("extracted_data", {}).get("top_rows_all_cols", [])

        hints = []

        # 检查年份模式
        if len(top_rows) > 1:
            second_row = top_rows[1]
            year_patterns = [r'\d{4}年', r'\d{4}', r'Y\d{4}']
            year_cells = []

            for cell in second_row:
                if cell and any(re.search(pattern, str(cell)) for pattern in year_patterns):
                    year_cells.append(cell)

            if year_cells:
                hints.append(f"🔍 年份提示：OCR第二行可能包含年份数据: {year_cells}")

        # 检查财务项目模式
        if len(top_rows) > 2:
            first_col_items = [row[0] for row in top_rows[2:7] if row and len(row) > 0]
            finance_terms = []

            finance_keywords = ["收入", "利润", "费用", "成本", "收益", "资产", "负债", "权益"]
            for item in first_col_items:
                if item and any(keyword in str(item) for keyword in finance_keywords):
                    finance_terms.append(item)

            if finance_terms:
                hints.append(f"📊 财务项目提示：OCR第一列可能包含财务项目: {finance_terms[:3]}")

        # 检查数字格式
        if len(top_rows) > 2:
            numeric_cells = []
            for i, row in enumerate(top_rows[2:4], start=2):
                for j, cell in enumerate(row[1:4], start=1):  # 检查前几列
                    if cell and self._looks_like_financial_number(cell):
                        numeric_cells.append(f"[{i},{j}]:{cell}")

            if numeric_cells:
                hints.append(f"💰 数字数据提示：以下位置可能是财务数据: {numeric_cells[:3]}")

        if hints:
            return "【匹配提示】\n" + "\n".join(hints)
        return ""

    def _looks_like_financial_number(self, text):
            """判断文本是否是财务数字格式"""
            if not text:
                return False

            text_str = str(text).strip()

            # 检查常见财务数字模式
            patterns = [
                r'^\d{1,3}(,\d{3})+(\.\d+)?$',  # 带千位分隔符
                r'^\(\d{1,3}(,\d{3})*(\.\d+)?\)$',  # 括号负数
                r'^-?\d{1,3}(,\d{3})*(\.\d+)?$',  # 可能带负号
                r'^-?\d+(\.\d+)?%?$',  # 数字或百分比
                r'^\(?\d+(\.\d+)?%?\)?$',  # 可能带括号的百分比
            ]

            for pattern in patterns:
                if re.match(pattern, text_str.replace(' ', '')):
                    return True

            return False

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

    def _parse_llm_response11111(self, response_text: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            cleaned = re.sub(r'^```json\s*|\s*```$', '', response_text.strip())
            data = json.loads(cleaned)
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {e}\n响应内容: {response_text[:200]}")

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """解析LLM响应 - 支持新格式"""
        try:
            cleaned = re.sub(r'^```json\s*|\s*```$', '', response_text.strip())
            data = json.loads(cleaned)

            # 验证和标准化输出结构
            return self._standardize_llm_output(data)

        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {e}\n响应内容: {response_text[:200]}")

    def _standardize_llm_output(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化LLM输出，确保兼容性"""
        standardized = {
            "table_headers": {},
            "consistency_checks": raw_data.get("consistency_checks", {}),
            "analysis_notes": raw_data.get("analysis_notes", {})
        }

        table_headers = raw_data.get("table_headers", {})

        # 处理新格式
        if "horizontal_for_replacement" in table_headers:
            standardized["table_headers"] = {
                "horizontal_for_replacement": table_headers.get("horizontal_for_replacement", []),
                "vertical_for_replacement": table_headers.get("vertical_for_replacement", []),
                "ocr_positions": table_headers.get("ocr_positions", {}),

                # 保持向后兼容
                "horizontal": [
                    {"field_path": h, "is_statistical": False, "is_header": True}
                    for h in table_headers.get("horizontal_for_replacement", [])
                ],
                "vertical": [
                    {"field_path": v, "is_statistical": False, "is_header": True}
                    for v in table_headers.get("vertical_for_replacement", [])
                ],
                "header_positions": {
                    "horizontal_header_rows": table_headers.get("ocr_positions", {}).get("horizontal_header_rows", []),
                    "vertical_header_cols": table_headers.get("ocr_positions", {}).get("vertical_header_cols", []),
                    "horizontal_header_depth": len(
                        table_headers.get("ocr_positions", {}).get("horizontal_header_rows", [])),
                    "vertical_header_depth": len(table_headers.get("ocr_positions", {}).get("vertical_header_cols", []))
                }
            }
        else:
            # 旧格式，直接使用
            standardized["table_headers"] = table_headers

        # 添加其他字段
        if "ocr_data_quality" in raw_data:
            standardized["ocr_data_quality"] = raw_data["ocr_data_quality"]
        if "matching_summary" in raw_data:
            standardized["matching_summary"] = raw_data["matching_summary"]
        if "data_extraction_plan" in raw_data:
            standardized["data_extraction_plan"] = raw_data["data_extraction_plan"]

        return standardized

    def _validate_llm_output_structure(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """验证LLM输出结构"""
        table_headers = llm_result.get("table_headers", {})

        # 检查必须有表头信息
        if not table_headers:
            return {"valid": False, "error": "缺少table_headers字段", "status": "critical"}

        # 检查新格式或旧格式
        has_new_format = "horizontal_for_replacement" in table_headers
        has_old_format = "horizontal" in table_headers

        if not has_new_format and not has_old_format:
            return {"valid": False, "error": "缺少表头信息", "status": "critical"}

        if has_new_format:
            horizontal = table_headers.get("horizontal_for_replacement", [])
            vertical = table_headers.get("vertical_for_replacement", [])
            ocr_positions = table_headers.get("ocr_positions", {})

            if not horizontal or not vertical:
                return {"valid": False, "error": "新格式表头内容为空", "status": "warning"}

            if "horizontal_header_rows" not in ocr_positions:
                return {"valid": False, "error": "缺少OCR位置信息", "status": "warning"}

        return {"valid": True, "status": "ok"}

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

        # 新增：验证LLM输出结构
        validation_result = self._validate_llm_output_structure(analysis_result)
        if not validation_result["valid"]:
            print(f"警告：LLM输出结构验证失败: {validation_result['error']}")
            # 可以尝试修复或记录问题

        # 新增：记录分析质量
        analysis_result["processing_metadata"] = {
            "prompt_version": "enhanced_v2",
            "ocr_coverage": ocr_extract.get("stats", {}).get("coverage_percentage", 0),
            "validation_status": validation_result["status"]
        }


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

    def analyze_image(self, image_path: str, ocr_service: TableOCRService = None, ocr_save_path="") -> Dict[str, Any]:
        """分析单张图片"""
        # 如果没有传入OCR服务，创建新的
        if ocr_service is None:
            ocr_service = TableOCRService()

        # OCR识别
        ocr_result = ocr_service.recognize_table(image_path)
        # 保存OCR结果到JSON文件
        if ocr_save_path:
            import json
            with open(ocr_save_path, 'w', encoding='utf-8') as f:
                json.dump(ocr_result, f, ensure_ascii=False, indent=2)

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