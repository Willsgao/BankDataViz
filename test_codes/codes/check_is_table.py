import os
import re
import base64
import time
import json
import fitz  # PyMuPDF
import hashlib
from typing import List, Dict, Any, Union
from openai import OpenAI


class FinancialTableAnalyzerLLM:
    """
    支持分析 PDF 或图片列表，判断是否包含财务表格，
    并分析线框省略情况、字段层级关系，同时统计耗时与 Token 消耗。
    优化版：每张图片的分析结果保持独立，并为每张图片生成唯一ID
    """

    def __init__(self, api_key: str, base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
                 model_name: str = "doubao-1-5-vision-pro-250328"):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

    def _generate_image_id(self, image_path: str) -> str:
        """
        为图片生成唯一ID（基于文件内容和路径的MD5哈希）

        Args:
            image_path: 图片文件路径

        Returns:
            str: 图片唯一ID（16位十六进制字符串）
        """
        try:
            # 基于文件内容生成哈希
            with open(image_path, "rb") as f:
                file_content = f.read()
            content_hash = hashlib.md5(file_content).hexdigest()[:16]

            # 结合文件名生成最终ID
            file_name = os.path.basename(image_path)
            combined = f"{file_name}_{content_hash}"
            image_id = hashlib.md5(combined.encode()).hexdigest()[:16]

            return f"img_{image_id}"

        except Exception as e:
            # 如果无法读取文件内容，使用路径哈希作为后备方案
            path_hash = hashlib.md5(image_path.encode()).hexdigest()[:16]
            return f"img_{path_hash}"

    def _encode_image_to_base64(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def pdf_to_images(self, pdf_path: str, output_dir: str) -> List[Dict[str, str]]:
        """将 PDF 转为图片列表，每张图片包含路径和ID"""
        os.makedirs(output_dir, exist_ok=True)
        doc = fitz.open(pdf_path)
        image_info_list = []

        for i, page in enumerate(doc):
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img_path = os.path.join(output_dir, f"page_{i + 1}.png")
            pix.save(img_path)

            # 生成图片ID
            image_id = self._generate_image_id(img_path)

            image_info_list.append({
                "image_path": img_path,
                "image_id": image_id,
                "page_number": i + 1
            })

        doc.close()
        return image_info_list

    def _build_system_prompt(self) -> str:
        # 保持原有的系统提示不变
        return """
        [原有的系统提示内容保持不变]
        """

    def _call_llm_vision_api(self, base64_image: str, prompt: str) -> tuple[str, dict, float]:
        # 保持原有的API调用逻辑不变
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

    def _build_table_structure(self, llm_table_data: Dict, image_info: Dict, page_num: int = None) -> Dict[str, Any]:
        """构建完整的表格数据结构，包含图片ID"""
        return {
            "table_id": llm_table_data.get("table_id"),
            "is_financial": llm_table_data.get("is_financial", False),
            "table_title": llm_table_data.get("table_title", ""),
            "currency": llm_table_data.get("currency", ""),
            "reporting_period": llm_table_data.get("reporting_period", ""),
            "horizontal_hierarchy_fields": llm_table_data.get("horizontal_hierarchy_fields", []),
            "vertical_hierarchy_fields": llm_table_data.get("vertical_hierarchy_fields", []),
            "location": {
                "page_number": page_num,
                "image_path": image_info["image_path"],
                "image_id": image_info["image_id"]  # 添加图片ID
            },
            "confidence": 0.8,
            "has_merged_cells": None,
            "data_cells_count": None
        }

    def _parse_llm_response(self, response_text: str, image_info: Dict, page_num: int = None) -> Dict[str, Any]:
        """解析 LLM 返回的 JSON 字符串，构建完整的表格数据结构"""
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
                full_table = self._build_table_structure(table_data, image_info, page_num)
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
        """分析一组图片，每张图片的结果保持独立，包含图片ID"""
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
                # 生成图片信息（包含ID）
                image_id = self._generate_image_id(img_path)
                image_info = {
                    "image_path": img_path,
                    "image_id": image_id,
                    "page_number": idx + 1
                }

                base64_img = self._encode_image_to_base64(img_path)
                prompt = self._build_system_prompt()
                raw_response, usage, elapsed = self._call_llm_vision_api(base64_img, prompt)
                parsed_result = self._parse_llm_response(raw_response, image_info, idx + 1)

                # 统计当前图片的表格数量
                current_tables_count = len(parsed_result["tables"])
                current_financial_tables_count = len([t for t in parsed_result["tables"] if t.get("is_financial")])
                total_tables_count += current_tables_count
                total_financial_tables_count += current_financial_tables_count

                image_result = {
                    "image_path": img_path,
                    "image_id": image_id,  # 添加图片ID到结果中
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

                print(f"[INFO] 图片 {idx + 1} (ID: {image_id}) 分析完成，检测到 {current_tables_count} 个表格")

            except Exception as e:
                print(f"[ERROR] 处理 {img_path} 时出错: {e}")
                # 即使出错也生成图片ID
                image_id = self._generate_image_id(img_path)
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

    def analyze_pdf(self, pdf_path: str, temp_dir: str = "./temp_imgs") -> Dict[str, Any]:
        """分析 PDF（内部转为图片后调用 analyze_image_list）"""
        print(f"[INFO] 正在转换 PDF 为图片: {pdf_path}")
        image_info_list = self.pdf_to_images(pdf_path, temp_dir)
        image_paths = [info["image_path"] for info in image_info_list]
        result = self.analyze_image_list(image_paths)
        result["input_type"] = "pdf"
        result["pdf_path"] = pdf_path

        return result

    def analyze(self, input_data: Union[str, List[str]], temp_dir: str = "./temp_imgs") -> Dict[str, Any]:
        """统一入口：自动判断输入类型并分析"""
        if isinstance(input_data, str):
            if not os.path.exists(input_data):
                raise FileNotFoundError(f"输入文件不存在: {input_data}")
            if input_data.lower().endswith('.pdf'):
                return self.analyze_pdf(input_data, temp_dir)
            else:
                # 单张图片
                return self.analyze_image_list([input_data])
        elif isinstance(input_data, list):
            if not input_data:
                raise ValueError("图片列表不能为空")
            return self.analyze_image_list(input_data)
        else:
            raise TypeError("input_data 必须是 PDF 路径（str）或图片路径列表（List[str]）")

    def save_results_to_json(self, result: Dict[str, Any], output_path: str) -> None:
        """
        将分析结果保存到 JSON 文件
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"[INFO] 分析结果已保存到: {output_path}")

        except Exception as e:
            print(f"[ERROR] 保存结果到 JSON 文件失败: {e}")
            raise





# ========================
# 使用示例
# ========================
if __name__ == "__main__":
    # 从外部导入配置参数
    API_KEY = "90b9c47f-815c-4216-913a-3d1a567e35ac"
    BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
    MODEL_NAME = "doubao-1-5-vision-pro-250328"

    # 初始化分析器
    analyzer = FinancialTableAnalyzerLLM(
        api_key=API_KEY,
        base_url=BASE_URL,
        model_name=MODEL_NAME
    )

    # === 示例 1：分析 PDF ===
    # result = analyzer.analyze("report.pdf")
    # analyzer.save_results_to_json(result, "output/report_analysis.json")

    # === 示例 2：分析多张图片 ===
    image_list = []
    image_dir = r"E:\Datas\base_pros\DocuVista\test_codes\pngs"
    for root, _, files in os.walk(image_dir):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_list.append(os.path.join(root, file))
    print("image_list:", image_list)
    image_list = image_list[:2]

    # 分析图片
    result = analyzer.analyze(image_list)

    # 保存结果到 JSON 文件
    cur_dir = os.getcwd()
    output_json_path = f"{cur_dir}/analysis_results.json"

    print("cur_dir:", cur_dir)
    analyzer.save_results_to_json(result, output_json_path)

    # === 打印汇总 ===
    summary = result["summary"]
    print("\n" + "=" * 60)
    print("📊 分析完成！性能与成本汇总")
    print("=" * 60)
    if result["input_type"] == "pdf":
        print(f"输入: PDF 文件 {result['pdf_path']}")
        print(f"总页数: {result['total_images']}")
    else:
        print(f"输入: {result['total_images']} 张图片")

    print(f"总表格数: {summary['total_tables']}")
    print(f"财务表格数: {summary['total_financial_tables']}")
    print(f"总耗时: {summary['total_analysis_time_sec']} 秒")
    print(f"总 Token 消耗: {summary['total_token_usage']['total_tokens']}")

    # === 逐张图片打印表格详情 ===
    print(f"\n📋 逐图片表格详情:")
    print("=" * 60)

    for image_result in result["image_results"]:
        print(f"\n📄 图片: {os.path.basename(image_result['image_path'])}")
        print(f"  页码: {image_result['page_number']}")
        print(f"  表格数量: {image_result['tables_count']}")
        print(f"  财务表格: {image_result['financial_tables_count']}")
        print(f"  分析耗时: {image_result['analysis_time_sec']} 秒")

        if image_result["tables"]:
            for table in image_result["tables"]:
                print(f"\n  ┌─ 表格 {table['table_id']} ──────────────────────")
                table_title = table.get("table_title") or "（无标题）"
                currency = table.get("currency") or "（未注明）"
                reporting_period = table.get("reporting_period") or "（未注明）"
                is_financial = table.get("is_financial", False)

                print(f"  │ 📌 表名: {table_title}")
                print(f"  │ 💱 币种: {currency}")
                print(f"  │ 📅 报告期: {reporting_period}")
                print(f"  │ 💰 财务表格: {'是' if is_financial else '否'}")

                if is_financial:
                    h_fields = table.get("horizontal_hierarchy_fields", [])
                    v_fields = table.get("vertical_hierarchy_fields", [])

                    if h_fields:
                        print(f"  │ ➤ 横向层级字段 ({len(h_fields)}个):")
                        for item in h_fields[:3]:  # 只显示前3个
                            field = item.get("field_path", "")
                            is_stat = item.get("is_statistical", False)
                            stat_tag = " [统计]" if is_stat else ""
                            print(f"  │   • {field}{stat_tag}")
                        if len(h_fields) > 3:
                            print(f"  │   ... 还有 {len(h_fields) - 3} 个字段")

                    if v_fields:
                        print(f"  │ ➤ 纵向层级字段 ({len(v_fields)}个):")
                        for item in v_fields[:3]:  # 只显示前3个
                            field = item.get("field_path", "")
                            is_stat = item.get("is_statistical", False)
                            stat_tag = " [统计]" if is_stat else ""
                            print(f"  │   • {field}{stat_tag}")
                        if len(v_fields) > 3:
                            print(f"  │   ... 还有 {len(v_fields) - 3} 个字段")

                print(f"  └────────────────────────────────────────")
        else:
            print(f"  ❌ 未检测到表格")
