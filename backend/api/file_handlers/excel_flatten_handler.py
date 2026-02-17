"""
Excel扁平化处理器 - 重构自file.py中的Excel扁平化相关功能
"""

import re
import glob
import datetime
from typing import Dict, Any, List


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

    def extract_metadata_and_clean_data00000(self, table_data: List[List[Any]]) -> tuple[Dict[str, str], List[List[Any]]]:
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

    def extract_metadata_and_clean_data00000(self, table_data: List[List[Any]]) -> tuple[Dict[str, str], List[List[Any]]]:
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
                    # 🔥🔥🔥 关键修改：在valid_keys列表中添加"entity"字段
                    valid_keys = ["bankname", "currency", "report_period", "unit", "table_name", "ocr_table_id",
                                  "entity"]
                    if key in valid_keys:
                        metadata[key] = value
                        print(f"✅ 提取到元数据字段: {key} = {value}")
                except:
                    pass

        print(f"📋 提取的元数据: {metadata}")
        return metadata, clean_table_data


    def build_final_source_info000000(self, source_info: Dict[str, Any], metadata: Dict[str, str]) -> Dict[str, Any]:
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

    def _convert_regular_table(self, table_data: List[List],
                               table_metadata: Dict[str, Any],
                               marks_info: Dict[str, Any],
                               bank_name: str = "",
                               entity: str = "") -> List[Dict]:
        """
        处理常规格式的表格数据转换为长格式 - 修复版
        注意：传入的 table_data 应该已经过滤了元数据行
        """
        print("🔧🔧 处理常规表格格式（修复版）...")

        if not table_data or len(table_data) < 2:
            print("❌❌ 表格数据为空或不足2行")
            return []

        print(f"📊📊 接收到的数据尺寸: {len(table_data)}行 × {len(table_data[0]) if table_data else 0}列")

        # 打印前几行数据用于调试
        print(f"🔍 数据样本（前5行）:")
        for i in range(min(5, len(table_data))):
            print(f"  行{i}: {table_data[i]}")

        if len(table_data) > 0:
            print(f"📊📊 第一行（表头）: {table_data[0]}")
        if len(table_data) > 1:
            print(f"📊📊 第二行（数据）: {table_data[1]}")

        # 🔥🔥🔥 关键修复：正确获取配置参数
        table_name = table_metadata.get('name', '')
        page_num = 0
        if table_name.startswith('P'):
            try:
                page_num = int(table_name.split('_')[0][1:].strip())
            except:
                page_num = 0

        # 银行名优先级：传入的bank_name > table_metadata中的bank_name > 默认值
        final_bank_name = bank_name or table_metadata.get('bank_name', '未知银行')

        # 🔥🔥🔥 关键修改1：实体值的确定逻辑
        final_entity = "本集团"  # 默认值

        if entity and str(entity).strip():  # 如果传入的entity参数有值
            final_entity = str(entity).strip()
            print(f"🔥🔥 使用传入的实体参数: '{final_entity}'，将覆盖所有记录的'主体'字段")
        elif table_metadata.get('entity') and str(table_metadata.get('entity')).strip():
            final_entity = str(table_metadata.get('entity')).strip()
            print(f"📋📋 使用元数据中的实体字段: '{final_entity}'")
        else:
            print(f"⚠️⚠️ 未指定实体，使用默认值: '{final_entity}'")

        final_currency = table_metadata.get('default_currency', '人民币')
        final_unit = table_metadata.get('default_unit', '')
        final_report_period = table_metadata.get('default_report_period', '')

        # 1. 智能识别表头行
        header_row_index = self._find_header_row_index(table_data, -1)  # 假设没有列标记行
        print(f"🔍🔍 识别到的表头行索引: {header_row_index}")

        if header_row_index < 0 or header_row_index >= len(table_data):
            print("❌❌ 无法识别有效的表头行")
            return []

        # 2. 智能识别数据行
        data_start_index = header_row_index + 1
        print(f"🔍 数据起始行索引: {data_start_index}")

        # 3. 构建长格式数据
        long_format_data = []

        for row_idx in range(data_start_index, len(table_data)):
            row_data = table_data[row_idx]

            if not row_data:
                continue

            # 🔥🔥 关键修复：检查是否是元数据行
            if len(row_data) > 0 and row_data[0] and str(row_data[0]).strip():
                first_cell = str(row_data[0]).strip()

                # 检查是否是以冒号结尾的元数据行
                if ":" in first_cell:
                    # 尝试解析键值对
                    try:
                        key, value = first_cell.split(":", 1)
                        key = key.strip().lower()
                        # 如果是有效的元数据键，跳过这行
                        valid_metadata_keys = ["bankname", "currency", "report_period", "unit",
                                               "table_name", "ocr_table_id", "entity"]
                        if key in valid_metadata_keys:
                            print(f"⏭️⏭️ 跳过元数据行 {row_idx}: '{first_cell}'")
                            continue
                    except:
                        # 如果不是有效的元数据格式，继续处理
                        pass

            # 🔥🔥 关键：提取纵向层级路径 - 只检查前两列
            vertical_path = ""

            # 硬编码检查第0列
            if len(row_data) > 0 and row_data[0] and str(row_data[0]).strip():
                vertical_path = str(row_data[0]).strip()
            # 硬编码检查第1列（如果第0列为空）
            elif len(row_data) > 1 and row_data[1] and str(row_data[1]).strip():
                vertical_path = str(row_data[1]).strip()
            else:
                # 🔥 关键：前两列都为空，跳过整行
                print(f"⏭️ 行{row_idx}前两列为空，跳过")
                continue

            # 🔥 额外的过滤：检查是否是数值行标记
            if vertical_path.isdigit() and len(vertical_path) <= 3:
                # 可能是行标记行，检查是否是数值
                print(f"⏭️ 跳过数值行标记行 {row_idx}: '{vertical_path}'")
                continue

            print(f"✅ 处理有效行{row_idx}: 纵向路径='{vertical_path}'")

            # 处理数据列
            for col_idx in range(1, len(row_data)):
                if col_idx >= len(table_data[header_row_index]):
                    break

                cell_value = row_data[col_idx]
                if cell_value is None or cell_value == "":
                    continue

                # 获取横向层级路径
                header_row = table_data[header_row_index]
                horizontal_path = ""
                if col_idx < len(header_row):
                    header_cell = header_row[col_idx]
                    horizontal_path = str(header_cell).strip() if header_cell is not None else f"列{col_idx}"

                # 检查横向路径是否为空
                if not horizontal_path or horizontal_path == "":
                    continue

                # 🔥 提取报告期
                report_period = self._extract_report_period_from_paths(horizontal_path, vertical_path, table_metadata)

                if not report_period and final_report_period:
                    report_period = final_report_period
                    print(f"📅📅 使用默认报告期: {report_period}")

                # 🔥 判断数据类型
                data_type = self.data_type_detector.get_data_type(
                    row_header=vertical_path,
                    col_header=horizontal_path,
                    cell_value=cell_value,
                    table_context=table_name
                )

                # 🔥 确定单位
                unit = self._determine_unit_by_paths(vertical_path, horizontal_path, final_unit)

                if not unit and final_unit:
                    unit = final_unit
                    print(f"📏📏 使用默认单位: {unit}")

                # 格式化数值
                formatted_value = self._format_numeric_value(cell_value)

                # 获取行标记
                row_marker = self._calculate_row_marker(formatted_value, data_type)

                # 🔥🔥🔥 关键修复：构建记录，使用确定后的final_entity
                record = {
                    '银行名': final_bank_name,
                    '表名': table_name,
                    '页号': page_num,
                    '主体': final_entity,  # 🔥 使用确定后的实体值
                    '纵向层级路径': vertical_path,
                    '横向层级路径': horizontal_path,
                    '数据类型': data_type,
                    '币种': final_currency,
                    '单位': unit,
                    '报告期': report_period,
                    '数值': formatted_value,
                    '行标记': row_marker,
                    '备注特征': ""  # 常规表格没有备注特征
                }

                long_format_data.append(record)

                if len(long_format_data) <= 3:  # 只打印前3条记录的详细日志
                    print(f"  📝📝 添加记录{len(long_format_data)}:")
                    print(f"     银行名: {final_bank_name}")
                    print(f"     主体: {final_entity}")
                    print(f"     纵向: {vertical_path}")
                    print(f"     横向: {horizontal_path}")
                    print(f"     数值: {formatted_value}")

        print(f"✅ 表格转换完成，共生成 {len(long_format_data)} 条记录")
        return long_format_data

    def convert_to_long_format(self, table_data: List[List[Any]], table_metadata: Dict[str, Any],
                               marks_info: Dict[str, Any], source_info: Dict[str, Any]) -> List[Dict]:
        """
        执行长格式转换 - 确保返回正确的数据结构
        """
        print(f"🔄🔄🔄🔄 开始转换表格数据...")

        converter = self.FinalDataConverter()

        # 🔥🔥🔥 关键修改：从source_info中获取entity参数
        entity_value = source_info.get('entity', '')
        bank_name_value = source_info.get('bank_name', '中国建设银行')

        print(f"🔧 传递给转换器的参数:")
        print(f"  - bank_name: {bank_name_value}")
        print(f"  - entity: '{entity_value}'")
        print(f"  - 表格数据行数: {len(table_data)}")
        print(
            f"  - 标记信息: 行标记{len(marks_info.get('row_marks', []))}个, 列标记{len(marks_info.get('col_marks', []))}个")

        long_format_data = converter.convert_table_to_long_format(
            table_data=table_data,
            table_metadata=table_metadata,
            marks_info=marks_info,
            bank_name=bank_name_value,
            entity=entity_value  # 🔥 传递entity参数
        )

        print(f"✅ 转换完成: {len(long_format_data)} 条标准格式记录")

        # 🔥🔥🔥 验证entity是否被正确应用
        if long_format_data and len(long_format_data) > 0:
            sample_entity = long_format_data[0].get('主体', '')
            print(f"📊 第一条记录的'主体'字段值: '{sample_entity}'")
            print(f"📊 传递给转换器的entity参数: '{entity_value}'")

            # 检查entity是否被正确应用
            if entity_value and sample_entity != entity_value:
                print(f"⚠️ 警告：entity参数可能未被正确应用！")
                print(f"  期望: '{entity_value}'")
                print(f"  实际: '{sample_entity}'")
            elif entity_value and sample_entity == entity_value:
                print(f"✅ entity参数被正确应用到'主体'字段")
            elif not entity_value:
                print(f"⚠️ 未指定entity参数，使用默认值")

        return long_format_data

    def prepare_table_metadata(self, data: Dict[str, Any], final_source_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备表格元数据 - 支持双字段名兼容
        """
        # 🔥 从两种可能的字段中获取原始元数据
        ori_table_metadata = {}
        if "table_metadata" in data and data["table_metadata"]:
            ori_table_metadata = data.get("table_metadata", {})
            print("✅ 从 table_metadata 字段获取原始元数据")
        elif "source_info" in data and data["source_info"]:
            # 从 source_info 中提取必要信息
            source_info = data.get("source_info", {})
            ori_table_metadata = {
                'name': source_info.get('table_name', ''),
                'pdf_id': source_info.get('pdf_id', ''),
                'excel_file': source_info.get('excel_file', ''),
                'bank_name': source_info.get('bank_name', ''),
                'entity': source_info.get('entity', '')
            }
            print("✅ 从 source_info 字段提取原始元数据")
        else:
            print("⚠️ 未找到 table_metadata 或 source_info 字段")

        table_metadata = {
            'name': ori_table_metadata.get('name', ''),
            'default_unit': final_source_info.get("default_unit", ""),
            'default_currency': final_source_info.get("default_currency", "人民币"),
            'default_report_period': final_source_info.get("default_report_period", ''),
            'bank_name': final_source_info.get("bank_name", "未知银行"),
            'entity': final_source_info.get("entity", "本集团"),
            'headers': {
                'rows': [],
                'cols': []
            }
        }

        print(f"📊 准备的表格元数据:")
        print(f"  - name: {table_metadata.get('name')}")
        print(f"  - entity: {table_metadata.get('entity')}")
        print(f"  - bank_name: {table_metadata.get('bank_name')}")

        return table_metadata


    def build_final_source_info00000(self, source_info: Dict[str, Any], metadata: Dict[str, str]) -> Dict[str, Any]:
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

        # 🔥🔥🔥 关键修改1：优先使用元数据中的entity
        if metadata.get("entity"):
            final_source_info["entity"] = metadata["entity"]
            print(f"✅ 使用元数据实体: {metadata['entity']}")
        # 🔥 如果metadata中没有entity，检查source_info中是否有
        elif "entity" in source_info and source_info["entity"]:
            final_source_info["entity"] = source_info["entity"]
            print(f"✅ 使用source_info中的实体: {source_info['entity']}")
        # 🔥 如果都没有，设置默认值
        elif "entity" not in final_source_info:
            final_source_info["entity"] = "本集团"  # 默认值
            print(f"⚠️ 未指定实体，使用默认值: '本集团'")

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

    def prepare_table_metadata000000(self, data: Dict[str, Any], final_source_info: Dict[str, Any]) -> Dict[str, Any]:
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

    def excel_flatten_from_excel(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理从Excel直接提取的标准格式数据 - 支持双字段名兼容
        """
        try:
            # 检查转换器是否可用
            if not self.CONVERTER_AVAILABLE:
                print("❌❌❌❌ 转换器不可用")
                return {
                    "success": False,
                    "error": "数据转换器模块不可用"
                }

            print("🎯🎯🎯🎯 开始Excel扁平化处理（双字段名兼容版）")

            # 1. 提取和验证输入数据
            table_data = data.get('table_data', [])

            # 🔥 关键修改1：支持双字段名读取
            # 优先级：source_info > table_metadata
            source_info = {}
            field_source = ""

            if 'source_info' in data and data['source_info']:
                source_info = data.get('source_info', {})
                field_source = "source_info"
                print("✅ 使用 source_info 字段作为源信息")
            elif 'table_metadata' in data and data['table_metadata']:
                # 将 table_metadata 转换为 source_info 格式
                table_metadata = data.get('table_metadata', {})
                source_info = {
                    'pdf_id': table_metadata.get('pdf_id', ''),
                    'excel_file': table_metadata.get('excel_file', ''),
                    'table_name': table_metadata.get('name', table_metadata.get('table_name', '')),
                    'bank_name': table_metadata.get('bank_name', '未知银行'),
                    'entity': table_metadata.get('entity', '本集团'),
                    'default_currency': table_metadata.get('default_currency', '人民币'),
                    'default_unit': table_metadata.get('default_unit', '')
                }
                field_source = "table_metadata (转换)"
                print("🔄 将 table_metadata 转换为 source_info 格式")
            else:
                source_info = {}
                field_source = "无"
                print("⚠️ 未找到 source_info 或 table_metadata 字段，使用空源信息")

            # 🔥 打印调试信息
            print(f"🔍 字段名兼容性调试:")
            print(f"  - 数据中包含的字段: {list(data.keys())}")
            print(f"  - 使用的字段来源: {field_source}")
            print(f"  - 提取的源信息: {source_info}")

            if 'entity' in source_info:
                print(f"  - entity参数值: '{source_info.get('entity')}'")
            else:
                print(f"  - entity参数: 未设置")

            if not table_data or len(table_data) < 2:
                print("❌❌❌❌ 表格数据至少需要表头行和一个数据行")
                return {
                    "success": False,
                    "error": "表格数据至少需要表头行和一个数据行"
                }

            print(f"📊📊📊📊 开始处理Excel表格数据:")
            print(f"  - 原始表格尺寸: {len(table_data)}行 × {len(table_data[0]) if table_data else 0}列")

            # 2. 提取元数据并清理数据
            print(f"🔧 提取元数据并清理数据...")
            metadata, clean_table_data = self.extract_metadata_and_clean_data(table_data)

            print(f"  - 从Excel提取的元数据: {metadata}")
            print(f"  - 清理后数据长度: {len(clean_table_data)}行")

            if 'entity' in metadata:
                print(f"  - 从Excel提取的entity元数据: '{metadata.get('entity')}'")

            # 3. 构建最终的source_info（优先使用元数据）
            print(f"🔧 构建最终source_info...")
            final_source_info = self.build_final_source_info(source_info, metadata)

            # 🔥 验证entity参数
            entity_value = final_source_info.get('entity', '')
            print(f"🎯 最终确定的entity值: '{entity_value}'")

            # 4. 提取标记信息
            marks_info = self.extract_marks_info(clean_table_data)
            print(
                f"🔧 标记信息: 行标记{len(marks_info.get('row_marks', []))}个, 列标记{len(marks_info.get('col_marks', []))}个")

            # 5. 准备表格元数据
            table_metadata = self.prepare_table_metadata(data, final_source_info)

            # 6. 执行转换
            print(f"🔧 开始长格式转换...")
            long_format_data = self.convert_to_long_format(
                clean_table_data, table_metadata, marks_info, final_source_info
            )

            # 🔥 添加转换结果详细分析
            print(f"📊 转换结果分析:")
            print(f"  - 生成的记录数: {len(long_format_data)}")

            if len(long_format_data) == 0:
                print(f"⚠️ 警告: 转换结果为空!")
                print(f"  可能原因分析:")
                print(f"  1. 清理后数据为空: {len(clean_table_data)}行")
                print(f"  2. 转换器可能过滤了所有数据")
                print(f"  3. 数据格式不符合转换要求")
            else:
                # 验证entity是否被正确应用
                sample_record = long_format_data[0]
                sample_entity = sample_record.get('主体', '')
                print(f"  - 第一条记录的'主体'字段: '{sample_entity}'")
                print(f"  - 期望的entity值: '{entity_value}'")

                if entity_value and sample_entity != entity_value:
                    print(f"  ⚠️ 警告: entity参数未被正确应用到'主体'字段!")

            # 7. 对结果应用单位处理
            if long_format_data:
                long_format_data = self.apply_units_to_flattened_data(long_format_data, final_source_info)
                print(f"✅ 单位处理完成")

            # 8. 转换为前端格式
            frontend_rows, field_names = self.convert_to_frontend_format(long_format_data)
            print(f"🔄 转换为前端格式: {len(frontend_rows)}行前端数据")

            # 9. 构建最终结果
            result = {
                "rows": frontend_rows,
                "total_rows": len(frontend_rows),
                "total_columns": len(field_names) if long_format_data else 0,
                "sheet_name": final_source_info.get('table_name', '扁平化数据'),
                "excel_file": final_source_info.get('excel_file', ''),
                "pdf_id": final_source_info.get('pdf_id', ''),
                "has_dual_headers": True,
                "success": True,
                "long_format_data": long_format_data,  # 原有的字段
                "data": long_format_data,  # 为了前端兼容性
                "source_info": final_source_info,
                "metadata": metadata,
                "has_custom_metadata": bool(metadata),
                "timestamp": datetime.datetime.now().isoformat(),
                "stats": {
                    "original_rows": len(table_data),
                    "converted_records": len(long_format_data),
                    "has_data": len(long_format_data) > 0
                },
                "debug_info": {  # 🔥 添加调试信息
                    "field_source": field_source,
                    "received_fields": list(data.keys()),
                    "final_entity": entity_value
                }
            }

            print("✅✅✅✅ API处理完成，返回结果")
            return result

        except Exception as e:
            print(f"❌❌❌❌ Excel数据处理失败: {str(e)}")
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error": f"处理失败: {str(e)}"
            }

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

    def convert_to_long_format00000(self, table_data: List[List[Any]], table_metadata: Dict[str, Any],
                               marks_info: Dict[str, Any], source_info: Dict[str, Any]) -> List[Dict]:
        """
        执行长格式转换 - 确保返回正确的数据结构
        """
        print(f"🔄🔄🔄🔄 开始转换表格数据...")

        converter = self.FinalDataConverter()

        # 🔥🔥🔥 关键修改：从source_info中获取entity参数
        entity_value = source_info.get('entity', '')
        bank_name_value = source_info.get('bank_name', '中国建设银行')

        print(f"🔧 传递给转换器的参数:")
        print(f"  - bank_name: {bank_name_value}")
        print(f"  - entity: {entity_value}")

        long_format_data = converter.convert_table_to_long_format(
            table_data=table_data,
            table_metadata=table_metadata,
            marks_info=marks_info,
            bank_name=bank_name_value,
            entity=entity_value  # 🔥 传递entity参数
        )

        print(f"✅ 转换完成: {len(long_format_data)} 条标准格式记录")

        # 🔥🔥🔥 验证entity是否被正确应用
        if long_format_data and len(long_format_data) > 0:
            sample_entity = long_format_data[0].get('主体', '')
            print(f"📊 第一条记录的'主体'字段值: {sample_entity}")
            print(f"📊 传递给转换器的entity参数: {entity_value}")

            # 检查entity是否被正确应用
            if entity_value and sample_entity != entity_value:
                print(f"⚠️ 警告：entity参数可能未被正确应用！")
                print(f"  期望: {entity_value}")
                print(f"  实际: {sample_entity}")

        return long_format_data

    def convert_to_long_format(self, table_data: List[List[Any]], table_metadata: Dict[str, Any],
                               marks_info: Dict[str, Any], source_info: Dict[str, Any]) -> List[Dict]:
        """
        执行长格式转换 - 确保返回正确的数据结构
        """
        print(f"🔄🔄🔄🔄 开始转换表格数据...")

        # 🔥 添加表格数据调试信息
        print(f"🔍 输入数据详情:")
        print(f"  - 表格数据行数: {len(table_data)}")
        if table_data and len(table_data) > 0:
            print(f"  - 表格数据列数: {len(table_data[0]) if table_data[0] else 0}")
            print(f"  - 第一行样本: {table_data[0]}")
            if len(table_data) > 1:
                print(f"  - 第二行样本: {table_data[1]}")

        print(f"🔍 元数据详情:")
        print(f"  - table_metadata: {table_metadata}")
        print(f"  - source_info: {source_info}")

        converter = self.FinalDataConverter()

        # 🔥🔥🔥 关键修改1：entity参数优先级处理
        # 优先级：source_info中的entity > table_metadata中的entity > 默认值
        entity_value = source_info.get('entity', '')
        if not entity_value:  # 如果source_info中没有entity
            entity_value = table_metadata.get('entity', '')
        if not entity_value:  # 如果都没有
            entity_value = '本集团'

        # 🔥🔥🔥 关键修改2：bank_name参数优先级处理
        # 优先级：source_info中的bank_name > table_metadata中的bank_name > 默认值
        bank_name_value = source_info.get('bank_name', '')
        if not bank_name_value:  # 如果source_info中没有bank_name
            bank_name_value = table_metadata.get('bank_name', '')
        if not bank_name_value:  # 如果都没有
            bank_name_value = '未知银行'

        print(f"🔧 传递给转换器的最终参数:")
        print(f"  - bank_name: '{bank_name_value}'")
        print(f"  - entity: '{entity_value}'")
        print(
            f"  - table_data形状: {len(table_data)}行 x {len(table_data[0]) if table_data and len(table_data) > 0 else 0}列")
        print(
            f"  - marks_info: 行标记{len(marks_info.get('row_marks', []))}个, 列标记{len(marks_info.get('col_marks', []))}个")

        try:
            long_format_data = converter.convert_table_to_long_format(
                table_data=table_data,
                table_metadata=table_metadata,
                marks_info=marks_info,
                bank_name=bank_name_value,
                entity=entity_value  # 🔥 传递entity参数
            )

            print(f"✅ 转换完成: {len(long_format_data)} 条标准格式记录")

            # 🔥🔥🔥 验证entity是否被正确应用
            if long_format_data and len(long_format_data) > 0:
                # 检查所有记录中的entity值
                entities_in_data = set()
                for record in long_format_data:
                    entity_in_record = record.get('主体', '')
                    if entity_in_record:
                        entities_in_data.add(entity_in_record)

                print(f"📊 转换结果中的entity值统计:")
                print(f"  - 传递给转换器的entity参数: '{entity_value}'")
                print(f"  - 转换结果中出现的entity值: {list(entities_in_data)}")

                if entity_value and entities_in_data and len(entities_in_data) == 1:
                    actual_entity = list(entities_in_data)[0]
                    if entity_value == actual_entity:
                        print(f"✅ entity参数被正确应用到所有记录的'主体'字段")
                    else:
                        print(f"⚠️ 警告：entity参数未被正确应用！")
                        print(f"  期望: '{entity_value}'")
                        print(f"  实际: '{actual_entity}'")
                elif len(entities_in_data) > 1:
                    print(f"⚠️ 警告：转换结果中包含多个不同的entity值: {list(entities_in_data)}")
                    print(f"  这可能表明entity参数未被统一应用")
                else:
                    print(f"⚠️ 警告：转换结果中没有找到有效的'主体'字段值")

            # 🔥 如果转换结果为空，提供详细的诊断信息
            if not long_format_data or len(long_format_data) == 0:
                print(f"❌ 转换结果为空，可能的原因:")
                print(f"  1. 输入数据table_data为空: {len(table_data)}行")
                print(f"  2. 转换器过滤了所有数据")
                print(f"  3. 数据格式不符合转换要求")

                # 打印更多调试信息
                if table_data and len(table_data) > 0:
                    print(f"  🔍 输入数据前5行:")
                    for i in range(min(5, len(table_data))):
                        print(f"    行{i}: {table_data[i]}")

            return long_format_data

        except Exception as e:
            print(f"❌❌❌❌ 转换过程中发生异常: {e}")
            import traceback
            traceback.print_exc()
            return []  # 返回空列表而不是抛出异常


    def convert_to_long_format000000(self, table_data: List[List[Any]], table_metadata: Dict[str, Any],
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

    def excel_flatten_from_excel00000(self, data: Dict[str, Any]) -> Dict[str, Any]:
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

            print("🎯🎯🎯🎯 开始Excel扁平化处理")

            # 1. 提取和验证输入数据
            table_data = data.get('table_data', [])
            source_info = data.get('source_info', {})

            # 🔥 添加请求数据调试
            print(f"🔍 请求数据摘要:")
            print(f"  - table_data长度: {len(table_data)}")
            print(f"  - source_info内容: {source_info}")

            if 'entity' in source_info:
                print(f"  - 前端传递的entity参数: '{source_info.get('entity')}'")
            else:
                print(f"  ⚠️ 前端未传递entity参数")

            if not table_data or len(table_data) < 2:
                print("❌❌❌❌ 表格数据至少需要表头行和一个数据行")
                return {
                    "success": False,
                    "error": "表格数据至少需要表头行和一个数据行"
                }

            print(f"📊📊📊📊 开始处理Excel表格数据:")
            print(f"  - 原始表格尺寸: {len(table_data)}行 × {len(table_data[0]) if table_data else 0}列")

            # 🔥 打印前两行数据样本
            if len(table_data) > 0:
                print(f"  - 第一行样本: {table_data[0]}")
            if len(table_data) > 1:
                print(f"  - 第二行样本: {table_data[1]}")

            # 2. 提取元数据并清理数据
            print(f"🔧 提取元数据并清理数据...")
            metadata, clean_table_data = self.extract_metadata_and_clean_data(table_data)

            print(f"  - 提取的元数据: {metadata}")
            print(f"  - 清理后数据长度: {len(clean_table_data)}行")

            if 'entity' in metadata:
                print(f"  - 从Excel提取的entity元数据: '{metadata.get('entity')}'")

            # 3. 构建最终的source_info（优先使用元数据）
            print(f"🔧 构建最终source_info...")
            final_source_info = self.build_final_source_info(source_info, metadata)

            # 🔥 验证entity参数
            entity_value = final_source_info.get('entity', '')
            print(f"🎯 最终确定的entity值: '{entity_value}'")

            # 4. 提取标记信息
            marks_info = self.extract_marks_info(clean_table_data)
            print(
                f"🔧 标记信息: 行标记{len(marks_info.get('row_marks', []))}个, 列标记{len(marks_info.get('col_marks', []))}个")

            # 5. 准备表格元数据
            table_metadata = self.prepare_table_metadata(data, final_source_info)

            # 6. 执行转换
            print(f"🔧 开始长格式转换...")
            long_format_data = self.convert_to_long_format(
                clean_table_data, table_metadata, marks_info, final_source_info
            )

            # 🔥 添加转换结果详细分析
            print(f"📊 转换结果分析:")
            print(f"  - 生成的记录数: {len(long_format_data)}")

            if len(long_format_data) == 0:
                print(f"⚠️ 警告: 转换结果为空!")
                print(f"  可能原因分析:")
                print(f"  1. 清理后数据为空: {len(clean_table_data)}行")
                print(f"  2. 转换器可能过滤了所有数据")
                print(f"  3. 数据格式不符合转换要求")

                # 打印清理后数据的样本
                if clean_table_data and len(clean_table_data) > 0:
                    print(f"  🔍 清理后数据前3行:")
                    for i in range(min(3, len(clean_table_data))):
                        print(f"    行{i}: {clean_table_data[i]}")
            else:
                # 验证entity是否被正确应用
                sample_record = long_format_data[0]
                sample_entity = sample_record.get('主体', '')
                print(f"  - 第一条记录的'主体'字段: '{sample_entity}'")
                print(f"  - 期望的entity值: '{entity_value}'")

                if entity_value and sample_entity != entity_value:
                    print(f"  ⚠️ 警告: entity参数未被正确应用到'主体'字段!")

            # 7. 对结果应用单位处理
            if long_format_data:
                long_format_data = self.apply_units_to_flattened_data(long_format_data, final_source_info)
                print(f"✅ 单位处理完成")

            # 8. 转换为前端格式
            frontend_rows, field_names = self.convert_to_frontend_format(long_format_data)
            print(f"🔄 转换为前端格式: {len(frontend_rows)}行前端数据")

            # 9. 构建最终结果
            result = {
                "rows": frontend_rows,
                "total_rows": len(frontend_rows),
                "total_columns": len(field_names) if long_format_data else 0,
                "sheet_name": final_source_info.get('table_name', '扁平化数据'),
                "excel_file": final_source_info.get('excel_file', ''),
                "pdf_id": final_source_info.get('pdf_id', ''),
                "has_dual_headers": True,
                "success": True,
                "long_format_data": long_format_data,  # 原有的字段
                "data": long_format_data,  # 🔥 为了前端兼容性
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

            print("✅✅✅✅ API处理完成，返回结果")
            return result

        except Exception as e:
            print(f"❌❌❌❌ Excel数据处理失败: {str(e)}")
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error": f"处理失败: {str(e)}"
            }

    def extract_metadata_and_clean_data(self, table_data: List[List[Any]]) -> tuple[Dict[str, str], List[List[Any]]]:
        """
        提取元数据并清理数据 - 修复版：保持原始列结构，不删除任何列

        参数：
            table_data: 原始表格数据，二维列表格式

        返回：
            tuple[Dict[str, str], List[List[Any]]]: 元数据字典和清理后的表格数据
        """
        metadata = {}
        clean_table_data = []

        print(f"🔍 开始提取元数据和清理数据，原始数据: {len(table_data)} 行")

        # 打印原始数据的前3行用于调试
        print(f"🔍 原始数据样本（前3行）:")
        for i in range(min(3, len(table_data))):
            print(f"  行{i}: {table_data[i]}")
            print(f"    长度: {len(table_data[i])} 列")

        for row_idx, row in enumerate(table_data):
            if not row or len(row) == 0:
                clean_table_data.append([])  # 保留空行结构
                print(f"📝 行{row_idx}: 空行，保留空结构")
                continue

            # 🔥 关键修改1：检查第一列是否为元数据行
            is_metadata = False

            if len(row) > 0 and row[0] is not None:
                first_cell = str(row[0]).strip()

                # 检查是否包含冒号，可能是元数据
                if ":" in first_cell:
                    try:
                        key, value = first_cell.split(":", 1)
                        key = key.strip().lower()
                        value = value.strip()

                        # 检查是否是有效的元数据键
                        valid_keys = ["bankname", "currency", "report_period", "unit",
                                      "table_name", "ocr_table_id", "entity"]
                        if key in valid_keys:
                            metadata[key] = value
                            print(f"✅ 提取元数据（行{row_idx}）: {key} = '{value}'")
                            is_metadata = True
                    except Exception as e:
                        # 解析失败，当作普通行处理
                        print(f"⚠️ 行{row_idx}元数据解析失败: {e}")
                        is_metadata = False

            if is_metadata:
                # 🔥 元数据行不添加到clean_table_data
                print(f"⏭️ 过滤元数据行 {row_idx}: '{first_cell}'")
                continue
            else:
                # 🔥 关键修改2：保持原始行结构，不删除任何列
                # 不合并前两列，不删除第二列
                clean_table_data.append(row)

                # 调试信息
                if row_idx < 3:  # 只打印前3行的详细信息
                    # 检查前两列的内容
                    col_0 = str(row[0]).strip() if len(row) > 0 and row[0] is not None else "空"
                    col_1 = str(row[1]).strip() if len(row) > 1 and row[1] is not None else "空"

                    print(f"✅ 保留行{row_idx}:")
                    print(f"  列数: {len(row)}")
                    print(f"  前两列: 列0='{col_0}', 列1='{col_1}'")
                    print(f"  完整行: {row}")

        # 打印元数据提取结果
        print(f"📊 元数据提取结果: {len(metadata)} 个字段")
        if metadata:
            for key, value in metadata.items():
                print(f"  - {key}: '{value}'")
        else:
            print(f"  - 未提取到元数据")

        # 打印清理后数据统计
        print(f"📊 清理后数据: {len(clean_table_data)} 行")
        if clean_table_data and len(clean_table_data) > 0:
            print(f"📊 清理后数据列数: 第0行有{len(clean_table_data[0])}列")
            print(f"📊 清理后数据样本（前5行）:")
            for i in range(min(5, len(clean_table_data))):
                row_str = str(clean_table_data[i])
                if len(row_str) > 100:  # 截断过长的行
                    row_str = row_str[:100] + "..."
                print(f"  行{i} ({len(clean_table_data[i])}列): {row_str}")

                # 特别检查每一行的列数是否一致
                if i > 0 and len(clean_table_data[i]) != len(clean_table_data[0]):
                    print(
                        f"  ⚠️ 警告: 行{i}的列数({len(clean_table_data[i])})与行0的列数({len(clean_table_data[0])})不一致")

        # 验证数据结构
        if clean_table_data and len(clean_table_data) > 1:
            first_row_cols = len(clean_table_data[0])
            consistent = True
            for i, row in enumerate(clean_table_data):
                if len(row) != first_row_cols:
                    print(f"❌ 数据结构错误: 行{i}有{len(row)}列，但行0有{first_row_cols}列")
                    consistent = False
                    break
            if consistent:
                print(f"✅ 数据结构检查通过: 所有行都有{first_row_cols}列")

        return metadata, clean_table_data

    def build_final_source_info(self, source_info: Dict[str, Any], metadata: Dict[str, str]) -> Dict[str, Any]:
        """
        构建最终的source_info，优先使用元数据
        支持从 table_metadata 转换的 source_info
        """
        final_source_info = source_info.copy()

        # 🔥 字段名映射和兼容性处理
        # 1. 处理 table_name/name 字段映射
        if 'name' in final_source_info and 'table_name' not in final_source_info:
            final_source_info['table_name'] = final_source_info.get('name', '')
        elif 'table_name' in final_source_info and 'name' not in final_source_info:
            final_source_info['name'] = final_source_info.get('table_name', '')

        # 2. 处理 pdf_id 字段
        if not final_source_info.get('pdf_id'):
            final_source_info['pdf_id'] = ''

        # 3. 处理 excel_file 字段
        if not final_source_info.get('excel_file'):
            final_source_info['excel_file'] = ''

        # 🔥 银行名处理 - 优先级：元数据 > source_info > 默认值
        if metadata.get("bankname"):
            final_source_info["bank_name"] = metadata["bankname"]
            print(f"✅ 使用元数据银行名: {metadata['bankname']}")
        elif not final_source_info.get("bank_name"):
            final_source_info["bank_name"] = "未知银行"
            print(f"⚠️ 未指定银行名，使用默认值: '未知银行'")
        else:
            print(f"✅ 使用source_info中的银行名: {final_source_info.get('bank_name')}")

        # 🔥 币种处理
        if metadata.get("currency"):
            final_source_info["default_currency"] = metadata["currency"]
            print(f"✅ 使用元数据币种: {metadata['currency']}")
        elif not final_source_info.get("default_currency"):
            final_source_info["default_currency"] = "人民币"
            print(f"⚠️ 未指定币种，使用默认值: '人民币'")

        # 🔥 单位处理
        if metadata.get("unit"):
            final_source_info["default_unit"] = metadata["unit"]
            print(f"✅ 使用元数据单位: {metadata['unit']}")
        elif not final_source_info.get("default_unit"):
            final_source_info["default_unit"] = ""
            print(f"⚠️ 未指定单位，使用空值")

        # 🔥 entity处理 - 关键修改
        if metadata.get("entity"):
            final_source_info["entity"] = metadata["entity"]
            print(f"✅ 使用元数据实体: {metadata['entity']}")
        elif not final_source_info.get("entity"):
            final_source_info["entity"] = "本集团"
            print(f"⚠️ 未指定实体，使用默认值: '本集团'")
        else:
            print(f"✅ 使用source_info中的实体: {final_source_info.get('entity')}")

        # 其他字段
        if metadata.get("report_period"):
            final_source_info["default_report_period"] = metadata["report_period"]
            print(f"✅ 使用元数据报告期: {metadata['report_period']}")

        if metadata.get("table_name") and not final_source_info.get("table_name"):
            final_source_info["table_name"] = metadata["table_name"]

        return final_source_info

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
            if len(raw_sheet) > 20:
                raw_sheet = re.sub(r'[^\u4e00-\u9fff]', '', raw_sheet)

            timestamp = datetime.datetime.now().strftime("%y%m%d_%H%M")
            sheet_name = f"{raw_sheet}_{timestamp}"
            sheet_name = sheet_name[:30]

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
