# backend/services/table_llm_service.py
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
    MAX_TOKENS_CONFIG, IMAGE_SIZE_TOKEN_INCREMENT, COMPLEXITY_MODE_MAPPING
)
from backend.utils.constants import EXCEL_OUTPUT_ROOT
from backend.schemas.table_schemas import AssessmentResult, ProcessingResult, ExcelSaveConfig
from backend.service.excel_storage_service import ExcelStorageService
from backend.utils.data_processor import DataProcessor
from backend.utils.image_utils import ImageUtils
from backend.models.database_manager import DatabaseManager
from backend.utils.llm_config import ARK_API_KEY, ARK_BASE_URL, DEFAULT_MODEL_ID
from backend.utils.constants import ASSESSMENT_PROMPT, SIMPLE_PROMPT, STANDARD_PROMPT, COMPLEX_PROMPT

# 提示词定义（这里省略具体内容）


logger = logging.getLogger(__name__)

# 单例实例
_table_processor_instance = None


def get_table_processor():
    """获取表格处理器单例实例"""
    global _table_processor_instance

    if _table_processor_instance is None:
        _table_processor_instance = TableLLMService()

    return _table_processor_instance


class TableLLMService:
    def __init__(self, llm_client=None, model_id=DEFAULT_MODEL_ID, enable_db_logging: bool = True):
        self.llm_client = llm_client or AsyncOpenAI(
            base_url=ARK_BASE_URL,
            api_key=ARK_API_KEY
        )
        self.model_id = model_id
        self.prompt_registry = {
            "assessment": ASSESSMENT_PROMPT,
            "simple": STANDARD_PROMPT,
            "standard": STANDARD_PROMPT,
            "complex": COMPLEX_PROMPT
        }
        # self.excel_storage = ExcelStorageService()
        self.excel_storage_base = Path(EXCEL_OUTPUT_ROOT)
        self.excel_storage_base.mkdir(parents=True, exist_ok=True)
        self.excel_storage = ExcelStorageService()
        self.data_processor = DataProcessor()
        self.image_utils = ImageUtils()

        # 数据库日志记录
        self.enable_db_logging = enable_db_logging
        if enable_db_logging:
            self.db_manager = DatabaseManager()

    async def assess_complexity(self, image_data: bytes) -> AssessmentResult:  # 确保方法名正确
        """评估表格复杂度"""
        response = await self.llm_client.chat.completions.create(
            model=self.model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.prompt_registry["assessment"]},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_data}"}
                        }
                    ]
                }
            ],
            max_tokens=200
        )

        usage_msg = response.usage
        logger.info(f"Assessment usage - prompt_tokens: {usage_msg.prompt_tokens}, "
                    f"completion_tokens: {usage_msg.completion_tokens}, "
                    f"total_tokens: {usage_msg.total_tokens}")

        return self._parse_assessment_response(response)

    def _select_processing_mode(self, complexity: str) -> str:
        """选择处理模式"""
        return COMPLEXITY_MODE_MAPPING.get(complexity, "standard")

    def _calculate_max_tokens(self, mode: str, complexity: str, img_size: int) -> int:
        """计算最大token数"""
        max_tokens = MAX_TOKENS_CONFIG["default"]

        if mode in ["standard"]:
            max_tokens = MAX_TOKENS_CONFIG["standard"]
            if complexity in ["中等-扩展型"]:
                max_tokens = MAX_TOKENS_CONFIG["standard_extended"]
        elif mode in ["complex"]:
            max_tokens = MAX_TOKENS_CONFIG["complex"]

        # 根据图片大小增加token
        for size_threshold, increment in IMAGE_SIZE_TOKEN_INCREMENT.items():
            if img_size > size_threshold:
                max_tokens += increment
                break

        return min(max_tokens, MAX_TOKENS_CONFIG["max_limit"])

    async def process_table(self, image_data: bytes, img_size: int, mode: str,
                            complexity: str, bank_name: str) -> Tuple[pd.DataFrame, str]:
        """处理表格数据"""
        prompt = self.prompt_registry[mode]
        max_tokens = self._calculate_max_tokens(mode, complexity, img_size)

        logger.info(f"Processing with max_tokens: {max_tokens}")

        response = await self.llm_client.chat.completions.create(
            model=self.model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
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
        logger.info(f"Processing usage - prompt_tokens: {usage_msg.prompt_tokens}, "
                    f"completion_tokens: {usage_msg.completion_tokens}, "
                    f"total_tokens: {usage_msg.total_tokens}")

        return self.data_processor.parse_llm_response(
            response.choices[0].message.content, bank_name, complexity
        )

    def _parse_assessment_response(self, response) -> AssessmentResult:
        """解析评估响应"""
        all_content = response.choices[0].message.content
        is_res = re.findall(r"<财务表格>(.*?)</财务表格>", all_content)

        if not is_res:
            return AssessmentResult(complexity="否", reason="未找到财务表格标记", is_financial_table=False)

        is_cont = is_res[0]
        if "是" not in is_cont:
            return AssessmentResult(complexity="否", reason="非财务表格", is_financial_table=False)

        cont_res = re.findall("<complexity.*?</complexity>", all_content)
        if not cont_res:
            return AssessmentResult(complexity="否", reason="未找到复杂度标记", is_financial_table=False)

        content = cont_res[0]

        if "极简单" in content:
            return AssessmentResult(complexity="极简单", reason="表格结构简单")
        elif "简单" in content:
            return AssessmentResult(complexity="简单", reason="表格结构简单")
        elif "中等" in content:
            if '紧凑' in content:
                return AssessmentResult(complexity="中等-紧凑型", reason="中等复杂度表格")
            return AssessmentResult(complexity="中等-扩展型", reason="中等复杂度表格")
        elif "极复杂" in content:
            return AssessmentResult(complexity="极复杂", reason="复杂结构表格")
        elif "复杂" in content:
            return AssessmentResult(complexity="复杂", reason="复杂结构表格")
        else:
            return AssessmentResult(complexity="否", reason="无法识别复杂度", is_financial_table=False)

    async def process_table_pipeline(self, image_path: str, out_file: str, sheet_name: str,
                                     bank_name: str, file_name: str,
                                     excel_config: ExcelSaveConfig = None) -> ProcessingResult:
        """完整的表格处理流程"""
        start_time = time.time()
        record_id = None

        if excel_config is None:
            excel_config = ExcelSaveConfig()

        try:
            # 使用已有的标识创建Excel存储文件夹
            # 从 image_path 提取标识：类似 d0586abf1323dbfd80a926ce1e2d5676
            folder_name = Path(image_path).stem.split('_')[0]  # 取第一个下划线前的部分

            excel_base_dir = Path("static/excel_data")
            excel_dir = excel_base_dir / folder_name
            excel_dir.mkdir(parents=True, exist_ok=True)

            # 重新构建输出路径
            excel_filename = Path(out_file).name
            new_out_file = excel_dir / excel_filename
            out_file = str(new_out_file)

            logger.info(f"Excel文件将保存到: {out_file}")

            # 编码图片
            image_data, img_size = self.image_utils.encode_image(image_path)
            logger.info(f"图片大小: {img_size} 像素")

            # 第一步：复杂度评估
            complexity_result = await self.assess_complexity(image_data)
            complexity_level = complexity_result.complexity
            logger.info(f"复杂度评估结果: {complexity_level}")

            if not complexity_result.is_financial_table:
                result = ProcessingResult(
                    status="skip",
                    complexity=complexity_level,
                    mode="",
                    assessment_reason=complexity_result.reason
                )
                # 记录到数据库
                if self.enable_db_logging:
                    record_id = self._log_to_database(
                        image_path, bank_name, "", complexity_level, "", "skip",
                        out_file, sheet_name, time.time() - start_time
                    )
                return result

            # 第二步：选择处理模式
            processing_mode = self._select_processing_mode(complexity_level)
            logger.info(f"选择处理模式: {processing_mode}")

            # 第三步：执行具体处理
            res_df, table_name = await self.process_table(
                image_data, img_size, processing_mode, complexity_level, bank_name
            )

            # 保存结果
            map_name = f"{table_name}_{processing_mode}"
            success = self.excel_storage.save_dataframe(
                res_df, out_file, sheet_name, map_name,
                image_data=image_path, config=excel_config
            )

            processing_time = time.time() - start_time

            # 记录到数据库
            if self.enable_db_logging:
                record_id = self._log_to_database(
                    image_path, bank_name, table_name, complexity_level,
                    processing_mode, "success" if success else "error",
                    out_file, sheet_name, processing_time
                )

            return ProcessingResult(
                status="success" if success else "error",
                complexity=complexity_level,
                mode=processing_mode,
                assessment_reason=complexity_result.reason,
                table_name=table_name
            )

        except Exception as e:
            logger.error(f"处理表格失败: {e}")
            processing_time = time.time() - start_time

            # 记录错误到数据库
            if self.enable_db_logging:
                record_id = self._log_to_database(
                    image_path, bank_name, "", "error", "error", "error",
                    out_file, sheet_name, processing_time
                )
                if record_id > 0:
                    self.db_manager.save_error_log(record_id, e)

            res_df = self.data_processor.create_error_dataframe(e)
            table_name = f"此表报错_{file_name}"

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
                error_message=str(e)
            )

    def _log_to_database(self, image_path: str, bank_name: str, table_name: str,
                         complexity: str, processing_mode: str, status: str,
                         output_file: str, sheet_name: str, processing_time: float) -> int:
        """记录处理信息到数据库"""
        if not self.enable_db_logging:
            return -1

        try:
            record_data = {
                'image_path': image_path,
                'bank_name': bank_name,
                'table_name': table_name,
                'complexity': complexity,
                'processing_mode': processing_mode,
                'status': status,
                'output_file': output_file,
                'sheet_name': sheet_name,
                'processing_time': processing_time
            }
            return self.db_manager.save_processing_record(record_data)
        except Exception as e:
            logger.error(f"数据库记录失败: {e}")
            return -1