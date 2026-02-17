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

    def _filter_and_clean_table_data_old(self, table_data: List[List], marks_info: Dict[str, Any]) -> List[List]:
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


    def batch_convert_tables(self, all_tables_data: List[List[List]],
                             all_llm_tables: List[Dict[str, Any]],
                             output_excel_path: str = None,
                             bank_name: str = "") -> bool:
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



    def _extract_vertical_path(self, row_data: List, row_idx: int, header_row_index: int,
                               mark_column_index: int) -> str:
        """
        从行数据中提取纵向层级路径
        🔥 只检查前两列，如果前两列都没有内容，返回空字符串
        """
        if not row_data:
            return ""

        # 🔥 只检查前两列（索引0和1），不往后查找
        for i in range(min(2, len(row_data))):  # 只检查0和1列
            if i == mark_column_index:  # 跳过标记列
                continue

            cell = row_data[i]
            if cell and str(cell).strip():
                return str(cell).strip()

        # 前两列都没有内容，返回空字符串（这一行将被跳过）
        return ""

    def _convert_mixed_format_table000(self, table_data: List[List],
                                    table_metadata: Dict[str, Any],
                                    marks_info: Dict[str, Any],
                                    bank_name: str = "",
                                    entity: str = "") -> List[Dict]:
        """
        处理混合格式表格，包含标记行列过滤和单位/报告期提取
        """
        print("🔧 处理混合格式表格...")
        # 获取标记信息
        row_marks = marks_info.get("row_marks", [])
        col_marks = marks_info.get("col_marks", [])

        print(f"📊 行标记数: {len(row_marks)}, 列标记数: {len(col_marks)}")

        # 查找元数据行
        metadata_row_idx = -1
        metadata = None

        for i, row in enumerate(table_data):
            if row and row[0] and isinstance(row[0], dict):
                if 'has_dual_headers' in row[0] or 'horizontal_headers' in row[0]:
                    metadata_row_idx = i
                    metadata = row[0]
                    break

        if metadata_row_idx < 0 or not metadata:
            print("❌ 未找到元数据")
            return self._convert_regular_table(table_data, table_metadata, marks_info,
                                               bank_name, entity)

        print(f"✅ 找到元数据，在行{metadata_row_idx}")

        # 提取表头信息
        horizontal_headers = metadata.get('horizontal_headers', [])
        vertical_headers = metadata.get('vertical_headers', [])

        print(f"📊 横向表头: {horizontal_headers}")
        print(f"📊 纵向表头数: {len(vertical_headers)}")

        # 🔥 关键1：找到"行标记"列
        mark_column_index = -1
        for i, header in enumerate(horizontal_headers):
            if str(header).strip() == "行标记":
                mark_column_index = i + 1  # 因为数据列从1开始
                print(f"🔍 找到'行标记'列: 在horizontal_headers中索引{i}")
                break

        # 🔥 关键2：找到"列标记"行
        mark_row_index = -1
        for i, header in enumerate(vertical_headers):
            if str(header).strip() == "列标记":
                mark_row_index = i
                print(f"🔍 找到'列标记'行: 在vertical_headers中索引{i}")
                break

        # 数据起始行
        data_start_idx = metadata_row_idx + 2
        if data_start_idx >= len(table_data):
            data_start_idx = metadata_row_idx + 1

        print(f"📊 数据起始行: {data_start_idx}")

        # 🔥 关键3：获取默认值
        table_name = table_metadata.get('name', '')
        page_num = 0
        if table_name.startswith('P'):
            page_num = int(table_name.split('_')[0][1:].strip())
        default_unit = table_metadata.get('default_unit', '')
        default_currency = table_metadata.get('default_currency', '人民币')
        default_report_period = table_metadata.get('default_report_period', '')
        entity = table_metadata.get('entity', '')

        long_format_data = []

        # 处理数据行
        for row_idx in range(data_start_idx, len(table_data)):
            row_data = table_data[row_idx]

            if not row_data or len(row_data) < 2:
                continue

            # 🔥 关键4：获取当前行标记
            current_row_mark = 1
            if mark_column_index != -1 and mark_column_index < len(row_data):
                mark_value = row_data[mark_column_index]
                try:
                    current_row_mark = int(mark_value) if mark_value not in [None, ''] else 1
                except:
                    current_row_mark = 1
            elif row_idx - data_start_idx < len(row_marks):
                current_row_mark = row_marks[row_idx - data_start_idx]

            print(f"🔍 处理行{row_idx}: 行标记={current_row_mark}")

            # 🔥 关键5：过滤行标记为0的行
            if current_row_mark == 0:
                print(f"⏭️ 过滤行标记为0的行 {row_idx}")
                continue

            # 提取纵向路径
            vertical_path = ""
            if len(row_data) > 9 and row_data[9]:
                vertical_path = str(row_data[9]).strip()

            if not vertical_path:
                v_idx = row_idx - data_start_idx
                if 0 <= v_idx < len(vertical_headers):
                    vertical_path = vertical_headers[v_idx]

            if not vertical_path:
                print(f"⏭️ 跳过行{row_idx}: 纵向路径为空")
                continue

            # 🔥 关键6：如果是"列标记"行，跳过
            if vertical_path == "列标记":
                print(f"⏭️ 跳过'列标记'行: 行{row_idx}")
                continue

            print(f"✅ 处理有效行{row_idx}: 纵向路径='{vertical_path}'")

            # 🔥 关键7：第一遍遍历 - 收集列标记为0的备注
            remark_features = []

            for col_idx in range(1, min(len(row_data), len(horizontal_headers) + 1)):
                # 🔥 关键8：跳过"行标记"列
                if col_idx == mark_column_index:
                    continue

                cell_value = row_data[col_idx]
                if cell_value is None or cell_value == "":
                    continue

                # 获取列标记
                current_col_mark = 1
                if mark_row_index != -1 and col_idx - 1 < len(col_marks):
                    # 检查是否是列标记行
                    if vertical_headers[col_idx - 1] == "列标记":
                        current_col_mark = 1
                    else:
                        current_col_mark = col_marks[col_idx - 1] if col_marks[col_idx - 1] is not None else 1
                elif col_idx - 1 < len(col_marks):
                    current_col_mark = col_marks[col_idx - 1] if col_marks[col_idx - 1] is not None else 1

                # 🔥 关键9：收集列标记为0的单元格
                if current_col_mark == 0:
                    remark_text = str(cell_value).strip()
                    if remark_text:
                        remark_features.append(remark_text)
                        print(f"📝 收集行{row_idx}列{col_idx}的备注特征: {remark_text}")

            # 🔥 关键10：第二遍遍历 - 只处理列标记不为0的列
            for col_idx in range(1, min(len(row_data), len(horizontal_headers) + 1)):
                # 🔥 关键11：跳过"行标记"列
                if col_idx == mark_column_index:
                    continue

                cell_value = row_data[col_idx]
                if cell_value is None or cell_value == "":
                    continue

                # 获取列标记
                current_col_mark = 1
                if mark_row_index != -1 and col_idx - 1 < len(col_marks):
                    if vertical_headers[col_idx - 1] == "列标记":
                        current_col_mark = 1
                    else:
                        current_col_mark = col_marks[col_idx - 1] if col_marks[col_idx - 1] is not None else 1
                elif col_idx - 1 < len(col_marks):
                    current_col_mark = col_marks[col_idx - 1] if col_marks[col_idx - 1] is not None else 1

                print(f"🔍 处理行{row_idx}列{col_idx}: 列标记={current_col_mark}")

                # 🔥 关键12：过滤列标记为0的列
                if current_col_mark == 0:
                    print(f"⏭️ 过滤列标记为0的列 {col_idx}")
                    continue

                # 横向路径
                horizontal_path = ""
                if col_idx - 1 < len(horizontal_headers):
                    horizontal_path = horizontal_headers[col_idx - 1]

                # 🔥 关键13：如果是"行标记"标题，跳过
                if horizontal_path == "行标记":
                    print(f"⏭️ 跳过'行标记'列: 列{col_idx}")
                    continue

                # 🔥 关键14：提取报告期
                report_period = self._extract_report_period_from_paths(
                    horizontal_path,
                    vertical_path,
                    table_metadata
                )

                if not report_period and default_report_period:
                    report_period = default_report_period
                    print(f"📅 使用默认报告期: {report_period}")

                # 🔥 关键15：判断数据类型
                data_type = self.data_type_detector.get_data_type(
                    row_header=vertical_path,
                    col_header=horizontal_path,
                    cell_value=cell_value,
                    table_context=table_name
                )

                # 🔥 关键16：确定单位
                unit = self._determine_unit_by_paths(
                    vertical_path,
                    horizontal_path,
                    default_unit
                )

                if not unit and default_unit:
                    unit = default_unit
                    print(f"📏 使用默认单位: {unit}")

                # 格式化数值
                formatted_value = self._format_numeric_value(cell_value)

                # 获取行标记
                row_marker = self._calculate_row_marker(formatted_value, data_type)

                # 备注特征字符串
                remark_features_str = "@@".join(remark_features) if remark_features else ""

                # 创建记录
                record = {
                    '银行名': bank_name,
                    '表名': table_name,
                    '页号': page_num,
                    '主体': entity,
                    '纵向层级路径': vertical_path,
                    '横向层级路径': horizontal_path,
                    '数据类型': data_type,
                    '币种': default_currency,
                    '单位': unit,
                    '报告期': report_period,
                    '数值': formatted_value,
                    '行标记': row_marker,
                    '备注特征': remark_features_str
                }

                long_format_data.append(record)

                if len(long_format_data) <= 3:
                    print(f"  📝 添加记录{len(long_format_data)}:")
                    print(f"     纵向: {vertical_path}")
                    print(f"     横向: {horizontal_path}")
                    print(f"     数值: {cell_value}")
                    print(f"     报告期: {report_period}")
                    print(f"     单位: {unit}")
                    print(f"     币种: {default_currency}")
                    if remark_features_str:
                        print(f"     备注特征: {remark_features_str}")

        print(f"✅ 混合格式转换完成，生成 {len(long_format_data)} 条记录")
        return long_format_data

    def _convert_mixed_format_table(self, table_data: List[List],
                                    table_metadata: Dict[str, Any],
                                    marks_info: Dict[str, Any],
                                    bank_name: str = "",
                                    entity: str = "") -> List[Dict]:
        """
        处理混合格式表格，包含标记行列过滤和单位/报告期提取
        """
        print("🔧 处理混合格式表格...")
        print("MMMMMMMMMMMtable_metadataMMMMMMMMMMMMMMM")
        print(table_metadata)

        # 获取标记信息
        row_marks = marks_info.get("row_marks", [])
        col_marks = marks_info.get("col_marks", [])

        print(f"📊 行标记数: {len(row_marks)}, 列标记数: {len(col_marks)}")

        # 查找元数据行
        metadata_row_idx = -1
        metadata = None

        for i, row in enumerate(table_data):
            if row and row[0] and isinstance(row[0], dict):
                if 'has_dual_headers' in row[0] or 'horizontal_headers' in row[0]:
                    metadata_row_idx = i
                    metadata = row[0]
                    break

        if metadata_row_idx < 0 or not metadata:
            print("❌ 未找到元数据")
            return self._convert_regular_table(table_data, table_metadata, marks_info,
                                               bank_name, entity)

        print(f"✅ 找到元数据，在行{metadata_row_idx}")

        # 提取表头信息
        horizontal_headers = metadata.get('horizontal_headers', [])
        vertical_headers = metadata.get('vertical_headers', [])

        print(f"📊 横向表头: {horizontal_headers}")
        print(f"📊 纵向表头数: {len(vertical_headers)}")

        # 🔥 关键1：找到"行标记"列
        mark_column_index = -1
        for i, header in enumerate(horizontal_headers):
            if str(header).strip() == "行标记":
                mark_column_index = i + 1  # 因为数据列从1开始
                print(f"🔍 找到'行标记'列: 在horizontal_headers中索引{i}")
                break

        # 🔥 关键2：找到"列标记"行
        mark_row_index = -1
        for i, header in enumerate(vertical_headers):
            if str(header).strip() == "列标记":
                mark_row_index = i
                print(f"🔍 找到'列标记'行: 在vertical_headers中索引{i}")
                break

        # 数据起始行
        data_start_idx = metadata_row_idx + 2
        if data_start_idx >= len(table_data):
            data_start_idx = metadata_row_idx + 1

        print(f"📊 数据起始行: {data_start_idx}")

        # 🔥 关键3：获取默认值
        table_name = table_metadata.get('name', '')
        page_num = 0
        if table_name.startswith('P'):
            page_num = int(table_name.split('_')[0][1:].strip())
        default_unit = table_metadata.get('default_unit', '')
        default_currency = table_metadata.get('default_currency', '人民币')
        default_report_period = table_metadata.get('default_report_period', '')
        default_entity = table_metadata.get('entity', '')  # 新增：获取元数据中的实体字段

        # 🔥🔥🔥 关键修改1：确定最终的主体值
        # 逻辑：如果传入的entity参数有值（非空字符串），则强制使用这个值
        #       如果传入的entity参数为空，则使用元数据中的entity字段
        #       如果元数据中的entity字段也为空，则使用默认值"本集团"
        final_entity = "本集团"  # 默认值

        if entity and str(entity).strip():  # 如果传入的entity参数有值
            final_entity = str(entity).strip()
            print(f"🔥 使用传入的实体参数: '{final_entity}'，将覆盖所有记录的'主体'字段")
        elif default_entity and str(default_entity).strip():
            final_entity = str(default_entity).strip()
            print(f"📋 使用元数据中的实体字段: '{final_entity}'")
        else:
            print(f"⚠️  未指定实体，使用默认值: '{final_entity}'")

        long_format_data = []

        # 处理数据行
        for row_idx in range(data_start_idx, len(table_data)):
            row_data = table_data[row_idx]

            if not row_data or len(row_data) < 2:
                continue

            # 🔥 关键4：获取当前行标记
            current_row_mark = 1
            if mark_column_index != -1 and mark_column_index < len(row_data):
                mark_value = row_data[mark_column_index]
                try:
                    current_row_mark = int(mark_value) if mark_value not in [None, ''] else 1
                except:
                    current_row_mark = 1
            elif row_idx - data_start_idx < len(row_marks):
                current_row_mark = row_marks[row_idx - data_start_idx]

            print(f"🔍 处理行{row_idx}: 行标记={current_row_mark}")

            # 🔥 关键5：过滤行标记为0的行
            if current_row_mark == 0:
                print(f"⏭️ 过滤行标记为0的行 {row_idx}")
                continue

            # 提取纵向路径
            vertical_path = ""
            if len(row_data) > 9 and row_data[9]:
                vertical_path = str(row_data[9]).strip()

            if not vertical_path:
                v_idx = row_idx - data_start_idx
                if 0 <= v_idx < len(vertical_headers):
                    vertical_path = vertical_headers[v_idx]

            if not vertical_path:
                print(f"⏭️ 跳过行{row_idx}: 纵向路径为空")
                continue

            # 🔥 关键6：如果是"列标记"行，跳过
            if vertical_path == "列标记":
                print(f"⏭️ 跳过'列标记'行: 行{row_idx}")
                continue

            print(f"✅ 处理有效行{row_idx}: 纵向路径='{vertical_path}'")

            # 🔥 关键7：第一遍遍历 - 收集列标记为0的备注
            remark_features = []

            for col_idx in range(1, min(len(row_data), len(horizontal_headers) + 1)):
                # 🔥 关键8：跳过"行标记"列
                if col_idx == mark_column_index:
                    continue

                cell_value = row_data[col_idx]
                if cell_value is None or cell_value == "":
                    continue

                # 获取列标记
                current_col_mark = 1
                if mark_row_index != -1 and col_idx - 1 < len(col_marks):
                    # 检查是否是列标记行
                    if vertical_headers[col_idx - 1] == "列标记":
                        current_col_mark = 1
                    else:
                        current_col_mark = col_marks[col_idx - 1] if col_marks[col_idx - 1] is not None else 1
                elif col_idx - 1 < len(col_marks):
                    current_col_mark = col_marks[col_idx - 1] if col_marks[col_idx - 1] is not None else 1

                # 🔥 关键9：收集列标记为0的单元格
                if current_col_mark == 0:
                    remark_text = str(cell_value).strip()
                    if remark_text:
                        remark_features.append(remark_text)
                        print(f"📝 收集行{row_idx}列{col_idx}的备注特征: {remark_text}")

            # 🔥 关键10：第二遍遍历 - 只处理列标记不为0的列
            for col_idx in range(1, min(len(row_data), len(horizontal_headers) + 1)):
                # 🔥 关键11：跳过"行标记"列
                if col_idx == mark_column_index:
                    continue

                cell_value = row_data[col_idx]
                if cell_value is None or cell_value == "":
                    continue

                # 获取列标记
                current_col_mark = 1
                if mark_row_index != -1 and col_idx - 1 < len(col_marks):
                    if vertical_headers[col_idx - 1] == "列标记":
                        current_col_mark = 1
                    else:
                        current_col_mark = col_marks[col_idx - 1] if col_marks[col_idx - 1] is not None else 1
                elif col_idx - 1 < len(col_marks):
                    current_col_mark = col_marks[col_idx - 1] if col_marks[col_idx - 1] is not None else 1

                print(f"🔍 处理行{row_idx}列{col_idx}: 列标记={current_col_mark}")

                # 🔥 关键12：过滤列标记为0的列
                if current_col_mark == 0:
                    print(f"⏭️ 过滤列标记为0的列 {col_idx}")
                    continue

                # 横向路径
                horizontal_path = ""
                if col_idx - 1 < len(horizontal_headers):
                    horizontal_path = horizontal_headers[col_idx - 1]

                # 🔥 关键13：如果是"行标记"标题，跳过
                if horizontal_path == "行标记":
                    print(f"⏭️ 跳过'行标记'列: 列{col_idx}")
                    continue

                # 🔥 关键14：提取报告期
                report_period = self._extract_report_period_from_paths(
                    horizontal_path,
                    vertical_path,
                    table_metadata
                )

                if not report_period and default_report_period:
                    report_period = default_report_period
                    print(f"📅 使用默认报告期: {report_period}")

                # 🔥 关键15：判断数据类型
                data_type = self.data_type_detector.get_data_type(
                    row_header=vertical_path,
                    col_header=horizontal_path,
                    cell_value=cell_value,
                    table_context=table_name
                )

                # 🔥 关键16：确定单位
                unit = self._determine_unit_by_paths(
                    vertical_path,
                    horizontal_path,
                    default_unit
                )

                if not unit and default_unit:
                    unit = default_unit
                    print(f"📏 使用默认单位: {unit}")

                # 格式化数值
                formatted_value = self._format_numeric_value(cell_value)

                # 获取行标记
                row_marker = self._calculate_row_marker(formatted_value, data_type)

                # 备注特征字符串
                remark_features_str = "@@".join(remark_features) if remark_features else ""

                # 🔥 关键修改2：创建记录，使用确定后的final_entity
                record = {
                    '银行名': bank_name,
                    '表名': table_name,
                    '页号': page_num,
                    '主体': final_entity,  # 🔥 使用确定后的实体值
                    '纵向层级路径': vertical_path,
                    '横向层级路径': horizontal_path,
                    '数据类型': data_type,
                    '币种': default_currency,
                    '单位': unit,
                    '报告期': report_period,
                    '数值': formatted_value,
                    '行标记': row_marker,
                    '备注特征': remark_features_str
                }

                long_format_data.append(record)

                if len(long_format_data) <= 3:
                    print(f"  📝 添加记录{len(long_format_data)}:")
                    print(f"     纵向: {vertical_path}")
                    print(f"     横向: {horizontal_path}")
                    print(f"     数值: {cell_value}")
                    print(f"     报告期: {report_period}")
                    print(f"     单位: {unit}")
                    print(f"     币种: {default_currency}")
                    print(f"     主体: {final_entity}")  # 🔥 显示主体值
                    if remark_features_str:
                        print(f"     备注特征: {remark_features_str}")

        print(f"✅ 混合格式转换完成，生成 {len(long_format_data)} 条记录")
        return long_format_data


    def _convert_regular_table00000(self, table_data: List[List],
                               table_metadata: Dict[str, Any],
                               marks_info: Dict[str, Any],
                               bank_name: str = "",
                               entity: str = "") -> List[Dict]:
        """
        处理常规格式的表格数据转换为长格式 - 修复版
        注意：传入的 table_data 已经经过 _filter_and_clean_table_data 清理
        """
        print("🔧🔧 处理常规表格格式（修复版）...")

        if not table_data or len(table_data) < 2:
            print("❌❌ 表格数据为空或不足2行")
            return []

        print(f"📊📊 接收到的数据尺寸: {len(table_data)}行 × {len(table_data[0]) if table_data else 0}列")
        print(f"📊📊 第一行（表头）: {table_data[0] if table_data else '空'}")
        print(f"📊📊 第二行（数据）: {table_data[1] if len(table_data) > 1 else '空'}")

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
        final_entity = entity or table_metadata.get('entity', '本集团')
        final_currency = table_metadata.get('default_currency', '人民币')
        final_unit = table_metadata.get('default_unit', '')
        final_report_period = table_metadata.get('default_report_period', '')

        # 🔥🔥 关键：数据已清理，行标记列已被移除，不需要再检测
        # 但为了兼容，还是检测一下（理论上应该找不到）
        mark_column_index = -1
        for i, row in enumerate(table_data):
            for j, cell in enumerate(row):
                if str(cell).strip() == "行标记":
                    mark_column_index = j
                    print(f"⚠️⚠️ 警告：清理后的数据中仍有'行标记'列: 第{mark_column_index}列")
                    break
            if mark_column_index != -1:
                break

        # 🔥🔥 关键：找到"列标记"行（在清理后的数据中）
        mark_row_index = -1
        for i, row in enumerate(table_data):
            for j, cell in enumerate(row):
                if str(cell).strip() == "列标记":
                    mark_row_index = i
                    print(f"🔍🔍 找到'列标记'行: 第{mark_row_index}行")
                    break
            if mark_row_index != -1:
                break

        # 1. 智能识别表头行
        header_row_index = self._find_header_row_index(table_data, mark_row_index)
        print(f"🔍🔍 识别到的表头行索引: {header_row_index}")

        if header_row_index < 0 or header_row_index >= len(table_data):
            print("❌❌ 无法识别有效的表头行")
            return []

        # 2. 智能识别数据行
        data_start_index = header_row_index + 1

        # 3. 构建长格式数据
        long_format_data = []

        for row_idx in range(data_start_index, len(table_data)):
            # 🔥🔥 关键：跳过"列标记"行
            if row_idx == mark_row_index:
                print(f"⏭⏭⏭️ 跳过'列标记'行: 行{row_idx}")
                continue

            row_data = table_data[row_idx]

            if not row_data:
                continue

            # 🔥🔥 关键：提取纵向层级路径 - 只检查前两列
            vertical_path = ""

            # 🔥 硬编码检查第0列
            if len(row_data) > 0 and row_data[0] and str(row_data[0]).strip():
                vertical_path = str(row_data[0]).strip()
                print(f"🔍 第0列有值: '{vertical_path}'")
            # 🔥 硬编码检查第1列（如果第0列为空）
            elif len(row_data) > 1 and row_data[1] and str(row_data[1]).strip():
                vertical_path = str(row_data[1]).strip()
                print(f"🔍 第1列有值: '{vertical_path}'")
            else:
                print(f"🔍 前两列都为空，跳过行{row_idx}")
                continue  # 🔥 关键：前两列都为空，跳过整行

            print(f"✅ 处理有效行{row_idx}: 纵向路径='{vertical_path}'")

            # 🔥🔥 关键：第一遍遍历 - 收集当前行所有列标记为0的单元格值
            remark_features = []

            for col_idx in range(1, len(row_data)):
                # 🔥🔥 关键：跳过"行标记"列（如果存在）
                if col_idx == mark_column_index:
                    continue

                if col_idx >= len(table_data[header_row_index]):
                    break

                cell_value = row_data[col_idx]
                if cell_value is None or cell_value == "":
                    continue

                # 获取列标记
                current_col_mark = 1
                if mark_row_index != -1 and col_idx < len(table_data[mark_row_index]):
                    mark_value = table_data[mark_row_index][col_idx]
                    try:
                        current_col_mark = int(mark_value) if mark_value not in [None, ''] else 1
                    except:
                        current_col_mark = 1

                # 🔥🔥 关键：如果列标记为0，收集该单元格的值
                if current_col_mark == 0:
                    remark_text = str(cell_value).strip()
                    if remark_text:
                        remark_features.append(remark_text)
                        print(f"📝📝 收集行{row_idx}列{col_idx}的备注特征: {remark_text}")

            # 🔥🔥 关键：第二遍遍历 - 只处理列标记不为0的列
            for col_idx in range(1, len(row_data)):
                # 🔥🔥 关键：跳过"行标记"列（如果存在）
                if col_idx == mark_column_index:
                    continue

                if col_idx >= len(table_data[header_row_index]):
                    break

                cell_value = row_data[col_idx]
                if cell_value is None or cell_value == "":
                    continue

                # 获取列标记
                current_col_mark = 1
                if mark_row_index != -1 and col_idx < len(table_data[mark_row_index]):
                    mark_value = table_data[mark_row_index][col_idx]
                    try:
                        current_col_mark = int(mark_value) if mark_value not in [None, ''] else 1
                    except:
                        current_col_mark = 1

                # 🔥🔥 关键：过滤列标记为0的列
                if current_col_mark == 0:
                    continue

                # 获取横向层级路径
                header_row = table_data[header_row_index]
                horizontal_path = ""
                if col_idx < len(header_row):
                    header_cell = header_row[col_idx]
                    horizontal_path = str(header_cell).strip() if header_cell is not None else f"列{col_idx}"

                # 🔥🔥 关键：提取报告期
                report_period = self._extract_report_period_from_paths(horizontal_path, vertical_path, table_metadata)

                if not report_period and final_report_period:
                    report_period = final_report_period
                    print(f"📅📅 使用默认报告期: {report_period}")

                # 🔥🔥 关键：判断数据类型
                data_type = self.data_type_detector.get_data_type(
                    row_header=vertical_path,
                    col_header=horizontal_path,
                    cell_value=cell_value,
                    table_context=table_name
                )

                # 🔥🔥 关键：确定单位
                unit = self._determine_unit_by_paths(vertical_path, horizontal_path, final_unit)

                if not unit and final_unit:
                    unit = final_unit
                    print(f"📏📏 使用默认单位: {unit}")

                # 格式化数值
                formatted_value = self._format_numeric_value(cell_value)

                # 获取行标记
                row_marker = self._calculate_row_marker(formatted_value, data_type)

                # 🔥🔥 关键：将收集的备注特征组合成字符串
                remark_features_str = "@@".join(remark_features) if remark_features else ""

                # 🔥🔥🔥 关键修复：构建记录
                record = {
                    '银行名': final_bank_name,
                    '表名': table_name,
                    '页号': page_num,
                    '主体': final_entity,
                    '纵向层级路径': vertical_path,
                    '横向层级路径': horizontal_path,
                    '数据类型': data_type,
                    '币种': final_currency,
                    '单位': unit,
                    '报告期': report_period,
                    '数值': formatted_value,
                    '行标记': row_marker,
                    '备注特征': remark_features_str
                }

                long_format_data.append(record)

                if len(long_format_data) <= 3:  # 只打印前3条记录的详细日志
                    print(f"  📝📝 添加记录{len(long_format_data)}:")
                    print(f"     银行名: {final_bank_name}")
                    print(f"     主体: {final_entity}")
                    print(f"     币种: {final_currency}")
                    print(f"     纵向: {vertical_path}")
                    print(f"     横向: {horizontal_path}")
                    print(f"     数值: {formatted_value}")
                    print(f"     报告期: {report_period}")
                    print(f"     单位: {unit}")
                    if remark_features_str:
                        print(f"     备注特征: {remark_features_str}")

        print(f"✅ 表格转换完成，共生成 {len(long_format_data)} 条记录")
        return long_format_data

    def _convert_regular_table(self, table_data: List[List],
                               table_metadata: Dict[str, Any],
                               marks_info: Dict[str, Any],
                               bank_name: str = "",
                               entity: str = "") -> List[Dict]:
        """
        处理常规格式的表格数据转换为长格式 - 修复版
        注意：传入的 table_data 已经经过 _filter_and_clean_table_data 清理
        """
        print("🔧🔧 处理常规表格格式（修复版）...")

        if not table_data or len(table_data) < 2:
            print("❌❌ 表格数据为空或不足2行")
            return []

        print(f"📊📊 接收到的数据尺寸: {len(table_data)}行 × {len(table_data[0]) if table_data else 0}列")
        print(f"📊📊 第一行（表头）: {table_data[0] if table_data else '空'}")
        print(f"📊📊 第二行（数据）: {table_data[1] if len(table_data) > 1 else '空'}")

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
        # 逻辑：如果传入的entity参数有值（非空字符串），则强制使用这个值
        #       如果传入的entity参数为空，则使用元数据中的entity字段
        #       如果元数据中的entity字段也为空，则使用默认值"本集团"
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

        # 🔥🔥 关键：数据已清理，行标记列已被移除，不需要再检测
        # 但为了兼容，还是检测一下（理论上应该找不到）
        mark_column_index = -1
        for i, row in enumerate(table_data):
            for j, cell in enumerate(row):
                if str(cell).strip() == "行标记":
                    mark_column_index = j
                    print(f"⚠️⚠️ 警告：清理后的数据中仍有'行标记'列: 第{mark_column_index}列")
                    break
            if mark_column_index != -1:
                break

        # 🔥🔥 关键：找到"列标记"行（在清理后的数据中）
        mark_row_index = -1
        for i, row in enumerate(table_data):
            for j, cell in enumerate(row):
                if str(cell).strip() == "列标记":
                    mark_row_index = i
                    print(f"🔍🔍 找到'列标记'行: 第{mark_row_index}行")
                    break
            if mark_row_index != -1:
                break

        # 1. 智能识别表头行
        header_row_index = self._find_header_row_index(table_data, mark_row_index)
        print(f"🔍🔍 识别到的表头行索引: {header_row_index}")

        if header_row_index < 0 or header_row_index >= len(table_data):
            print("❌❌ 无法识别有效的表头行")
            return []

        # 2. 智能识别数据行
        data_start_index = header_row_index + 1

        # 3. 构建长格式数据
        long_format_data = []

        for row_idx in range(data_start_index, len(table_data)):
            # 🔥🔥 关键：跳过"列标记"行
            if row_idx == mark_row_index:
                print(f"⏭⏭⏭️ 跳过'列标记'行: 行{row_idx}")
                continue

            row_data = table_data[row_idx]

            if not row_data:
                continue

            # 🔥🔥 关键：提取纵向层级路径 - 只检查前两列
            vertical_path = ""

            # 🔥 硬编码检查第0列
            if len(row_data) > 0 and row_data[0] and str(row_data[0]).strip():
                vertical_path = str(row_data[0]).strip()
                print(f"🔍 第0列有值: '{vertical_path}'")
            # 🔥 硬编码检查第1列（如果第0列为空）
            elif len(row_data) > 1 and row_data[1] and str(row_data[1]).strip():
                vertical_path = str(row_data[1]).strip()
                print(f"🔍 第1列有值: '{vertical_path}'")
            else:
                print(f"🔍 前两列都为空，跳过行{row_idx}")
                continue  # 🔥 关键：前两列都为空，跳过整行

            print(f"✅ 处理有效行{row_idx}: 纵向路径='{vertical_path}'")

            # 🔥🔥 关键：第一遍遍历 - 收集当前行所有列标记为0的单元格值
            remark_features = []

            for col_idx in range(1, len(row_data)):
                # 🔥🔥 关键：跳过"行标记"列（如果存在）
                if col_idx == mark_column_index:
                    continue

                if col_idx >= len(table_data[header_row_index]):
                    break

                cell_value = row_data[col_idx]
                if cell_value is None or cell_value == "":
                    continue

                # 获取列标记
                current_col_mark = 1
                if mark_row_index != -1 and col_idx < len(table_data[mark_row_index]):
                    mark_value = table_data[mark_row_index][col_idx]
                    try:
                        current_col_mark = int(mark_value) if mark_value not in [None, ''] else 1
                    except:
                        current_col_mark = 1

                # 🔥🔥 关键：如果列标记为0，收集该单元格的值
                if current_col_mark == 0:
                    remark_text = str(cell_value).strip()
                    if remark_text:
                        remark_features.append(remark_text)
                        print(f"📝📝 收集行{row_idx}列{col_idx}的备注特征: {remark_text}")

            # 🔥🔥 关键：第二遍遍历 - 只处理列标记不为0的列
            for col_idx in range(1, len(row_data)):
                # 🔥🔥 关键：跳过"行标记"列（如果存在）
                if col_idx == mark_column_index:
                    continue

                if col_idx >= len(table_data[header_row_index]):
                    break

                cell_value = row_data[col_idx]
                if cell_value is None or cell_value == "":
                    continue

                # 获取列标记
                current_col_mark = 1
                if mark_row_index != -1 and col_idx < len(table_data[mark_row_index]):
                    mark_value = table_data[mark_row_index][col_idx]
                    try:
                        current_col_mark = int(mark_value) if mark_value not in [None, ''] else 1
                    except:
                        current_col_mark = 1

                # 🔥🔥 关键：过滤列标记为0的列
                if current_col_mark == 0:
                    continue

                # 获取横向层级路径
                header_row = table_data[header_row_index]
                horizontal_path = ""
                if col_idx < len(header_row):
                    header_cell = header_row[col_idx]
                    horizontal_path = str(header_cell).strip() if header_cell is not None else f"列{col_idx}"

                # 🔥🔥 关键：提取报告期
                report_period = self._extract_report_period_from_paths(horizontal_path, vertical_path, table_metadata)

                if not report_period and final_report_period:
                    report_period = final_report_period
                    print(f"📅📅 使用默认报告期: {report_period}")

                # 🔥🔥 关键：判断数据类型
                data_type = self.data_type_detector.get_data_type(
                    row_header=vertical_path,
                    col_header=horizontal_path,
                    cell_value=cell_value,
                    table_context=table_name
                )

                # 🔥🔥 关键：确定单位
                unit = self._determine_unit_by_paths(vertical_path, horizontal_path, final_unit)

                if not unit and final_unit:
                    unit = final_unit
                    print(f"📏📏 使用默认单位: {unit}")

                # 格式化数值
                formatted_value = self._format_numeric_value(cell_value)

                # 获取行标记
                row_marker = self._calculate_row_marker(formatted_value, data_type)

                # 🔥🔥 关键：将收集的备注特征组合成字符串
                remark_features_str = "@@".join(remark_features) if remark_features else ""

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
                    '备注特征': remark_features_str
                }

                long_format_data.append(record)

                if len(long_format_data) <= 3:  # 只打印前3条记录的详细日志
                    print(f"  📝📝 添加记录{len(long_format_data)}:")
                    print(f"     银行名: {final_bank_name}")
                    print(f"     主体: {final_entity}")  # 🔥 显示主体值
                    print(f"     币种: {final_currency}")
                    print(f"     纵向: {vertical_path}")
                    print(f"     横向: {horizontal_path}")
                    print(f"     数值: {formatted_value}")
                    print(f"     报告期: {report_period}")
                    print(f"     单位: {unit}")
                    if remark_features_str:
                        print(f"     备注特征: {remark_features_str}")

        print(f"✅ 表格转换完成，共生成 {len(long_format_data)} 条记录")
        return long_format_data

    def _filter_and_clean_table_data00000(self, table_data: List[List], marks_info: Dict[str, Any]) -> List[List]:
        """
        过滤和清理表格数据，同时移除标记列和标记行
        保持旧版返回格式：纯二维数组，第一行是表头，后面是数据行
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
                            str(row_header).strip() not in ["0", "1", "2", "3", "4"]):
                        cleaned_data.append(cleaned_row)
                    else:
                        print(f"过滤第{row_idx}行：行表头缺失或无效 ('{row_header}')")
                else:
                    print(f"过滤第{row_idx}行：行数据为空")

        print(f"清理后表格尺寸: {len(cleaned_data)}行 × {len(cleaned_data[0]) if cleaned_data else 0}列")

        return cleaned_data

    def _filter_and_clean_table_data00(self, table_data: List[List], marks_info: Dict[str, Any]) -> tuple[
        List[List[Any]], Dict[str, Any]]:
        """
        过滤和清理表格数据，同时移除标记列和标记行
        保持旧版返回格式：纯二维数组，第一行是表头，后面是数据行
        """
        if not table_data or len(table_data) < 2:
            return [], marks_info

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
                # 🔥 关键修改：检查前两列是否都为空
                if cleaned_row and len(cleaned_row) >= 2:
                    col_0 = cleaned_row[0] if cleaned_row[0] is not None else ""
                    col_1 = cleaned_row[1] if len(cleaned_row) > 1 and cleaned_row[1] is not None else ""

                    # 前两列都为空才过滤
                    if not str(col_0).strip() and not str(col_1).strip():
                        print(f"过滤第{row_idx}行：前两列为空")
                    else:
                        cleaned_data.append(cleaned_row)
                else:
                    cleaned_data.append(cleaned_row)

        print(f"清理后表格尺寸: {len(cleaned_data)}行 × {len(cleaned_data[0]) if cleaned_data else 0}列")

        return cleaned_data, marks_info

    def _is_cell_empty(self, cell_value) -> bool:
        """
        检查单元格是否为空
        处理各种空值情况：None, '', 'nan', 'NaN', 'null', 空字符串等
        """
        if cell_value is None:
            return True

        # 转换为字符串
        cell_str = str(cell_value)

        # 去除首尾空白
        cell_str = cell_str.strip()

        # 检查各种空值表示
        empty_values = ['', 'nan', 'NaN', 'null', 'None', 'none', 'NULL', 'NAN']

        if cell_str in empty_values:
            return True

        # 检查是否全部是空白字符
        if not cell_str:
            return True

        return False

    def _filter_and_clean_table_data(self, table_data: List[List], marks_info: Dict[str, Any]) -> tuple[
        List[List[Any]], Dict[str, Any]]:
        """
        过滤和清理表格数据，同时移除标记列和标记行
        保持旧版返回格式：纯二维数组，第一行是表头，后面是数据行

        参数:
            table_data: 原始表格数据，二维数组格式
            marks_info: 标记信息字典，包含行标记列索引和列标记行索引

        返回:
            tuple[List[List[Any]], Dict[str, Any]]: 清理后的表格数据和更新后的标记信息
        """
        if not table_data or len(table_data) < 2:
            print("❌ 表格数据为空或不足2行")
            return [], marks_info

        original_rows = len(table_data)
        original_cols = len(table_data[0]) if table_data else 0
        print(f"原始表格尺寸: {original_rows}行 × {original_cols}列")

        # 🔥 调试：打印原始数据结构的前3行
        print(f"🔍 原始表格数据结构（前3行）:")
        for i in range(min(3, len(table_data))):
            print(f"  行{i}: {table_data[i]}")

        # 获取标记信息
        row_mark_col_index = marks_info.get("row_mark_col_index", -1)
        col_mark_row_index = marks_info.get("col_mark_row_index", -1)

        print(f"🔍 标记信息: 行标记列索引={row_mark_col_index}, 列标记行索引={col_mark_row_index}")

        cleaned_data = []
        filtered_count = 0
        kept_count = 0

        for row_idx, row in enumerate(table_data):
            # 1. 跳过列标记行
            if row_idx == col_mark_row_index:
                print(f"⏭️ 跳过列标记行: 行{row_idx}")
                filtered_count += 1
                continue

            # 2. 处理每一行，排除行标记列
            cleaned_row = []
            for col_idx, cell in enumerate(row):
                # 跳过行标记列
                if col_idx == row_mark_col_index:
                    if row_idx < 3:  # 只打印前3行的调试信息
                        print(f"⏭️ 行{row_idx}列{col_idx}: 跳过行标记列")
                    continue
                cleaned_row.append(cell)

            # 调试：显示清理前后的列数（前3行）
            if row_idx < 3:
                print(f"🔍 行{row_idx}清理结果: 原始{len(row)}列 → 清理后{len(cleaned_row)}列")
                print(f"  清理后: {cleaned_row}")

            # 3. 第一行总是保留（表头行）
            if row_idx == 0:
                cleaned_data.append(cleaned_row)
                kept_count += 1
                if kept_count <= 3:
                    print(f"✅ 保留表头行{row_idx}")
                continue

            # 4. 检查前两列是否都为空
            if cleaned_row and len(cleaned_row) >= 2:
                # 使用智能空值检查
                col_0_empty = self._is_cell_empty(cleaned_row[0])
                col_1_empty = self._is_cell_empty(cleaned_row[1])

                # 获取原始值用于调试
                col_0_raw = cleaned_row[0]
                col_1_raw = cleaned_row[1] if len(cleaned_row) > 1 else None

                # 调试信息
                if kept_count <= 5:  # 只打印前5行过滤原因的详细信息
                    print(
                        f"🔍 检查行{row_idx}: 列0='{col_0_raw}' (为空: {col_0_empty}), 列1='{col_1_raw}' (为空: {col_1_empty})")

                # 前两列都为空才过滤
                if col_0_empty and col_1_empty:
                    print(f"⏭️ 过滤行{row_idx}：前两列为空 (列0='{col_0_raw}', 列1='{col_1_raw}')")
                    filtered_count += 1
                    continue
                else:
                    cleaned_data.append(cleaned_row)
                    kept_count += 1
                    if kept_count <= 5:
                        print(f"✅ 保留行{row_idx}: 前两列至少有一列不为空")
            else:
                # 如果行长度小于2，也保留
                cleaned_data.append(cleaned_row)
                kept_count += 1
                if kept_count <= 5:
                    print(f"✅ 保留行{row_idx}: 行长度小于2")

        print(f"清理后表格尺寸: {len(cleaned_data)}行 × {len(cleaned_data[0]) if cleaned_data else 0}列")
        print(f"📊 过滤统计: 总共{original_rows}行, 保留{kept_count}行, 过滤{filtered_count}行")

        # 打印清理后数据样本
        if cleaned_data and len(cleaned_data) > 0:
            print(f"🔍 清理后数据样本（前10行）:")
            for i in range(min(10, len(cleaned_data))):
                print(f"  行{i}: {cleaned_data[i]}")

        # 更新标记信息（移除标记列后，行标记列索引可能需要调整）
        # 注意：由于移除了行标记列，相关的索引信息可能需要更新
        updated_marks_info = marks_info.copy()
        # 这里可以添加逻辑来更新标记索引

        return cleaned_data, updated_marks_info


    def convert_table_to_long_format(self, table_data: List[List],
                                     table_metadata: Dict[str, Any],
                                     marks_info: Dict[str, Any],
                                     bank_name: str = "",
                                     entity: str = "") -> List[Dict]:
        """
        将表格数据转换为长格式
        """
        print("原始表格尺寸: {}行 × {}列".format(
            len(table_data), len(table_data[0]) if table_data else 0))

        # 🔥 添加输入数据验证
        if not table_data or not isinstance(table_data, list):
            print("❌ 无效的表格数据: {}".format(type(table_data)))
            return []

        print("🔍 开始处理表格数据，总共 {} 行".format(len(table_data)))

        # 过滤和清理数据
        clean_table_data, updated_marks_info = self._filter_and_clean_table_data(
            table_data, marks_info
        )

        print("🧹🧹 清理后数据: {}行 × {}列".format(
            len(clean_table_data),
            len(clean_table_data[0]) if clean_table_data else 0
        ))

        if not clean_table_data or len(clean_table_data) < 2:
            print("❌ 清理后数据不足2行")
            return []

        # 检查是否是混合格式（包含特殊元数据行）
        is_mixed_format = False

        # 🔥 关键修复：安全遍历和类型检查
        for i, row in enumerate(clean_table_data):
            # 1. 检查行是否为字典类型
            if isinstance(row, dict):
                print("⚠️ 行{}是字典类型: {}".format(i, type(row)))
                # 如果有任何行是字典，可能是混合格式
                is_mixed_format = True
                break

            # 2. 检查行是否为列表
            if not isinstance(row, list):
                print("❌ 行{}不是列表类型: {}".format(i, type(row)))
                continue

            # 3. 检查行是否为空
            if not row or len(row) == 0:
                continue

            # 4. 安全检查 row[0] 是否存在
            try:
                first_cell = row[0]
                # 5. 检查第一个单元格是否为字典
                if isinstance(first_cell, dict):
                    print("✅ 行{}的第一个单元格是字典，检测到混合格式".format(i))
                    is_mixed_format = True
                    break
            except (IndexError, KeyError, TypeError) as e:
                print("⚠️ 无法访问行{}的第一个单元格: {}".format(i, e))
                continue

        print("🔍 表格格式检测: {}".format("混合格式" if is_mixed_format else "常规格式"))

        # 根据格式类型调用不同的处理方法
        if is_mixed_format:
            print("🔧 处理混合格式表格...")
            return self._convert_mixed_format_table(
                clean_table_data, table_metadata, updated_marks_info, bank_name, entity
            )
        else:
            print("🔧 处理常规格式表格...")
            return self._convert_regular_table(
                clean_table_data, table_metadata, updated_marks_info, bank_name, entity
            )


    def _extract_report_period_from_paths(self, horizontal_path: str, vertical_path: str, table_metadata: Dict) -> str:
        """
        从路径中提取报告期
        """
        import re

        # 优先从横向路径提取
        if horizontal_path:
            # 混合格式中通常是 a>>2024年12月31日 的格式
            if '>>' in horizontal_path:
                # 尝试提取日期部分
                parts = horizontal_path.split('>>')
                for part in parts:
                    report_period = self._extract_date_from_text(part)
                    if report_period:
                        return report_period
            else:
                report_period = self._extract_date_from_text(horizontal_path)
                if report_period:
                    return report_period

        # 然后从纵向路径提取
        if vertical_path:
            if '>>' in vertical_path:
                parts = vertical_path.split('>>')
                for part in parts:
                    report_period = self._extract_date_from_text(part)
                    if report_period:
                        return report_period
            else:
                report_period = self._extract_date_from_text(vertical_path)
                if report_period:
                    return report_period

        # 从表格名称中尝试提取
        table_name = table_metadata.get('name', '')
        if table_name:
            report_period = self._extract_date_from_text(table_name)
            if report_period:
                return report_period

        # 最后从表格元数据中获取
        return table_metadata.get('default_report_period', '')

    def _determine_unit_by_paths(self, vertical_path: str, horizontal_path: str, default_unit: str) -> str:
        """
        根据路径信息确定单位 - 强制使用默认单位
        """
        # 🔥🔥🔥 紧急修复：直接使用默认单位
        combined_text = f"{vertical_path} {horizontal_path}".lower()

        # 只有明确是百分比数据才用%，其他都用默认单位
        if any(keyword in combined_text for keyword in ['%', '率', '比例', '百分比']):
            return '%'
        else:
            return default_unit

    def _format_numeric_value(self, value) -> str:
        """
        格式化数值
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

    def _calculate_row_marker(self, formatted_value: str, data_type: str) -> int:
        """
        计算行标记
        """
        state = 0
        if formatted_value:
            # 如果是数值类型
            try:
                float(formatted_value)
                state = 1
            except:
                state = 2

        return state

    def _find_header_row_index(self, table_data: List[List], mark_row_index: int = -1) -> int:
        """
        智能识别表头行索引，跳过标记行
        """
        # if not table_data or len(table_data) < 2:
        #     return 0
        #
        # # 策略1：查找包含>>的行
        # for i, row in enumerate(table_data):
        #     # 跳过标记行
        #     if i == mark_row_index:
        #         continue
        #
        #     if not row:
        #         continue
        #
        #     for cell in row:
        #         if cell and '>>' in str(cell):
        #             return i
        #
        # # 策略2：使用第一行非标记行
        # for i, row in enumerate(table_data):
        #     if i == mark_row_index:
        #         continue
        #
        #     if row and any(cell for cell in row if cell):
        #         return i

        return 0

    def _extract_date_from_text(self, text: str) -> str:
        """
        从文本中提取日期
        """
        if not text:
            return ""

        import re

        patterns = [
            r'(\d{4}年\d{1,2}月\d{1,2}日)',
            r'(\d{4}年\d{1,2}月)',
            r'(\d{4}年)',
            r'(\d{4}-\d{1,2}-\d{1,2})',
            r'(\d{4}/\d{1,2}/\d{1,2})',
            r'(\d{8})'  # 20241231格式
        ]

        for pattern in patterns:
            match = re.search(pattern, str(text))
            if match:
                return match.group(1)

        return ""


    def convert_table_to_long_format00000(self, table_data: List[List],
                                     table_metadata: Dict[str, Any],
                                     marks_info: Dict[str, Any],
                                     bank_name: str = "",
                                     entity: str = "") -> List[Dict]:
        """
        主函数：智能选择处理方式
        """

        if not table_data or len(table_data) < 2:
            print("❌ 表格数据为空或不足2行")
            return []

        # 🔥🔥 关键修复：先清理数据（移除标记行列）
        cleaned_data = self._filter_and_clean_table_data(table_data, marks_info)
        print(f"🧹🧹 清理后数据: {len(cleaned_data)}行 × {len(cleaned_data[0]) if cleaned_data else 0}列")

        # 检查是否是混合格式（使用清理后的数据）
        is_mixed_format = False
        for i, row in enumerate(cleaned_data[:2]):
            if row and len(row) > 0 and row[0] and isinstance(row[0], dict):
                if 'has_dual_headers' in row[0] or 'horizontal_headers' in row[0]:
                    is_mixed_format = True
                    print(f"🔍 检测到混合格式，元数据在行{i}")
                    break

        if is_mixed_format:
            return self._convert_mixed_format_table(cleaned_data, table_metadata, marks_info,
                                                    bank_name, entity)
        else:
            return self._convert_regular_table(cleaned_data, table_metadata, marks_info,
                                               bank_name, entity)


