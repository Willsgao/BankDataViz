# file name: ocr_adapter.py
# -*- coding:utf-8 -*-
"""
OCR适配器层 - 统一不同OCR接口的数据格式
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import json


class OCRCell:
    """统一OCR单元格数据模型"""

    def __init__(self,
                 row_start: int,
                 col_start: int,
                 row_end: int,
                 col_end: int,
                 content: str,
                 confidence: float = 1.0,
                 cell_type: str = "body"):
        self.row_start = row_start
        self.col_start = col_start
        self.row_end = row_end
        self.col_end = col_end
        self.content = content
        self.confidence = confidence
        self.cell_type = cell_type

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "row_start": self.row_start,
            "col_start": self.col_start,
            "row_end": self.row_end,
            "col_end": self.col_end,
            "words": self.content,
            "confidence": self.confidence,
            "type": self.cell_type
        }


class OCRTable:
    """统一OCR表格数据模型"""

    def __init__(self, cells: List[OCRCell]):
        self.cells = cells

    def get_body_cells(self) -> List[OCRCell]:
        """获取主体单元格"""
        return [cell for cell in self.cells if cell.cell_type == "body"]

    def get_header_cells(self) -> List[OCRCell]:
        """获取表头单元格"""
        return [cell for cell in self.cells if cell.cell_type == "header"]

    def get_footer_cells(self) -> List[OCRCell]:
        """获取页脚单元格"""
        return [cell for cell in self.cells if cell.cell_type == "footer"]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "body": [cell.to_dict() for cell in self.get_body_cells()],
            "header": [cell.to_dict() for cell in self.get_header_cells()],
            "footer": [cell.to_dict() for cell in self.get_footer_cells()]
        }

    def get_dimensions(self) -> Dict[str, int]:
        """获取表格维度"""
        max_row = 0
        max_col = 0
        for cell in self.cells:
            max_row = max(max_row, cell.row_end)
            max_col = max(max_col, cell.col_end)
        return {"rows": max_row + 1, "cols": max_col + 1}


class BaseOCRAdapter(ABC):
    """OCR适配器基类"""

    @abstractmethod
    def adapt(self, ocr_result: Dict[str, Any]) -> List[OCRTable]:
        """将OCR结果适配为标准格式"""
        pass


class BaiduOCRAdapter(BaseOCRAdapter):
    """百度OCR适配器"""

    def adapt(self, ocr_result: Dict[str, Any]) -> List[OCRTable]:
        """适配百度OCR结果"""
        tables_result = ocr_result.get("tables_result", [])
        adapted_tables = []

        for table_idx, table_data in enumerate(tables_result):
            cells = []

            # 处理body单元格
            body_cells = table_data.get("body", [])
            for cell_data in body_cells:
                cell = OCRCell(
                    row_start=cell_data.get("row_start", 0),
                    col_start=cell_data.get("col_start", 0),
                    row_end=cell_data.get("row_end", 0),
                    col_end=cell_data.get("col_end", 0),
                    content=cell_data.get("words", ""),
                    confidence=cell_data.get("confidence", 1.0),
                    cell_type="body"
                )
                cells.append(cell)

            # 百度OCR可能没有单独的header/footer
            adapted_table = OCRTable(cells)
            adapted_tables.append(adapted_table)

        return adapted_tables


class TencentOCRAdapter(BaseOCRAdapter):
    """腾讯OCR适配器"""

    def adapt(self, ocr_result: Dict[str, Any]) -> List[OCRTable]:
        """适配腾讯OCR结果"""
        response_data = ocr_result.get("Response", {})
        table_detections = response_data.get("TableDetections", [])
        adapted_tables = []

        for table_data in table_detections:
            cells = []
            table_cells = table_data.get("Cells", [])

            # 腾讯OCR的Type字段标识单元格类型
            cell_type_mapping = {
                "header": "header",
                "body": "body",
                "footer": "footer"
            }

            for cell_data in table_cells:
                # 腾讯OCR使用Row, Col, RowSpan, ColSpan
                row_start = cell_data.get("Row", 0)
                col_start = cell_data.get("Col", 0)
                row_span = cell_data.get("RowSpan", 1)
                col_span = cell_data.get("ColSpan", 1)

                cell = OCRCell(
                    row_start=row_start,
                    col_start=col_start,
                    row_end=row_start + row_span - 1,
                    col_end=col_start + col_span - 1,
                    content=cell_data.get("Content", ""),
                    confidence=cell_data.get("Confidence", 100) / 100.0,
                    cell_type=cell_type_mapping.get(cell_data.get("Type", "body"), "body")
                )
                cells.append(cell)

            adapted_table = OCRTable(cells)
            adapted_tables.append(adapted_table)

        return adapted_tables


class OCRAdapterFactory:
    """OCR适配器工厂"""

    @staticmethod
    def create_adapter(ocr_type: str = "baidu") -> BaseOCRAdapter:
        """创建适配器"""
        adapters = {
            "baidu": BaiduOCRAdapter,
            "tencent": TencentOCRAdapter
        }

        adapter_class = adapters.get(ocr_type.lower())
        if not adapter_class:
            raise ValueError(f"不支持的OCR类型: {ocr_type}")

        return adapter_class()


class UniversalOCRResult:
    """统一OCR结果类"""

    def __init__(self, image_info: Dict[str, Any], tables: List[OCRTable]):
        self.image_info = image_info
        self.tables = tables

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（保持向后兼容）"""
        return {
            "image_info": self.image_info,
            "tables_result": [table.to_dict() for table in self.tables],
            "success": True
        }

    def get_compatibility_format(self) -> Dict[str, Any]:
        """获取兼容格式（用于现有代码）"""
        # 转换为现有代码期望的格式
        tables_result = []
        for table in self.tables:
            tables_result.append({
                "body": [cell.to_dict() for cell in table.get_body_cells()],
                "header": [cell.to_dict() for cell in table.get_header_cells()],
                "footer": [cell.to_dict() for cell in table.get_footer_cells()]
            })

        return {
            "image_info": self.image_info,
            "tables_result": tables_result
        }

