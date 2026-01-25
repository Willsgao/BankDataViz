# -*- coding:utf-8 -*-
import json
import time
import os
import hashlib
import gzip
from typing import Dict, Any
from openai import OpenAI

from backend.configs.config import config, tableconfig
from backend.src.services.table_processor.cache_gateway import get as cache_get, upsert as cache_upsert, delete as cache_delete
from backend.src.services.table_processor.object_store import get_object, put_object, extract_pdf_uuid_from_image_path
from backend.src.services.table_processor.image_utils import TableImageUtils

# 全局常量
LLM_FORCE_REFRESH = os.getenv("LLM_FORCE_REFRESH", "false").lower() == "true"
print(f"[LLM] 强制刷新设置: {LLM_FORCE_REFRESH} (env), {tableconfig.LLM_FORCE_REFRESH} (config)")


class EnhancedFinancialTableAnalyzer:
    """增强版金融表格分析器 - 表格结构分析"""

    def __init__(self):
        self.client = OpenAI(
            base_url=config.TABLE_LLM_BASE_URL,
            api_key=config.TABLE_LLM_API_KEY
        )
        self.model_name = config.TABLE_LLM_MODEL_NAME
        self.max_sample_rows = 3
        self.max_sample_cols = 3

    def _prepare_ocr_summary(self, ocr_result: Dict[str, Any]) -> str:
        """准备OCR数据摘要 - 增强版，支持多种格式"""
        ocr_tables = ocr_result.get("tables_result", [])
        print(f"🔍 准备OCR摘要，表格数量: {len(ocr_tables)}")

        tables_info = []
        for i, table in enumerate(ocr_tables):
            body_cells = table.get("body", [])
            print(f"🔍 表格{i}: {len(body_cells)} 个单元格")

            if not body_cells:
                tables_info.append({
                    "ocr_table_id": i,
                    "dimensions": {"rows": 0, "cols": 0},
                    "text_features": [],
                    "extracted_data": {
                        "top_rows_all_cols": [],
                        "left_cols_all_rows": []
                    }
                })
                print(f"表格{i}: 空表格")
                continue

            if body_cells:
                print(f"表格{i} 第一个单元格: {body_cells[0]}")

            max_row_idx = 0
            max_col_idx = 0
            for cell in body_cells:
                row_end = cell.get("row_end", cell.get("RowBr", 0))
                col_end = cell.get("col_end", cell.get("ColBr", 0))
                max_row_idx = max(max_row_idx, row_end)
                max_col_idx = max(max_col_idx, col_end)

            rows = max_row_idx
            cols = max_col_idx
            print(f"表格{i}: {rows}行 × {cols}列")

            cell_matrix = [["" for _ in range(cols)] for _ in range(rows)]

            for cell in body_cells:
                row_start = cell.get("row_start", cell.get("RowTl", 0))
                col_start = cell.get("col_start", cell.get("ColTl", 0))
                words = cell.get("words", cell.get("Text", cell.get("content", "")))

                if 0 <= row_start < rows and 0 <= col_start < cols:
                    cell_matrix[row_start][col_start] = words
                else:
                    print(f"⚠️ 表格{i}: 单元格超出范围 行{row_start},列{col_start}")

            top_rows = []
            for r in range(min(self.max_sample_rows, rows)):
                row_data = []
                for c in range(cols):
                    cell_text = cell_matrix[r][c]
                    row_data.append(cell_text if cell_text else "")
                top_rows.append(row_data)

            left_cols = []
            for c in range(min(self.max_sample_cols, cols)):
                col_data = []
                for r in range(rows):
                    cell_text = cell_matrix[r][c]
                    col_data.append(cell_text if cell_text else "")
                left_cols.append(col_data)

            text_features = []
            for r in range(min(3, rows)):
                for c in range(min(3, cols)):
                    text = cell_matrix[r][c]
                    if text and len(text) > 0:
                        text_features.append(f"({r},{c}):{text[:20]}")

            tables_info.append({
                "ocr_table_id": i,
                "dimensions": {"rows": rows, "cols": cols},
                "text_features": text_features[:5],
                "extracted_data": {
                    "top_rows_all_cols": top_rows,
                    "left_cols_all_rows": left_cols
                }
            })

            print(f"表格{i} 提取数据: {len(top_rows)}行 × {len(top_rows[0]) if top_rows else 0}列")

        result = json.dumps({"ocr_tables": tables_info}, ensure_ascii=False, indent=2)
        print(f"🔍 OCR摘要准备完成，长度: {len(result)} 字符")
        return result

    def _build_global_analysis_prompt(self, ocr_summary: str) -> str:
        """构建全局分析prompt - 强制关注OCR文本，改进多层表头处理"""
        return f"""
    【任务】分析图片中的表格，提取表头结构和表格元数据，只输出组合好的表头文本。

    【OCR数据参考】{ocr_summary}

    【OCR文本特征强制规则】
    1、ocr_summary中给出的前三行、前三列的数据你要都看一遍，来判断表格的表头
    2. 你必须基于OCR识别出的实际文本来分析表格，不能忽略这些文本内容
    3. 如果OCR识别出具体文本（如日期、数字、中文），绝对不能输出为字母或占位符
    4. 当图片模糊或难以辨认时，以OCR文本内容为准

    【横向表头规则 - 重点修正 - 支持多层级】
    1. 横向表头是指表格顶部的标题行，可能有1行、2行甚至3行构成多级表头
    2. 对每一列，识别该列顶部**所有层级的标题文本**（从上到下）
    3. 如果某列顶部没有明确标题（例如第一列常常是项目名称列），则输出空字符串""作为占位符
    4. 格式："顶层>>中层>>底层"，支持任意多层：
       - 如果只有一层：直接输出文本，如"2024年"
       - 如果有两层："年份>>日期" 如"2024年>>12月31日"
       - 如果有三层："类型>>年份>>日期" 如"实际值>>2024年>>12月31日"
    5. 必须包含表格中每一列的表头路径，数量与列数相同，不能省略
    6. 特别注意：不要将数据行中的内容误判为横向表头！
    7. **关键：对于财务报表，仔细检查顶部是否有合并单元格形成的多级表头**

    【纵向表头规则 - 多层级分组】
    1. 识别分组：如果某行在数据区为空或只有表头文本，这是高级表头
    2. 组合方式：高级表头 >> 次级表头 >> 具体数据文本，支持任意多层：
       - "一级分类>>二级分类>>具体项目"
       - "资产>>流动资产>>货币资金"
    3. 每个有数据的行都要有一条对应的路径，并且符合语义层面的包含关系
    4. 输出为字符串数组，一定不能为空

    【表格元数据识别规则 - 新增币种和单位字段】
    1. **核心币种识别**：
       - 观察表格中数值数据的主要币种类型
       - 常见币种：人民币、美元、欧元、日元、港元、英镑等
       - 常见符号：¥（人民币）、$（美元）、€（欧元）、£（英镑）、HK$（港元）等
       - 识别依据：表格标题、表头、数值前的货币符号、表格说明文字
       - 如果表格涉及多种币种，识别主要币种或表格默认币种
       - 字段名：default_currency，如"人民币"、"美元"、"欧元"等，没有则输出""

    2. **核心单位识别**：
       - 观察表格中数值数据的主要计量单位
       - 常见单位：元、千元、万元、亿元、百万元、百万、美元、欧元等
       - 金融报表常见：万元、亿元（中国财务报表常用），美元、欧元（国际报表）
       - 百分比单位：% 或 "百分比"（用于比率、比例数据）
       - 识别依据：表格标题、表头、数值后的单位标注、表格右上角说明
       - **特别注意**：如果表格中有多种单位（如金额用"万元"，比率用"%")，识别主要数值的单位
       - 字段名：default_unit，如"万元"、"亿元"、"%"、"美元"等，没有则输出""

    3. 默认报告期：观察表格标题、表头或上方文本中的时间信息
       - 识别表格的报告期间，按实际识别结果输出
       - 常见格式："2024年"、"2024年度"、"2024年第一季度"、"2024年上半年"、"截至2024年12月31日"等
       - 按识别到的实际文本输出，保持原格式
       - 字段名：default_report_period，如果没有明确报告期信息，输出""

    4. 识别位置：主要观察以下区域：
       - 表格左上角或右上角的小字
       - 表格标题行
       - 表头行中的括号说明
       - 表格上方的描述文本
       - 数值列的表头或数值后面的单位标注

    【币种和单位识别示例】
    1. 人民币财务报表：
       - 常见：default_currency: "人民币", default_unit: "万元" 或 "亿元"
       - 示例：表格标题"2024年财务报表(单位:万元)" → default_unit: "万元"

    2. 国际财务报表：
       - default_currency: "美元", default_unit: "百万美元"
       - 示例：表格标题"Financial Statement (in millions of US dollars)" → default_currency: "美元", default_unit: "百万美元"

    3. 百分比表格：
       - default_unit: "%" 或 "百分比"
       - 示例：表格标题"市场份额分析(%)" → default_unit: "%"

    4. 混合单位表格：
       - 优先识别主要数值列的单位
       - 如：金额列用"万元"，比例列用"%" → 主要单位识别为"万元"

    【多层表头示例 - 新增】
    1. **两行表头示例**：
       表格：
       |          |      2024年      |      2023年      |
       |----------|------------------|------------------|
       |  项目    | 12月31日 | 变化(%) | 12月31日 | 变化(%) |
       |----------|----------|---------|----------|---------|
       | 资产总额 |   1000   |   5%    |    950   |   -     |

       正确输出：
       {{
         "tables": [
           {{
             "id": "1",
             "name": "资产表",
             "ocr_tables": [0],
             "headers": {{
               "cols": [
                 "",
                 "2024年>>12月31日",
                 "2024年>>变化(%)",
                 "2023年>>12月31日",
                 "2023年>>变化(%)"
               ],
               "rows": [
                 "资产总额"
               ]
             }},
             "default_currency": "人民币",
             "default_report_period": "2024年",
             "default_unit": "万元"
           }}
         ]
       }}

    【多表格示例 - 新增】
    如果有多个独立表格，应该这样输出：
    {{
      "tables": [
        {{
          "id": "1",
          "name": "表格1名称",
          "ocr_tables": [0],
          "headers": {{
            "cols": [...],
            "rows": [...]
          }},
          "default_currency": "人民币",
          "default_report_period": "2024年",
          "default_unit": "万元"
        }},
        {{
          "id": "2", 
          "name": "表格2名称",
          "ocr_tables": [1],
          "headers": {{
            "cols": [...],
            "rows": [...]
          }},
          "default_currency": "美元",
          "default_report_period": "2024年度",
          "default_unit": "百万美元"
        }},
        {{
          "id": "3",
          "name": "表格3名称",
          "ocr_tables": [2],
          "headers": {{
            "cols": [...],
            "rows": [...]
          }},
          "default_currency": "",
          "default_report_period": "",
          "default_unit": "%"
        }}
      ]
    }}

    【财务报表示例 - 多层表头】
    对于财务报表（如资产表、损益表）：
    1. 第一列通常是"项目"或"指标"列，顶部可能没有标题 → cols[0] = ""
    2. 后续列可能有复杂多级表头，如：
       - 年份+日期："2024年>>12月31日"
       - 类型+年份："实际值>>2024年"
       - 年份+指标："2024年>>金额"、"2024年>>比例"
    3. 注意观察表格上方的币种、单位信息

    【多级列标题识别技巧】
    1. 先识别**列标题行数**：顶部有几行连续的文本行（没有数据）？
    2. 为每一列构建**垂直路径**：从上到下的所有文本
    3. 合并单元格的处理：如果一个标题跨越多列，它应该应用于所有相关列
    4. 空单元格处理：如果某列在某个标题层级为空，继承上一级的标题

    【其他特别注意】
    1、表头内容要基于图片和ocr_summary给出，优先使用OCR识别到的准确文本
    2、一定不能漏掉横向或纵向的表头信息，特别是多级表头
    3、各自存在独立的横向表头的表格，不能当成同一个表格
    4、对于表头检查一定要仔细，层级关系绝对不能丢
    5、特别注意区分：横向表头（顶部标题） vs 纵向表头（左侧项目）
    6、如果第一列的顶部没有明确标题（常见于财务报表），横向表头的第一个元素应为空字符串""
    7、**关键：检查顶部是否有合并单元格！合并单元格的标题应该应用到所有相关列**

    【注意】
    1. 只输出JSON，不要解释
    2. 路径用>>连接，不要空格
    3. 确保横向表头覆盖每一列，支持多层结构
    4. 纵向表头要识别分组结构并组合，支持多层结构
    5. 要给表格一个合适的表格名"name"
    6. "ocr_tables"中的数字是指该表格在ocr_summary中对应的表格的序号ocr_table_id
    7. 新增三个字段：default_currency、default_report_period、default_unit，如果无法识别请输出空字符串""
    8. **特别注意：列标题必须反映实际的多层结构，不能简化为单层**
    9. **新增要求：仔细识别表格的核心币种和核心数据单位**

    现在分析，直接输出JSON：
    """

    def _call_llm_global(self, base64_image: str, prompt: str) -> Dict[str, Any]:
        """调用LLM进行全局分析 - 最终版"""
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
            temperature=0,
            top_p=0.1,
            seed=42,
            response_format={"type": "json_object"}
        )

        elapsed = time.time() - start_time
        content = response.choices[0].message.content.strip()

        try:
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

            result = json.loads(content)

            if "tables" not in result:
                raise ValueError("响应缺少tables字段")

            for i, table in enumerate(result["tables"]):
                if "id" not in table or "headers" not in table:
                    raise ValueError(f"表格{i}缺少必要字段")
                if not isinstance(table["headers"].get("cols"), list):
                    raise ValueError(f"表格{i}的cols不是数组")
                if not isinstance(table["headers"].get("rows"), list):
                    raise ValueError(f"表格{i}的rows不是数组")

        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"LLM响应解析失败: {e}\n原始内容: {content[:200]}...")

        usage = response.usage if hasattr(response, 'usage') else None
        token_usage = {
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0
        }

        return {
            "tables": result["tables"],
            "time_sec": round(elapsed, 2),
            "token_usage": token_usage
        }


    def analyze_image(self, image_path: str, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """分析单张图片中的所有表格"""
        base64_image = TableImageUtils.encode_image_to_base64(image_path)
        md5 = hashlib.md5(base64_image.encode()).hexdigest()
        provider_key = f"llm:{self.model_name}"

        # 提取序号
        filename = os.path.basename(image_path)
        filename_without_ext = os.path.splitext(filename)[0]
        parts = filename_without_ext.split('_')
        sequence_number = parts[-1] if parts else "unknown"

        if not LLM_FORCE_REFRESH:
            hit = cache_get(md5, provider_key)
            if hit:
                print("LLM cache hit, skip cost")
                try:
                    pdf_uuid = extract_pdf_uuid_from_image_path(image_path)
                    llm_result = json.loads(gzip.decompress(get_object(hit["s3_key"], pdf_uuid)))
                    return {
                        "success": True,
                        "image_info": ocr_result.get("image_info", {}),
                        "tables_structure": {"tables": llm_result["tables"]},
                        "processing_stats": {
                            "analysis_time_sec": 0,
                            "ocr_tables_count": len(ocr_result.get("tables_result", [])),
                            "visual_tables_count": len(llm_result["tables"]),
                            "token_usage": hit.get("token_usage", {})
                        }
                    }
                except FileNotFoundError as e:
                    print(f"⚠️ 缓存文件缺失: {e}")
                    print("  继续执行LLM调用...")
                    try:
                        cache_delete(md5, provider_key)
                        print(f"  已删除无效缓存记录")
                    except:
                        pass

        ocr_summary = self._prepare_ocr_summary(ocr_result)
        prompt = self._build_global_analysis_prompt(ocr_summary)
        print(f"[LLM] Prompt长度: {len(prompt)} 字符")

        llm_result = self._call_llm_global(base64_image, prompt)

        compressed = gzip.compress(json.dumps(llm_result).encode())

        # s3_key = f"llm/{md5}.json.gz"
        s3_key = f"llm/{sequence_number}_{md5}.json.gz"

        pdf_uuid = extract_pdf_uuid_from_image_path(image_path)
        put_object(s3_key, compressed, pdf_uuid)

        cost_usd = 0.0
        prompt_tokens = llm_result.get("token_usage", {}).get("prompt_tokens", 0)
        completion_tokens = llm_result.get("token_usage", {}).get("completion_tokens", 0)
        cache_upsert(md5, provider_key, self.model_name,
                     cost_usd, prompt_tokens, completion_tokens, s3_key)

        return {
            "success": True,
            "image_info": ocr_result.get("image_info", {}),
            "tables_structure": {"tables": llm_result["tables"]},
            "processing_stats": {
                "analysis_time_sec": llm_result["time_sec"],
                "ocr_tables_count": len(ocr_result.get("tables_result", [])),
                "visual_tables_count": len(llm_result["tables"]),
                "token_usage": llm_result["token_usage"]
            }
        }



