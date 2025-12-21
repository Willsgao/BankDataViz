# backend/services/non_financial_table_service.py
import logging
from typing import Dict, Any, Tuple
import asyncio
import pandas as pd
from pathlib import Path
import re
import time
from openai import AsyncOpenAI

from backend.utils.llm_config import (
    ARK_API_KEY, ARK_BASE_URL, DEFAULT_MODEL_ID,
    MAX_TOKENS_CONFIG, IMAGE_SIZE_TOKEN_INCREMENT
)
from backend.utils.constants import EXCEL_OUTPUT_ROOT, NON_FINANCIAL_PROMPT
from backend.schemas.table_schemas import ProcessingResult, ExcelSaveConfig
from backend.service.excel_storage_service import ExcelStorageService
from backend.utils.data_processor import DataProcessor
from backend.utils.image_utils import ImageUtils
# from backend.models.database_manager import OldDatabaseManager
from backend.models.unified_db import DatabaseManager as OldDatabaseManager

logger = logging.getLogger(__name__)


class NonFinancialTableService:
    """普通表格识别服务"""

    def __init__(self, llm_client=None, model_id=DEFAULT_MODEL_ID, enable_db_logging: bool = True):
        self.llm_client = llm_client or AsyncOpenAI(
            base_url=ARK_BASE_URL,
            api_key=ARK_API_KEY
        )
        self.model_id = model_id
        self.prompt = NON_FINANCIAL_PROMPT

        self.excel_storage_base = Path(EXCEL_OUTPUT_ROOT)
        self.excel_storage_base.mkdir(parents=True, exist_ok=True)
        self.excel_storage = ExcelStorageService()
        self.data_processor = DataProcessor()
        self.image_utils = ImageUtils()

        # 数据库日志记录
        self.enable_db_logging = enable_db_logging
        if enable_db_logging:
            self.db_manager = OldDatabaseManager()

    def _calculate_max_tokens(self, img_size: int) -> int:
        """计算最大token数"""
        max_tokens = MAX_TOKENS_CONFIG["default"]

        # 根据图片大小增加token
        for size_threshold, increment in IMAGE_SIZE_TOKEN_INCREMENT.items():
            if img_size > size_threshold:
                max_tokens += increment
                break

        return min(max_tokens, MAX_TOKENS_CONFIG["max_limit"])

    async def extract_table_name_from_image(self, image_data: bytes) -> str:
        """直接从图片中提炼表格名"""
        try:
            table_name_prompt = """
请仔细分析这张图片中的表格，根据表格的标题、表头内容和数据特征，提炼一个准确描述表格主题的名称。

要求：
1. 名称要具体反映表格的核心业务内容（如：销售业绩报表、人员信息表、库存清单等）
2. 长度控制在5-12个汉字
3. 避免使用"表格"、"数据"、"信息"等泛泛词语
4. 要体现表格的实际用途和业务场景
5. 如果表格有明确标题，请基于标题优化

示例：
- 销售业绩报表 → "销售业绩统计"
- 员工基本信息 → "员工信息登记"
- 产品库存清单 → "产品库存明细"
- 月度费用支出 → "月度费用统计"

请直接返回表格名称，不要添加任何解释。
"""

            response = await self.llm_client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": table_name_prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_data}"}
                            }
                        ]
                    }
                ],
                max_tokens=50,
                temperature=0.1,
            )

            table_name = response.choices[0].message.content.strip()

            # 清理返回结果
            table_name = re.sub(r'[“”"\'《》]', '', table_name)  # 去除引号等符号
            table_name = re.sub(r'^(表格名称|名称|表名)[：:]?\s*', '', table_name)  # 去除前缀
            table_name = table_name.strip()

            # 验证表格名质量
            if len(table_name) < 2 or len(table_name) > 20:
                table_name = "业务数据表"

            logger.info(f"提炼的表格名: {table_name}")
            return table_name

        except Exception as e:
            logger.error(f"从图片提炼表格名失败: {e}")
            return "业务数据表"

    async def process_table(self, image_data: bytes, img_size: int,
                            bank_name: str, table_name: str) -> Tuple[pd.DataFrame, str]:
        """处理普通表格数据"""
        max_tokens = self._calculate_max_tokens(img_size)

        logger.info(f"处理普通表格 - max_tokens: {max_tokens}, 表格名: {table_name}")

        response = await self.llm_client.chat.completions.create(
            model=self.model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_data}"}
                        }
                    ]
                }
            ],
            max_tokens=max_tokens,
            temperature=0.01,
        )

        usage_msg = response.usage
        logger.info(f"普通表格处理使用情况 - prompt_tokens: {usage_msg.prompt_tokens}, "
                    f"completion_tokens: {usage_msg.completion_tokens}, "
                    f"total_tokens: {usage_msg.total_tokens}")

        return self._parse_non_financial_response(
            response.choices[0].message.content, bank_name, table_name
        )

    def _parse_non_financial_response(self, content: str, bank_name: str, table_name: str) -> Tuple[pd.DataFrame, str]:
        """解析普通表格响应"""
        try:
            # 提取CSV数据
            csv_match = re.search(r'```csv\s*(.*?)\s*```', content, re.DOTALL)
            if csv_match:
                csv_data = csv_match.group(1).strip()
                return self._convert_csv_to_dataframe(csv_data, table_name)
            else:
                # 如果没有找到CSV格式，尝试直接解析表格数据
                return self._parse_plain_table_data(content, table_name)

        except Exception as e:
            logger.error(f"解析普通表格响应失败: {e}")
            # 错误情况下也添加表格名列
            error_df = self.data_processor.create_error_dataframe(e)
            if not error_df.empty:
                error_df["表格名"] = table_name
            return error_df, table_name

    def _convert_csv_to_dataframe(self, csv_data: str, table_name: str) -> Tuple[pd.DataFrame, str]:
        """将CSV数据转换为DataFrame - 添加表格名列"""
        try:
            lines = csv_data.strip().split('\n')
            if len(lines) < 2:
                raise ValueError("CSV数据行数不足")

            # 解析表头
            headers = [h.strip() for h in lines[0].split('|')]

            # 添加"表格名"列到表头
            headers.append("表格名")

            # 解析数据行
            data = []
            for line in lines[1:]:
                if line.strip():
                    row_data = [cell.strip() for cell in line.split('|')]
                    if len(row_data) == len(headers) - 1:  # 减去新增的表格名列
                        # 为每一行添加表格名
                        row_data.append(table_name)
                        data.append(row_data)
                    elif len(row_data) == len(headers):
                        # 如果已经有表格名列，保持原样
                        data.append(row_data)
                    else:
                        # 列数不匹配，跳过该行或处理异常
                        print(f"⚠️ 数据行列数不匹配: 期望{len(headers)}列，实际{len(row_data)}列")
                        continue

            # 创建DataFrame
            df = pd.DataFrame(data, columns=headers)
            return df, table_name

        except Exception as e:
            logger.error(f"CSV转换失败: {e}")
            error_df = self.data_processor.create_error_dataframe(e)
            if not error_df.empty:
                error_df["表格名"] = table_name
            return error_df, table_name

    def _parse_plain_table_data(self, content: str, table_name: str) -> Tuple[pd.DataFrame, str]:
        """解析普通表格数据 - 添加表格名列"""
        try:
            # 简单的表格数据解析逻辑
            lines = content.strip().split('\n')
            data_lines = []

            for line in lines:
                line = line.strip()
                if line and not line.startswith('<') and '|' in line:
                    data_lines.append([cell.strip() for cell in line.split('|')])

            if len(data_lines) > 0:
                # 第一行作为表头
                headers = data_lines[0]
                # 添加"表格名"列到表头
                headers.append("表格名")

                data = []
                # 处理数据行
                for row_data in data_lines[1:] if len(data_lines) > 1 else []:
                    # 为每一行添加表格名
                    if len(row_data) == len(headers) - 1:  # 减去新增的表格名列
                        row_data.append(table_name)
                        data.append(row_data)
                    elif len(row_data) == len(headers):
                        # 如果已经有表格名列，保持原样
                        data.append(row_data)
                    else:
                        # 列数不匹配，跳过该行或处理异常
                        print(f"⚠️ 数据行列数不匹配: 期望{len(headers)}列，实际{len(row_data)}列")
                        continue

                df = pd.DataFrame(data, columns=headers)
                return df, table_name
            else:
                raise ValueError("未找到表格数据")

        except Exception as e:
            logger.error(f"解析普通表格数据失败: {e}")
            error_df = self.data_processor.create_error_dataframe(e)
            if not error_df.empty:
                error_df["表格名"] = table_name
            return error_df, table_name

    async def process_table_pipeline(self, image_path: str, out_file: str, sheet_name: str,
                                     bank_name: str, file_name: str,
                                     excel_config: ExcelSaveConfig = None) -> ProcessingResult:
        """完整的普通表格处理流程 - 修复Excel路径生成"""
        start_time = time.time()
        record_id = None

        if excel_config is None:
            excel_config = ExcelSaveConfig()

        try:
            # 使用已有的标识创建Excel存储文件夹
            folder_name = Path(image_path).stem.split('_')[0]

            # ⭐⭐⭐ 修复：使用常量导入的路径 ⭐⭐⭐
            from backend.utils.constants import MAIN_ROOT, EXCEL_OUTPUT_ROOT

            excel_base_dir = Path(MAIN_ROOT) / EXCEL_OUTPUT_ROOT
            excel_dir = excel_base_dir / folder_name
            excel_dir.mkdir(parents=True, exist_ok=True)

            # 重新构建输出路径
            excel_filename = Path(out_file).name
            new_out_file = excel_dir / excel_filename
            out_file = str(new_out_file)

            logger.info(f"普通表格Excel文件将保存到: {out_file}")

            # 编码图片
            image_data, img_size = self.image_utils.encode_image(image_path)
            logger.info(f"图片大小: {img_size} 像素")

            # 第一步：提炼表格名
            extracted_table_name = await self.extract_table_name_from_image(image_data)
            logger.info(f"提炼的表格名: {extracted_table_name}")

            # 第二步：处理表格数据
            res_df, final_table_name = await self.process_table(
                image_data, img_size, bank_name, extracted_table_name
            )

            # 检查 DataFrame 是否为空
            if res_df is None or res_df.empty:
                logger.warning(f"处理得到的 DataFrame 为空: {image_path}")
                res_df = self.data_processor.create_error_dataframe(Exception("表格识别结果为空"))
                if not res_df.empty:
                    res_df["表格名"] = extracted_table_name

            # 第三步：确保表格名列存在
            if not res_df.empty and "表格名" not in res_df.columns:
                res_df["表格名"] = extracted_table_name
                print(f"✅ 已添加表格名列: {extracted_table_name}")

            # 保存结果
            map_name = f"{extracted_table_name}_non_financial"
            success = self.excel_storage.save_dataframe(
                res_df, out_file, sheet_name, map_name,
                image_data=image_path, config=excel_config
            )

            processing_time = time.time() - start_time

            # ⭐⭐⭐ 关键修复：确保生成有效的 Excel URL ⭐⭐⭐
            excel_url = ""
            if success and Path(out_file).exists():
                # 生成前端可访问的URL
                from backend.llm_services.utils import convert_to_excel_url
                excel_url = convert_to_excel_url(out_file)
                print(f"✅ 生成的Excel URL: {excel_url}")

            # 记录到数据库
            if self.enable_db_logging:
                record_id = self._log_to_database(
                    image_path, bank_name, extracted_table_name,
                    "non_financial", "success" if success else "error",
                    out_file, sheet_name, processing_time
                )

            return ProcessingResult(
                status="success" if success else "error",
                complexity="普通表格",
                mode="non_financial",
                assessment_reason="普通表格模式",
                table_name=extracted_table_name,
                table_type="non_financial",
                df=res_df,
                error_message="" if success else "保存失败",
                # ⭐⭐⭐ 新增：返回Excel URL ⭐⭐⭐
                excel_url=excel_url if success else ""
            )

        except Exception as e:
            logger.error(f"处理普通表格失败: {e}")
            processing_time = time.time() - start_time

            # 记录错误到数据库
            if self.enable_db_logging:
                record_id = self._log_to_database(
                    image_path, bank_name, "处理失败", "error", "error",
                    out_file, sheet_name, processing_time
                )
                if record_id > 0:
                    self.db_manager.save_error_log(record_id, e)

            res_df = self.data_processor.create_error_dataframe(e)
            table_name = f"表格处理失败_{file_name}"

            if not res_df.empty:
                res_df["表格名"] = table_name

            # 保存错误结果
            map_name = f"{table_name}_error"
            self.excel_storage.save_dataframe(
                res_df, out_file, sheet_name, map_name,
                image_data=image_path, config=excel_config
            )

            return ProcessingResult(
                status="error",
                complexity="error",
                mode="error",
                assessment_reason=str(e),
                table_name=table_name,
                error_message=str(e),
                table_type="non_financial",
                df=res_df,
                excel_url=""
            )


    def _log_to_database(self, image_path: str, bank_name: str, table_name: str,
                         processing_mode: str, status: str,
                         output_file: str, sheet_name: str, processing_time: float) -> int:
        """记录处理信息到数据库"""
        if not self.enable_db_logging:
            return -1

        try:
            record_data = {
                'image_path': image_path,
                'bank_name': bank_name,
                'table_name': table_name,
                'complexity': "普通表格",
                'processing_mode': processing_mode,
                'status': status,
                'output_file': output_file,
                'sheet_name': sheet_name,
                'processing_time': processing_time,
                'table_type': "non_financial"
            }
            return self.db_manager.save_processing_record(record_data)
        except Exception as e:
            logger.error(f"数据库记录失败: {e}")
            return -1