# -*- coding:utf-8 -*-


from typing import Dict, Any, List, Tuple
import re


class OCRProcessor:
    @staticmethod
    def ocr_to_matrix(table_data: Dict[str, Any]) -> Tuple[List[List[str]], Dict[str, int]]:
        """将OCR的body数据转换为行列矩阵"""
        body = table_data.get("body", [])
        if not body:
            return [], {"rows": 0, "cols": 0}

        max_row = max(cell.get("row_end", 0) for cell in body)
        max_col = max(cell.get("col_end", 0) for cell in body)

        matrix = [["" for _ in range(max_col)] for _ in range(max_row)]

        for cell in body:
            text = cell.get("words", "").strip()
            row_start = cell.get("row_start", 0)
            row_end = cell.get("row_end", row_start + 1)
            col_start = cell.get("col_start", 0)
            col_end = cell.get("col_end", col_start + 1)

            for r in range(row_start, row_end):
                for c in range(col_start, col_end):
                    if r < max_row and c < max_col:
                        matrix[r][c] = text

        return matrix, {"rows": max_row, "cols": max_col}

    @staticmethod
    def extract_for_llm(table_data: Dict[str, Any], extract_rows: int = 3, extract_cols: int = 3) -> Dict[str, Any]:
        """提取前三行全列 + 前三列全行数据"""
        matrix, dimensions = OCRProcessor.ocr_to_matrix(table_data)
        rows, cols = dimensions["rows"], dimensions["cols"]

        if rows == 0 or cols == 0:
            return {"success": False, "error": "空表格"}

        # 提取前三行所有列
        top_rows = []
        for r in range(min(extract_rows, rows)):
            top_rows.append(matrix[r][:])  # 该行所有列

        # 提取前三列所有行
        left_cols = []
        for r in range(rows):
            left_cols.append(matrix[r][:min(extract_cols, cols)])  # 该行前三列

        total_cells = rows * cols
        extracted_cells = (extract_rows * cols) + (rows * extract_cols) - (extract_rows * extract_cols)

        return {
            "success": True,
            "dimensions": dimensions,
            "extracted_data": {
                "top_rows_all_cols": top_rows,
                "left_cols_all_rows": left_cols
            },
            "stats": {
                "cells_extracted": extracted_cells,
                "coverage_percentage": round(extracted_cells / total_cells * 100, 1) if total_cells > 0 else 0
            }
        }