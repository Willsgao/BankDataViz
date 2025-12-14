# file: final_data.py

import pandas as pd
from typing import List, Dict, Any, Optional
import re


class DataTypeDeterminer:
    """
    数据类型判断器
    判断规则：余额 | 发生额 | 本期增加 | 本期减少 | 占比 | 同比 | 环比 | 减值准备 | 其他
    """

    def __init__(self):
        # 关键词映射表
        self.keyword_mapping = {
            "余额": ["余额", "结余", "结存", "存量", "总额", "合计", "总计", "小计",
                     "期末", "期初", "年末", "年初", "月底", "月初", "结余", "结存"],
            "发生额": ["发生", "发生额", "发生数", "金额", "数额", "数值", "数",
                       "收入", "支出", "费用", "成本", "收益", "利润", "损失",
                       "发生合计", "发生总计", "发生小计"],
            "本期增加": ["增加", "增长", "上升", "上涨", "提高", "提升", "追加",
                         "新增", "本期增加", "本年增加", "年度增加", "增加额", "增长额"],
            "本期减少": ["减少", "下降", "下跌", "降低", "缩减", "削减", "减少额",
                         "下降额", "本期减少", "本年减少", "年度减少", "减少数"],
            "占比": ["占比", "比例", "比率", "百分比", "百分率", "比重", "份额",
                     "占", "率", "百分比", "百分率", "%", "比例"],
            "同比": ["同比", "比上年", "较上年", "与上年比", "年度同比", "同比变化",
                     "同比增长", "同比减少", "同比变动", "同比增减"],
            "环比": ["环比", "比上期", "较上期", "与上期比", "环比变化", "环比增长",
                     "环比减少", "环比变动", "环比增减", "较上月", "比上月"],
            "减值准备": ["减值", "坏账", "拨备", "准备", "减值准备", "坏账准备",
                         "拨备覆盖率", "贷款拨备率", "减值损失", "坏账损失"]
        }

        # 表格类型映射
        self.table_type_mapping = {
            "资产负债表": "余额",
            "财务状况表": "余额",
            "资产表": "余额",
            "负债表": "余额",
            "所有者权益表": "余额",
            "利润表": "发生额",
            "损益表": "发生额",
            "收益表": "发生额",
            "现金流量表": "发生额",
            "财务比率表": "占比",
            "指标分析表": "其他",
            "明细表": "其他"
        }

        # 反转关键词映射，便于快速查找
        self.keyword_to_type = {}
        for data_type, keywords in self.keyword_mapping.items():
            for keyword in keywords:
                self.keyword_to_type[keyword] = data_type

    def get_data_type(self, row_header: str, col_header: str,
                      cell_value: Any, table_context: str = "") -> str:
        """
        精确的数据类型判断

        Args:
            row_header: 行表头
            col_header: 列表头
            cell_value: 单元格值
            table_context: 表格类型/上下文

        Returns:
            str: 数据类型
        """
        # 第1层：优先从列标题提取（因为列标题更可能包含数据类型）
        col_data_type = self._extract_from_header(col_header)
        if col_data_type:
            return col_data_type

        # 第2层：从行标题提取
        row_data_type = self._extract_from_header(row_header)
        if row_data_type:
            return row_data_type

        # 第3层：从行列组合判断
        combined_type = self._infer_from_combined_headers(row_header, col_header)
        if combined_type != "其他":
            return combined_type

        # 第4层：从数值特征判断
        value_type = self._infer_from_value(cell_value, col_header)

        # 第5层：从表格上下文推断
        if table_context:
            for table_keyword, default_type in self.table_type_mapping.items():
                if table_keyword in table_context:
                    return default_type

        return value_type or "其他"

    def _extract_from_header(self, header: str) -> Optional[str]:
        """
        从表头中提取数据类型

        Args:
            header: 表头文本

        Returns:
            数据类型或None
        """
        if not header:
            return None

        header_str = str(header).lower()  # 转为小写方便匹配

        # 检查是否包含关键词
        for keyword, data_type in self.keyword_to_type.items():
            if keyword in header_str:
                return data_type

        return None

    def _infer_from_combined_headers(self, row_header: str, col_header: str) -> str:
        """
        从行列表头组合推断数据类型

        Args:
            row_header: 行表头
            col_header: 列表头

        Returns:
            数据类型
        """
        combined_text = f"{row_header} {col_header}".lower()

        # 检查组合文本中的关键词
        for keyword, data_type in self.keyword_to_type.items():
            if keyword in combined_text:
                return data_type

        # 特殊模式判断
        if "%" in combined_text or "百分比" in combined_text:
            if "同比" in combined_text:
                return "同比"
            elif "环比" in combined_text:
                return "环比"
            else:
                return "占比"

        # 检查是否为变化率列
        change_keywords = ["变化", "变动", "增减", "增减率", "增长率"]
        for keyword in change_keywords:
            if keyword in combined_text:
                if "同比" in combined_text:
                    return "同比"
                elif "环比" in combined_text:
                    return "环比"
                elif "年度" in combined_text or "上年" in combined_text:
                    return "同比"
                else:
                    return "其他"  # 一般变化

        return "其他"

    def _infer_from_value(self, value: Any, col_header: str = "") -> str:
        """
        从数值特征推断数据类型

        Args:
            value: 单元格值
            col_header: 列表头（用于辅助判断）

        Returns:
            数据类型
        """
        if value is None:
            return "其他"

        value_str = str(value).strip()

        # 检查是否为百分比格式
        if '%' in value_str:
            # 根据列表头判断是占比还是同比环比
            if col_header and ("同比" in col_header or "比上年" in col_header):
                return "同比"
            elif col_header and ("环比" in col_header or "比上期" in col_header):
                return "环比"
            else:
                return "占比"

        # 检查是否为百分比数值（0-100之间）
        try:
            # 清理数值字符串
            clean_str = value_str.replace(',', '').replace('(', '').replace(')', '')
            clean_str = re.sub(r'[^\d.-]', '', clean_str)  # 只保留数字、点、负号

            if clean_str:
                num = float(clean_str)
                if -100 <= num <= 100 and '.' in str(num):
                    # 根据列表头进一步判断
                    if col_header and ("变化" in col_header or "变动" in col_header):
                        if col_header and "同比" in col_header:
                            return "同比"
                        elif col_header and "环比" in col_header:
                            return "环比"
                        else:
                            return "占比"
                    else:
                        return "占比"
        except:
            pass

        # 检查是否为负数（可能表示减少）
        try:
            if value_str.startswith('(') and value_str.endswith(')'):
                return "本期减少"

            clean_str = value_str.replace(',', '').replace(' ', '')
            if clean_str.startswith('-'):
                return "本期减少"
        except:
            pass

        # 检查是否为大额数值（可能是余额或发生额）
        try:
            clean_str = value_str.replace(',', '').replace('(', '').replace(')', '')
            clean_str = re.sub(r'[^\d.-]', '', clean_str)

            if clean_str:
                num = float(clean_str)
                if abs(num) > 100:  # 假设大于100的数值
                    # 进一步判断
                    if col_header and ("余额" in col_header or "期末" in col_header):
                        return "余额"
                    else:
                        return "发生额"
        except:
            pass

        return "其他"

    def get_data_type(self, row_header: str, col_header: str,
                      cell_value: Any, table_context: str = "") -> str:
        """
        精确的数据类型判断

        Args:
            row_header: 行表头
            col_header: 列表头
            cell_value: 单元格值
            table_context: 表格类型/上下文

        Returns:
            str: 数据类型
        """
        # 第1层：优先从列标题提取（因为列标题更可能包含数据类型）
        col_data_type = self._extract_from_header(col_header)
        if col_data_type:
            return col_data_type

        # 第2层：从行标题提取
        row_data_type = self._extract_from_header(row_header)
        if row_data_type:
            return row_data_type

        # 第3层：从行列组合判断
        combined_type = self._infer_from_combined_headers(row_header, col_header)
        if combined_type != "其他":
            return combined_type

        # 第4层：从数值特征判断
        value_type = self._infer_from_value(cell_value, col_header)

        # 第5层：从表格上下文推断
        if table_context:
            for table_keyword, default_type in self.table_type_mapping.items():
                if table_keyword in table_context:
                    return default_type

        return value_type or "其他"

    def _infer_from_value(self, value: Any, col_header: str = "") -> str:
        """
        从数值特征推断数据类型
        同时考虑单位信息
        """
        if value is None:
            return "其他"

        value_str = str(value).strip()

        # 检查是否为百分比格式
        if '%' in value_str:
            # 根据列表头判断是占比还是同比环比
            if col_header and ("同比" in col_header or "比上年" in col_header):
                return "同比"
            elif col_header and ("环比" in col_header or "比上期" in col_header):
                return "环比"
            else:
                return "占比"

        # 检查是否为百分比数值（0-100之间）
        try:
            # 清理数值字符串
            clean_str = value_str.replace(',', '').replace('(', '').replace(')', '')
            clean_str = re.sub(r'[^\d.-]', '', clean_str)  # 只保留数字、点、负号

            if clean_str:
                num = float(clean_str)
                # 如果数值在0-100之间，且不是整百万/千万级的大额数值
                if -100 <= num <= 100 and abs(num) < 1000:
                    # 检查是否有%符号或相关文本
                    if '%' in value_str or "百分比" in value_str:
                        return "占比"
                    # 进一步根据列表头判断
                    if col_header and ("变化" in col_header or "变动" in col_header):
                        if col_header and "同比" in col_header:
                            return "同比"
                        elif col_header and "环比" in col_header:
                            return "环比"
                        else:
                            return "占比"
                    else:
                        return "占比"
        except:
            pass

        # 检查是否为负数（可能表示减少）
        try:
            if value_str.startswith('(') and value_str.endswith(')'):
                return "本期减少"

            clean_str = value_str.replace(',', '').replace(' ', '')
            if clean_str.startswith('-'):
                return "本期减少"
        except:
            pass

        # 检查是否为大额数值（可能是余额或发生额）
        try:
            clean_str = value_str.replace(',', '').replace('(', '').replace(')', '')
            clean_str = re.sub(r'[^\d.-]', '', clean_str)

            if clean_str:
                num = float(clean_str)
                # 检查是否为大额数值
                if abs(num) > 100:  # 假设大于100的数值
                    # 进一步判断
                    if col_header and ("余额" in col_header or "期末" in col_header or
                                       "期初" in col_header or "年末" in col_header or
                                       "年初" in col_header):
                        return "余额"
                    else:
                        return "发生额"
        except:
            pass

        return "其他"


class FinalDataConverter:
    """
    最终数据转换器
    将带表头的二维表格数据转换为长格式最终数据
    """

    def __init__(self, data_type_detector=None):
        """
        初始化转换器

        Args:
            data_type_detector: 数据类型判断器实例
        """
        self.data_type_detector = data_type_detector or DataTypeDeterminer()

    def convert_table_to_long_format1111(self, table_data: List[List],
                                     table_metadata: Dict[str, Any],
                                     bank_name: str = "中国建设银行",
                                     page_num: int = 1,
                                     entity: str = "本集团") -> List[Dict]:
        """
        将单个表格转换为长格式

        Args:
            table_data: 二维表格数据，包含表头
            table_metadata: 表格元数据
                {
                    'id': '1',
                    'name': '表名',
                    'default_currency': '人民币',
                    'default_report_period': '2024年',
                    'default_unit': '万元',
                    'headers': {
                        'cols': [...],  # 横向表头
                        'rows': [...]   # 纵向表头
                    }
                }
            bank_name: 银行名称
            page_num: 页号
            entity: 主体

        Returns:
            List[Dict]: 长格式数据列表
        """
        if not table_data or len(table_data) < 2:
            return []

        long_format_data = []

        # 获取表头信息
        col_headers = table_data[0]  # 第0行是列标题
        row_headers_original = table_metadata.get('headers', {}).get('rows', [])

        # 遍历数据区域（从第1行开始，跳过表头行）
        for row_idx in range(1, len(table_data)):
            row_data = table_data[row_idx]

            # 获取行表头（使用LLM分析的行表头，比Excel中的更准确）
            if row_idx - 1 < len(row_headers_original):
                row_header = row_headers_original[row_idx - 1]
            else:
                # 如果没有对应的LLM行表头，使用Excel中的第一列
                row_header = row_data[0] if row_data else ""

            # 遍历每一列的数据
            for col_idx in range(1, len(row_data)):  # 从第1列开始，跳过行表头列
                cell_value = row_data[col_idx]

                # 跳过空值和标记列
                if cell_value is None or cell_value == "":
                    continue

                if col_idx - 1 < len(col_headers):
                    col_header = col_headers[col_idx - 1]
                else:
                    col_header = ""

                # 判断报告期（优先使用列标题中的报告期）
                report_period = self._extract_report_period(col_header, table_metadata)

                # 判断数据类型
                data_type = self.data_type_detector.get_data_type(
                    row_header=row_header,
                    col_header=col_header,
                    cell_value=cell_value,
                    table_context=table_metadata.get('name', '')
                )

                # 构建长格式数据记录
                record = {
                    '银行名': bank_name,
                    '表名': table_metadata.get('name', ''),
                    '页号': page_num,
                    '主体': entity,
                    '纵向层级路径': self._clean_header_path(row_header),
                    '横向层级路径': self._clean_header_path(col_header),
                    '数据类型': data_type,
                    '币种': table_metadata.get('default_currency', ''),
                    '单位': table_metadata.get('default_unit', ''),
                    '报告期': report_period,
                    '数值': self._format_numeric_value(cell_value)
                }

                long_format_data.append(record)

        return long_format_data


    def _extract_report_period(self, col_header: str,
                               table_metadata: Dict[str, Any]) -> str:
        """
        提取报告期

        优先级：
        1. 列标题中的报告期（如果有）
        2. LLM默认报告期
        3. 空字符串
        """
        # 1. 尝试从列标题中提取报告期
        col_report_period = self._extract_report_period_from_header(col_header)
        if col_report_period:
            return col_report_period

        # 2. 使用LLM默认报告期
        default_report_period = table_metadata.get('default_report_period', '')
        return default_report_period

    def _extract_report_period_from_header(self, header: str) -> str:
        """
        从表头中提取报告期
        """
        if not header:
            return ""

        header_str = str(header)

        # 常见的报告期模式
        patterns = [
            # 年份模式
            r'(20\d{2})年',  # 2024年
            r'(20\d{2})年度',  # 2024年度
            r'(20\d{2})年(?:第)?([一二三四1-4])季度',  # 2024年第一季度
            r'(20\d{2})年(?:第)?([一二三四1-4])季度',  # 2024年第一季度
            r'(20\d{2})年(?:上|下)半年',  # 2024年上半年
            r'(20\d{2})年(?:第)?([1-4])季度',  # 2024年第1季度
            # 完整日期模式
            r'(20\d{2})年(\d{1,2})月(\d{1,2})日',  # 2024年12月31日
            r'(20\d{2})-(\d{2})-(\d{2})',  # 2024-12-31
            r'(20\d{2})/(\d{1,2})/(\d{1,2})',  # 2024/12/31
            # 相对时间模式
            r'截至(20\d{2})年(\d{1,2})月(\d{1,2})日',  # 截至2024年12月31日
            r'截止(20\d{2})年(\d{1,2})月(\d{1,2})日',  # 截止2024年12月31日
            # 季度模式
            r'第[一二三四1-4]季度',  # 第一季度
            r'Q[1-4]',  # Q1, Q2, Q3, Q4
        ]

        for pattern in patterns:
            match = re.search(pattern, header_str)
            if match:
                # 提取匹配的完整文本
                return match.group(0)

        return ""

    def _clean_header_path(self, header_path: str) -> str:
        """
        清理表头路径
        - 去掉多余的>>分隔符
        - 去掉特殊字符
        """
        if not header_path:
            return ""

        # 如果包含>>，拆分为路径列表
        if '>>' in str(header_path):
            parts = str(header_path).split('>>')
            # 过滤空的部分
            parts = [part.strip() for part in parts if part.strip()]
            # 去掉可能的分组标记如a>>, b>>等
            filtered_parts = []
            for part in parts:
                if len(part) == 1 and part.isalpha():  # 单个字母标记如a, b, c
                    continue
                filtered_parts.append(part)
            return '>>'.join(filtered_parts)

        return str(header_path).strip()

    def _format_numeric_value(self, value) -> str:
        """
        格式化数值
        - 去掉千分位逗号
        - 处理括号表示法
        - 保留负号
        """
        if value is None:
            return ""

        value_str = str(value).strip()

        # 处理括号表示法（表示负数）
        if value_str.startswith('(') and value_str.endswith(')'):
            value_str = '-' + value_str[1:-1]

        # 去掉千分位逗号
        value_str = value_str.replace(',', '')

        # 去掉空格
        value_str = value_str.replace(' ', '')

        return value_str

    def batch_convert_tables(self, all_tables_data: List[List[List]],
                             all_llm_tables: List[Dict[str, Any]],
                             output_excel_path: str = None,  # 允许为None
                             bank_name: str = "中国建设银行") -> bool:
        """
        批量转换多个表格
        """
        try:
            # 检查输出路径
            if output_excel_path is None:
                # 设置默认路径
                output_excel_path = "final_data.xlsx"
                print(f"使用默认输出路径: {output_excel_path}")
            elif not isinstance(output_excel_path, str):
                print(f"错误：输出路径必须是字符串，当前类型: {type(output_excel_path)}")
                return False

            all_long_data = []

            # 对每个表格进行转换
            for table_idx, (table_data, llm_table) in enumerate(zip(all_tables_data, all_llm_tables)):
                if not table_data:
                    continue

                print(f"转换表格 {table_idx + 1}/{len(all_tables_data)}: {llm_table.get('name', '')}")

                # 转换为长格式
                long_data = self.convert_table_to_long_format(
                    table_data=table_data,
                    table_metadata=llm_table,
                    bank_name=bank_name,
                    page_num=table_idx + 1
                )

                all_long_data.extend(long_data)

            # 转换为DataFrame
            if not all_long_data:
                print("警告：没有转换出任何数据")
                return False

            df = pd.DataFrame(all_long_data)

            # 保存到Excel
            with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Sheet1', index=False)

                # 设置列宽
                worksheet = writer.sheets['Sheet1']
                for idx, col in enumerate(df.columns):
                    column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = min(column_width, 50)

            print(f"✅ 最终数据保存成功: {output_excel_path}")
            print(f"   共转换 {len(all_long_data)} 条记录")

            return True

        except Exception as e:
            print(f"❌ 最终数据转换失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _filter_and_clean_table_data(self, table_data: List[List]) -> List[List]:
        """
        过滤和清理表格数据：
        1. 移除行标记和列标记列
        2. 过滤行表头缺失的行
        3. 返回干净的表格数据

        Args:
            table_data: 原始表格数据，包含特征标记

        Returns:
            List[List]: 清理后的表格数据
        """
        if not table_data or len(table_data) < 2:
            return []

        print(f"原始表格尺寸: {len(table_data)}行 × {len(table_data[0]) if table_data else 0}列")

        # 深拷贝表格数据
        cleaned_data = []

        # 1. 检查并移除特征标记列（最后一列的"行标记"）
        has_row_mark_column = False
        row_mark_column_index = -1

        if table_data and len(table_data[0]) > 0:
            # 检查第一行最后一列是否是"行标记"
            for col_idx in range(len(table_data[0])):
                cell_value = table_data[0][col_idx]
                if cell_value and str(cell_value).strip() == "行标记":
                    row_mark_column_index = col_idx
                    has_row_mark_column = True
                    break

        # 2. 检查并移除特征标记行（最后一行的"列标记"）
        has_column_mark_row = False
        column_mark_row_index = -1

        for row_idx in range(len(table_data)):
            row = table_data[row_idx]
            if row and len(row) > 0:
                first_cell = row[0]
                if first_cell and str(first_cell).strip() == "列标记":
                    column_mark_row_index = row_idx
                    has_column_mark_row = True
                    break

        print(f"检测到行标记列: {has_row_mark_column}, 列标记行: {has_column_mark_row}")

        # 3. 提取有效数据区域（排除标记行和列）
        for row_idx, row in enumerate(table_data):
            # 跳过列标记行
            if has_column_mark_row and row_idx == column_mark_row_index:
                continue

            # 处理每一行，排除行标记列
            cleaned_row = []
            for col_idx, cell in enumerate(row):
                # 跳过行标记列
                if has_row_mark_column and col_idx == row_mark_column_index:
                    continue
                cleaned_row.append(cell)

            # 4. 过滤行表头缺失的行（从第1行开始检查）
            if row_idx == 0:
                # 保留表头行
                cleaned_data.append(cleaned_row)
            else:
                # 检查第一列（行表头列）是否为空
                if cleaned_row and len(cleaned_row) > 0:
                    row_header = cleaned_row[0]
                    # 判断行表头是否有效
                    if (row_header is not None and
                            str(row_header).strip() != "" and
                            str(row_header).strip() not in ["0", "1", "2", "3"]):  # 排除标记值
                        cleaned_data.append(cleaned_row)
                    else:
                        print(f"过滤第{row_idx}行：行表头缺失或无效 ('{row_header}')")
                else:
                    print(f"过滤第{row_idx}行：行数据为空")

        print(f"清理后表格尺寸: {len(cleaned_data)}行 × {len(cleaned_data[0]) if cleaned_data else 0}列")
        return cleaned_data

    def batch_convert_tables(self, all_tables_data: List[List[List]],
                             all_llm_tables: List[Dict[str, Any]],
                             output_excel_path: str = None,
                             bank_name: str = "中国建设银行") -> bool:
        """
        批量转换多个表格 - 增强版，包含数据过滤
        """
        try:
            # 检查输出路径
            if output_excel_path is None:
                output_excel_path = "final_data.xlsx"
                print(f"使用默认输出路径: {output_excel_path}")

            all_long_data = []

            # 对每个表格进行转换
            for table_idx, (table_data, llm_table) in enumerate(zip(all_tables_data, all_llm_tables)):
                if not table_data:
                    print(f"表格{table_idx + 1}数据为空，跳过")
                    continue

                print(f"\n转换表格 {table_idx + 1}/{len(all_tables_data)}: {llm_table.get('name', '')}")

                # ========== 关键修改：过滤和清理表格数据 ==========
                cleaned_table_data = self._filter_and_clean_table_data(table_data)

                if not cleaned_table_data or len(cleaned_table_data) < 2:
                    print(f"表格{table_idx + 1}清理后数据不足，跳过")
                    continue
                # ===============================================

                # 转换为长格式（使用清理后的数据）
                long_data = self.convert_table_to_long_format(
                    table_data=cleaned_table_data,  # 使用清理后的数据
                    table_metadata=llm_table,
                    bank_name=bank_name,
                    page_num=table_idx + 1
                )

                all_long_data.extend(long_data)
                print(f"  转换出 {len(long_data)} 条记录")

            # 转换为DataFrame
            if not all_long_data:
                print("警告：没有转换出任何数据")
                return False

            df = pd.DataFrame(all_long_data)

            # 保存到Excel
            with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Sheet1', index=False)

                # 设置列宽
                worksheet = writer.sheets['Sheet1']
                for idx, col in enumerate(df.columns):
                    column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.column_dimensions[chr(65 + idx)].width = min(column_width, 50)

            print(f"\n✅ 最终数据保存成功: {output_excel_path}")
            print(f"   共转换 {len(all_long_data)} 条记录")
            print(f"   数据列: {list(df.columns)}")

            # 数据预览
            if not df.empty:
                print(f"\n数据预览 (前5行):")
                print(df.head().to_string(index=False))

            return True

        except Exception as e:
            print(f"❌ 最终数据转换失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def convert_table_to_long_format111(self, table_data: List[List],
                                     table_metadata: Dict[str, Any],
                                     bank_name: str = "中国建设银行",
                                     page_num: int = 1,
                                     entity: str = "本集团") -> List[Dict]:
        """
        将单个表格转换为长格式
        注意：此方法接收的是已经过滤清理后的表格数据
        """
        if not table_data or len(table_data) < 2:
            return []

        long_format_data = []

        # 获取表头信息
        col_headers = table_data[0]  # 第0行是列标题
        row_headers_original = table_metadata.get('headers', {}).get('rows', [])

        # 遍历数据区域（从第1行开始，跳过表头行）
        for row_idx in range(1, len(table_data)):
            row_data = table_data[row_idx]

            # 注意：行表头有效性检查已经在 _filter_and_clean_table_data 中完成
            # 这里直接使用行表头

            # 获取行表头（第一列）
            row_header_cell = row_data[0] if row_data else ""

            # 优先使用LLM分析的行表头
            if row_idx - 1 < len(row_headers_original):
                row_header = row_headers_original[row_idx - 1]
                if not row_header or str(row_header).strip() == "":
                    # LLM行表头为空，使用单元格中的行表头
                    row_header = str(row_header_cell).strip()
            else:
                # 没有LLM行表头，使用单元格中的行表头
                row_header = str(row_header_cell).strip()

            # 清理行表头
            row_header = self._clean_header_path(row_header)

            # 遍历每一列的数据
            for col_idx in range(1, len(row_data)):  # 从第1列开始，跳过行表头列
                cell_value = row_data[col_idx]

                # 跳过空值
                if cell_value is None or cell_value == "":
                    continue

                if col_idx - 1 < len(col_headers):
                    col_header = col_headers[col_idx - 1]
                else:
                    col_header = ""

                # 判断报告期（优先使用列标题中的报告期）
                report_period = self._extract_report_period(col_header, table_metadata)

                # 判断数据类型
                data_type = self.data_type_detector.get_data_type(
                    row_header=row_header,
                    col_header=col_header,
                    cell_value=cell_value,
                    table_context=table_metadata.get('name', '')
                )

                # 构建长格式数据记录
                record = {
                    '银行名': bank_name,
                    '表名': table_metadata.get('name', ''),
                    '页号': page_num,
                    '主体': entity,
                    '纵向层级路径': row_header,
                    '横向层级路径': self._clean_header_path(col_header),
                    '数据类型': data_type,
                    '币种': table_metadata.get('default_currency', ''),
                    '单位': table_metadata.get('default_unit', ''),
                    '报告期': report_period,
                    '数值': self._format_numeric_value(cell_value)
                }

                long_format_data.append(record)

        return long_format_data

    def convert_table_to_long_format(self, table_data: List[List],
                                     table_metadata: Dict[str, Any],
                                     bank_name: str = "中国建设银行",
                                     page_num: int = 1,
                                     entity: str = "本集团") -> List[Dict]:
        """
        将单个表格转换为长格式
        横向路径和纵向路径直接使用原始的表头，不进行处理
        """
        if not table_data or len(table_data) < 2:
            return []

        long_format_data = []

        # 获取表头信息
        col_headers = table_data[0]  # 第0行是列标题

        # 调试：打印列标题
        print(f"\n[DEBUG] 表格列标题（共{len(col_headers)}列）:")
        for i, header in enumerate(col_headers):
            print(f"  列{i}: '{header}'")
        print("-" * 50)

        row_headers_original = table_metadata.get('headers', {}).get('rows', [])

        # 调试：打印LLM提供的行表头
        print(f"[DEBUG] LLM行表头（共{len(row_headers_original)}行）:")
        for i, header in enumerate(row_headers_original[:5]):  # 只显示前5个
            print(f"  行{i}: '{header}'")
        if len(row_headers_original) > 5:
            print(f"  ... 还有{len(row_headers_original) - 5}个行表头")
        print("-" * 50)

        # 遍历数据区域（从第1行开始，跳过表头行）
        for row_idx in range(1, len(table_data)):
            row_data = table_data[row_idx]

            if not row_data:
                continue

            # 获取行表头（第一列）
            row_header_cell = row_data[0] if len(row_data) > 0 else ""

            # 优先使用LLM分析的行表头
            if row_idx - 1 < len(row_headers_original):
                row_header = row_headers_original[row_idx - 1]
                if not row_header or str(row_header).strip() == "":
                    # LLM行表头为空，使用单元格中的行表头
                    row_header = str(row_header_cell).strip() if row_header_cell else ""
            else:
                # 没有LLM行表头，使用单元格中的行表头
                row_header = str(row_header_cell).strip() if row_header_cell else ""

            # 调试：打印当前行的表头
            if row_idx <= 5:  # 只显示前5行
                print(f"[DEBUG] 处理第{row_idx}行: 行表头='{row_header}'")

            # 如果行表头为空，跳过这一行
            if not row_header or row_header == "":
                if row_idx <= 5:
                    print(f"  [DEBUG] 跳过第{row_idx}行: 行表头为空")
                continue

            # 遍历每一列的数据（从第1列开始，跳过行表头列）
            for col_idx in range(1, len(row_data)):
                cell_value = row_data[col_idx]

                # 跳过空值
                if cell_value is None or cell_value == "":
                    continue

                # 获取列表头
                if col_idx < len(col_headers):
                    col_header = col_headers[col_idx]
                else:
                    col_header = ""

                # 调试：打印第一个数据单元格的详细信息
                if row_idx == 1 and col_idx == 1:
                    print(f"\n[DEBUG] 第一个数据单元格:")
                    print(f"  行索引: {row_idx}")
                    print(f"  列索引: {col_idx}")
                    print(f"  行表头: '{row_header}'")
                    print(f"  列表头: '{col_header}'")
                    print(f"  单元格值: '{cell_value}'")
                    print("-" * 50)

                # 判断报告期（优先使用列标题中的报告期）
                report_period = self._extract_report_period(col_header, table_metadata)

                # 判断数据类型
                data_type = self.data_type_detector.get_data_type(
                    row_header=row_header,
                    col_header=col_header,
                    cell_value=cell_value,
                    table_context=table_metadata.get('name', '')
                )

                # 构建长格式数据记录
                # 关键修改：直接使用原始的表头，不进行清理处理
                record = {
                    '银行名': bank_name,
                    '表名': table_metadata.get('name', ''),
                    '页号': page_num,
                    '主体': entity,
                    '纵向层级路径': row_header,  # 直接使用，不清理
                    '横向层级路径': col_header,  # 直接使用，不清理
                    '数据类型': data_type,
                    '币种': table_metadata.get('default_currency', ''),
                    '单位': table_metadata.get('default_unit', ''),
                    '报告期': report_period,
                    '数值': self._format_numeric_value(cell_value)
                }

                long_format_data.append(record)

        print(f"\n[DEBUG] 共转换 {len(long_format_data)} 条记录")
        return long_format_data

    def _determine_unit_by_headers(self, row_header: str, col_header: str,
                                   default_unit: str) -> str:
        """
        根据行表头和列表头确定单位

        优先级:
        1. 行表头或列表头包含 % -> "百分比"
        2. 行表头或列表头包含特定单位关键词
        3. LLM给出的默认单位
        """
        # 合并表头文本用于检查
        header_text = f"{row_header}{col_header}".lower()

        # 1. 检查是否包含百分比
        if ('%' in row_header or '%' in col_header or
                '百分比' in header_text or '比例' in header_text or
                '率' in header_text):
            return "%"

        # 2. 检查特定单位关键词
        unit_keywords = {
            '万元': ['万元', '万'],
            '亿元': ['亿元', '亿'],
            '元': ['元', '人民币', '￥', '¥'],
            '百万': ['百万', 'm', '百万美元'],
            '千元': ['千元', '千'],
            '百万元': ['百万元'],
            '亿元': ['亿元', '亿'],
            '美元': ['美元', '$', 'usd'],
            '欧元': ['欧元', '€', 'eur'],
            '港元': ['港元', '港币', 'hk$'],
            '日元': ['日元', '¥', 'jpy']
        }

        for unit, keywords in unit_keywords.items():
            for keyword in keywords:
                if keyword in header_text:
                    return unit

        # 3. 返回默认单位
        return default_unit

    def _format_numeric_value(self, value, row_header: str = "", col_header: str = "",
                              default_unit: str = "") -> str:
        """
        格式化数值并确定单位

        Args:
            value: 单元格值
            row_header: 行表头
            col_header: 列表头
            default_unit: LLM默认单位

        Returns:
            str: 格式化后的数值
        """
        if value is None:
            return ""

        value_str = str(value).strip()

        # 处理括号表示法（表示负数）
        if value_str.startswith('(') and value_str.endswith(')'):
            value_str = '-' + value_str[1:-1]

        # 去掉千分位逗号
        value_str = value_str.replace(',', '')

        # 去掉空格
        value_str = value_str.replace(' ', '')

        return value_str

    def convert_table_to_long_format(self, table_data: List[List],
                                     table_metadata: Dict[str, Any],
                                     bank_name: str = "中国建设银行",
                                     page_num: int = 1,
                                     entity: str = "本集团") -> List[Dict]:
        """
        将单个表格转换为长格式
        横向路径和纵向路径直接使用原始的表头，不进行处理
        """
        if not table_data or len(table_data) < 2:
            return []

        long_format_data = []

        # 获取表头信息
        col_headers = table_data[0]  # 第0行是列标题
        row_headers_original = table_metadata.get('headers', {}).get('rows', [])

        # 获取默认单位
        default_unit = table_metadata.get('default_unit', '')

        # 遍历数据区域（从第1行开始，跳过表头行）
        for row_idx in range(1, len(table_data)):
            row_data = table_data[row_idx]

            if not row_data:
                continue

            # 获取行表头（第一列）
            row_header_cell = row_data[0] if len(row_data) > 0 else ""

            # 优先使用LLM分析的行表头
            if row_idx - 1 < len(row_headers_original):
                row_header = row_headers_original[row_idx - 1]
                if not row_header or str(row_header).strip() == "":
                    # LLM行表头为空，使用单元格中的行表头
                    row_header = str(row_header_cell).strip() if row_header_cell else ""
            else:
                # 没有LLM行表头，使用单元格中的行表头
                row_header = str(row_header_cell).strip() if row_header_cell else ""

            # 如果行表头为空，跳过这一行
            if not row_header or row_header == "":
                continue

            # 遍历每一列的数据（从第1列开始，跳过行表头列）
            for col_idx in range(1, len(row_data)):
                cell_value = row_data[col_idx]

                # 跳过空值
                if cell_value is None or cell_value == "":
                    continue

                # 获取列表头
                if col_idx < len(col_headers):
                    col_header = col_headers[col_idx]
                else:
                    col_header = ""

                # 判断报告期（优先使用列标题中的报告期）
                report_period = self._extract_report_period(col_header, table_metadata)

                # 判断数据类型
                data_type = self.data_type_detector.get_data_type(
                    row_header=row_header,
                    col_header=col_header,
                    cell_value=cell_value,
                    table_context=table_metadata.get('name', '')
                )

                # 根据行表头和列表头确定单位（优先于LLM默认单位）
                unit = self._determine_unit_by_headers(row_header, col_header, default_unit)

                # 构建长格式数据记录
                record = {
                    '银行名': bank_name,
                    '表名': table_metadata.get('name', ''),
                    '页号': page_num,
                    '主体': entity,
                    '纵向层级路径': row_header,  # 直接使用，不清理
                    '横向层级路径': col_header,  # 直接使用，不清理
                    '数据类型': data_type,
                    '币种': table_metadata.get('default_currency', ''),
                    '单位': unit,  # 使用根据表头确定的单位
                    '报告期': report_period,
                    '数值': self._format_numeric_value(cell_value, row_header, col_header, default_unit)
                }

                long_format_data.append(record)

        return long_format_data





