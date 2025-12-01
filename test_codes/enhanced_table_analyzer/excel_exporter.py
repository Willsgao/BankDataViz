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
            table_data = table_data[horizontal_headers_count:]

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
        """创建汇总表数据（增加状态列和特征值列）"""
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

                horizontal_count = len(table_headers.get("horizontal", []))
                vertical_count = len(table_headers.get("vertical", []))

                dimensions = table_info.get("dimensions", {})
                ocr_cells = dimensions.get("rows", 0) * dimensions.get("cols", 0)

                if ocr_extract:
                    stats = ocr_extract.get("stats", {})
                    ocr_cells = stats.get("cells_extracted", ocr_cells)

                # 表格标题
                table_title = table_info.get("title", f"表格_{table_info.get('table_id', i + 1)}")

                # 特征值：新表头结构描述
                features = f"H{horizontal_count}V{vertical_count}"

                summary_data.append([
                    table_info.get("table_id", i + 1),
                    table_title,
                    "是",
                    "人民币",
                    "",
                    "1",
                    horizontal_count,
                    vertical_count,
                    ocr_cells,
                    horizontal_count + vertical_count,
                    "成功",
                    features
                ])

        return summary_data

    def extract_raw_ocr_data(self, ocr_extract: Dict[str, Any]) -> List[List[str]]:
        """提取OCR原始数据"""
        extracted_data = ocr_extract.get("extracted_data", {})
        table_data = extracted_data.get("top_rows_all_cols", [])

        if not table_data:
            left_data = extracted_data.get("left_cols_all_rows", [])
            if left_data:
                table_data = []
                for i in range(len(left_data[0]) if left_data else 0):
                    row = []
                    for col_data in left_data:
                        if i < len(col_data):
                            row.append(col_data[i])
                    table_data.append(row)

        return table_data

    def save_ocr_raw_data(self, worksheet, ocr_data: List[List[str]]):
        """保存OCR原始数据到工作表"""
        if not ocr_data:
            worksheet.cell(row=1, column=1, value="无OCR原始数据")
            return

        for row_idx, row_data in enumerate(ocr_data, 1):
            for col_idx, cell_value in enumerate(row_data, 1):
                cell = worksheet.cell(row=row_idx, column=col_idx, value=cell_value)
                cell.border = self.thin_border
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.font = self.data_font

        # 调整列宽
        if ocr_data:
            for col_idx in range(1, len(ocr_data[0]) + 1):
                col_letter = get_column_letter(col_idx)
                max_length = 0
                for row_idx in range(1, len(ocr_data) + 1):
                    cell_value = worksheet.cell(row=row_idx, column=col_idx).value
                    if cell_value:
                        cell_length = len(str(cell_value))
                        max_length = max(max_length, cell_length)

                adjusted_width = min(max(max_length + 2, 10), 30)
                worksheet.column_dimensions[col_letter].width = adjusted_width

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

            # 总是先创建OCR原始数据工作表
            ocr_sheet_name = f"P152_表格_{table_id}{self.ocr_sheet_suffix}"
            if len(ocr_sheet_name) > 31:
                ocr_sheet_name = ocr_sheet_name[:31]

            ocr_extract = table_result.get("source_data", {}).get("ocr_extract", {})
            ocr_raw_data = self.extract_raw_ocr_data(ocr_extract)

            ws_ocr = wb.create_sheet(title=ocr_sheet_name)
            self.save_ocr_raw_data(ws_ocr, ocr_raw_data)
            print(f"  已保存OCR原始数据到工作表: {ocr_sheet_name}")

            # 检查表格是否成功分析
            if not table_result.get("success", False):
                error_msg = table_result.get("error", "未知错误")
                print(f"表格 {table_id} 分析失败: {error_msg}")
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
        wb.save(output_path)
        print(f"Excel文件已保存到: {output_path}")

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

    def build_table_with_new_headers(self,
                                     analysis_result: Dict[str, Any],
                                     ocr_extract: Dict[str, Any]) -> Tuple[List[List[str]], Dict[str, Any]]:
        """基于LLM分析结果对齐表格 - 右对齐/下对齐版本"""

        # 获取OCR原始数据
        extracted_data = ocr_extract.get("extracted_data", {})
        table_data = extracted_data.get("top_rows_all_cols", [])

        if not table_data:
            return [], {"error": "无表格数据"}

        print(f"原始OCR数据: {len(table_data)}行 × {len(table_data[0]) if table_data else 0}列")

        # 从LLM获取表头信息
        table_headers = analysis_result.get("table_headers", {})
        horizontal_headers = table_headers.get("horizontal", [])
        vertical_headers = table_headers.get("vertical", [])

        # 提取新表头文本
        new_horizontal = [h.get("field_path", "") for h in horizontal_headers]
        new_vertical = [v.get("field_path", "") for v in vertical_headers]

        print(f"LLM水平表头({len(new_horizontal)}): {new_horizontal}")
        print(f"LLM垂直表头({len(new_vertical)}): {new_vertical}")

        # **关键：获取表头位置信息**
        # 从LLM的header_positions或推断
        header_positions = table_headers.get("header_positions", {})
        horizontal_header_rows = header_positions.get("horizontal_header_rows", [0])
        vertical_header_cols = header_positions.get("vertical_header_cols", [0])

        # 确定数据起始位置
        data_start_row = max(horizontal_header_rows) + 1 if horizontal_header_rows else 1
        data_start_col = max(vertical_header_cols) + 1 if vertical_header_cols else 1

        print(f"数据起始位置: 行{data_start_row}, 列{data_start_col}")

        # **提取纯数据（删除原始表头）**
        pure_data = []
        for row_idx in range(len(table_data)):
            if row_idx >= data_start_row:  # 行表头之后
                row = table_data[row_idx]
                # 删除列表头左边的列
                if row and len(row) > data_start_col:
                    pure_data.append(row[data_start_col:])
                elif row:
                    pure_data.append([])

        print(f"纯数据: {len(pure_data)}行 × {len(pure_data[0]) if pure_data else 0}列")

        # **调整新表头**
        # 1. 处理重叠：如果水平表头和垂直表头第一个单元格相同
        if new_horizontal and new_vertical and new_horizontal[0] == new_vertical[0]:
            print(f"表头重叠: 删除垂直表头第一个 '{new_vertical[0]}'")
            new_vertical = new_vertical[1:] if len(new_vertical) > 1 else []

        # 2. 根据数据数量调整表头长度
        # 水平表头应该对应数据列数 + 1（垂直表头列）
        expected_horizontal_count = (len(pure_data[0]) if pure_data else 0) + 1
        if len(new_horizontal) > expected_horizontal_count:
            print(f"水平表头过多({len(new_horizontal)} > {expected_horizontal_count})，截断")
            new_horizontal = new_horizontal[:expected_horizontal_count]
        elif len(new_horizontal) < expected_horizontal_count:
            print(f"水平表头不足({len(new_horizontal)} < {expected_horizontal_count})，补充")
            while len(new_horizontal) < expected_horizontal_count:
                new_horizontal.append(f"列{len(new_horizontal) + 1}")

        # 垂直表头应该对应数据行数
        expected_vertical_count = len(pure_data)
        if len(new_vertical) > expected_vertical_count:
            print(f"垂直表头过多({len(new_vertical)} > {expected_vertical_count})，截断")
            new_vertical = new_vertical[:expected_vertical_count]
        elif len(new_vertical) < expected_vertical_count:
            print(f"垂直表头不足({len(new_vertical)} < {expected_vertical_count})，从数据补充")
            # 尝试从原始数据的第一列获取垂直表头
            for i in range(len(new_vertical), expected_vertical_count):
                if i < len(pure_data) and data_start_col - 1 < len(table_data[data_start_row + i]):
                    cell = table_data[data_start_row + i][data_start_col - 1]
                    if cell:
                        new_vertical.append(str(cell).strip())
                    else:
                        new_vertical.append(f"行{i + 1}")
                else:
                    new_vertical.append(f"行{i + 1}")

        print(f"调整后水平表头({len(new_horizontal)}): {new_horizontal}")
        print(f"调整后垂直表头({len(new_vertical)}): {new_vertical[:5]}...")

        # **构建新表格 - 右对齐/下对齐**
        new_table_data = []

        # 1. 水平表头行（第1行）
        # 水平表头从A1开始
        new_table_data.append(new_horizontal)

        # 2. 数据行 - 右对齐/下对齐
        for i in range(len(pure_data)):
            row_data = []

            # 垂直表头（第一列）
            if i < len(new_vertical):
                row_data.append(new_vertical[i])
            else:
                row_data.append(f"行{i + 1}")

            # **关键：右对齐数据**
            # 数据从右侧对齐，如果数据列数少于表头列数，左边补空
            if i < len(pure_data):
                data_row = pure_data[i]

                # 计算需要补空的数量
                empty_cells_needed = len(new_horizontal) - 1 - len(data_row)

                # 左边补空（右对齐）
                for _ in range(max(0, empty_cells_needed)):
                    row_data.append("")

                # 添加数据
                for cell in data_row:
                    row_data.append(str(cell).strip() if cell else "")

            # 确保行长度正确
            while len(row_data) < len(new_horizontal):
                row_data.append("")

            new_table_data.append(row_data)

        # **下对齐：如果数据行数少于表头行数，补空行**
        expected_total_rows = len(new_vertical) + 1  # 垂直表头行数 + 水平表头行
        while len(new_table_data) < expected_total_rows:
            empty_row = [f"行{len(new_table_data)}"] + [""] * (len(new_horizontal) - 1)
            new_table_data.append(empty_row)

        return new_table_data, {
            "horizontal_header_depth": len(horizontal_header_rows),
            "vertical_header_depth": len(vertical_header_cols),
            "data_start_row": data_start_row,
            "data_start_col": data_start_col,
            "pure_data_rows": len(pure_data),
            "pure_data_cols": len(pure_data[0]) if pure_data else 0,
            "success": True
        }


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