from typing import Dict, Any, List


class DataFormatAdapter:
    """数据格式适配器"""

    @staticmethod
    def normalize_llm_data(llm_data: Dict) -> Dict:
        """标准化LLM数据格式"""
        normalized = {
            "input_type": llm_data.get("input_type", "unknown"),
            "total_images": llm_data.get("total_images", 0),
            "image_results": [],
            "summary": llm_data.get("summary", {})
        }

        for img_result in llm_data.get("image_results", []):
            normalized_img = {
                "image_path": img_result.get("image_path", ""),
                "image_id": img_result.get("image_id", ""),
                "page_number": img_result.get("page_number", 0),
                "has_table": img_result.get("has_table", False),
                "tables": img_result.get("tables", []),
                "tables_count": img_result.get("tables_count", 0),
                "financial_tables_count": img_result.get("financial_tables_count", 0)
            }
            normalized["image_results"].append(normalized_img)

        return normalized

    @staticmethod
    def normalize_ocr_data(ocr_data: Dict) -> Dict:
        """标准化OCR数据格式"""
        if "image_info" not in ocr_data:
            ocr_data["image_info"] = {
                "image_id": "unknown",
                "image_path": "unknown"
            }
        return ocr_data