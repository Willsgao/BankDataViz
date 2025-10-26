# backend/utils/data_processor.py
import pandas as pd
import traceback
from typing import Tuple, Optional
from io import StringIO
import re
import logging

logger = logging.getLogger(__name__)


class DataProcessor:
    def __init__(self):
        pass

    def safe_float(self, x) -> Optional[float]:
        """安全转换为浮点数"""
        try:
            x = str(x).replace(',', '').strip()
            if x.startswith('(') and x.endswith(')'):
                x = '-' + x[1:-1]
            if x.replace('.', '', 1).replace('-', '', 1).isdigit():
                return float(x) if x else 0.0
            else:
                return None
        except Exception:
            return None

    def count_decimal_places(self, x) -> int:
        """计算数值的有效小数点位数"""
        if x is None:
            return 0
        try:
            x_str = str(x).split('e')[0].split('E')[0]
            if '.' in x_str:
                decimal_part = x_str.split('.')[1].rstrip('0')
                return len(decimal_part) if decimal_part else 0
            else:
                return 0
        except Exception:
            return 0

    def is_numeric_type(self, x) -> int:
        """判断是否为有效数值类型"""
        return 1 if x is not None else 0

    def parse_llm_response(self, response_content: str, bank_name: str,
                           complexity_name: str) -> Tuple[pd.DataFrame, str]:
        """解析LLM响应内容"""
        cont_pat1 = r"<start4>[\s\S]*?(序号\|主体\|[\s\S]*?)```[\s\S]*?</start4>"
        cont_pat2 = r"<start3>[\s\S]*?(序号\|主体\|[\s\S]*?)```[\s\S]*?</start3>"
        table_pat = r"<start1>(.*?)</start1>"

        table_res = re.findall(table_pat, response_content)
        table_name = table_res[0] if table_res else ""

        cont_res = re.search(cont_pat1, response_content)
        if not cont_res:
            cont_res = re.search(cont_pat2, response_content)

        if not cont_res:
            logger.error("未找到表格数据内容")
            return pd.DataFrame(), table_name

        raw_txt = cont_res.group(1).strip()
        ct_res = raw_txt.split("\n")

        if len(ct_res) < 1:
            logger.error("表格数据格式错误")
            return pd.DataFrame(), table_name

        # 构建增强的CSV数据
        name_ct = "银行名|表名|" + ct_res[0] + "|表格复杂度|小数点位数|数值类型"
        val_res = ct_res[1:]

        # 根据数据量确定复杂度状态
        val_num = len(val_res)
        val_state = "少" if val_num <= 50 else "中" if val_num <= 100 else "多"
        complexity_state = f"{complexity_name}_{val_state}"

        val_cts = [f"{bank_name}|{table_name}|{val_ct}|{complexity_state}||" for val_ct in val_res]
        res_cts = [name_ct] + val_cts
        final_cont = '\n'.join(res_cts)

        # 读取CSV并处理数值列
        df = pd.read_csv(StringIO(final_cont), sep='|', dtype=str)
        df['数值'] = df['数值'].apply(self.safe_float)
        df['小数点位数'] = df['数值'].apply(self.count_decimal_places)
        df['数值类型'] = df['数值'].apply(self.is_numeric_type)

        return df, table_name

    def create_error_dataframe(self, exc: Exception) -> pd.DataFrame:
        """创建错误DataFrame"""
        tb_str = traceback.format_exception(type(exc), exc, exc.__traceback__)
        error_text = ''.join(tb_str)
        return pd.DataFrame({'error_msg': [error_text]})