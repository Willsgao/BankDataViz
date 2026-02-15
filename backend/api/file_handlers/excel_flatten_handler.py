"""
Excel扁平化处理器 - 重构自file.py中的Excel扁平化相关功能
"""

import glob
import datetime
from typing import Dict, Any, List
from flask import jsonify
import traceback


class ExcelFlattenHandler:
    """Excel扁平化处理器"""

    def __init__(self, converter_available: bool, final_data_converter, db_connection=None):
        self.CONVERTER_AVAILABLE = converter_available
        self.FinalDataConverter = final_data_converter
        self.db = db_connection
        self._db_available = False

        # 测试数据库连接
        if self.db:
            try:
                conn = self.db.connect()
                if conn:
                    conn.close()
                    self._db_available = True
                    print("✅ 数据库连接测试成功")
                else:
                    print("⚠️ 数据库连接不可用")
            except Exception as e:
                print(f"⚠️ 数据库连接测试失败: {e}")


    def _extract_and_update_bank_name(self, file_id: int, filename: str) -> str:
        """
        智能识别银行名称并更新到数据库
        """
        try:
            # 🔥🔥🔥 导入银行名称提取器
            # 根据你的实际路径调整导入
            from backend.src.services.table_processor.get_bank_name import get_bank_name_from_document

            print(f"🤖 调用LLM识别银行名称: {filename}")

            # 调用LLM识别银行名称
            bank_name = get_bank_name_from_document(filename)

            if not bank_name:
                print("❌ LLM未能识别出银行名称")
                return "未知银行"

            print(f"✅ LLM识别结果: {bank_name}")

            # 更新到数据库
            conn = self.db.connect()
            if not conn:
                return "未知银行"

            c = conn.cursor()
            update_query = "UPDATE files SET bank_name = ? WHERE id = ?"
            c.execute(update_query, (bank_name, file_id))
            conn.commit()
            conn.close()

            print(f"✅✅ 银行名称已更新到数据库: {bank_name}")
            return bank_name

        except Exception as e:
            print(f"❌❌ 银行名称识别失败: {e}")
            return "未知银行"

    def get_pdf_file_info(self, file_id: str) -> Dict[str, Any]:
        """
        从数据库获取PDF文件的详细信息 - 优化文件名匹配版本
        """
        print(f"🔍🔍 查询文件信息: file_id={file_id}")

        if not self.db:
            return self._get_fallback_info(file_id)

        try:
            conn = self.db.connect()
            if not conn:
                return self._get_fallback_info(file_id)

            c = conn.cursor()

            # 🔥🔥🔥 优化1：自动处理文件扩展名
            # 如果file_id没有扩展名，自动添加.pdf
            if not file_id.lower().endswith('.pdf'):
                file_id_with_ext = file_id + '.pdf'
                print(f"🔧 自动添加扩展名: {file_id} -> {file_id_with_ext}")
            else:
                file_id_with_ext = file_id

            # 🔥🔥🔥 优化2：多种查询方式组合
            queries = [
                # 尝试1：带扩展名的精确匹配
                ("带扩展名精确匹配", "SELECT * FROM files WHERE filename = ?", (file_id_with_ext,)),
                # 尝试2：不带扩展名的精确匹配
                ("不带扩展名精确匹配", "SELECT * FROM files WHERE filename = ?", (file_id,)),
                # 尝试3：包含查询（最宽松）
                ("包含查询", "SELECT * FROM files WHERE filename LIKE ?", (f"%{file_id}%",)),
            ]

            matched_row = None
            for query_name, query_sql, params in queries:
                print(f"🔍 尝试查询: {query_name} -> {params}")
                c.execute(query_sql, params)
                result = c.fetchone()
                if result:
                    matched_row = result
                    print(f"✅ {query_name} 找到记录!")
                    break
                else:
                    print(f"❌ {query_name} 未找到记录")

            if not matched_row:
                print(f"❌ 所有查询方式都未找到文件 {file_id}")
                conn.close()
                return self._get_fallback_info(file_id)

            print(f"✅ 找到文件记录:")
            print(f"   - ID: {matched_row['id']}")
            print(f"   - 文件名: {matched_row['filename']}")
            print(f"   - 原始名: {matched_row['raw_filename']}")
            print(f"   - 银行名称: {matched_row['bank_name']}")

            result = {
                "id": matched_row["id"],
                "disk_filename": matched_row["filename"],
                "raw_filename": matched_row["raw_filename"] or "未知文件名",
                "file_type": matched_row["file_type"],
                "bank_name": matched_row["bank_name"] or "未知银行",
                "created_at": matched_row["created_at"],
                "source": "database"
            }

            # 🔥🔥🔥 保持原有的LLM调用逻辑不变
            if (not matched_row['bank_name'] or matched_row['bank_name'] == "未知银行") and matched_row['raw_filename']:
                print("🏦🏦 银行名称为空，尝试智能识别银行名称...")
                bank_name = self._extract_and_update_bank_name(matched_row['id'], matched_row['raw_filename'])

                if bank_name and bank_name != "未知银行":
                    result["bank_name"] = bank_name
                    result["source"] = "llm_extracted"
                    print(f"✅✅ 成功识别银行名称: {bank_name}")
                else:
                    print("❌ 未能识别出银行名称")

            conn.close()
            return result

        except Exception as e:
            print(f"❌❌ 查询PDF文件信息失败: {e}")
            return self._get_fallback_info(file_id)


    def _get_fallback_info(self, file_id: str) -> Dict[str, Any]:
        """安全的回退方案"""
        return {
            "id": file_id,
            "disk_filename": file_id,
            "raw_filename": "未知文件名",
            "file_type": "pdf",
            "bank_name": "未知银行",
            "created_at": None,
            "source": "fallback"
        }

    def extract_metadata_and_clean_data_old(self, table_data: List[List[Any]]) -> tuple[Dict[str, str], List[List[Any]]]:
        metadata = {}

        # 🔥🔥🔥 直接返回所有数据，不做任何删除
        clean_table_data = table_data

        # 只提取元数据，不删除任何行
        for row in table_data:
            if row and row[0] and ":" in str(row[0]).strip():
                try:
                    key, value = str(row[0]).strip().split(":", 1)
                    key, value = key.strip().lower(), value.strip()
                    if key in ["bankname", "currency", "report_period", "unit", "table_name", "ocr_table_id"]:
                        metadata[key] = value
                except:
                    pass

        return metadata, clean_table_data

    def extract_metadata_and_clean_data(self, table_data: List[List[Any]]) -> tuple[Dict[str, str], List[List[Any]]]:
        metadata = {}

        # 🔥🔥🔥 关键修改：合并前两列
        clean_table_data = []

        for row in table_data:
            if not row or len(row) == 0:
                continue

            # 获取前两列的内容
            col_0 = str(row[0]).strip() if len(row) > 0 and row[0] is not None else ""
            col_1 = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""

            # 合并前两列
            merged_col = ""
            if col_0 and col_1:
                # 两列都有内容，用>>拼接
                merged_col = f"{col_0}>>{col_1}"
            elif col_0:
                # 只有第0列有内容
                merged_col = col_0
            elif col_1:
                # 只有第1列有内容
                merged_col = col_1
            # 否则保持空字符串

            # 构建新行：合并后的第一列 + 剩余列（从第2列开始）
            new_row = [merged_col] + row[2:] if len(row) > 2 else [merged_col]
            clean_table_data.append(new_row)

            # 提取元数据（只从合并后的第一列提取）
            if merged_col and ":" in merged_col:
                try:
                    key, value = merged_col.split(":", 1)
                    key, value = key.strip().lower(), value.strip()
                    if key in ["bankname", "currency", "report_period", "unit", "table_name", "ocr_table_id"]:
                        metadata[key] = value
                except:
                    pass

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



    def _find_excel_files_simple(self, excel_path: str, file_id: str):
        """最简单的版本"""
        try:
            # 直接查找所有匹配的Excel文件
            pattern = f"{excel_path}/{file_id}*.xlsx"
            files = glob.glob(pattern)

            # 返回文件路径列表
            return [{'file_path': f, 'file_name': f.split('/')[-1]} for f in files]

        except:
            return []

    def get_sheet_names_from_excel(self, excel_file_path: str) -> List[str]:
        """
        从Excel文件中获取所有sheet名称

        Args:
            excel_file_path: Excel文件路径

        Returns:
            sheet名称列表
        """
        try:
            # TODO: 使用openpyxl或pandas读取Excel文件的sheet名称
            # 示例实现：
            import openpyxl
            wb = openpyxl.load_workbook(excel_file_path, read_only=True)
            return wb.sheetnames

        except Exception as e:
            print(f"❌ 读取Excel sheet名称失败: {e}")
            return []

    def read_excel_sheet_data(self, excel_file_path: str, sheet_name: str) -> List[List[Any]]:
        """
        读取Excel文件中指定sheet的数据

        Args:
            excel_file_path: Excel文件路径
            sheet_name: sheet名称

        Returns:
            二维列表格式的表格数据
        """
        try:
            # 示例实现：
            import pandas as pd
            df = pd.read_excel(excel_file_path, sheet_name=sheet_name, header=None)
            return df.fillna('').values.tolist()

        except Exception as e:
            print(f"❌ 读取Excel数据失败: {e}")
            return []

    def get_custom_field_mapping(self):
        """
        返回自定义字段名映射
        """
        return {
            'bank_name': '银行名',
            'table_name': '表名',
            'page_number': '页号',
            'entity': '主体',
            'vertical_hierarchy_path': '纵向层级路径',
            'horizontal_hierarchy_path': '横向层级路径',
            'data_type': '数据类型',
            'currency': '币种',
            'unit': '单位',
            'reporting_period': '报告期',
            'value': '数值',
            'row_mark': '行标记',
            'source_sheet_name_original': '原sheet名称'  # 🔥 新增映射
        }


    def convert_to_frontend_format(self, long_format_data: List[Dict]) -> tuple[List[Dict], List[str]]:
        """
        将长格式数据转换为前端需要的双表头格式 - 修复：将表头作为第一行数据
        """
        print(f"🔄🔄🔄🔄 将长格式数据转换为前端双表头格式...")

        if not long_format_data or len(long_format_data) == 0:
            print("⚠️ 长格式数据为空，返回空结构")
            return [], []

        # 获取自定义字段映射
        field_mapping = self.get_custom_field_mapping()

        # 提取所有原始字段名
        original_field_names = list(long_format_data[0].keys())

        # 应用字段名映射：将英文字段名映射为中文表头
        mapped_field_names = []
        for field_name in original_field_names:
            mapped_name = field_mapping.get(field_name, field_name)
            mapped_field_names.append(mapped_name)

        print(f"📊📊 原始字段名: {original_field_names}")
        print(f"📊📊 映射后字段名: {mapped_field_names}")

        # 构建前端需要的rows数组
        frontend_rows = []

        # 1. 添加元数据行
        metadata_row = {
            "__metadata": {
                "has_dual_headers": True,
                "top_left_cell": "",
                "horizontal_headers": mapped_field_names,
                "vertical_headers": []
            }
        }
        frontend_rows.append(metadata_row)

        # 2. 添加表头行（作为第一行数据）
        header_row = {
            "__is_first_row": True,
            "__top_left_cell": "字段名"
        }
        for i, field_name in enumerate(mapped_field_names, 1):
            header_row[f"H_{i}"] = field_name
        frontend_rows.append(header_row)

        # 🔥🔥🔥🔥 关键修复：将表头内容作为第一行数据
        # 3. 添加表头数据行（将表头字段名作为第一行数据）
        header_data_row = {
            "__is_data_row": True,
            "__vertical_header": "表头"
        }
        for i, field_name in enumerate(mapped_field_names, 1):
            header_data_row[f"H_{i}"] = field_name
        frontend_rows.append(header_data_row)

        # 4. 添加实际的数据行
        for record_idx, record in enumerate(long_format_data):
            data_row = {
                "__is_data_row": True,
                "__vertical_header": f"记录{record_idx + 1}"
            }

            for i, original_field_name in enumerate(original_field_names, 1):
                value = record.get(original_field_name, "")
                if original_field_name == 'row_mark' and isinstance(value, (int, float)):
                    data_row[f"H_{i}"] = value
                else:
                    data_row[f"H_{i}"] = str(value) if value is not None else ""

            frontend_rows.append(data_row)

        print(f"✅ 转换完成: {len(frontend_rows)} 行前端格式数据")
        return frontend_rows, mapped_field_names

    def _is_header_row(self, row) -> bool:
        """
        判断是否是表头行（包含字段名的行）
        """
        # 检查行中是否包含字段名
        header_keywords = ['银行名', '表名', '页号', '主体', '纵向层级路径',
                           '横向层级路径', '数据类型', '币种', '单位', '报告期', '数值', '行标记']

        for value in row.values:
            if isinstance(value, str):
                for keyword in header_keywords:
                    if keyword == value.strip():  # 精确匹配字段名
                        return True
        return False


    def global_flatten_from_excel_files(self, file_id: str, excel_path) -> Dict[str, Any]:
        """
        整体扁平化处理 - 返回与excel_flatten_from_excel一致的格式
        """
        try:
            print(f"🔥🔥🔥🔥🔥 开始整体扁平化处理 🔥🔥🔥🔥🔥🔥🔥")

            # 1. 获取PDF文件信息
            pdf_file_info = self.get_pdf_file_info(file_id)
            bank_name = pdf_file_info.get("bank_name", "未知银行")
            raw_filename = pdf_file_info.get("raw_filename", file_id)

            print(f"🏦🏦🏦🏦 文件信息 - 银行: {bank_name}, 文件名: {raw_filename}")

            # 2. 查找Excel文件
            excel_files_info = self._find_excel_files_simple(excel_path, file_id)
            if not excel_files_info:
                return {
                    "success": False,
                    "error": f"未找到PDF {file_id} 对应的Excel文件",
                    "long_format_data": [],  # 保持字段一致性
                    "rows": [],
                    "total_rows": 0
                }

            print(f"📊📊📊📊 找到 {len(excel_files_info)} 个Excel文件")

            all_flattened_data = []
            processed_sheets = []  # 记录处理成功的sheet
            failed_sheets = []  # 记录处理失败的sheet

            # 3. 处理每个Excel文件的每个sheet
            for file_info in excel_files_info:
                file_path = file_info['file_path']
                file_name = file_info['file_name']

                print(f"🎯🎯🎯🎯 处理Excel文件: {file_name}")

                sheet_names = self.get_sheet_names_from_excel(file_path)
                print(f"  📋📋📋📋 包含 {len(sheet_names)} 个sheet: {sheet_names}")

                for sheet_name in sheet_names:
                    print(f"    📄📄📄📄 处理sheet: {sheet_name}")

                    try:
                        # 读取sheet数据
                        original_data = self.read_excel_sheet_data(file_path, sheet_name)
                        if not original_data or len(original_data) < 2:
                            print(f"    ⚠⚠⚠⚠⚠️ sheet {sheet_name} 数据不足，跳过")
                            failed_sheets.append({
                                'sheet': sheet_name,
                                'file': file_name,
                                'reason': '数据不足或为空'
                            })
                            continue

                        print(f"    📈📈📈📈 读取到 {len(original_data)} 行原始数据")

                        # 构建扁平化请求
                        flatten_request = {
                            'table_data': original_data,
                            'source_info': {
                                'pdf_id': file_id,
                                'excel_file': file_name,
                                'table_name': sheet_name,
                                'bank_name': bank_name,
                                'default_currency': '人民币',
                                'default_unit': ''
                            }
                        }

                        # 执行扁平化
                        print(f"    🔥🔥🔥 调用excel_flatten_from_excel...")
                        flatten_result = self.excel_flatten_from_excel(flatten_request)

                        print(f"    🔍🔍🔍🔍 flatten_result结构: {list(flatten_result.keys())}")
                        print(f"    🔍🔍🔍🔍 flatten_result.success: {flatten_result.get('success')}")

                        if flatten_result.get('success'):
                            print(f"    ✅ sheet {sheet_name} 扁平化成功")

                            # 提取扁平化数据
                            flattened_rows = self._extract_flattened_data_from_result(
                                flatten_result=flatten_result,
                                file_id=file_id,
                                file_name=file_name,
                                sheet_name=sheet_name,
                                bank_name=bank_name,
                                raw_filename=raw_filename
                            )

                            print(f"    🔍🔍🔍🔍 提取到 {len(flattened_rows)} 行数据")

                            if flattened_rows:
                                all_flattened_data.extend(flattened_rows)
                                processed_sheets.append({
                                    'sheet': sheet_name,
                                    'file': file_name,
                                    'rows': len(flattened_rows)
                                })
                                print(f"    ✅✅ 成功添加到总数据")
                            else:
                                print(f"    ⚠⚠⚠⚠⚠️ 未提取到数据")
                                failed_sheets.append({
                                    'sheet': sheet_name,
                                    'file': file_name,
                                    'reason': '提取数据为空'
                                })
                        else:
                            error_msg = flatten_result.get('error', '未知错误')
                            print(f"    ❌❌❌❌ 扁平化失败: {error_msg}")
                            failed_sheets.append({
                                'sheet': sheet_name,
                                'file': file_name,
                                'reason': f'扁平化失败: {error_msg}'
                            })

                    except Exception as e:
                        error_msg = f"处理异常: {str(e)}"
                        print(f"    ❌❌❌❌ {error_msg}")
                        failed_sheets.append({
                            'sheet': sheet_name,
                            'file': file_name,
                            'reason': error_msg
                        })
                        import traceback
                        traceback.print_exc()

            # 4. 检查结果
            print(f"📊📊📊📊📊📊📊📊📊📊📊📊 最终数据统计: {len(all_flattened_data)} 行")
            print(f"✅ 成功处理 {len(processed_sheets)} 个sheet")
            print(f"❌❌ 失败 {len(failed_sheets)} 个sheet")

            # 5. 保存文件
            saved_result = None
            if all_flattened_data:
                print("💾💾💾💾 开始保存文件...")
                saved_result = self.save_merged_flattened_data(
                    pdf_id=file_id,
                    flattened_data=all_flattened_data,
                    excel_path=excel_path,
                    bank_name=bank_name,
                    source_pdf_name=raw_filename
                )

            # 6. 转换为前端格式（与excel_flatten_from_excel保持一致）
            frontend_rows, field_names = self.convert_to_frontend_format(all_flattened_data)

            # 7. 构建与excel_flatten_from_excel完全一致的返回格式
            result = {
                "success": True,
                "rows": frontend_rows,
                "total_rows": len(frontend_rows),
                "total_columns": len(field_names) if all_flattened_data else 0,
                "sheet_name": '整体扁平化数据',
                "excel_file": saved_result.get('filename', '') if saved_result else '',
                "pdf_id": file_id,
                "has_dual_headers": True,
                "data": all_flattened_data,
                "long_format_data": all_flattened_data,  # ✅ 关键：使用一致的字段名
                "source_info": {
                    'pdf_id': file_id,
                    'excel_file': saved_result.get('filename', '') if saved_result else '',
                    'table_name': '整体扁平化数据',
                    'bank_name': bank_name,
                    'default_currency': '人民币',
                    'default_unit': '',
                    'raw_filename': raw_filename
                },
                "metadata": {},
                "has_custom_metadata": False,
                "timestamp": datetime.datetime.now().isoformat(),
                "stats": {
                    "original_rows": len(all_flattened_data),
                    "converted_records": len(all_flattened_data),
                    "has_data": len(all_flattened_data) > 0
                },
                "file_info": saved_result,
                "summary": {
                    'pdf_id': file_id,
                    'bank_name': bank_name,
                    'raw_filename': raw_filename,
                    'total_excel_files': len(excel_files_info),
                    'total_sheets_processed': len(processed_sheets),
                    'total_sheets_failed': len(failed_sheets),
                    'total_rows': len(all_flattened_data),
                    'processed_sheets': processed_sheets,
                    'failed_sheets': failed_sheets,
                    'processed_at': datetime.datetime.now().isoformat()
                }
            }

            if not all_flattened_data:
                result.update({
                    "success": False,
                    "error": "所有sheet处理失败，未生成数据",
                    "rows": [],
                    "long_format_data": [],
                    "total_rows": 0,
                    "total_columns": 0
                })

            print(f"✅✅✅✅ 整体扁平化处理完成，返回格式与excel_flatten_from_excel一致")
            return result

        except Exception as e:
            print(f"❌❌❌❌❌❌❌❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"处理失败: {str(e)}",
                "long_format_data": [],  # 保持字段一致性
                "rows": [],
                "total_rows": 0
            }


    def convert_to_long_format(self, table_data: List[List[Any]], table_metadata: Dict[str, Any],
                               marks_info: Dict[str, Any], source_info: Dict[str, Any]) -> List[Dict]:
        """
        执行长格式转换 - 确保返回正确的数据结构
        """
        print(f"🔄🔄🔄🔄 开始转换表格数据...")

        converter = self.FinalDataConverter()
        long_format_data = converter.convert_table_to_long_format(
            table_data=table_data,
            table_metadata=table_metadata,
            marks_info=marks_info,
            bank_name=source_info.get('bank_name', '中国建设银行'),
            entity=source_info.get('entity', '本集团')
        )

        print(f"✅ 转换完成: {len(long_format_data)} 条标准格式记录")

        # 🔥🔥🔥 关键：确保数据结构正确
        if long_format_data and len(long_format_data) > 0:
            print(f"📊 第一条记录结构: {long_format_data[0].keys()}")
            print(f"📊 示例记录: {long_format_data[0]}")

        return long_format_data

    def excel_flatten_from_excel(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理从Excel直接提取的标准格式数据 - 恢复正确版本
        """
        try:
            # 检查转换器是否可用
            if not self.CONVERTER_AVAILABLE:
                print("❌❌❌❌ 转换器不可用")
                return {
                    "success": False,
                    "error": "数据转换器模块不可用"
                }


            print("TTTTTTTTTTTTTTTTTTTTTTTTTT:", data)

            # 1. 提取和验证输入数据
            table_data = data.get('table_data', [])
            source_info = data.get('source_info', {})

            if not table_data or len(table_data) < 2:
                print("❌❌❌❌ 表格数据至少需要表头行和一个数据行")
                return {
                    "success": False,
                    "error": "表格数据至少需要表头行和一个数据行"
                }

            print(f"📊📊📊📊 开始处理Excel表格数据:")
            print("|source_info::::", source_info)

            print(f"  - 原始表格尺寸: {len(table_data)}行 × {len(table_data[0]) if table_data else 0}列")

            # 2. 提取元数据并清理数据
            metadata, clean_table_data = self.extract_metadata_and_clean_data(table_data)

            # 3. 构建最终的source_info（优先使用元数据）
            final_source_info = self.build_final_source_info(source_info, metadata)

            print(f"🎯🎯 最终source_info: {final_source_info}")
            print(f"🧹🧹 清理后数据: {len(clean_table_data)}行")

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

            # 9. 构建最终结果 - 🔥🔥🔥 确保包含long_format_data
            result = {
                "rows": frontend_rows,
                "total_rows": len(frontend_rows),
                "total_columns": len(field_names) if long_format_data else 0,
                "sheet_name": final_source_info.get('table_name', '扁平化数据'),
                "excel_file": final_source_info.get('excel_file', ''),
                "pdf_id": final_source_info.get('pdf_id', ''),
                "has_dual_headers": True,
                "success": True,
                "long_format_data": long_format_data,  # 🔥🔥🔥 关键：确保包含这个字段
                "source_info": final_source_info,
                "metadata": metadata,
                "has_custom_metadata": bool(metadata),
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
            print(f"❌❌❌❌ Excel数据处理失败: {str(e)}")
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error": f"处理失败: {str(e)}"
            }

    def _extract_flattened_data_from_result(self, flatten_result: Dict[str, Any], file_id: str, file_name: str,
                                            sheet_name: str, bank_name: str = None, raw_filename: str = None) -> List[
        Dict]:
        """
        从扁平化结果中提取有效的数据行 - 严格按指定字段返回
        """
        try:
            print(f"🔍🔍 开始提取数据: sheet={sheet_name}")
            flattened_data = []

            # 提取页号
            page_number = self._extract_page_number_from_sheet_name(sheet_name)

            if flatten_result.get('long_format_data'):
                long_format_data = flatten_result['long_format_data']
                print(f"✅ 找到long_format_data: {len(long_format_data)} 条记录")

                for i, record in enumerate(long_format_data):
                    # 🔥🔥🔥 严格按照指定字段构建记录
                    new_record = {
                        '银行名': bank_name or "未知银行",
                        '表名': sheet_name,
                        '页号': page_number,
                        '主体': record.get('主体', ''),
                        '纵向层级路径': record.get('纵向层级路径', ''),
                        '横向层级路径': record.get('横向层级路径', ''),
                        '数据类型': record.get('数据类型', ''),
                        '币种': record.get('币种', ''),
                        '单位': record.get('单位', ''),
                        '报告期': record.get('报告期', ''),
                        '数值': record.get('数值', ''),
                        '行标记': record.get('行标记', '')
                    }

                    # 清理空值字段（可选）
                    new_record = {k: v for k, v in new_record.items() if v is not None and v != ''}

                    flattened_data.append(new_record)

                print(f"✅ 提取完成: {len(flattened_data)} 条数据")
                if flattened_data:
                    print(f"📊 字段列表: {list(flattened_data[0].keys())}")
                    print(f"📊 示例数据: {flattened_data[0]}")

                return flattened_data

            print("❌ 没有找到long_format_data")
            return []

        except Exception as e:
            print(f"❌❌ 提取数据失败: {e}")
            import traceback
            traceback.print_exc()
            return []


    def _extract_page_number_from_sheet_name(self, sheet_name: str) -> int:
        """
        从sheet名称中提取页号

        示例:
        - "P005_监管并表关键审慎" -> 5
        - "P006_2024年度资本管理相关数据" -> 6
        - "P009_风险加权资产概况" -> 9
        - "P010_资本构成" -> 10
        """
        try:
            # 查找模式：P后跟数字
            import re
            match = re.search(r'P(\d+)', sheet_name)

            if match:
                page_str = match.group(1)  # 提取数字部分
                return int(page_str)  # 转为整数
            else:
                # 如果没找到P数字模式，尝试其他模式
                match = re.search(r'(\d+)', sheet_name)
                if match:
                    return int(match.group(1))

            print(f"⚠️ 无法从sheet名称提取页号: {sheet_name}")
            return 0

        except Exception as e:
            print(f"❌ 提取页号失败: {e}")
            return 0

    def save_merged_flattened_data(self, pdf_id: str, flattened_data: List[Dict], excel_path,
                                   bank_name: str = None, source_pdf_name: str = None) -> Dict[str, Any]:
        """
        保存合并后的扁平化数据到Excel - 使用中文表头
        """
        try:
            import pandas as pd

            if not flattened_data:
                return {'success': False, 'error': '没有数据可保存'}

            # 转换为DataFrame
            df = pd.DataFrame(flattened_data)

            # 提取页号
            if '表名' in df.columns and '页号' in df.columns:
                df['页号'] = df['表名'].apply(self._extract_page_number_from_sheet_name)

            # 移除系统列
            columns_to_remove = [col for col in df.columns if col.startswith('_')]
            if columns_to_remove:
                df = df.drop(columns=columns_to_remove)

            # 构建正确的列顺序
            preferred_order = ['银行名', '表名', '页号', '主体', '纵向层级路径', '横向层级路径',
                               '数据类型', '币种', '单位', '报告期', '数值', '行标记', '备注特征']

            existing_columns = [col for col in preferred_order if col in df.columns]
            other_columns = [col for col in df.columns if col not in existing_columns]
            final_columns = existing_columns + other_columns
            df = df[final_columns]

            # 保存文件
            filename = f"{excel_path}/flattened_整合_{pdf_id}.xlsx"

            raw_sheet = source_pdf_name.replace("pdf", "").replace(".", "")
            print("*************raw_sheet:", raw_sheet)
            timestamp = datetime.datetime.now().strftime("%y%m%d_%H%M")
            sheet_name = f"{raw_sheet}_{timestamp}"
            print("**********************sheet_name:", sheet_name)
            sheet_name = sheet_name[-30:]

            # 🔥🔥🔥 关键：使用中文字段名作为表头
            df.to_excel(filename, index=False, header=True, engine='openpyxl', sheet_name=sheet_name)

            print(f"✅✅ 文件保存成功! 表头已保留")
            return {
                'success': True,
                'filename': filename,
                'saved_rows': len(df)
            }

        except Exception as e:
            print(f"❌❌ 保存失败: {e}")
            return {'success': False, 'error': str(e)}
