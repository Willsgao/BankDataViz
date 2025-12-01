# -*- coding:utf-8 -*-
"""
Excel导出模块 - 基于分析结果生成Excel表格（完全替换表头版）
"""
import os
import json
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font, Border, Side, PatternFill
from typing import Dict, List, Any, Optional, Tuple
import re


# 在 excel_exporter.py 文件开头或合适位置添加以下类

class OCRDataAdapter:
    """OCR数据适配器 - 处理不同来源的OCR数据结构"""

    @staticmethod
    def extract_table_data(data_source: Dict[str, Any]) -> List[List[str]]:
        """
        从不同来源的OCR数据中提取表格数据

        Args:
            data_source: OCR数据源，可能是不同格式

        Returns:
            二维列表表示的表格数据
        """
        if not data_source:
            return []

        # 1. 尝试从百度OCR原始结构提取
        if "tables_result" in data_source:
            return OCRDataAdapter._from_baidu_ocr(data_source)

        # 2. 尝试从处理后的OCR结构提取
        if "extracted_data" in data_source:
            return OCRDataAdapter._from_processed_ocr(data_source)

        # 3. 尝试从LLM分析结果结构提取
        if "table_headers" in data_source:
            return OCRDataAdapter._from_llm_analysis(data_source)

        # 4. 尝试从其他常见结构提取
        return OCRDataAdapter._try_common_formats(data_source)

    @staticmethod
    def _from_baidu_ocr(ocr_data: Dict[str, Any], table_index: int = 0) -> List[List[str]]:
        tables_result = ocr_data.get("tables_result", [])
        if not tables_result:
            return []

        # 根据索引获取对应的表格
        if table_index < len(tables_result):
            table = tables_result[table_index]
            return OCRDataAdapter._parse_baidu_table_body(table)
        return []

    @staticmethod
    def _parse_baidu_table_body(table: Dict[str, Any]) -> List[List[str]]:
        """解析百度OCR表格body数据"""
        body_cells = table.get("body", [])

        if not body_cells:
            return []

        # 计算表格最大行列
        max_row = 0
        max_col = 0
        for cell in body_cells:
            max_row = max(max_row, cell.get("row_end", 0))
            max_col = max(max_col, cell.get("col_end", 0))

        # 创建空表格（+1因为索引从0开始）
        table_data = [["" for _ in range(max_col + 1)] for _ in range(max_row + 1)]

        # 填充数据
        for cell in body_cells:
            row_start = cell.get("row_start", 0)
            col_start = cell.get("col_start", 0)
            row_end = cell.get("row_end", row_start)
            col_end = cell.get("col_end", col_start)
            words = cell.get("words", "")

            # 处理合并单元格
            for r in range(row_start, row_end + 1):
                for c in range(col_start, col_end + 1):
                    if r < len(table_data) and c < len(table_data[0]):
                        # 如果单元格已填充且不为空，用"/"分隔（处理重叠）
                        if table_data[r][c] and table_data[r][c] != words:
                            table_data[r][c] = f"{table_data[r][c]}/{words}"
                        else:
                            table_data[r][c] = words

        # 清理空行和空列
        return OCRDataAdapter._clean_table(table_data)

    @staticmethod
    def _from_processed_ocr(ocr_data: Dict[str, Any]) -> List[List[str]]:
        """从处理后的OCR结构提取表格数据"""
        extracted_data = ocr_data.get("extracted_data", {})

        # 尝试不同的数据键
        data_keys = ["top_rows_all_cols", "left_cols_all_rows", "grid",
                     "table_data", "data", "cells"]

        for key in data_keys:
            if key in extracted_data:
                data = extracted_data[key]
                if data and isinstance(data, list):
                    # 确保是二维列表
                    if data and isinstance(data[0], list):
                        return data
                    else:
                        # 转换为一维列表到二维列表
                        return [data]

        return []

    @staticmethod
    def _from_llm_analysis(llm_data: Dict[str, Any]) -> List[List[str]]:
        """从LLM分析结果提取表格数据"""
        # LLM分析结果可能包含OCR原始数据引用
        if "source_data" in llm_data:
            source_data = llm_data.get("source_data", {})
            if "ocr_extract" in source_data:
                return OCRDataAdapter.extract_table_data(source_data["ocr_extract"])

        return []

    @staticmethod
    def _try_common_formats(data: Dict[str, Any]) -> List[List[str]]:
        """尝试常见的数据格式"""
        # 尝试直接是列表的情况
        if isinstance(data, list):
            if data and isinstance(data[0], list):
                return data
            elif data:
                return [data]

        # 尝试从"data"键获取
        if "data" in data and isinstance(data["data"], list):
            return OCRDataAdapter._try_common_formats(data["data"])

        return []

    @staticmethod
    def _clean_table(table_data: List[List[str]]) -> List[List[str]]:
        """清理表格：移除完全空白的行和列"""
        if not table_data:
            return []

        # 找出有数据的列
        has_data_cols = set()
        for row in table_data:
            for col_idx, cell in enumerate(row):
                if cell and str(cell).strip():
                    has_data_cols.add(col_idx)

        if not has_data_cols:
            return []

        # 过滤列
        cleaned_data = []
        min_col = min(has_data_cols)
        max_col = max(has_data_cols)

        for row in table_data:
            # 提取有数据的列范围
            cleaned_row = row[min_col:max_col + 1]
            # 检查行是否有数据
            if any(cell and str(cell).strip() for cell in cleaned_row):
                cleaned_data.append(cleaned_row)

        return cleaned_data

    @staticmethod
    def get_table_metadata(ocr_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取表格元数据"""
        metadata = {
            "source_type": "unknown",
            "table_count": 0,
            "dimensions": {"rows": 0, "cols": 0}
        }

        if "tables_result" in ocr_data:
            metadata["source_type"] = "baidu_ocr"
            tables = ocr_data.get("tables_result", [])
            metadata["table_count"] = len(tables)

            if tables:
                table = tables[0]
                body_cells = table.get("body", [])
                if body_cells:
                    max_row = max(cell.get("row_end", 0) for cell in body_cells)
                    max_col = max(cell.get("col_end", 0) for cell in body_cells)
                    metadata["dimensions"] = {
                        "rows": max_row + 1,
                        "cols": max_col + 1
                    }

        elif "extracted_data" in ocr_data:
            metadata["source_type"] = "processed_ocr"
            data = OCRDataAdapter._from_processed_ocr(ocr_data)
            if data:
                metadata["dimensions"] = {
                    "rows": len(data),
                    "cols": len(data[0]) if data[0] else 0
                }

        return metadata

class ExcelTableGenerator:
    """Excel表格生成器（完全替换表头）"""

    def __init__(self):
        # 样式定义
        self.thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # 表头样式
        self.header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        self.header_font = Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')

        # 数据样式
        self.data_font = Font(name='微软雅黑', size=10)

        # 错误样式
        self.error_fill = PatternFill(start_color="FF9999", end_color="FF9999", fill_type="solid")
        self.error_font = Font(name='微软雅黑', size=10, bold=True, color="FF0000")

        # OCR原始数据工作表后缀
        self.ocr_sheet_suffix = "_原始OCR"
        self.ocr_adapter = OCRDataAdapter()

    def extract_pure_data_from_ocr(self, ocr_extract: Dict[str, Any],
                                   horizontal_headers_count: int,
                                   vertical_headers_count: int) -> List[List[str]]:
        """
        从OCR数据中提取纯数据部分（删除表头行和表头列）
        """
        extracted_data = ocr_extract.get("extracted_data", {})

        # 使用top_rows_all_cols作为完整表格数据
        table_data = extracted_data.get("top_rows_all_cols", [])

        if not table_data:
            return []

        # 删除水平表头行
        if horizontal_headers_count > 0:
            horizontal_headers_count = min(horizontal_headers_count, len(table_data))
            # table_data = table_data[horizontal_headers_count:]

        # 删除垂直表头列
        if vertical_headers_count > 0:
            pure_data = []
            for row in table_data:
                if vertical_headers_count < len(row):
                    pure_row = row[vertical_headers_count:]
                else:
                    pure_row = []
                pure_data.append(pure_row)

            return pure_data

        return table_data

    def identify_headers_from_ocr(self, ocr_extract: Dict[str, Any]) -> Tuple[int, int]:
        """
        尝试从OCR数据中识别表头行数和列数
        """
        extracted_data = ocr_extract.get("extracted_data", {})
        table_data = extracted_data.get("top_rows_all_cols", [])

        if not table_data:
            return 1, 1

        horizontal_headers = 1
        vertical_headers = 1

        return horizontal_headers, vertical_headers

    def create_summary_sheet_data(self, analysis_results: Dict[str, Any]) -> List[List[str]]:
        """创建汇总表数据（支持新格式，增加质量信息）"""
        summary_data = []

        # 标题行
        summary_data.append(["📊 对齐统计", "", "", "", "", "", "", "", "", "", "", ""])

        # 从分析结果中获取统计数据
        tables_count = analysis_results.get("tables_count", 0)
        summary = analysis_results.get("summary", {})
        successfully_analyzed = summary.get("successfully_analyzed", 0)
        failed = summary.get("failed", 0)

        summary_data.append([f"LLM识别表格: {tables_count} 个", "", "", "", "", "", "", "", "", "", "", ""])
        summary_data.append([f"OCR识别表格: {tables_count} 个", "", "", "", "", "", "", "", "", "", "", ""])
        summary_data.append([f"成功匹配: {successfully_analyzed} 个", "", "", "", "", "", "", "", "", "", "", ""])
        summary_data.append([f"未匹配LLM表格: {failed} 个", "", "", "", "", "", "", "", "", "", "", ""])
        summary_data.append([f"未匹配OCR表格: 0 个", "", "", "", "", "", "", "", "", "", "", ""])
        summary_data.append(["", "", "", "", "", "", "", "", "", "", "", ""])

        # 表头行（增加状态列和特征值列）
        summary_data.append(["表格ID", "表格标题", "是否财务报表", "货币单位", "报告期间",
                             "匹配相似度", "水平层级数", "垂直层级数", "OCR单元格数", "表头单元格数",
                             "处理状态", "特征值"])

        # 为每个表格添加行
        tables_analysis = analysis_results.get("tables_analysis", [])
        for i, table_result in enumerate(tables_analysis):
            if table_result.get("success", False):
                table_info = table_result.get("table_info", {})
                analysis_result = table_result.get("analysis_result", {})
                table_headers = analysis_result.get("table_headers", {})
                ocr_extract = table_result.get("source_data", {}).get("ocr_extract", {})

                # 获取分析质量信息
                ocr_data_quality = analysis_result.get("ocr_data_quality", {})
                matching_summary = analysis_result.get("matching_summary", {})
                consistency_checks = analysis_result.get("consistency_checks", {})

                # 获取表头数量 - 支持新旧格式
                # 1. 尝试新格式
                horizontal_for_replacement = table_headers.get("horizontal_for_replacement", [])
                vertical_for_replacement = table_headers.get("vertical_for_replacement", [])

                horizontal_count = len(horizontal_for_replacement)
                vertical_count = len(vertical_for_replacement)

                # 2. 如果新格式为空，尝试旧格式
                if horizontal_count == 0:
                    horizontal_headers = table_headers.get("horizontal", [])
                    if isinstance(horizontal_headers, list):
                        horizontal_count = len(horizontal_headers)
                    else:
                        horizontal_count = 0

                if vertical_count == 0:
                    vertical_headers = table_headers.get("vertical", [])
                    if isinstance(vertical_headers, list):
                        vertical_count = len(vertical_headers)
                    else:
                        vertical_count = 0

                # 获取OCR位置信息 - 支持新旧格式
                ocr_positions = table_headers.get("ocr_positions", {})
                header_positions = table_headers.get("header_positions", {})

                # 计算水平表头行数
                horizontal_header_rows = ocr_positions.get("horizontal_header_rows",
                                                           header_positions.get("horizontal_header_rows", []))
                horizontal_header_depth = len(horizontal_header_rows)

                # 计算垂直表头列数
                vertical_header_cols = ocr_positions.get("vertical_header_cols",
                                                         header_positions.get("vertical_header_cols", []))
                vertical_header_depth = len(vertical_header_cols)

                # 获取OCR单元格数
                dimensions = table_info.get("dimensions", {})
                ocr_cells = dimensions.get("rows", 0) * dimensions.get("cols", 0)

                if ocr_extract:
                    stats = ocr_extract.get("stats", {})
                    ocr_cells = stats.get("cells_extracted", ocr_cells)

                # 表格标题
                table_title = table_info.get("title", f"表格_{table_info.get('table_id', i + 1)}")

                # 获取匹配相似度
                match_similarity = "1"  # 默认值

                # 从匹配摘要中获取匹配率
                if matching_summary:
                    horizontal_match_rate = matching_summary.get("horizontal_match_rate", "100%")
                    vertical_match_rate = matching_summary.get("vertical_match_rate", "100%")

                    # 转换百分比到0-1之间的小数
                    try:
                        h_rate = float(horizontal_match_rate.strip('%')) / 100
                        v_rate = float(vertical_match_rate.strip('%')) / 100
                        avg_rate = (h_rate + v_rate) / 2
                        match_similarity = f"{avg_rate:.2f}"
                    except:
                        match_similarity = "1"

                # 获取置信度
                confidence = matching_summary.get("confidence_level", "high")
                if isinstance(confidence, str):
                    if confidence.lower() == "high":
                        confidence_score = "高"
                    elif confidence.lower() == "medium":
                        confidence_score = "中"
                    elif confidence.lower() == "low":
                        confidence_score = "低"
                    else:
                        confidence_score = confidence
                else:
                    confidence_score = "高"

                # 获取OCR数据质量
                data_quality = ocr_data_quality.get("data_quality", "")
                coverage = ocr_data_quality.get("coverage_percentage", 100)
                quality_note = ocr_data_quality.get("notes", "")

                # 特征值：包含更多信息
                features_parts = []

                # 基础特征
                if horizontal_count > 0 and vertical_count > 0:
                    features_parts.append(f"H{horizontal_count}V{vertical_count}")

                # 表头深度
                if horizontal_header_depth > 0 or vertical_header_depth > 0:
                    features_parts.append(f"R{horizontal_header_depth}C{vertical_header_depth}")

                # 匹配质量
                if confidence_score == "中" or confidence_score == "低":
                    features_parts.append(f"置信度{confidence_score}")

                # 数据质量
                if data_quality and data_quality != "好":
                    features_parts.append(f"质量{data_quality}")

                # 覆盖率
                if coverage < 90:
                    features_parts.append(f"覆盖{coverage}%")

                # 组合特征值
                if features_parts:
                    features = " ".join(features_parts)
                else:
                    features = f"H{horizontal_count}V{vertical_count}"

                # 处理状态
                # 检查是否需要人工干预
                needs_human = False
                if consistency_checks:
                    table_count_check = consistency_checks.get("table_count", {})
                    text_vs_visual = consistency_checks.get("text_vs_visual", {})

                    if table_count_check.get("needs_human") or text_vs_visual.get("needs_human"):
                        needs_human = True

                header_ocr_match = consistency_checks.get("header_ocr_match", {})
                if header_ocr_match.get("needs_human"):
                    needs_human = True

                # 确定处理状态
                if needs_human:
                    processing_status = "需人工检查"
                elif confidence_score == "低":
                    processing_status = "低置信度"
                elif data_quality == "差":
                    processing_status = "数据质量差"
                else:
                    processing_status = "成功"

                # 报告期间推断（从水平表头中提取年份）
                report_period = ""
                if horizontal_for_replacement:
                    # 从表头中提取年份信息
                    years = []
                    for header in horizontal_for_replacement[:5]:  # 只检查前5个
                        if header and isinstance(header, str):
                            # 查找年份模式
                            year_match = re.search(r'(\d{4})年?', header)
                            if year_match:
                                years.append(year_match.group(1))

                    if years:
                        # 按数字排序
                        years_sorted = sorted(years, key=int)
                        if len(years_sorted) > 1:
                            report_period = f"{years_sorted[0]}-{years_sorted[-1]}"
                        else:
                            report_period = years_sorted[0]

                # 计算表头单元格数
                header_cells = 0
                if horizontal_header_depth > 0 and vertical_header_depth > 0:
                    header_cells = (horizontal_header_depth * (dimensions.get("cols", 0) - vertical_header_depth) +
                                    (vertical_header_depth * dimensions.get("rows", 0)))
                elif horizontal_count > 0 and vertical_count > 0:
                    header_cells = horizontal_count + vertical_count

                summary_data.append([
                    table_info.get("table_id", i + 1),  # 表格ID
                    table_title,  # 表格标题
                    "是",  # 是否财务报表
                    "人民币",  # 货币单位
                    report_period,  # 报告期间
                    match_similarity,  # 匹配相似度
                    horizontal_count,  # 水平层级数
                    vertical_count,  # 垂直层级数
                    ocr_cells,  # OCR单元格数
                    header_cells,  # 表头单元格数
                    processing_status,  # 处理状态
                    features  # 特征值
                ])
            else:
                # 失败的情况
                table_info = table_result.get("table_info", {})
                error_msg = table_result.get("error", "未知错误")

                summary_data.append([
                    table_info.get("table_id", i + 1) if table_info else i + 1,
                    f"表格_{i + 1}",
                    "是",
                    "人民币",
                    "",
                    "0",
                    0,
                    0,
                    0,
                    0,
                    "失败",
                    f"错误: {error_msg[:20]}..."  # 截断错误信息
                ])

        return summary_data

    def extract_raw_ocr_data(self, ocr_extract: Dict[str, Any]) -> List[List[str]]:
        """提取OCR原始数据 - 使用适配器"""
        if not ocr_extract:
            return []

        try:
            # 使用适配器提取数据
            table_data = self.ocr_adapter.extract_table_data(ocr_extract)

            # 添加调试日志
            if table_data:
                print(f"成功提取OCR数据: {len(table_data)}行 × {len(table_data[0]) if table_data[0] else 0}列")
            else:
                print("警告: 未提取到OCR数据，数据结构:", list(ocr_extract.keys())[:5])
                # 尝试打印数据结构用于调试
                import json
                print("OCR数据样本:", json.dumps({k: type(v).__name__ for k, v in ocr_extract.items()}, indent=2))

            return table_data

        except Exception as e:
            print(f"提取OCR数据时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def save_ocr_raw_data(self, worksheet, ocr_data: List[List[str]]):
        """保存OCR原始数据到工作表 - 增强版"""
        if not ocr_data:
            worksheet.cell(row=1, column=1, value="无OCR原始数据")
            # 添加调试信息
            worksheet.cell(row=2, column=1, value="⚠️ OCR数据为空或格式不支持")
            return

        print(f"保存OCR数据到工作表: {len(ocr_data)}行 × {len(ocr_data[0]) if ocr_data else 0}列")

        # 计算最大列数以正确设置列宽
        max_cols = max(len(row) for row in ocr_data) if ocr_data else 0

        for row_idx, row_data in enumerate(ocr_data, 1):
            # 确保每行都有足够的列
            padded_row = row_data + [""] * (max_cols - len(row_data))

            for col_idx, cell_value in enumerate(padded_row, 1):
                cell = worksheet.cell(row=row_idx, column=col_idx, value=cell_value)
                cell.border = self.thin_border
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.font = self.data_font

        # 调整列宽
        if ocr_data and max_cols > 0:
            for col_idx in range(1, max_cols + 1):
                col_letter = get_column_letter(col_idx)
                max_length = 0

                for row_idx in range(1, len(ocr_data) + 1):
                    cell_value = worksheet.cell(row=row_idx, column=col_idx).value
                    if cell_value:
                        cell_length = len(str(cell_value))
                        max_length = max(max_length, cell_length)

                adjusted_width = min(max(max_length + 2, 10), 30)
                worksheet.column_dimensions[col_letter].width = adjusted_width

        # 在第一行添加数据来源信息
        if ocr_data:
            info_cell = worksheet.cell(row=1, column=max_cols + 1,
                                       value=f"数据行: {len(ocr_data)}, 列: {max_cols}")
            info_cell.font = Font(name='微软雅黑', size=9, italic=True, color='666666')

    def mark_table_in_summary(self, summary_ws, table_id: int, status: str, features: str = "",
                              error_msg: str = ""):
        """在汇总表中标记表格状态"""
        # 找到表格对应的行（从第10行开始是表格数据）
        for row in range(10, summary_ws.max_row + 1):
            cell_value = summary_ws.cell(row=row, column=1).value
            if cell_value == table_id:
                # 更新状态列（第11列）
                status_cell = summary_ws.cell(row=row, column=11, value=status)
                # 更新特征值列（第12列）
                features_cell = summary_ws.cell(row=row, column=12, value=features)

                # 如果状态是失败，应用错误样式
                if status == "失败":
                    status_cell.fill = self.error_fill
                    status_cell.font = self.error_font
                    features_cell.value = error_msg[:50]  # 错误信息作为特征值

                break

    def export_analysis_to_excel(self,
                                 analysis_results: Dict[str, Any],
                                 output_path: str) -> str:
        """将分析结果导出到Excel"""

        # 创建新的工作簿
        wb = Workbook()

        # 移除默认工作表
        default_ws = wb.active
        wb.remove(default_ws)

        # 1. 创建汇总表
        print("创建汇总表...")
        summary_data = self.create_summary_sheet_data(analysis_results)
        ws_summary = wb.create_sheet(title="汇总表")

        # 写入汇总数据
        for row_idx, row_data in enumerate(summary_data, 1):
            for col_idx, cell_value in enumerate(row_data, 1):
                cell = ws_summary.cell(row=row_idx, column=col_idx, value=cell_value)

                cell.border = self.thin_border
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

                # 标题行样式
                if row_idx <= 7:
                    cell.font = Font(bold=True, size=12)
                # 表头行样式
                elif row_idx == 9:
                    cell.font = self.header_font
                    cell.fill = self.header_fill
                # 数据行样式
                elif row_idx > 9:
                    cell.font = self.data_font

        # 调整汇总表列宽
        column_widths = [20, 20, 12, 10, 12, 12, 12, 12, 12, 12, 12, 20]
        for col_idx, width in enumerate(column_widths, 1):
            col_letter = get_column_letter(col_idx)
            ws_summary.column_dimensions[col_letter].width = width

        # 2. 为每个表格创建工作表
        print("创建表格工作表...")
        tables_analysis = analysis_results.get("tables_analysis", [])

        for table_idx, table_result in enumerate(tables_analysis):
            table_info = table_result.get("table_info", {})
            table_id = table_info.get("table_id", table_idx + 1)

            # 获取OCR数据（在try块外定义，确保作用域）
            ocr_extract = table_result.get("source_data", {}).get("ocr_extract", {})

            # 提取OCR数据（在try块外定义）
            ocr_raw_data = []
            ocr_sheet_name = f"P152_表格_{table_id}{self.ocr_sheet_suffix}"

            try:
                # 限制工作表名称长度
                if len(ocr_sheet_name) > 31:
                    ocr_sheet_name = ocr_sheet_name[:31]

                # 调试：打印OCR数据结构
                print(f"\n表格 {table_id} OCR数据结构:")
                print(f"  可用键: {list(ocr_extract.keys())}")

                # 使用适配器获取元数据
                metadata = self.ocr_adapter.get_table_metadata(ocr_extract)
                print(f"  数据源类型: {metadata['source_type']}")
                print(f"  表格维度: {metadata['dimensions']}")

                # 提取数据
                ocr_raw_data = self.extract_raw_ocr_data(ocr_extract)

                # 创建OCR原始数据工作表
                ws_ocr = wb.create_sheet(title=ocr_sheet_name)
                self.save_ocr_raw_data(ws_ocr, ocr_raw_data)
                print(f"  已保存OCR原始数据到工作表: {ocr_sheet_name}")

            except Exception as e:
                print(f"创建OCR原始数据工作表失败: {str(e)}")
                # 即使OCR数据提取失败，也继续处理后续步骤
                # 创建一个空的OCR工作表
                try:
                    ws_ocr = wb.create_sheet(title=ocr_sheet_name)
                    ws_ocr.cell(row=1, column=1, value="OCR数据提取失败")
                    ws_ocr.cell(row=2, column=1, value=f"错误: {str(e)[:100]}")
                except:
                    pass

            # 检查表格是否成功分析
            if not table_result.get("success", False):
                error_msg = table_result.get("error", "未知错误")
                print(f"表格 {table_id} 分析失败: {error_msg}")

                # 尝试获取OCR数据
                ocr_extract = table_result.get("source_data", {}).get("ocr_extract", {})

                # 如果表格1没有OCR数据，尝试从分析结果的完整OCR数据中获取
                if not ocr_extract and table_id == 1:
                    print(f"  表格 {table_id} 没有OCR数据，尝试从完整OCR数据中查找...")
                    # 从analysis_results中获取完整的OCR数据
                    full_ocr_data = analysis_results.get("ocr_data", {})
                    if full_ocr_data and "tables_result" in full_ocr_data:
                        # 提取第一个表格（索引0）作为表格1的数据
                        tables_result = full_ocr_data.get("tables_result", [])
                        if len(tables_result) >= 1:
                            # 创建模拟的ocr_extract结构
                            ocr_extract = {
                                "tables_result": [tables_result[0]],
                                "table_num": 1
                            }
                            print(f"  从完整OCR数据中提取了表格 {table_id} 的数据")

                if ocr_extract:
                    print(f"  尝试使用OCR原始数据恢复表格 {table_id}...")
                    try:
                        self.create_fallback_table_from_ocr(
                            wb, table_id, ocr_extract,
                            error_msg, ws_summary
                        )
                        print(f"  表格 {table_id} 已从OCR数据恢复")
                    except Exception as e:
                        print(f"  OCR数据恢复失败: {str(e)}")
                        self.mark_table_in_summary(ws_summary, table_id, "失败", error_msg=error_msg)
                else:
                    self.mark_table_in_summary(ws_summary, table_id, "失败", error_msg=error_msg)

                continue

            try:
                print(f"处理表格 {table_id}...")

                analysis_result = table_result.get("analysis_result", {})

                # 构建带新表头的表格数据
                table_data, metadata = self.build_table_with_new_headers(analysis_result, ocr_extract)

                if not table_data or metadata.get("error"):
                    error_msg = metadata.get("error", "构建表格失败")
                    print(f"表格 {table_id} 处理失败: {error_msg}")
                    self.mark_table_in_summary(ws_summary, table_id, "失败", error_msg=error_msg)
                    continue

                # 创建新表头工作表
                sheet_name = f"P152_表格_{table_id}"
                if len(sheet_name) > 31:
                    sheet_name = sheet_name[:31]

                ws_table = wb.create_sheet(title=sheet_name)

                # 写入表格数据
                for row_idx, row_data in enumerate(table_data, 1):
                    for col_idx, cell_value in enumerate(row_data, 1):
                        cell = ws_table.cell(row=row_idx, column=col_idx, value=cell_value)

                        cell.border = self.thin_border
                        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

                        # 水平表头区域样式
                        if row_idx <= metadata.get("horizontal_header_depth", 1):
                            cell.font = self.header_font
                            cell.fill = self.header_fill
                        # 垂直表头区域样式
                        elif col_idx <= metadata.get("vertical_header_depth", 1):
                            cell.font = Font(bold=True)
                        else:
                            cell.font = self.data_font

                # 调整列宽
                if table_data:
                    for col_idx in range(1, len(table_data[0]) + 1):
                        col_letter = get_column_letter(col_idx)
                        max_length = 0

                        for row_idx in range(1, len(table_data) + 1):
                            cell_value = ws_table.cell(row=row_idx, column=col_idx).value
                            if cell_value:
                                cell_length = len(str(cell_value))
                                max_length = max(max_length, cell_length)

                        adjusted_width = min(max(max_length + 2, 10), 30)
                        ws_table.column_dimensions[col_letter].width = adjusted_width

                # 计算特征值
                features = f"H{metadata.get('horizontal_header_depth', 0)}×V{metadata.get('vertical_header_depth', 0)}"
                features += f" D{metadata.get('pure_data_rows', 0)}×{metadata.get('pure_data_cols', 0)}"

                # 标记为成功
                self.mark_table_in_summary(ws_summary, table_id, "成功", features)

                print(f"表格 {table_id} 已导出到工作表: {sheet_name}")
                print(f"  特征值: {features}")

            except Exception as e:
                error_msg = str(e)
                print(f"导出表格 {table_id} 时出错: {error_msg}")
                self.mark_table_in_summary(ws_summary, table_id, "失败", error_msg=error_msg)
                import traceback
                traceback.print_exc()

        # 3. 保存工作簿
        try:
            wb.save(output_path)
            print(f"Excel文件已保存到: {output_path}")
        except Exception as e:
            print(f"保存Excel文件失败: {str(e)}")
            raise

        return output_path

    def _looks_like_header(self, cell_content: str) -> bool:
        """判断单元格内容是否看起来像表头"""
        if not cell_content:
            return False

        content = str(cell_content).strip()

        # 表头特征：
        # 1. 不包含数字（或很少数字）
        # 2. 长度较短
        # 3. 包含常见表头词汇

        header_keywords = ['项目', '名称', '金额', '比例', '日期', '年份',
                           '单位', '类型', '状态', '序号', '合计', '总计']

        # 检查是否包含表头关键词
        for keyword in header_keywords:
            if keyword in content:
                return True

        # 检查长度和数字比例
        if len(content) < 20:  # 表头通常较短
            # 计算数字比例
            digit_count = sum(c.isdigit() for c in content)
            if digit_count / max(len(content), 1) < 0.3:  # 数字比例低于30%
                return True

        return False


    # 需要修改 build_table_with_new_headers 方法：
    def build_table_with_new_headers(self, analysis_result: Dict[str, Any],
                                     ocr_extract: Dict[str, Any]) -> Tuple[List[List[str]], Dict[str, Any]]:
        """基于新的LLM分析结果对齐表格"""

        # 获取新结构的数据
        table_headers = analysis_result.get("table_headers", {})

        # 1. 获取用于替换的新表头
        horizontal_for_replacement = table_headers.get("horizontal_for_replacement", [])
        vertical_for_replacement = table_headers.get("vertical_for_replacement", [])

        # 如果新字段不存在，尝试从旧字段获取（兼容性）
        if not horizontal_for_replacement:
            horizontal_headers = table_headers.get("horizontal", [])
            horizontal_for_replacement = [h.get("field_path", "") for h in horizontal_headers]

        if not vertical_for_replacement:
            vertical_headers = table_headers.get("vertical", [])
            vertical_for_replacement = [v.get("field_path", "") for v in vertical_headers]

        # 2. 获取OCR中的表头位置
        ocr_positions = table_headers.get("ocr_positions", {})

        # 从新结构获取表头位置
        horizontal_header_rows = ocr_positions.get("horizontal_header_rows", [])
        vertical_header_cols = ocr_positions.get("vertical_header_cols", [])
        data_start_row = ocr_positions.get("data_start_row")
        data_start_col = ocr_positions.get("data_start_col")

        # 如果新字段不存在，从旧结构获取
        if not horizontal_header_rows:
            header_positions = table_headers.get("header_positions", {})
            horizontal_header_rows = header_positions.get("horizontal_header_rows", [0])
            vertical_header_cols = header_positions.get("vertical_header_cols", [0])

        # 3. 获取OCR原始数据
        extracted_data = ocr_extract.get("extracted_data", {})
        table_data = extracted_data.get("top_rows_all_cols", [])

        if not table_data:
            return [], {"error": "无表格数据"}

        # 4. 计算数据起始位置（如果未提供）
        if data_start_row is None:
            data_start_row = max(horizontal_header_rows) + 1 if horizontal_header_rows else 1
        if data_start_col is None:
            data_start_col = max(vertical_header_cols) + 1 if vertical_header_cols else 1

        print(f"表头位置 - 行: {horizontal_header_rows}, 列: {vertical_header_cols}")
        print(f"数据起始 - 行: {data_start_row}, 列: {data_start_col}")
        print(f"新横向表头({len(horizontal_for_replacement)}): {horizontal_for_replacement[:3]}...")
        print(f"新纵向表头({len(vertical_for_replacement)}): {vertical_for_replacement[:3]}...")

        # 5. 提取纯数据
        pure_data = []
        for row_idx in range(len(table_data)):
            if row_idx >= data_start_row:
                row = table_data[row_idx]
                if row and len(row) > data_start_col:
                    pure_data.append(row[data_start_col:])
                elif row:
                    pure_data.append([])

        # 6. 构建新表格
        new_table_data = self._rebuild_table_with_new_headers(
            horizontal_for_replacement,
            vertical_for_replacement,
            pure_data
        )

        return new_table_data, {
            "horizontal_header_depth": len(horizontal_header_rows),
            "vertical_header_depth": len(vertical_header_cols),
            "data_start_row": data_start_row,
            "data_start_col": data_start_col,
            "pure_data_rows": len(pure_data),
            "pure_data_cols": len(pure_data[0]) if pure_data else 0,
            "success": True,
            "ocr_data_quality": analysis_result.get("ocr_data_quality", {}),
            "matching_summary": analysis_result.get("matching_summary", {})
        }

    def _rebuild_table_with_new_headers(self, horizontal_headers, vertical_headers, pure_data):
        """使用新表头重建表格"""
        new_table = []

        # 第一行：横向表头
        header_row = [""] + horizontal_headers  # 左上角空白单元格
        new_table.append(header_row)

        # 数据行：每行以纵向表头开头
        for i in range(max(len(vertical_headers), len(pure_data))):
            row = []

            # 纵向表头
            if i < len(vertical_headers):
                row.append(vertical_headers[i])
            else:
                row.append(f"行{i + 1}")

            # 数据部分
            if i < len(pure_data):
                data_row = pure_data[i]
                # 确保数据列数与表头列数匹配
                for j in range(len(horizontal_headers)):
                    if j < len(data_row):
                        row.append(data_row[j])
                    else:
                        row.append("")
            else:
                # 没有数据，填充空白
                row.extend([""] * len(horizontal_headers))

            new_table.append(row)

        return new_table


# 简化接口函数
def generate_excel_from_analysis(analysis_json_path: str, output_dir: str = "./output") -> str:
    """从分析JSON文件生成Excel"""

    os.makedirs(output_dir, exist_ok=True)

    with open(analysis_json_path, 'r', encoding='utf-8') as f:
        analysis_results = json.load(f)

    base_name = os.path.splitext(os.path.basename(analysis_json_path))[0]
    if base_name.endswith('_analysis'):
        base_name = base_name[:-9]

    output_filename = f"{base_name}_aligned.xlsx"
    output_path = os.path.join(output_dir, output_filename)

    generator = ExcelTableGenerator()
    return generator.export_analysis_to_excel(analysis_results, output_path)


def generate_excel_directly(analysis_results: Dict[str, Any],
                            image_path: str,
                            output_dir: str = "./output") -> str:
    """直接从分析结果生成Excel"""

    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    output_filename = f"{base_name}_aligned.xlsx"
    output_path = os.path.join(output_dir, output_filename)

    generator = ExcelTableGenerator()
    return generator.export_analysis_to_excel(analysis_results, output_path)


# 主函数
if __name__ == "__main__":
    analysis_json_path = r"E:\Datas\base_pros\DocuVista\test_codes\pngs\514001_152_analysis.json"
    output_dir = r"./output"

    try:
        result_file = generate_excel_from_analysis(analysis_json_path, output_dir)
        print(f"生成成功: {result_file}")
    except Exception as e:
        print(f"生成失败: {str(e)}")
        import traceback

        traceback.print_exc()