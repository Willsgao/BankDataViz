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
你是一名专业的金融文档分析师，请严格按以下规则分析图像中的所有表格：

## 分析步骤
1. 识别图像中所有的表格（包括无线框表格），按从上到下、从左到右的顺序编号为 Table 1, Table 2, ..., Table N。
2. 对每个表格：
   a. 判断是否为财务相关表格（含资产、负债、收入、利润、现金流量、股东权益、贷款、利息、准备金、折旧、摊销、应收款、应付款、股本、净利润、毛利率等关键词）。
   b. 如果是财务表格：
      - 提取横向（列方向）的带层级字段名，格式为路径形式，例如："2024年 > 平均余额"、"项目 > 公司类贷款 > 短期贷款"
      - 提取纵向（行方向）的带层级字段名，格式同上，例如："地区 > 华东 > 上海"、"费用 > 销售费用 > 广告费"
      - 层级关系指：父级标题覆盖多个子项（即使无合并单元格，只要语义上有包含关系即可）
   c. 如果不是财务表格，字段名列表留空。

## 输出格式（必须严格遵守）
- 仅输出一个合法的 JSON 对象，不要任何额外文字、解释或 Markdown
- 结构如下：
{
  "has_table": true,
  "tables": [
    {
      "table_id": 1,
      "is_financial": true,
      "horizontal_hierarchy_fields": ["2024年 > 利润", "2023年 > 收入"],
      "vertical_hierarchy_fields": ["项目 > 资产 > 流动资产", "项目 > 负债"]
    },
    ...
  ]
}
- 如果没有表格，输出：{"has_table": false, "tables": []}
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

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """解析 LLM 返回的 JSON 字符串，容错处理"""
        import json
        try:
            # 清理可能的 ```json 包裹
            cleaned = re.sub(r'^```json\s*|\s*```$', '', response_text.strip())
            data = json.loads(cleaned)
            has_table = data.get("has_table", False)
            tables = data.get("tables", [])
            return {
                "has_table": bool(has_table),
                "tables": tables
            }
        except (json.JSONDecodeError, ValueError) as e:
            # 解析失败时返回安全默认值
            print(f"[WARN] JSON 解析失败，跳过该图。错误: {e}")
            return {
                "has_table": False,
                "tables": []
            }

    def analyze_image_list(self, image_paths: List[str]) -> Dict[str, Any]:
        """分析一组图片（支持 JPG/PNG 等），返回结构化结果"""
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
                    "has_table": parsed_result["has_table"],
                    "tables": parsed_result["tables"]
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
                    "tables": [],
                    "error": str(e),
                    "analysis_time_sec": 0,
                    "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                })

        # 提取所有财务表格详情（用于汇总）
        financial_tables_detail = []
        for idx, res in enumerate(results):
            for tbl in res.get("tables", []):
                if tbl.get("is_financial", False):
                    financial_tables_detail.append({
                        "image_index": idx + 1,
                        "image_path": res["image_path"],
                        "table_id": tbl["table_id"],
                        "horizontal_hierarchy_fields": tbl.get("horizontal_hierarchy_fields", []),
                        "vertical_hierarchy_fields": tbl.get("vertical_hierarchy_fields", [])
                    })

        return {
            "input_type": "image_list",
            "total_images": len(image_paths),
            "financial_tables_detail": financial_tables_detail,
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
        # 将 image_index 映射为页码
        for ft in result["financial_tables_detail"]:
            ft["page_number"] = ft.pop("image_index")
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
    for root, _, files in os.walk(image_dir):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_list.append(os.path.join(root, file))
    print("image_list:", image_list)
    result = analyzer.analyze(image_list)

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

    print(f"总耗时: {summary['total_analysis_time_sec']} 秒")
    print(f"总 Token 消耗: {summary['total_token_usage']['total_tokens']}")

    # === 打印所有财务表格详情 ===
    financial_tables = result.get("financial_tables_detail", [])
    if not financial_tables:
        print("\n❌ 未检测到财务类表格")
    else:
        print(f"\n✅ 共检测到 {len(financial_tables)} 个财务表格：")
        for ft in financial_tables:
            if result["input_type"] == "pdf":
                loc = f"Page {ft['page_number']}"
            else:
                loc = f"Image {ft['image_index']}"
            print(f"\n📄 {loc} - Table {ft['table_id']}")
            h_fields = ft.get("horizontal_hierarchy_fields", [])
            v_fields = ft.get("vertical_hierarchy_fields", [])
            if h_fields:
                print("  横向层级字段:")
                for f in h_fields:
                    print(f"    • {f}")
            if v_fields:
                print("  纵向层级字段:")
                for f in v_fields:
                    print(f"    • {f}")