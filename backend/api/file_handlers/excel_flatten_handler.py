"""
Excel扁平化处理器 - 重构自file.py中的Excel扁平化相关功能
"""

import datetime
from typing import Dict, Any, List
from flask import jsonify
import traceback


class ExcelFlattenHandler:
    """Excel扁平化处理器"""

    def __init__(self, converter_available: bool, final_data_converter):
        """
        初始化处理器

        Args:
            converter_available: 转换器是否可用
            final_data_converter: 数据转换器类
        """
        self.CONVERTER_AVAILABLE = converter_available
        self.FinalDataConverter = final_data_converter

    def excel_flatten_from_excel(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理从Excel直接提取的标准格式数据
        使用long_format_converter.py的逻辑进行扁平化转换
        """
        try:
            # 检查转换器是否可用
            if not self.CONVERTER_AVAILABLE:
                print("❌ 转换器不可用")
                return {
                    "success": False,
                    "error": "数据转换器模块不可用"
                }

            table_data = data.get('table_data', [])
            source_info = data.get('source_info', {})

            if not table_data or len(table_data) < 2:
                print("❌ 表格数据至少需要表头行和一个数据行")
                return {
                    "success": False,
                    "error": "表格数据至少需要表头行和一个数据行"
                }

            print(f"📊 开始处理Excel表格数据:")
            print(f"  - 原始表格尺寸: {len(table_data)}行 × {len(table_data[0]) if table_data else 0}列")

            # 🔥 修复1：直接使用原始数据，不自动添加表头
            processed_table_data = table_data
            print(f"📊 使用原始数据，不添加表头行")

            # 创建转换器实例
            converter = self.FinalDataConverter()

            print("source_infosource_infosource_info:", source_info)
            ori_table_metadata = data.get("table_metadata", {})
            print("table_metadata:", ori_table_metadata)
            print("data:", data)

            # 准备表格元数据
            table_metadata = {
                'name': ori_table_metadata.get('name', ''),
                'default_unit': ori_table_metadata.get('default_unit', ''),
                'default_currency': ori_table_metadata.get('default_currency', '人民币'),
                'default_report_period': ori_table_metadata.get('default_report_period', ''),
                'headers': {
                    'rows': [],
                    'cols': []
                }
            }

            print(f"📊 提取原始标记信息...")

            # 1. 找行标记列
            row_mark_col_index = -1
            if len(processed_table_data) > 0:
                first_row = processed_table_data[0]
                for j in range(len(first_row)):
                    header = str(first_row[j]).strip() if first_row[j] else ""
                    if header == "行标记":
                        row_mark_col_index = j
                        print(f"✅ '行标记'列位置: 第{j}列")
                        break

            # 2. 找列标记行
            col_mark_row_index = -1
            for i in range(len(processed_table_data)):
                if len(processed_table_data[i]) > 0:
                    cell_value = str(processed_table_data[i][0]).strip() if processed_table_data[i][0] else ""
                    if cell_value == "列标记":
                        col_mark_row_index = i
                        print(f"✅ '列标记'行位置: 第{i}行")
                        break

            # 3. 读取行标记
            row_marks = []
            if row_mark_col_index >= 0:
                print(f"🔍 读取行标记...")
                for i in range(1, len(processed_table_data)):
                    if row_mark_col_index < len(processed_table_data[i]):
                        mark_value = processed_table_data[i][row_mark_col_index]
                        try:
                            if mark_value is None or mark_value == "":
                                row_mark = 1
                            else:
                                if isinstance(mark_value, (int, float)):
                                    row_mark = int(mark_value)
                                else:
                                    row_mark = int(float(mark_value)) if '.' in str(mark_value) else int(mark_value)
                        except:
                            row_mark = 1
                        row_marks.append(row_mark)
                    else:
                        row_marks.append(1)
                print(f"✅ 读取完成: {len(row_marks)}个行标记")

            # 4. 读取列标记
            col_marks = []
            if col_mark_row_index >= 0:
                print(f"🔍 读取列标记...")
                col_mark_row = processed_table_data[col_mark_row_index]  # 🔥 修复变量名
                for j in range(1, len(col_mark_row)):
                    mark_value = col_mark_row[j]
                    try:
                        if mark_value is None or mark_value == "":
                            col_mark = 1
                        else:
                            if isinstance(mark_value, (int, float)):
                                col_mark = int(mark_value)
                            else:
                                col_mark = int(float(mark_value)) if '.' in str(mark_value) else int(mark_value)
                    except:
                        col_mark = 1
                    col_marks.append(col_mark)
                print(f"✅ 读取完成: {len(col_marks)}个列标记")

            marks_info = {
                'row_marks': row_marks,
                'col_marks': col_marks,
                'row_mark_col_index': row_mark_col_index,
                'col_mark_row_index': col_mark_row_index
            }

            # 执行转换
            print(f"🔄 开始转换表格数据...")

            long_format_data = converter.convert_table_to_long_format(
                table_data=processed_table_data,
                table_metadata=table_metadata,
                marks_info=marks_info,
                bank_name=source_info.get('bank_name', '中国建设银行'),
                entity=source_info.get('entity', '本集团')
            )

            print(f"✅ 转换完成: {len(long_format_data)} 条标准格式记录")

            # 将长格式数据转换为前端需要的双表头格式
            print(f"🔄 将长格式数据转换为前端双表头格式...")

            if not long_format_data or len(long_format_data) == 0:
                print("⚠️ 长格式数据为空，返回空结构")
                frontend_rows = []
                field_names = []
            else:
                # 提取所有字段名作为表头
                field_names = list(long_format_data[0].keys())
                print(f"📊 字段名（表头）: {field_names}")

                # 构建前端需要的rows数组
                frontend_rows = []

                # 添加元数据行
                metadata_row = {
                    "__metadata": {
                        "has_dual_headers": True,
                        "top_left_cell": "",
                        "horizontal_headers": field_names,
                        "vertical_headers": []
                    }
                }
                frontend_rows.append(metadata_row)

                # 添加表头行
                header_row = {
                    "__is_first_row": True,
                    "__top_left_cell": "字段名"
                }
                for i, field_name in enumerate(field_names, 1):
                    header_row[f"H_{i}"] = field_name
                frontend_rows.append(header_row)

                # 添加数据行
                for record_idx, record in enumerate(long_format_data):
                    data_row = {
                        "__is_data_row": True,
                        "__vertical_header": f"记录{record_idx + 1}"
                    }

                    for i, field_name in enumerate(field_names, 1):
                        value = record.get(field_name, "")
                        if field_name == '行标记' and isinstance(value, (int, float)):
                            data_row[f"H_{i}"] = value
                        else:
                            data_row[f"H_{i}"] = str(value) if value is not None else ""

                    frontend_rows.append(data_row)

                print(f"✅ 转换完成: {len(frontend_rows)} 行前端格式数据")

            # 返回结果
            result = {
                "rows": frontend_rows,
                "total_rows": len(frontend_rows),
                "total_columns": len(field_names) if long_format_data else 0,
                "sheet_name": source_info.get('table_name', '扁平化数据'),
                "excel_file": source_info.get('excel_file', ''),
                "pdf_id": source_info.get('pdf_id', ''),
                "has_dual_headers": True,
                "success": True,
                "source_info": source_info,
                "timestamp": datetime.datetime.now().isoformat(),
                "stats": {
                    "original_rows": len(table_data),
                    "converted_records": len(long_format_data),
                    "has_data": len(long_format_data) > 0
                }
            }

            print("✅ API处理完成，返回结果")
            return result

        except Exception as e:
            print(f"❌ Excel数据处理失败: {str(e)}")
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error": f"处理失败: {str(e)}"
            }