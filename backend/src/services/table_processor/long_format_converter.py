# file: long_format_converter.py

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

    def _extract_marks_from_table(self, table_data: List[List]) -> Dict[str, Any]:
        """
        从表格数据中提取行标记和列标记

        Args:
            table_data: 原始表格数据

        Returns:
            Dict: 包含行标记和列标记的字典
        """
        if not table_data:
            return {"row_marks": [], "col_marks": []}

        # 初始化标记列表
        row_marks = []
        col_marks = []

        # 查找行标记列（最后一列的"行标记"）
        row_mark_col_index = -1
        if len(table_data[0]) > 0:
            for col_idx in range(len(table_data[0])):
                cell_value = table_data[0][col_idx]
                if cell_value and str(cell_value).strip() == "行标记":
                    row_mark_col_index = col_idx
                    break

        # 查找列标记行（最后一行的"列标记"）
        col_mark_row_index = -1
        for row_idx in range(len(table_data)):
            row = table_data[row_idx]
            if row and len(row) > 0:
                first_cell = row[0]
                if first_cell and str(first_cell).strip() == "列标记":
                    col_mark_row_index = row_idx
                    break

        # 提取行标记
        if row_mark_col_index >= 0:
            for row_idx in range(len(table_data)):
                if row_idx == 0:  # 表头行，跳过
                    row_marks.append(0)
                    continue
                if row_idx == col_mark_row_index:  # 列标记行，跳过
                    row_marks.append(0)
                    continue

                if len(table_data[row_idx]) > row_mark_col_index:
                    mark_value = table_data[row_idx][row_mark_col_index]
                    try:
                        row_mark = int(mark_value) if mark_value is not None else 0
                    except:
                        row_mark = 0
                else:
                    row_mark = 0
                row_marks.append(row_mark)
        else:
            # 没有行标记列，全部设为0
            row_marks = [0] * len(table_data)

        # 提取列标记
        if col_mark_row_index >= 0 and len(table_data) > col_mark_row_index:
            col_mark_row = table_data[col_mark_row_index]
            # 跳过第一列（"列标记"）和最后一列（"行标记"）
            for col_idx in range(1, len(col_mark_row)):
                if col_idx == row_mark_col_index:  # 跳过行标记列
                    col_marks.append(0)
                    continue
                mark_value = col_mark_row[col_idx]
                try:
                    col_mark = int(mark_value) if mark_value is not None else 0
                except:
                    col_mark = 0
                col_marks.append(col_mark)
        else:
            # 没有列标记行，全部设为0
            if len(table_data) > 0:
                col_count = len(table_data[0])
                if row_mark_col_index >= 0:
                    col_count -= 1  # 减去行标记列
                col_marks = [0] * col_count

        return {
            "row_marks": row_marks,
            "col_marks": col_marks,
            "row_mark_col_index": row_mark_col_index,
            "col_mark_row_index": col_mark_row_index
        }

    def _filter_and_clean_table_data(self, table_data: List[List], marks_info: Dict[str, Any]) -> List[List]:
        """
        过滤和清理表格数据，同时移除标记列和标记行

        Args:
            table_data: 原始表格数据
            marks_info: 标记信息

        Returns:
            List[List]: 清理后的表格数据
        """
        if not table_data or len(table_data) < 2:
            return []

        print(f"原始表格尺寸: {len(table_data)}行 × {len(table_data[0]) if table_data else 0}列")

        # 获取标记信息
        row_mark_col_index = marks_info["row_mark_col_index"]
        col_mark_row_index = marks_info["col_mark_row_index"]

        cleaned_data = []

        for row_idx, row in enumerate(table_data):
            # 跳过列标记行
            if row_idx == col_mark_row_index:
                continue

            # 处理每一行，排除行标记列
            cleaned_row = []
            for col_idx, cell in enumerate(row):
                # 跳过行标记列
                if col_idx == row_mark_col_index:
                    continue
                cleaned_row.append(cell)

            # 第一行总是保留（表头行）
            if row_idx == 0:
                cleaned_data.append(cleaned_row)
            else:
                # 检查第一列（行表头列）是否为空
                if cleaned_row and len(cleaned_row) > 0:
                    row_header = cleaned_row[0]
                    # 判断行表头是否有效
                    if (row_header is not None and
                            str(row_header).strip() != "" and
                            str(row_header).strip() not in ["0", "1", "2", "3", "4"]):  # 排除标记值
                        cleaned_data.append(cleaned_row)
                    else:
                        print(f"过滤第{row_idx}行：行表头缺失或无效 ('{row_header}')")
                else:
                    print(f"过滤第{row_idx}行：行数据为空")

        print(f"清理后表格尺寸: {len(cleaned_data)}行 × {len(cleaned_data[0]) if cleaned_data else 0}列")
        return cleaned_data



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
        row_header = str(row_header)
        col_header = str(col_header)
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

    def batch_convert_tables(self, all_tables_data: List[List[List]],
                             all_llm_tables: List[Dict[str, Any]],
                             output_excel_path: str = None,
                             bank_name: str = "中国建设银行") -> bool:
        """
        批量转换多个表格 - 增强版，包含数据过滤和标记处理

        Args:
            all_tables_data: 所有表格的原始数据
            all_llm_tables: 所有表格的LLM元数据
            output_excel_path: 输出Excel文件路径
            bank_name: 银行名称

        Returns:
            bool: 转换是否成功
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

                print(f"\n========== 转换表格 {table_idx + 1}/{len(all_tables_data)} ==========")
                print(f"表格名称: {llm_table.get('name', '')}")

                # 步骤1：从表格数据中提取标记信息
                marks_info = self._extract_marks_from_table(table_data)
                print(f"提取到行标记: {len(marks_info['row_marks'])}个, 列标记: {len(marks_info['col_marks'])}个")

                # 步骤2：转换为长格式（传入标记信息）
                long_data = self.convert_table_to_long_format(
                    table_data=table_data,
                    table_metadata=llm_table,
                    marks_info=marks_info,
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

                # 显示行标记统计
                print(f"\n行标记统计:")
                print(df['行标记'].value_counts().sort_index())

                # 显示有备注特征的数据
                has_remark = df[df['备注特征'] != '']
                if not has_remark.empty:
                    print(f"\n有备注特征的数据 ({len(has_remark)}条):")
                    print(has_remark[['纵向层级路径', '横向层级路径', '备注特征']].head().to_string(index=False))

            return True

        except Exception as e:
            print(f"❌ 最终数据转换失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    # ================ 新增：简化的行标记计算方法 ================
    def _calculate_simple_row_marker(self, formatted_value: str) -> int:
        """
        简化版行标记计算 - 修正版，正确区分0.x%和0xx%
        """
        if not formatted_value:
            return 4

        value_str = str(formatted_value).strip()

        if not value_str:
            return 4

        # 特殊错误值
        if value_str in ['-', '--', '—', '/', '\\', '*', 'N/A', 'NA', 'null', 'None', 'nan', 'NaN']:
            return 3

        # 预处理
        cleaned = value_str.replace(',', '').replace(' ', '')
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = '-' + cleaned[1:-1]

        # 检查百分比
        if '%' in cleaned:
            # 1. 检查是否有多个百分号
            if cleaned.count('%') > 1:
                return 2

            # 2. 去掉百分号
            without_percent = cleaned.replace('%', '')

            # 3. 关键修正：区分 0.xx 和 0xx
            #   0.22% -> without_percent = "0.22" (合法)
            #   018% -> without_percent = "018" (不合法，漏小数点)
            #   082% -> without_percent = "082" (不合法，漏小数点)

            if without_percent.startswith('0'):
                if len(without_percent) >= 3 and '.' not in without_percent:
                    # 以0开头，长度>=3，且没有小数点 -> 如018、082
                    return 2  # 漏小数点
                # 其他情况：0.22、0、0.1 等都是合法的

            # 4. 检查是否包含非法字符
            import re
            # 允许的字符：数字、小数点、负号
            if re.search(r'[^0-9.\-]', without_percent):
                return 2

            # 5. 检查是否有多个小数点
            if without_percent.count('.') > 1:
                return 2

            # 6. 尝试转换
            try:
                float_val = float(without_percent)

                # 7. 百分比合理性检查
                if float_val < -1000 or float_val > 10000:
                    return 2

                return 1  # 合法百分比
            except:
                return 2

        # 非百分比
        try:
            float_val = float(cleaned)
            return 1
        except:
            if any(c.isdigit() for c in cleaned):
                return 2
            return 4


    def convert_table_to_long_format(self, table_data: List[List],
                                     table_metadata: Dict[str, Any],
                                     marks_info: Dict[str, Any],
                                     bank_name: str = "中国建设银行",
                                     page_num: int = 1,
                                     entity: str = "本集团") -> List[Dict]:
        """
        将单个表格转换为长格式（优化版）

        Args:
            table_data: 原始表格数据
            table_metadata: 表格元数据
            marks_info: 标记信息，包含row_marks和col_marks
            bank_name: 银行名称
            page_num: 页号
            entity: 主体

        Returns:
            List[Dict]: 长格式数据列表
        """
        if not table_data or len(table_data) < 2:
            return []

        # 获取标记信息
        row_marks = marks_info.get("row_marks", [])
        col_marks = marks_info.get("col_marks", [])

        # 清理表格数据（移除标记列和标记行）
        cleaned_table_data = self._filter_and_clean_table_data(table_data, marks_info)

        if not cleaned_table_data or len(cleaned_table_data) < 2:
            return []

        long_format_data = []

        # 获取表头信息
        col_headers = cleaned_table_data[0]  # 第0行是列标题
        row_headers_original = table_metadata.get('headers', {}).get('rows', [])

        # 获取默认单位
        default_unit = table_metadata.get('default_unit', '')

        print(f"\n[DEBUG] 处理表格: {table_metadata.get('name', '')}")
        print(f"[DEBUG] 行标记数量: {len(row_marks)}, 列标记数量: {len(col_marks)}")
        print(f"[DEBUG] 清理后数据行数: {len(cleaned_table_data)}")
        print(f"[DEBUG] 列标记值: {col_marks}")

        # 遍历数据区域（从第1行开始，跳过表头行）
        for row_idx in range(1, len(cleaned_table_data)):
            row_data = cleaned_table_data[row_idx]

            if not row_data:
                continue

            # 获取对应的原始行标记
            if row_idx < len(row_marks):
                current_row_mark = row_marks[row_idx]
            else:
                current_row_mark = 0

            # 核心优化1：只处理行标记不为0的数据
            if current_row_mark == 0:
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

            # 核心修改：先收集当前行所有列标记为0的单元格值
            remark_features = []

            # 第一遍：遍历所有列，收集列标记为0的单元格值
            for col_idx in range(1, len(row_data)):
                cell_value = row_data[col_idx]

                # 跳过空值
                if cell_value is None or cell_value == "":
                    continue

                # 获取对应的列标记（注意索引映射）
                if col_idx - 1 < len(col_marks):
                    col_mark = col_marks[col_idx - 1]
                else:
                    col_mark = 0

                # 如果列标记为0，收集该单元格的值
                if col_mark == 0:
                    remark_features.append(str(cell_value).strip())

            # 核心修改：第二遍只处理列标记不为0的列
            for col_idx in range(1, len(row_data)):
                cell_value = row_data[col_idx]

                # 跳过空值
                if cell_value is None or cell_value == "":
                    continue

                # 获取对应的列标记（注意索引映射）
                if col_idx - 1 < len(col_marks):
                    current_col_mark = col_marks[col_idx - 1]
                else:
                    current_col_mark = 0

                # 核心优化2：只处理列标记不为0的列
                if current_col_mark == 0:
                    continue  # 跳过列标记为0的列，它们已在remark_features中

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

                # 格式化数值
                formatted_value = self._format_numeric_value(cell_value)

                # 构建长格式数据记录
                record = {
                    '银行名': bank_name,
                    '表名': table_metadata.get('name', ''),
                    '页号': page_num,
                    '主体': entity,
                    '纵向层级路径': row_header,
                    '横向层级路径': col_header,
                    '数据类型': data_type,
                    '币种': table_metadata.get('default_currency', ''),
                    '单位': unit,
                    '报告期': report_period,
                    '数值': formatted_value,
                    # 直接使用函数计算结果
                    '行标记': self._calculate_simple_row_marker(formatted_value),
                    '备注特征': "@@".join(remark_features) if remark_features else ""
                }

                long_format_data.append(record)

                # 调试输出
                if remark_features:
                    print(
                        f"[DEBUG] 行{row_idx} 列{col_idx}: 行标记={record['行标记']}, 列标记={current_col_mark}, 备注特征={record['备注特征']}")

        print(f"[DEBUG] 表格 {table_metadata.get('name', '')} 转换出 {len(long_format_data)} 条记录")
        return long_format_data

