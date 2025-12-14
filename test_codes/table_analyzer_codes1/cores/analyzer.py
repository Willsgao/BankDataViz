# -*- coding:utf-8 -*-
import json
import time
from typing import Dict, Any, List
from openai import OpenAI

from backend.services.table_processor.table_config import settings


class EnhancedFinancialTableAnalyzer:
    """增强版金融表格分析器 - 表格结构分析"""

    def __init__(self):
        self.client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key
        )
        self.model_name = settings.llm_model_name
        self.max_sample_rows = 3  # 每个表格采样前3行
        self.max_sample_cols = 3  # 每个表格采样前3列

    def _prepare_ocr_summary(self, ocr_result: Dict[str, Any]) -> str:
        """准备OCR数据摘要 - 修正版，保持原有逻辑"""
        ocr_tables = ocr_result.get("tables_result", [])

        tables_info = []
        for i, table in enumerate(ocr_tables):
            # 从body数据推断表格维度
            body_cells = table.get("body", [])

            if not body_cells:
                # 空表格
                tables_info.append({
                    "ocr_table_id": i,
                    "dimensions": {"rows": 0, "cols": 0},
                    "text_features": [],
                    "extracted_data": {
                        "top_rows_all_cols": [],
                        "left_cols_all_rows": []
                    }
                })
                continue

            # 找到最大的行索引和列索引
            max_row_idx = 0
            max_col_idx = 0
            for cell in body_cells:
                max_row_idx = max(max_row_idx, cell.get("row_end", 0))
                max_col_idx = max(max_col_idx, cell.get("col_end", 0))

            # 确定表格实际大小
            rows = max_row_idx  # row_end是最大行索引，需要+1
            cols = max_col_idx  # col_end是最大列索引，需要+1

            # 创建单元格矩阵，初始化为空字符串
            cell_matrix = [["" for _ in range(cols)] for _ in range(rows)]

            # 填充单元格矩阵 - 对于合并单元格，所有位置都填充相同内容
            for cell in body_cells:

                row_start = cell.get("row_start", 0)
                col_start = cell.get("col_start", 0)
                # row_end = cell.get("row_end", 0)
                # col_end = cell.get("col_end", 0)
                words = cell.get("words", "")
                cell_matrix[row_start][col_start] = words  # 只填充左上角

                # # 填充合并单元格的所有位置
                # for r in range(row_start, row_end + 1):
                #     for c in range(col_start, col_end + 1):
                #         if r < rows and c < cols:
                #             cell_matrix[r][c] = words  # 直接赋值


            # 提取前三行所有列 - 保持原有逻辑：空字符串保留为空
            top_rows = []
            for r in range(min(self.max_sample_rows, rows)):
                row_data = []
                for c in range(cols):
                    cell_text = cell_matrix[r][c]
                    row_data.append(cell_text if cell_text else "")
                top_rows.append(row_data)  # 只取前5列展示

            # 提取前三列所有行 - 保持原有逻辑：空字符串保留为空
            left_cols = []
            for c in range(min(self.max_sample_cols, cols)):
                col_data = []
                for r in range(rows):
                    cell_text = cell_matrix[r][c]
                    col_data.append(cell_text if cell_text else "")
                left_cols.append(col_data)  # 只取前8行展示

            tables_info.append({
                "ocr_table_id": i,
                "dimensions": {"rows": rows, "cols": cols},
                # "text_features": text_features,
                "extracted_data": {
                    "top_rows_all_cols": top_rows,
                    "left_cols_all_rows": left_cols
                }
            })

        return json.dumps({"ocr_tables": tables_info}, ensure_ascii=False, indent=2)


    def _build_global_analysis_prompt(self, ocr_summary: str) -> str:
        """构建全局分析prompt - 强制关注OCR文本"""
        return f"""
    【任务】分析图片中的表格，提取表头结构，只输出组合好的表头文本。

    【OCR数据参考】{ocr_summary}

    【OCR文本特征强制规则】
    1、ocr_summary中给出的前三行、前三列的数据你要都看一遍，来判断表格的表头
    2. 你必须基于OCR识别出的实际文本来分析表格，不能忽略这些文本内容
    3. 如果OCR识别出具体文本（如日期、数字、中文），绝对不能输出为字母或占位符
    4. 当图片模糊或难以辨认时，以OCR文本内容为准

    【横向表头规则】
    1. 对每一列，从上到下组合所有表头层级
    2. 格式："顶层>>中层>>底层"
    3. 必须包含表格中每一列的表头路径
    4. 输出为字符串数组，每个元素是一列的表头路径，该列没有则用""占位,数量与列数相同，不能省略
    5、表头列数如果与ocr_summary中列数不同，要检查

    【纵向表头规则】
    1. 识别分组：如果某行在数据区为空或只有表头文本，这是高级表头
    2. 组合方式：高级表头 + 次级表头 + 具体数据文本
    3. 格式："高级表头>>次级表头>>数据内容"
    4. 每个有数据的行都要有一条对应的路径，并且符合语义层面的包含关系
    5. 输出为字符串数组，一定不能为空

    【其他特别注意】
    1、表头内容要基于图片和ocr_summary给出
    2、一定不能漏掉横向或纵向的表头信息
    3、各自存在独立的横向表头的表格，不能当成同一个表格
    4、对于表头检查一定要仔细，层级关系绝对不能丢

    【分组表示例】
    表格：
    | 地区 | 城市 | 销售额 |
    |------|------|--------|
    | 华东 |      |        |
    |      | 上海 | 100    |
    |      | 南京 | 90     |
    | 华北 |      |        |
    |      | 北京 | 120    |

    正确输出：
    {{
      "tables": [
        {{
          "id": "1",
          "name":"租赁负债财务表",          
          "ocr_tables": [0],
          "headers": {{
            "cols": ["地区", "城市", "销售额"],
            "rows": [
              "地区>>华东>>城市>>上海",
              "地区>>华东>>城市>>南京", 
              "地区>>华北>>城市>>北京"
            ]
          }}
        }}
      ]
    }}

    【注意】
    1. 只输出JSON，不要解释
    2. 路径用>>连接，不要空格
    3. 确保横向表头覆盖每一列
    4. 纵向表头要识别分组结构并组合
    5. 要给表格一个合适的表格名"name"
    6. "ocr_tables"中的数字是指该表格在ocr_summary中对应的表格的序号ocr_table_id
    

    现在分析，直接输出：
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

        # 提取JSON
        try:
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

            result = json.loads(content)

            # 验证格式 - 简化验证
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

        # 计算token消耗
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
        from backend.services.table_processor import ImageUtils

        # 1. 准备数据
        image_utils = ImageUtils()
        base64_image = image_utils.encode_image_to_base64(image_path)
        ocr_summary = self._prepare_ocr_summary(ocr_result)

        # 2. 调用LLM全局分析
        prompt = self._build_global_analysis_prompt(ocr_summary)

        print("####################################")
        print(prompt)
        print("####################################")

        llm_result = self._call_llm_global(base64_image, prompt)

        # 3. 构建最终结果
        return {
            "success": True,
            "image_info": ocr_result.get("image_info", {}),
            "tables_structure": {  # 改为tables_structure字段
                "tables": llm_result["tables"]
            },
            "processing_stats": {
                "analysis_time_sec": llm_result["time_sec"],
                "ocr_tables_count": len(ocr_result.get("tables_result", [])),
                "visual_tables_count": len(llm_result["tables"]),  # 改为tables字段
                "token_usage": llm_result["token_usage"]
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
    from backend.services.table_processor import TableOCRService

    ocr_service = TableOCRService()
    image_path = r"E:\Datas\base_pros\DocuVista\test_codes\pngs\123.png"
    # image_path = r"E:\Datas\base_pros\DocuVista\test_codes\pngs\7d4a49dd-9b72-4c02-a7ee-d09a0921ca4b_014.png"

    # 1. OCR识别
    ocr_result = ocr_service.recognize_table(image_path)

    print("ocr_result:", ocr_result)

    # 2. 全局分析
    from pprint import pprint

    result = analyzer.analyze_image(image_path, ocr_result)
    print("llm_result:", result)

    pprint(result)

    print(f"分析完成，发现{result['processing_stats']['visual_tables_count']}个表格")

    # 3. 使用映射关系提取数据
    for table in result["tables_structure"]["tables"]:
        print(f"\n表格ID: {table.get('id')}")
        print(f"横向表头({len(table['headers']['cols'])}个):")
        for col_path in table["headers"]["cols"]:
            print(f"  {col_path}")

        print(f"纵向表头({len(table['headers']['rows'])}个):")
        if len(table["headers"]["rows"]) > 10:
            for row_path in table["headers"]["rows"][:5]:
                print(f"  {row_path}")
            print(f"  ... 还有{len(table['headers']['rows']) - 5}个")
        else:
            for row_path in table["headers"]["rows"]:
                print(f"  {row_path}")
        print("-" * 50)