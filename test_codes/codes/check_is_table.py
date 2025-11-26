import os
import re
import base64
import time
import fitz  # PyMuPDF
from typing import List, Dict, Any, Union
from openai import OpenAI


class FinancialTableAnalyzerLLM:
    """
    支持分析 PDF 或图片列表，判断是否包含财务表格，
    并分析线框省略情况、字段层级关系，同时统计耗时与 Token 消耗。
    """

    def __init__(self, api_key: str, model_name: str = "doubao-1-5-vision-pro-250328"):
        self.api_key = api_key
        self.model_name = model_name
        self.client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=self.api_key
        )

    def _encode_image_to_base64(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def pdf_to_images(self, pdf_path: str, output_dir: str) -> List[str]:
        """将 PDF 转为图片列表"""
        os.makedirs(output_dir, exist_ok=True)
        doc = fitz.open(pdf_path)
        image_paths = []
        for i, page in enumerate(doc):
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img_path = os.path.join(output_dir, f"page_{i + 1}.png")
            pix.save(img_path)
            image_paths.append(img_path)
        doc.close()
        return image_paths

    def _build_system_prompt(self) -> str:
        return '''
你是一名专业的金融文档分析师。请严格按以下规则分析图像：

## 分析任务
1. 判断图像中是否存在表格（包括不完整边框的表格）。
2. 若存在表格，判断是否为财务相关表格（如含资产、负债、收入、利润、现金流量等字段）。
3. 判断表格的边框情况：
   - 横向线框是否省略？（即行之间无横线）
   - 纵向线框是否省略？（即列之间无竖线）
4. 判断字段是否存在层级关系：
   - 横向层级：同一行中是否有父级标题覆盖多个子列
   - 纵向层级：同一列中是否有父级标题覆盖多个子行

## 输出格式（必须严格遵守，每行以指定前缀开头，结尾加 _END）
是否有表格：是/否_END
是否为财务表格：是/否_END
横向线框是否省略：是/否_END
纵向线框是否省略：是/否_END
是否存在横向层级：是/否_END
是否存在纵向层级：是/否_END
'''

    def _call_llm_vision_api(self, base64_image: str, prompt: str) -> tuple[str, dict, float]:
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
            content = response.choices[0].message.content

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

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        def extract_field(pattern: str, text: str, default: str = "否") -> str:
            match = re.search(pattern, text)
            return match.group(1) if match else default

        return {
            "has_table": extract_field(r"是否有表格[:：]\s*(是|否)", response_text) == "是",
            "is_financial": extract_field(r"是否为财务表格[:：]\s*(是|否)", response_text) == "是",
            "horizontal_lines_omitted": extract_field(r"横向线框是否省略[:：]\s*(是|否)", response_text) == "是",
            "vertical_lines_omitted": extract_field(r"纵向线框是否省略[:：]\s*(是|否)", response_text) == "是",
            "has_horizontal_hierarchy": extract_field(r"是否存在横向层级[:：]\s*(是|否)", response_text) == "是",
            "has_vertical_hierarchy": extract_field(r"是否存在纵向层级[:：]\s*(是|否)", response_text) == "是",
        }

    def analyze_image_list(self, image_paths: List[str]) -> Dict[str, Any]:
        """
        分析一组图片（支持 JPG/PNG 等），返回结构化结果
        """
        print(f"[INFO] 即将分析 {len(image_paths)} 张图片")
        results = []
        total_time = 0.0
        total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        for img_path in image_paths:
            if not os.path.exists(img_path):
                print(f"[WARN] 图片不存在，跳过: {img_path}")
                continue

            print(f"[INFO] 正在分析: {img_path}")
            try:
                base64_img = self._encode_image_to_base64(img_path)
                prompt = self._build_system_prompt()
                raw_response, usage, elapsed = self._call_llm_vision_api(base64_img, prompt)
                parsed_result = self._parse_llm_response(raw_response)

                result = {
                    "image_path": img_path,
                    "raw_llm_output": raw_response,
                    "analysis_time_sec": round(elapsed, 2),
                    "token_usage": usage,
                    **parsed_result
                }
                results.append(result)

                total_time += elapsed
                total_tokens["prompt_tokens"] += usage["prompt_tokens"]
                total_tokens["completion_tokens"] += usage["completion_tokens"]
                total_tokens["total_tokens"] += usage["total_tokens"]

            except Exception as e:
                print(f"[ERROR] 处理 {img_path} 时出错: {e}")
                results.append({
                    "image_path": img_path,
                    "has_table": False,
                    "is_financial": False,
                    "error": str(e),
                    "analysis_time_sec": 0,
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                })

        financial_pages = [
            i + 1 for i, r in enumerate(results)
            if r.get("is_financial", False)
        ]

        return {
            "input_type": "image_list",
            "total_images": len(image_paths),
            "financial_table_indices": financial_pages,  # 从1开始的索引
            "image_results": results,
            "summary": {
                "total_analysis_time_sec": round(total_time, 2),
                "total_token_usage": total_tokens
            }
        }

    def analyze_pdf(self, pdf_path: str, temp_dir: str = "./temp_imgs") -> Dict[str, Any]:
        """分析 PDF（内部转为图片后调用 analyze_image_list）"""
        print(f"[INFO] 正在转换 PDF 为图片: {pdf_path}")
        image_paths = self.pdf_to_images(pdf_path, temp_dir)
        result = self.analyze_image_list(image_paths)
        result["input_type"] = "pdf"
        result["pdf_path"] = pdf_path
        # 将 indices 改为页码（与 PDF 页码一致）
        result["financial_table_pages"] = result.pop("financial_table_indices")
        return result

    def analyze(self, input_data: Union[str, List[str]], temp_dir: str = "./temp_imgs") -> Dict[str, Any]:
        """
        统一入口：自动判断输入类型并分析
        :param input_data: PDF 路径（str）或图片路径列表（List[str]）
        :param temp_dir: PDF 转图临时目录
        :return: 分析结果
        """
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


# ========================
# 使用示例
# ========================
if __name__ == "__main__":
    API_KEY = "90b9c47f-815c-4216-913a-3d1a567e35ac"

    analyzer = FinancialTableAnalyzerLLM(api_key=API_KEY)

    # === 示例 1：分析 PDF ===
    # result = analyzer.analyze("report.pdf")

    # === 示例 2：分析多张图片 ===
    image_list = []

    image_dir = r"E:\Datas\base_pros\DocuVista\test_codes\pngs"
    for root,_, files in os.walk(image_dir):
        for file in files:
            image_name = f"{root}/{file}"
            image_list.append(image_name)

    print("image_list:", image_list)

    result = analyzer.analyze(image_list)

    # === 打印汇总 ===
    summary = result["summary"]
    print("\n" + "="*60)
    print("📊 分析完成！性能与成本汇总")
    print("="*60)
    if result["input_type"] == "pdf":
        print(f"输入: PDF 文件 {result['pdf_path']}")
        print(f"总页数: {result['total_images']}")
        print(f"含财务表格的页码: {result.get('financial_table_pages', [])}")
    else:
        print(f"输入: {result['total_images']} 张图片")
        print(f"含财务表格的图片序号（从1开始）: {result.get('financial_table_indices', [])}")

    print(f"总耗时: {summary['total_analysis_time_sec']} 秒")
    print(f"总 Token 消耗: {summary['total_token_usage']['total_tokens']}")
    print(f"  - Prompt: {summary['total_token_usage']['prompt_tokens']}")
    print(f"  - Completion: {summary['total_token_usage']['completion_tokens']}")

    # === 打印详情 ===
    results_key = "image_results" if result["input_type"] == "image_list" else "image_results"
    for i, res in enumerate(result[results_key]):
        if res.get("is_financial"):
            basename = os.path.basename(res["image_path"])
            print(f"\n📄 {basename}")
            print(f"  耗时: {res['analysis_time_sec']}s | Tokens: {res['token_usage']['total_tokens']}")
            print(f"  无线框 → 横向: {'✅' if res['horizontal_lines_omitted'] else '❌'}, "
                  f"纵向: {'✅' if res['vertical_lines_omitted'] else '❌'}")
            print(f"  层级 → 横向: {'✅' if res['has_horizontal_hierarchy'] else '❌'}, "
                  f"纵向: {'✅' if res['has_vertical_hierarchy'] else '❌'}")