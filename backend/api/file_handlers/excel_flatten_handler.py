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


    def extract_metadata_and_clean_data(self, table_data: List[List[Any]]) -> tuple[Dict[str, str], List[List[Any]]]:
        """
        从表格数据中提取元数据并清理数据
        """
        metadata = {}
        clean_table_data = []

        for row in table_data:
            if not row or not row[0]:
                clean_table_data.append(row)
                continue

            first_cell = str(row[0]).strip()

            # 查找包含冒号的行作为元数据
            if ":" in first_cell:
                try:
                    key, value = first_cell.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()

                    # 只收集已知的元数据字段
                    valid_keys = ["bankname", "currency", "report_period", "unit", "table_name", "ocr_table_id"]
                    if key in valid_keys:
                        metadata[key] = value
                        print(f"✅ 找到元数据: {key} = {value}")
                except:
                    clean_table_data.append(row)
            else:
                clean_table_data.append(row)

        print(f"📋 提取的元数据: {metadata}")

        return metadata, clean_table_data

    def build_final_source_info(self, source_info: Dict[str, Any], metadata: Dict[str, str]) -> Dict[str, Any]:
        """
        构建最终的source_info，优先使用元数据
        """
        final_source_info = source_info.copy()

        # 优先使用元数据中的银行名
        if metadata.get("bankname"):
            final_source_info["bank_name"] = metadata["bankname"]
            print(f"✅ 使用元数据银行名: {metadata['bankname']}")
        elif not final_source_info.get("bank_name"):
            final_source_info["bank_name"] = "未知银行"

        # 优先使用元数据中的币种
        if metadata.get("currency"):
            final_source_info["default_currency"] = metadata["currency"]
            print(f"✅ 使用元数据币种: {metadata['currency']}")
        elif not final_source_info.get("default_currency"):
            final_source_info["default_currency"] = "人民币"

        # 设置单位（数额类用元数据单位，百分比保持%）
        if metadata.get("unit"):
            final_source_info["default_unit"] = metadata["unit"]
            print(f"✅ 使用元数据单位: {metadata['unit']}")
        elif not final_source_info.get("default_unit"):
            final_source_info["default_unit"] = ""

        # 其他元数据
        if metadata.get("report_period"):
            final_source_info["default_report_period"] = metadata["report_period"]

        if metadata.get("table_name"):
            final_source_info["table_name"] = metadata["table_name"]

        return final_source_info

    def extract_marks_info(self, table_data: List[List[Any]]) -> Dict[str, Any]:
        """
        提取行标记和列标记信息
        """
        marks_info = {
            'row_marks': [],
            'col_marks': [],
            'row_mark_col_index': -1,
            'col_mark_row_index': -1
        }

        if not table_data:
            return marks_info

        print(f"📊📊 提取原始标记信息...")

        # 1. 找行标记列
        first_row = table_data[0]
        for j in range(len(first_row)):
            header = str(first_row[j]).strip() if first_row[j] else ""
            if header == "行标记":
                marks_info['row_mark_col_index'] = j
                print(f"✅ '行标记'列位置: 第{j}列")
                break

        # 2. 找列标记行
        for i in range(len(table_data)):
            if len(table_data[i]) > 0:
                cell_value = str(table_data[i][0]).strip() if table_data[i][0] else ""
                if cell_value == "列标记":
                    marks_info['col_mark_row_index'] = i
                    print(f"✅ '列标记'行位置: 第{i}行")
                    break

        # 3. 读取行标记
        if marks_info['row_mark_col_index'] >= 0:
            print(f"🔍🔍 读取行标记...")
            for i in range(1, len(table_data)):
                if marks_info['row_mark_col_index'] < len(table_data[i]):
                    mark_value = table_data[i][marks_info['row_mark_col_index']]
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
                    marks_info['row_marks'].append(row_mark)
                else:
                    marks_info['row_marks'].append(1)
            print(f"✅ 读取完成: {len(marks_info['row_marks'])}个行标记")

        # 4. 读取列标记
        if marks_info['col_mark_row_index'] >= 0:
            print(f"🔍🔍 读取列标记...")
            col_mark_row = table_data[marks_info['col_mark_row_index']]
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
                marks_info['col_marks'].append(col_mark)
            print(f"✅ 读取完成: {len(marks_info['col_marks'])}个列标记")

        return marks_info

    def prepare_table_metadata(self, data: Dict[str, Any], final_source_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备表格元数据
        """
        ori_table_metadata = data.get("table_metadata", {})

        table_metadata = {
            'name': ori_table_metadata.get('name', ''),
            'default_unit': final_source_info.get("default_unit", ""),
            'default_currency': final_source_info.get("default_currency", "人民币"),
            'default_report_period': final_source_info.get("default_report_period", ''),
            'headers': {
                'rows': [],
                'cols': []
            }
        }

        return table_metadata

    def convert_to_long_format(self, table_data: List[List[Any]], table_metadata: Dict[str, Any],
                               marks_info: Dict[str, Any], source_info: Dict[str, Any]) -> List[Dict]:
        """
        执行长格式转换
        """
        print(f"🔄🔄 开始转换表格数据...")

        converter = self.FinalDataConverter()
        long_format_data = converter.convert_table_to_long_format(
            table_data=table_data,
            table_metadata=table_metadata,
            marks_info=marks_info,
            bank_name=source_info.get('bank_name', '中国建设银行'),
            entity=source_info.get('entity', '本集团')
        )

        print(f"✅ 转换完成: {len(long_format_data)} 条标准格式记录")
        return long_format_data

    def apply_units_to_flattened_data(self, flattened_data: List[Dict], source_info: Dict[str, Any]) -> List[Dict]:
        """
        对扁平化数据应用单位（优先使用元数据单位，但百分比保持%）
        """
        default_unit = source_info.get("default_unit", "")

        for row in flattened_data:
            if "value" in row and row["value"] is not None:
                value_str = str(row["value"]).strip()
                indicator = row.get("indicator", "")

                # 判断是否是百分比数据
                is_percentage = (
                        "%" in value_str or
                        "率" in indicator or
                        "比例" in indicator or
                        "百分比" in indicator or
                        any(keyword in indicator for keyword in ["%", "比率", "占比"])
                )

                if is_percentage:
                    # 百分比数据强制使用%
                    row["unit"] = "%"
                    # 确保值包含%符号
                    if "%" not in value_str and value_str.replace(".", "").replace("-", "").isdigit():
                        row["value"] = f"{value_str}%"
                else:
                    # 数额类数据：优先使用元数据中的单位
                    row["unit"] = default_unit

        return flattened_data

    def convert_to_frontend_format(self, long_format_data: List[Dict]) -> tuple[List[Dict], List[str]]:
        """
        将长格式数据转换为前端需要的双表头格式
        """
        print(f"🔄🔄 将长格式数据转换为前端双表头格式...")

        if not long_format_data or len(long_format_data) == 0:
            print("⚠️ 长格式数据为空，返回空结构")
            return [], []

        # 提取所有字段名作为表头
        field_names = list(long_format_data[0].keys())
        print(f"📊📊 字段名（表头）: {field_names}")

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
        return frontend_rows, field_names

    def build_final_result(self, frontend_rows: List[Dict], field_names: List[str],
                           long_format_data: List[Dict], final_source_info: Dict[str, Any],
                           metadata: Dict[str, str], original_table_data: List[List[Any]]) -> Dict[str, Any]:
        """
        构建最终返回结果
        """
        result = {
            "rows": frontend_rows,
            "total_rows": len(frontend_rows),
            "total_columns": len(field_names) if long_format_data else 0,
            "sheet_name": final_source_info.get('table_name', '扁平化数据'),
            "excel_file": final_source_info.get('excel_file', ''),
            "pdf_id": final_source_info.get('pdf_id', ''),
            "has_dual_headers": True,
            "success": True,
            "source_info": final_source_info,
            "metadata": metadata,
            "has_custom_metadata": bool(metadata),
            "timestamp": datetime.datetime.now().isoformat(),
            "stats": {
                "original_rows": len(original_table_data),
                "converted_records": len(long_format_data),
                "has_data": len(long_format_data) > 0
            }
        }

        return result


    def excel_flatten_from_excel(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理从Excel直接提取的标准格式数据
        使用long_format_converter.py的逻辑进行扁平化转换
        """
        try:
            # 检查转换器是否可用
            if not self.CONVERTER_AVAILABLE:
                print("❌❌ 转换器不可用")
                return {
                    "success": False,
                    "error": "数据转换器模块不可用"
                }

            # 1. 提取和验证输入数据
            table_data = data.get('table_data', [])
            source_info = data.get('source_info', {})

            if not table_data or len(table_data) < 2:
                print("❌❌ 表格数据至少需要表头行和一个数据行")
                return {
                    "success": False,
                    "error": "表格数据至少需要表头行和一个数据行"
                }

            print(f"📊📊 开始处理Excel表格数据:")
            print(f"  - 原始表格尺寸: {len(table_data)}行 × {len(table_data[0]) if table_data else 0}列")

            # 2. 提取元数据并清理数据
            metadata, clean_table_data = self.extract_metadata_and_clean_data(table_data)

            # 3. 构建最终的source_info（优先使用元数据）
            final_source_info = self.build_final_source_info(source_info, metadata)

            print(f"🎯 最终source_info: {final_source_info}")
            print(f"🧹 清理后数据: {len(clean_table_data)}行")

            # 4. 提取标记信息
            marks_info = self.extract_marks_info(clean_table_data)

            # 5. 准备表格元数据
            table_metadata = self.prepare_table_metadata(data, final_source_info)

            # 6. 执行转换
            long_format_data = self.convert_to_long_format(
                clean_table_data, table_metadata, marks_info, final_source_info
            )

            # 7. 对结果应用单位处理
            if long_format_data:
                long_format_data = self.apply_units_to_flattened_data(long_format_data, final_source_info)

            # 8. 转换为前端格式
            frontend_rows, field_names = self.convert_to_frontend_format(long_format_data)

            # 9. 构建最终结果
            result = self.build_final_result(
                frontend_rows, field_names, long_format_data,
                final_source_info, metadata, table_data
            )

            print("✅ API处理完成，返回结果")
            return result

        except Exception as e:
            print(f"❌❌ Excel数据处理失败: {str(e)}")
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error": f"处理失败: {str(e)}"
            }
