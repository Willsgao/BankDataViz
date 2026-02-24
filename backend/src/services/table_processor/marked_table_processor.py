# marked_table_processor.py

import re
from collections import Counter


class MarkedTableProcessor:
    """带标记表格处理器：负责分析单元格类型并创建标记行列"""

    def __init__(self):
        self.warnings = []
        self.issues = []

    def log_warning(self, message):
        """记录警告"""
        self.warnings.append(message)
        print(f"⚠️ {message}")

    def log_issue(self, message):
        """记录问题"""
        self.issues.append(message)
        print(f"❓ {message}")

    def _analyze_cell_type(self, cell_value):
        """
        分析单元格类型
        返回: "blank", "text", "std_num", "minor_num", "error_num"
        """
        if cell_value is None:
            return "blank"

        text = str(cell_value).strip()

        # 1. 空白单元格
        if text == "":
            return "blank"

        # 2. 检查是否为纯文本（不包含数字）
        if not any(c.isdigit() for c in text):
            return "text"

        # ========== 新增：检查%号前是否有逗号 ==========
        if '%' in text:
            # 找到%号的位置
            percent_pos = text.find('%')
            # 检查%号前面是否有逗号
            if percent_pos > 0 and ',' in text[:percent_pos]:
                # %号前面有逗号，这是错误格式（如"0,82%"）
                # 但是要排除类似"1,234.56%"的情况
                # 检查逗号是否在正确的位置
                before_percent = text[:percent_pos]
                if '.' in before_percent:
                    # 有小数点，检查逗号和小数点的关系
                    dot_pos = before_percent.find('.')
                    for i, char in enumerate(before_percent):
                        if char == ',' and i > dot_pos:
                            # 逗号在小数点后面，这是错误格式
                            return "error_num"
                else:
                    # 没有小数点，%号前不应该有逗号
                    return "error_num"

        # 3. 检查负值格式
        cleaned = text

        # 处理括号负数
        is_parenthesis_negative = (
                cleaned.startswith('(') and
                cleaned.endswith(')') and
                '(' not in cleaned[1:-1] and
                ')' not in cleaned[1:-1]
        )

        if is_parenthesis_negative:
            # 检查括号内是否还有负号
            inside = cleaned[1:-1].strip()
            if inside.startswith('-') or inside.endswith('-'):
                return "error_num"  # 如"(-450)"或"(450-)"，错误格式
            cleaned = '-' + inside

        # 4. 检查多个负号或负号位置错误
        if cleaned.count('-') > 1:
            return "error_num"  # 如"--450"

        if '-' in cleaned and not cleaned.startswith('-'):
            return "error_num"  # 如"450-"

        # 5. 移除负号、逗号、小数点、%号用于数值转换
        test_str = cleaned
        if '-' in test_str:
            test_str = test_str.replace('-', '', 1)

        # 记录原始符号用于格式检查
        has_percent = '%' in test_str
        dot_count = test_str.count('.')
        comma_count = test_str.count(',')

        # 用于数值转换的字符串
        numeric_test = test_str.replace(',', '').replace('.', '').replace('%', '')

        # 6. 尝试转换为数值
        try:
            # 如果转换失败，说明不是有效数值
            float(numeric_test)
        except ValueError:
            return "text"  # 包含数字但不是有效数值

        # 7. 格式检查
        # 检查%号
        if has_percent:
            if not cleaned.endswith('%'):
                return "error_num"  # %不在末尾
            if cleaned.count('%') > 1:
                return "error_num"  # 多个%

        # 检查小数点
        if dot_count > 1:
            return "error_num"  # 多个小数点

        # 检查逗号位置（如果有小数点）
        if dot_count == 1 and comma_count > 0:
            dot_pos = cleaned.find('.')
            # 检查逗号是否都在小数点前面
            for i, char in enumerate(cleaned):
                if char == ',' and i > dot_pos:
                    return "error_num"  # 逗号在小数点后面

        # 8. 检查是否为标准格式
        # 标准格式：有逗号时必须在正确位置，%在末尾等
        if self._is_standard_format(cleaned):
            return "std_num"
        else:
            return "minor_num"

    def _is_standard_format(self, text):
        """
        判断是否为标准数值格式
        标准格式要求：
        1. 千分位逗号格式正确（每3位一个逗号）
        2. 如果有小数点，后面通常有数字
        3. 没有多余的空格或其他字符
        """
        if not text:
            return False

        # 移除负号和%号
        test_text = text
        if test_text.startswith('-'):
            test_text = test_text[1:]
        if test_text.endswith('%'):
            test_text = test_text[:-1]

        # 检查逗号格式
        if ',' in test_text:
            # 分割整数和小数部分
            if '.' in test_text:
                int_part, dec_part = test_text.split('.', 1)
            else:
                int_part, dec_part = test_text, ""

            # 检查整数部分的逗号格式
            groups = int_part.split(',')
            # 第一组可以是1-3位
            if not (1 <= len(groups[0]) <= 3):
                return False

            # 后面的每组必须正好是3位
            for group in groups[1:]:
                if len(group) != 3:
                    return False

        return True

    def _fill_blank_cells(self, cell_types):
        """
        填充空白单元格的类型（根据同行/同列的众数类型）
        """
        if not cell_types:
            return

        num_rows = len(cell_types)
        num_cols = len(cell_types[0]) if num_rows > 0 else 0

        for r in range(num_rows):
            for c in range(num_cols):
                if cell_types[r][c] == "blank":
                    # 查找同行和同列的非空白类型
                    row_types = []
                    col_types = []

                    # 同行
                    for cc in range(num_cols):
                        if cc != c and cell_types[r][cc] != "blank":
                            row_types.append(cell_types[r][cc])

                    # 同列
                    for rr in range(num_rows):
                        if rr != r and cell_types[rr][c] != "blank":
                            col_types.append(cell_types[rr][c])

                    # 合并所有类型
                    all_types = row_types + col_types

                    if all_types:
                        # 找出众数类型
                        type_counts = Counter(all_types)
                        most_common = type_counts.most_common(1)

                        if most_common:
                            cell_types[r][c] = most_common[0][0]

    def _determine_row_column_mark(self, cell_types, label):
        """
        根据单元格类型列表确定行或列的标记
        """
        # 过滤掉空白单元格
        non_blank_types = [t for t in cell_types if t != "blank"]

        if not non_blank_types:
            return 0  # 全空白，视为纯文本

        # 检查是否有文本
        has_text = "text" in non_blank_types
        has_std_num = "std_num" in non_blank_types
        has_minor_num = "minor_num" in non_blank_types
        has_error_num = "error_num" in non_blank_types

        # 4. 混合类型（包含文本和任何数值）
        if has_text and (has_std_num or has_minor_num or has_error_num):
            return 4

        # 3. 很可能错误的数值
        if has_error_num:
            return 3

        # 现在只包含数值类型
        # 2. 有小问题的数值（有minor_num，可能也有std_num）
        if has_minor_num:
            print(f"  {label}: 标记2 - 格式问题数值")
            return 2

        # 1. 完全正确的数值（全是std_num）
        if has_std_num and not has_minor_num and not has_error_num:
            # print(f"  {label}: 标记1 - 标准数值")
            return 1

        # 0. 纯文本
        if not has_std_num and not has_minor_num and not has_error_num:
            # print(f"  {label}: 标记0 - 纯文本")
            return 0

        # 默认返回0
        return 0

    def _count_marks(self, marks_list):
        """
        统计标记数量
        """
        counter = Counter(marks_list)

        result = []
        for mark in range(5):
            count = counter.get(mark, 0)
            if count > 0:
                result.append(f"标记{mark}:{count}个")

        return ", ".join(result)

    def is_numeric_value(self, cell_value):
        """
        判断单元格值是否为数值类数据
        """
        cell_type = self._analyze_cell_type(cell_value)
        return cell_type in ["std_num", "minor_num", "error_num"]

    def _is_pure_numeric(self, cell):
        """
        判断是否为纯数值
        """
        cell_type = self._analyze_cell_type(cell)
        return cell_type in ["std_num", "minor_num"]

    def _looks_like_numeric_data(self, text):
        """判断文本是否看起来像数值型数据"""
        if not text:
            return False

        text_str = str(text).strip()
        clean_text = text_str.replace(',', '').replace(' ', '').replace('¥', '').replace('$', '').replace('€', '')

        if clean_text.startswith('(') and clean_text.endswith(')'):
            clean_text = '-' + clean_text[1:-1]

        if not any(c.isdigit() for c in clean_text):
            return False

        try:
            if '%' in clean_text:
                clean_text = clean_text.replace('%', '')
                float(clean_text)
                return True
            else:
                float(clean_text)
                return True
        except ValueError:
            digit_count = sum(1 for c in clean_text if c.isdigit())
            total_len = len(clean_text)
            if digit_count / total_len > 0.7:
                return True

        return False

    def create_marked_table(self, table, row_checks=None, col_checks=None):
        """
        智能两轮处理版：创建带标记的表格
        第一轮：正常计算所有行列标记
        第二轮：只有在有列标记为0时，才重新计算行标记（排除标记为0的列）
        新增：对于整行或整列都是空的，特征值给0
        """
        if not table:
            return []

        num_rows = len(table)
        num_cols = len(table[0]) if table else 0

        # ========== 辅助函数：检查单元格是否为空 ==========
        def is_cell_empty(cell):
            if cell is None:
                return True
            cell_str = str(cell)
            # 处理nan情况
            if cell_str.lower() in ['nan', 'nat', 'null', 'none']:
                return True
            # 检查是否只包含空白字符
            if cell_str.strip() == '':
                return True
            return False

        # 检测整行为空的函数
        def is_empty_row(row_idx):
            if row_idx >= num_rows:
                return False
            row_data = table[row_idx]
            for cell in row_data:
                if not is_cell_empty(cell):
                    return False
            return True

        # 检测整列为空的函数
        def is_empty_col(col_idx):
            if col_idx >= num_cols:
                return False
            for r in range(num_rows):
                cell = table[r][col_idx] if col_idx < len(table[r]) else None
                if not is_cell_empty(cell):
                    return False
            return True

        # ========== 关键优化：找到第一个真正的数值数据行 ==========
        first_data_row = 0

        for r in range(num_rows):
            has_pure_numeric = False
            for c in range(1, min(3, num_cols)):
                if c < num_cols and table[r][c] is not None:
                    cell = table[r][c]
                    if self.is_numeric_value(cell) and self._is_pure_numeric(cell):
                        has_pure_numeric = True
                        break

            if has_pure_numeric:
                first_data_row = r
                print(f"找到第一个数值数据行: 行{first_data_row}")
                break

        # 自动检测数据列
        data_column_indices = []
        for c in range(num_cols):
            if c == 0:  # 第一列通常是行表头
                continue
            header = str(table[0][c]) if table[0][c] else ""
            if any(marker in header for marker in ["行标记", "列标记", "标记", "标识", "flag"]):
                print(f"跳过标记列: 列{c}")
                continue
            data_column_indices.append(c)

        print(f"数据列索引: {data_column_indices}")

        # 如果没有提供标记，则根据数据类型计算
        if row_checks is None or col_checks is None:
            # 初始化标记数组
            row_checks = [0] * num_rows
            col_checks = [0] * num_cols

            # 1. 分析所有单元格的类型
            cell_types = [[None] * num_cols for _ in range(num_rows)]

            for r in range(num_rows):
                for c in range(num_cols):
                    cell_value = table[r][c]
                    cell_types[r][c] = self._analyze_cell_type(cell_value)

            # 2. 处理空白单元格
            self._fill_blank_cells(cell_types)

            # ========== 第一轮：正常计算行列标记 ==========
            print("\n=== 第一轮：正常计算行列标记 ===")

            # 计算列标记
            for c in data_column_indices:
                # 先检查是否整列为空
                if is_empty_col(c):
                    col_checks[c] = 0
                else:
                    col_cell_types = []
                    for r in range(first_data_row, num_rows):
                        if c < num_cols:
                            col_cell_types.append(cell_types[r][c])

                    # 过滤掉空白单元格
                    non_blank_types = [t for t in col_cell_types if t != "blank"]

                    if not non_blank_types:
                        col_checks[c] = 0
                    else:
                        col_checks[c] = self._determine_row_column_mark(non_blank_types, f"列{c}")

            # 计算行标记（第一轮，使用所有列）
            for r in range(first_data_row):
                # 检查是否整行为空
                if is_empty_row(r):
                    row_checks[r] = 0
                else:
                    row_checks[r] = 0

            for r in range(first_data_row, num_rows):
                # 先检查是否整行为空
                if is_empty_row(r):
                    row_checks[r] = 0
                else:
                    # 收集该行所有数据列的单元格类型
                    row_cell_types = []
                    for c in data_column_indices:
                        if c < num_cols:
                            row_cell_types.append(cell_types[r][c])

                    # 过滤掉空白单元格
                    non_blank_types = [t for t in row_cell_types if t != "blank"]

                    if not non_blank_types:
                        row_checks[r] = 0  # 空白行
                    else:
                        row_checks[r] = self._determine_row_column_mark(non_blank_types, f"行{r}（第一轮）")

            # ========== 检查是否需要第二轮处理 ==========
            zero_marked_columns = [c for c in data_column_indices if col_checks[c] == 0]

            if zero_marked_columns:
                # 重新计算行标记，排除纯文本列
                for r in range(first_data_row, num_rows):
                    # 如果已经是空行标记为0，跳过重新计算
                    if row_checks[r] == 0 and is_empty_row(r):
                        continue

                    # 只收集非纯文本列的单元格类型
                    row_cell_types = []
                    for c in data_column_indices:
                        if c < num_cols and col_checks[c] != 0:  # 排除标记为0的列
                            row_cell_types.append(cell_types[r][c])

                    # 过滤掉空白单元格
                    non_blank_types = [t for t in row_cell_types if t != "blank"]

                    if not non_blank_types:
                        # 如果没有非空白数据，检查是否有文本数据
                        has_any_text = False
                        for c in data_column_indices:
                            if c < num_cols and cell_types[r][c] == "text":
                                has_any_text = True
                                break

                        if has_any_text:
                            row_checks[r] = 0  # 只有文本
                        else:
                            row_checks[r] = 0  # 空白行
                    else:
                        # 使用新的单元格类型重新计算行标记
                        new_mark = self._determine_row_column_mark(non_blank_types, f"行{r}（第二轮）")

                        # 比较新旧标记，打印变化
                        old_mark = row_checks[r]
                        row_checks[r] = new_mark
            else:
                print(f"\n=== 无需第二轮处理（没有纯文本列） ===")

        # ========== 创建带标记的表格 ==========
        marked_table = []
        for r in range(num_rows + 1):
            marked_table.append([None] * (num_cols + 1))

        # 复制原始数据
        for r in range(num_rows):
            for c in range(num_cols):
                marked_table[r][c] = table[r][c]

        # 添加行标记
        for r in range(num_rows):
            marked_table[r][num_cols] = row_checks[r]

        marked_table[0][num_cols] = "行标记"

        # 添加列标记
        for c in range(num_cols):
            marked_table[num_rows][c] = col_checks[c]

        marked_table[num_rows][0] = "列标记"

        marked_table[num_rows][num_cols] = "标记说明:0-纯文本 1-标准数值 2-格式问题 3-可能错误 4-混合类型"

        return marked_table

    def add_feature_marks(self, validated_table, validation_marks):
        """
        添加特征标记 - 修复最后一列表头问题
        修改：对于整行或整列都是空的，特征值给0
        """
        marked_table = [row[:] for row in validated_table]  # 深拷贝

        print(f"\n=== add_feature_marks调试信息 ===")

        if not marked_table:
            return marked_table

        row_marks = validation_marks["row_marks"]
        col_marks = validation_marks["col_marks"]

        # 辅助函数：检查单元格是否为空
        def is_cell_empty(cell):
            if cell is None:
                return True
            cell_str = str(cell)
            # 处理nan情况
            if cell_str.lower() in ['nan', 'nat', 'null']:
                return True
            # 检查是否只包含空白字符
            if cell_str.strip() == '':
                return True
            return False

        # 1. 添加最后一列（行标记列）
        print(f"\n添加行标记列:")

        for i in range(len(marked_table)):
            if i == 0:
                # 第一行：添加"行标记"作为列标题
                marked_table[i].append("行标记")
            else:
                # 检查是否整行为空
                is_empty_row = True
                row_values = marked_table[i]
                for cell in row_values:
                    if not is_cell_empty(cell):
                        is_empty_row = False
                        break

                if is_empty_row:
                    # 整行为空，特征值给0
                    mark_value = "0"
                else:
                    # 其他行：添加对应的行标记值
                    mark_idx = i - 1 if (i - 1) < len(row_marks) else len(row_marks) - 1
                    mark_value = str(row_marks[mark_idx]) if mark_idx >= 0 and mark_idx < len(row_marks) else "0"
                marked_table[i].append(mark_value)

        # 2. 添加最后一行（列标记行）
        last_row = []

        # 第一列：写"列标记"作为行标题
        last_row.append("列标记")

        # 检查整列为空的情况
        num_rows = len(marked_table)  # 当前行数（包括表头行）
        num_cols = len(marked_table[0])  # 当前列数（已添加行标记列）

        # 其他列：添加列标记（注意索引对齐）
        for j in range(1, num_cols):
            # 检查是否整列为空（不包括表头行）
            is_empty_col = True
            for i in range(1, num_rows):  # 从第1行开始，跳过表头行
                if i < len(marked_table) and j < len(marked_table[i]):
                    cell = marked_table[i][j]
                    if not is_cell_empty(cell):
                        is_empty_col = False
                        break

            if is_empty_col:
                # 整列为空，特征值给0
                mark_value = "0"
            else:
                # 正常处理列标记
                mark_idx = j - 1  # 因为第0列是行表头列

                if mark_idx < len(col_marks):
                    mark_value = str(col_marks[mark_idx])
                else:
                    # 对于行标记列（最后一列），给它一个特殊的列标记值
                    if j == num_cols - 1:
                        mark_value = "1"  # 行标记列的列标记
                    else:
                        mark_value = "0"

            last_row.append(mark_value)

        marked_table.append(last_row)

        # 打印一些调试信息，查看哪些行被标记为0
        print(f"\n=== 空行标记统计 ===")
        empty_row_count = 0
        for i in range(1, num_rows):  # 跳过表头行
            if marked_table[i][-1] == "0":  # 检查最后一列（行标记）
                empty_row_count += 1

        print(f"总共发现 {empty_row_count} 个空行")
        print(f"标记列的值分布: {[marked_table[i][-1] for i in range(1, min(10, num_rows))]}...")

        return marked_table





# 使用示例
def example_usage():
    # 示例表格数据
    sample_table = [
        ["项目", "2024年", "2023年", "变化"],
        ["营业收入", "1,234,567", "987,654", "246,913"],
        ["净利润", "123,456.78", "98,765.43", "24,691.35"],
        ["毛利率", "25.5%", "23.8%", "1.7%"],
        ["备注", "业绩增长良好", "稳定增长", "持续改善"]
    ]

    # 创建处理器
    processor = MarkedTableProcessor()

    # 创建带标记的表格
    marked_table = processor.create_marked_table(sample_table)

    # 打印结果
    print("\n生成的标记表格:")
    for row in marked_table:
        print(row)

    return marked_table


if __name__ == "__main__":
    example_usage()