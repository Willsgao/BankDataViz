# -*- coding:utf-8 -*-


# 尝试导入转换器，提供多种导入路径
CONVERTER_AVAILABLE = False
FinalDataConverter = None

try:
    # 尝试从 backend.core.services.table_processor 导入
    from backend.core.table_processor import FinalDataConverter as FC
    FinalDataConverter = FC
    CONVERTER_AVAILABLE = True
    print("✅ long_format_converter 从标准路径导入成功")
except ImportError as e:
    print(f"⚠️ 标准路径导入失败: {e}")
    try:
        # 尝试从当前目录导入
        from long_format_converter import FinalDataConverter as FC
        FinalDataConverter = FC
        CONVERTER_AVAILABLE = True
        print("✅ long_format_converter 从当前目录导入成功")
    except ImportError as e2:
        print(f"❌ 所有导入尝试都失败: {e2}")
        CONVERTER_AVAILABLE = False


def extract_table_data(input_data):
    """
    从输入数据中提取二维表格数据
    支持多种格式：
    1. 二维数组（直接返回）
    2. 对象数组（转换为二维数组）
    3. 双表头结构（解析为二维数组）
    """
    if not input_data or not isinstance(input_data, list):
        return []

    # 情况1：已经是二维数组
    if len(input_data) > 0 and isinstance(input_data[0], list):
        print(f"📊 输入数据是二维数组: {len(input_data)}行 × {len(input_data[0])}列")
        return input_data

    # 情况2：对象数组（包含__metadata的）
    if len(input_data) > 0 and isinstance(input_data[0], dict):
        print(f"📊 输入数据是对象数组: {len(input_data)}个对象")
        return convert_object_array_to_table(input_data)

    print(f"⚠️ 无法识别的数据格式: {type(input_data[0]) if input_data else '空'}")
    return []


def convert_object_array_to_table(object_array):
    """
    将对象数组转换为二维表格
    处理双表头结构
    """
    if not object_array:
        return []

    # 检查是否是双表头结构
    first_item = object_array[0]
    if isinstance(first_item, dict) and first_item.get('__metadata'):
        print("📊 检测到双表头结构")
        return parse_dual_header_structure(object_array)

    # 普通对象数组
    print("📊 检测到普通对象数组")

    # 收集所有字段
    field_names = set()
    for obj in object_array:
        if isinstance(obj, dict):
            # 过滤掉以__开头的元数据字段
            for key in obj.keys():
                if not key.startswith('__'):
                    field_names.add(key)

    field_names = list(field_names)
    if not field_names:
        return []

    # 构建表格
    result = []

    # 表头行
    result.append(field_names)

    # 数据行
    for obj in object_array:
        if isinstance(obj, dict):
            row = [obj.get(field, '') for field in field_names]
            result.append(row)

    print(f"📊 转换为表格: {len(result)}行 × {len(field_names)}列")
    return result


def parse_dual_header_structure(data):
    """
    解析双表头结构为二维表格 - 修正版
    """
    try:
        # 1. 查找元数据行
        metadata_row = None
        for row in data:
            if isinstance(row, dict) and row.get('__metadata'):
                metadata_row = row
                break

        if not metadata_row:
            return []

        metadata = metadata_row.get('__metadata', {})
        horizontal_headers = metadata.get('horizontal_headers', [])
        vertical_headers = metadata.get('vertical_headers', [])

        print(f"📊 解析到: {len(horizontal_headers)}个横向表头, {len(vertical_headers)}个纵向表头")

        # 2. 查找表头行和数据行
        header_row = None
        data_rows = []

        for row in data:
            if isinstance(row, dict):
                if row.get('__is_first_row'):
                    header_row = row
                elif row.get('__is_data_row'):
                    data_rows.append(row)

        if not header_row:
            print("⚠️ 未找到表头行")
            return []

        # 3. 构建二维表格
        table_data = []

        # 第一行：左上角 + 横向表头
        top_left = metadata.get('top_left_cell', '')
        first_row = [top_left]

        # 从表头行获取横向表头值
        for i in range(1, len(horizontal_headers) + 1):
            header_key = f'H_{i}'
            header_value = header_row.get(header_key, '')
            first_row.append(str(header_value) if header_value is not None else '')

        table_data.append(first_row)

        # 数据行（使用vertical_headers作为行表头）
        for idx, data_row in enumerate(data_rows):
            # 获取纵向表头
            vertical_header = data_row.get('__vertical_header', '')
            if not vertical_header and idx < len(vertical_headers):
                vertical_header = vertical_headers[idx]

            row_data = [vertical_header]

            # 获取数据单元格
            for i in range(1, len(horizontal_headers) + 1):
                header_key = f'H_{i}'
                cell_value = data_row.get(header_key, '')
                row_data.append(cell_value)

            table_data.append(row_data)

        print(f"📊 双表头转换为表格: {len(table_data)}行 × {len(table_data[0])}列")

        # 打印前几行查看
        for i in range(min(3, len(table_data))):
            print(f"  行{i}: {table_data[i]}")

        return table_data

    except Exception as e:
        print(f"❌ 解析双表头结构失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def prepare_conversion_params(input_data, source_info):
    """
    准备转换参数 - 修正版，正确提取标记信息
    """
    # 1. 提取表格数据
    table_data = extract_table_data(input_data)
    if not table_data:
        return None, None, None

    print(f"📊 提取到的表格数据: {len(table_data)}行 × {len(table_data[0])}列")

    # 2. 构建表格元数据
    table_metadata = {
        'name': source_info.get('table_name', '未知表格'),
        'default_unit': source_info.get('default_unit', ''),
        'default_currency': source_info.get('default_currency', '人民币'),
        'default_report_period': source_info.get('default_report_period', ''),
        'headers': {
            'rows': [],  # 这些将在转换过程中从 table_data 中提取
            'cols': []
        }
    }

    # 3. 正确提取标记信息（关键修正！）
    marks_info = extract_marks_info_from_table_data(table_data)

    print(f"📊 标记信息:")
    print(f"  - 行标记数量: {len(marks_info['row_marks'])}")
    print(f"  - 列标记数量: {len(marks_info['col_marks'])}")
    print(f"  - 行标记列索引: {marks_info['row_mark_col_index']}")
    print(f"  - 列标记行索引: {marks_info['col_mark_row_index']}")
    print(f"  - 列标记值: {marks_info['col_marks']}")

    return table_data, table_metadata, marks_info


def extract_marks_info_from_table_data(table_data):
    """
    从表格数据中提取标记信息
    根据你的数据结构：最后一列是行标记，最后一行是列标记
    """
    if not table_data or len(table_data) < 2:
        return get_default_marks_info(table_data)

    rows = len(table_data)
    cols = len(table_data[0]) if table_data else 0

    # 初始化标记信息
    marks_info = {
        'row_marks': [0] * rows,
        'col_marks': [0] * cols,
        'row_mark_col_index': -1,
        'col_mark_row_index': -1
    }

    # 1. 查找行标记列（最后一列的标题是"行标记"）
    if cols > 0:
        # 检查第一行的最后一列是否是"行标记"
        last_col_header = str(table_data[0][-1]).strip() if len(table_data[0]) > 0 else ""
        if "行标记" in last_col_header:
            marks_info['row_mark_col_index'] = cols - 1
            print(f"✅ 找到行标记列: 索引 {marks_info['row_mark_col_index']}")

    # 2. 查找列标记行（最后一行的第一列是"列标记"）
    if rows > 0:
        # 检查最后一行的第一列是否是"列标记"
        last_row = table_data[-1]
        first_cell = str(last_row[0]).strip() if len(last_row) > 0 else ""
        if "列标记" in first_cell:
            marks_info['col_mark_row_index'] = rows - 1
            print(f"✅ 找到列标记行: 索引 {marks_info['col_mark_row_index']}")

    # 3. 提取行标记（从行标记列提取）
    if marks_info['row_mark_col_index'] >= 0:
        for i in range(rows):
            if i == marks_info['col_mark_row_index']:
                # 跳过列标记行
                marks_info['row_marks'][i] = 0
                continue

            if len(table_data[i]) > marks_info['row_mark_col_index']:
                mark_value = table_data[i][marks_info['row_mark_col_index']]
                try:
                    marks_info['row_marks'][i] = int(mark_value) if mark_value not in [None, ''] else 0
                except:
                    marks_info['row_marks'][i] = 0

    # 4. 提取列标记（从列标记行提取）
    if marks_info['col_mark_row_index'] >= 0:
        col_mark_row = table_data[marks_info['col_mark_row_index']]
        for j in range(cols):
            if j == marks_info['row_mark_col_index']:
                # 跳过行标记列
                marks_info['col_marks'][j] = 0
                continue

            if j < len(col_mark_row):
                mark_value = col_mark_row[j]
                try:
                    marks_info['col_marks'][j] = int(mark_value) if mark_value not in [None, ''] else 0
                except:
                    marks_info['col_marks'][j] = 0
        print(f"✅ 提取的列标记: {marks_info['col_marks']}")

    return marks_info


def get_default_marks_info(table_data):
    """
    获取默认标记信息（当找不到标记时使用）
    """
    if not table_data:
        return {
            'row_marks': [],
            'col_marks': [],
            'row_mark_col_index': -1,
            'col_mark_row_index': -1
        }

    rows = len(table_data)
    cols = len(table_data[0]) if table_data else 0

    # 默认：所有数据列标记为1，所有数据行标记为1
    row_marks = [1] * rows
    col_marks = [1] * cols

    return {
        'row_marks': row_marks,
        'col_marks': col_marks,
        'row_mark_col_index': -1,
        'col_mark_row_index': -1
    }


def convert_directly_with_markers(input_data, source_info):
    """
    直接转换，利用已有的标记信息
    """
    if not input_data or len(input_data) < 2:
        return []

    # 1. 提取元数据
    metadata = None
    for item in input_data:
        if isinstance(item, dict) and item.get('__metadata'):
            metadata = item['__metadata']
            break

    if not metadata:
        return []

    # 2. 创建转换器
    converter = FinalDataConverter()

    # 3. 准备表格数据（保持原始格式）
    table_data = []

    # 添加表头行（从 __is_first_row 提取）
    for item in input_data:
        if isinstance(item, dict) and item.get('__is_first_row'):
            row = []
            # 左上角单元格
            row.append(item.get('__top_left_cell', ''))
            # 横向表头值
            horizontal_headers = metadata.get('horizontal_headers', [])
            for i in range(1, len(horizontal_headers) + 1):
                row.append(item.get(f'H_{i}', ''))
            table_data.append(row)
            break

    # 添加数据行（从 __is_data_row 提取）
    for item in input_data:
        if isinstance(item, dict) and item.get('__is_data_row'):
            row = []
            # 纵向表头
            row.append(item.get('__vertical_header', ''))
            # 数据单元格
            horizontal_headers = metadata.get('horizontal_headers', [])
            for i in range(1, len(horizontal_headers) + 1):
                row.append(item.get(f'H_{i}', ''))
            table_data.append(row)

    print(f"📊 直接构建的表格: {len(table_data)}行 × {len(table_data[0])}列")

    # 4. 准备标记信息
    marks_info = extract_marks_from_original_data(input_data, table_data)

    # 5. 准备元数据
    table_metadata = {
        'name': source_info.get('table_name', metadata.get('table_name', '未知表格')),
        'default_unit': source_info.get('default_unit', ''),
        'default_currency': source_info.get('default_currency', '人民币'),
        'default_report_period': source_info.get('default_report_period', ''),
        'headers': {
            'rows': metadata.get('vertical_headers', []),
            'cols': metadata.get('horizontal_headers', [])
        }
    }

    # 6. 执行转换
    try:
        long_format_data = converter.convert_table_to_long_format(
            table_data=table_data,
            table_metadata=table_metadata,
            marks_info=marks_info,
            bank_name=source_info.get('bank_name', '中国建设银行'),
            page_num=source_info.get('page_num', 1),
            entity=source_info.get('entity', '本集团')
        )
        return long_format_data
    except Exception as e:
        print(f"❌ 直接转换失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def extract_marks_from_original_data(input_data, table_data):
    """
    从原始数据中提取标记信息
    """
    if not input_data or not table_data:
        return get_default_marks_info(table_data)

    rows = len(table_data)
    cols = len(table_data[0]) if table_data else 0

    # 初始化
    marks_info = {
        'row_marks': [1] * rows,  # 默认所有行为数据行
        'col_marks': [1] * cols,  # 默认所有列为数据列
        'row_mark_col_index': -1,
        'col_mark_row_index': -1
    }

    # 查找行标记列（检查横向表头中是否有"行标记"）
    horizontal_headers = []
    for item in input_data:
        if isinstance(item, dict) and item.get('__metadata'):
            metadata = item['__metadata']
            horizontal_headers = metadata.get('horizontal_headers', [])
            break

    # 在横向表头中查找"行标记"
    for i, header in enumerate(horizontal_headers):
        if '行标记' in str(header):
            marks_info['row_mark_col_index'] = i
            print(f"✅ 找到行标记列索引: {i}")
            break

    # 查找列标记行（在数据行中查找__vertical_header为"列标记"的行）
    for i, item in enumerate(input_data):
        if isinstance(item, dict) and item.get('__is_data_row'):
            vertical_header = item.get('__vertical_header', '')
            if '列标记' in str(vertical_header):
                # 找到列标记行，需要找到它在table_data中的索引
                # 注意：table_data的第一行是表头行，所以索引要+1
                marks_info['col_mark_row_index'] = i + 1
                print(f"✅ 找到列标记行索引: {marks_info['col_mark_row_index']}")
                break

    # 提取行标记值（从每个数据行的H_5字段）
    if marks_info['row_mark_col_index'] >= 0:
        for i, item in enumerate(input_data):
            if isinstance(item, dict) and item.get('__is_data_row'):
                # H_5对应行标记列
                row_mark = item.get('H_5', 0)
                try:
                    if isinstance(row_mark, int):
                        marks_info['row_marks'][i + 1] = row_mark  # +1因为table_data有表头行
                    elif isinstance(row_mark, str) and row_mark.isdigit():
                        marks_info['row_marks'][i + 1] = int(row_mark)
                except:
                    marks_info['row_marks'][i + 1] = 0

    # 提取列标记值（从列标记行的各列）
    if marks_info['col_mark_row_index'] >= 0 and marks_info['col_mark_row_index'] < len(table_data):
        col_mark_row = table_data[marks_info['col_mark_row_index']]
        for j in range(cols):
            if j < len(col_mark_row):
                mark_value = col_mark_row[j]
                try:
                    if isinstance(mark_value, int):
                        marks_info['col_marks'][j] = mark_value
                    elif isinstance(mark_value, str) and mark_value.isdigit():
                        marks_info['col_marks'][j] = int(mark_value)
                except:
                    marks_info['col_marks'][j] = 0

    print(f"📊 提取的标记信息:")
    print(f"  - 行标记: {marks_info['row_marks']}")
    print(f"  - 列标记: {marks_info['col_marks']}")

    return marks_info




