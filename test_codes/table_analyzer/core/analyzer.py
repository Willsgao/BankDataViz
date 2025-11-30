import os
import re
import time
import json
from typing import List, Dict, Any, Union
from openai import OpenAI

from test_codes.table_analyzer.utils.image_utils import ImageUtils
from test_codes.table_analyzer.utils.config import settings


class FinancialTableAnalyzer:
    """重构后的LLM分析器"""

    def __init__(self):
        self.image_utils = ImageUtils()
        self.client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key
        )
        self.model_name = settings.llm_model_name

    def _build_system_prompt(self) -> str:
        """系统提示词"""
        return """
        你是一名专业的金融文档分析师，正在分析一张银行或金融机构PDF页面的图像。请严格基于图像中**实际可见的文本和表格结构**进行分析，**禁止推测、补充或假设任何图像中未明确显示的内容**。

## 分析步骤
1. 识别图像中所有表格（包括无边框表格、由空格/对齐形成的隐式表格），按从上到下、从左到右的顺序编号为 T_1, T_2, ..., T_N。
2. 对每个表格：
   a. 判断是否为财务或金融相关表格：满足以下任一条件即视为金融表格：
      - 包含金额数字（如带"¥"、"元"、千分位逗号、小数点后两位的数值）；
      - 包含以下任一关键词（含同义或近义表述）：
        资产、负债、收入、利润、现金流量、股东权益、贷款、利息、准备金、折旧、摊销、应收款、应付款、股本、净利润、毛利率、拨备、资本充足率、存贷比、平均余额、日均、敞口、风险加权资产、
        股东、持股、股份、持股比例、持股数量、限售股、流通股、股权结构、前十大股东、实际控制人、出资额、认缴、实缴、出资比例、股份质押、股份冻结。
   b. 如果是金融表格，执行以下子任务：
      i. **表名（table_title）**：
         - 若表格正上方（通常1~3行内）有明显标题（如"表1-1"、"合并资产负债表"等），且语义与表格内容一致，则基于该文本给出表名；
         - 若无显式表名，则根据表格内容相关信息生成一个合适表名，不能空缺。**仅限使用行业通用术语，不得编造具体公司名、项目名或数据值。**
      ii. **币种（currency）**：
         - 币种优先级：表格内显式标注 > 页面全局标注 > 金额符号（如出现"¥"即视为人民币）。
         - 检查表格内部或右上角附近是否出现币种标识（如"人民币"、"RMB"、"CNY"、"美元"、"USD"、"单位：千元"、"币种：人民币"等）；
         - 提取最可能的主币种，标准化为常见形式（如"人民币"、"美元"、"港币"），若未明确标注但金额含"¥"则默认为"人民币"；
      iii. **默认报告期（reporting_period）**：
         - 优先从表格列标题中提取（如"2024年6月30日"、"2023年度"、"截至2024年末"）；
         - 若同一图像中，表格上方不超过5行、或页面顶部页眉区域、或紧邻的章节标题中存在全局性说明（如"截至2023年12月31日"），且逻辑上适用于该表格，则可将其作为报告期；
         - 格式尽量保持原文，如"2024年6月30日"、"2023年度"；
      iv. **横向层级字段（horizontal_hierarchy_fields）**：
          - 构建列方向的完整路径（如 "2024年 > 平均余额"）；
          - 对每个字段路径，判断其是否为**统计类型**：若字段名包含"合计"、"总计"、"小计"、"余额"、"净额"、"总额"等汇总性词汇，则标记为统计类型；
          - 输出格式改为对象数组：{"field_path": "2024年 > 合计", "is_statistical": true}
      v. **纵向层级字段（vertical_hierarchy_fields）**：
          - 构建行方向的完整路径（如 "项目 > 资产 > 流动资产"）；
          - 同样判断是否为统计类型（如"流动资产合计"、"负债总计"）；
          - 输出格式同上：{"field_path": "项目 > 资产 > 合计", "is_statistical": true}
      vi. **层级完整性规则**：
          - 只要某层级节点在表格中有对应数据（数值或关键信息），就必须输出其完整路径；
          - 路径必须使用图像中的原始文本，不得改写。
   c. 如果不是金融表格，所有字段（除 table_id 和 is_financial）设为空或 null。

## 输出要求
- 仅输出一个合法 JSON 对象，无任何前缀、解释、注释或 Markdown。
- 所有字段值必须基于图像可见内容，严禁臆测。
- 若图像中无表格或无法解析，返回 {"has_table": false, "tables": []}。

## 输出格式
{
  "has_table": true,
  "tables": [
    {
      "table_id": 1,
      "is_financial": true,
      "table_title": "前十大股东持股情况",
      "currency": "人民币",
      "reporting_period": "2024年6月30日",
      "horizontal_hierarchy_fields": [
        {"field_path": "股东名称", "is_statistical": false},
        {"field_path": "持股数量（万股）", "is_statistical": false},
        {"field_path": "持股比例（%）", "is_statistical": false}
      ],
      "vertical_hierarchy_fields": [
        {"field_path": "前十大股东", "is_statistical": false},
        {"field_path": "前十大股东 > 中央汇金公司", "is_statistical": false},
        {"field_path": "前十大股东 > 合计", "is_statistical": true}
      ]
    }
  ]
}"""

    def _call_llm_vision_api(self, base64_image: str, prompt: str) -> tuple[str, dict, float]:
        """调用LLM视觉API"""
        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                        }
                    ]
                }]
            )
            elapsed = time.time() - start_time
            content = response.choices[0].message.content.strip()

            usage = getattr(response, 'usage', None)
            usage_dict = {
                "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                "completion_tokens": getattr(usage, "completion_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0)
            } if usage else {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

            return content, usage_dict, elapsed

        except Exception as e:
            elapsed = time.time() - start_time
            raise RuntimeError(f"API 调用失败: {e}") from e

    def _parse_llm_response(self, response_text: str, image_path: str, page_num: int = None) -> Dict[str, Any]:
        """解析 LLM 返回的 JSON 字符串"""
        try:
            print(f"[DEBUG] 原始响应: {response_text[:500]}...")

            cleaned = re.sub(r'^```json\s*|\s*```$', '', response_text.strip())
            data = json.loads(cleaned)

            tables = []
            for table_data in data.get("tables", []):
                # 检查表格字段完整性
                required_fields = ["table_title", "currency", "reporting_period"]
                for field in required_fields:
                    if field not in table_data:
                        print(f"[WARN] 表格缺少字段: {field}")
                        table_data[field] = ""

                # 构建完整表格结构
                full_table = {
                    "table_id": table_data.get("table_id"),
                    "is_financial": table_data.get("is_financial", False),
                    "table_title": table_data.get("table_title", ""),
                    "currency": table_data.get("currency", ""),
                    "reporting_period": table_data.get("reporting_period", ""),
                    "horizontal_hierarchy_fields": table_data.get("horizontal_hierarchy_fields", []),
                    "vertical_hierarchy_fields": table_data.get("vertical_hierarchy_fields", []),
                    "location": {
                        "page_number": page_num,
                        "image_path": image_path
                    },
                    "confidence": 0.8,
                    "has_merged_cells": None,
                    "data_cells_count": None
                }
                tables.append(full_table)

            return {
                "has_table": bool(data.get("has_table", False)),
                "tables": tables
            }
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[ERROR] JSON 解析失败: {e}")
            print(f"[DEBUG] 响应内容: {response_text}")
            return {
                "has_table": False,
                "tables": []
            }

    def analyze_image_list(self, image_paths: List[str]) -> Dict[str, Any]:
        """分析一组图片"""
        print(f"[INFO] 即将分析 {len(image_paths)} 张图片")
        image_results = []
        total_time = 0.0
        total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        total_tables_count = 0
        total_financial_tables_count = 0

        for idx, img_path in enumerate(image_paths):
            if not os.path.exists(img_path):
                print(f"[WARN] 图片不存在，跳过: {img_path}")
                continue

            print(f"[INFO] 正在分析: {img_path}")
            try:
                # 生成图片ID
                image_id = self.image_utils.generate_image_id(img_path)

                base64_img = self.image_utils.encode_image_to_base64(img_path)
                prompt = self._build_system_prompt()
                raw_response, usage, elapsed = self._call_llm_vision_api(base64_img, prompt)
                parsed_result = self._parse_llm_response(raw_response, img_path, idx + 1)

                # 统计当前图片的表格数量
                current_tables_count = len(parsed_result["tables"])
                current_financial_tables_count = len([t for t in parsed_result["tables"] if t.get("is_financial")])
                total_tables_count += current_tables_count
                total_financial_tables_count += current_financial_tables_count

                image_result = {
                    "image_path": img_path,
                    "image_id": image_id,
                    "page_number": idx + 1,
                    "raw_llm_output": raw_response,
                    "analysis_time_sec": round(elapsed, 2),
                    "token_usage": usage,
                    "has_table": parsed_result["has_table"],
                    "tables": parsed_result["tables"],
                    "tables_count": current_tables_count,
                    "financial_tables_count": current_financial_tables_count
                }
                image_results.append(image_result)

                total_time += elapsed
                total_tokens["prompt_tokens"] += usage["prompt_tokens"]
                total_tokens["completion_tokens"] += usage["completion_tokens"]
                total_tokens["total_tokens"] += usage["total_tokens"]

                print(
                    f"[INFO] 图片 {idx + 1} (ID: {image_id}) 分析完成，检测到 {current_tables_count} 个表格（{current_financial_tables_count} 个财务表格）")

            except Exception as e:
                print(f"[ERROR] 处理 {img_path} 时出错: {e}")
                image_id = self.image_utils.generate_image_id(img_path)
                image_results.append({
                    "image_path": img_path,
                    "image_id": image_id,
                    "page_number": idx + 1,
                    "has_table": False,
                    "tables": [],
                    "error": str(e),
                    "analysis_time_sec": 0,
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "tables_count": 0,
                    "financial_tables_count": 0
                })

        return {
            "input_type": "image_list",
            "total_images": len(image_paths),
            "image_results": image_results,
            "summary": {
                "total_tables": total_tables_count,
                "total_financial_tables": total_financial_tables_count,
                "total_analysis_time_sec": round(total_time, 2),
                "total_token_usage": total_tokens
            }
        }

    def analyze_pdf(self, pdf_path: str, temp_dir: str = None) -> Dict[str, Any]:
        """分析 PDF"""
        if temp_dir is None:
            temp_dir = settings.temp_dir

        print(f"[INFO] 正在转换 PDF 为图片: {pdf_path}")
        image_paths = self.image_utils.pdf_to_images(pdf_path, temp_dir)
        result = self.analyze_image_list(image_paths)
        result["input_type"] = "pdf"
        result["pdf_path"] = pdf_path
        return result

    def analyze(self, input_data: Union[str, List[str]], temp_dir: str = None) -> Dict[str, Any]:
        """统一入口：自动判断输入类型并分析"""
        if temp_dir is None:
            temp_dir = settings.temp_dir

        if isinstance(input_data, str):
            if not os.path.exists(input_data):
                raise FileNotFoundError(f"输入文件不存在: {input_data}")
            if input_data.lower().endswith('.pdf'):
                return self.analyze_pdf(input_data, temp_dir)
            else:
                return self.analyze_image_list([input_data])
        elif isinstance(input_data, list):
            if not input_data:
                raise ValueError("图片列表不能为空")
            return self.analyze_image_list(input_data)
        else:
            raise TypeError("input_data 必须是 PDF 路径（str）或图片路径列表（List[str]）")

    def save_results_to_json(self, result: Dict[str, Any], output_path: str) -> None:
        """将分析结果保存到 JSON 文件"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"[INFO] 分析结果已保存到: {output_path}")
        except Exception as e:
            print(f"[ERROR] 保存结果到 JSON 文件失败: {e}")
            raise