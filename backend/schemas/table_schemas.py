# backend/schemas/table_schemas.py

import pandas as pd
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class AssessmentResult(BaseModel):
    complexity: str
    reason: str
    is_financial_table: bool = True


# 在 backend/schemas/table_schemas.py 中确保 ProcessingResult 有 df 字段
class ProcessingResult:
    def __init__(self, status: str, complexity: str, mode: str, assessment_reason: str,
                 table_name: str, table_type: str, df: pd.DataFrame = None, error_message: str = ""):
        self.status = status
        self.complexity = complexity
        self.mode = mode
        self.assessment_reason = assessment_reason
        self.table_name = table_name
        self.table_type = table_type
        self.df = df  # ⭐⭐⭐ 确保有这个字段 ⭐⭐⭐
        self.error_message = error_message

class TableData(BaseModel):
    bank_name: str
    table_name: str
    complexity: str
    data_rows: List[Dict[str, Any]]
    decimal_places: List[int]
    numeric_types: List[int]

class ExcelSaveConfig(BaseModel):
    anchor_cell: str = 'R2'
    width_px: int = 768
    mode: str = 'overwrite'

class TableProcessingRequest(BaseModel):
    image_path: str
    out_file: str
    sheet_name: str
    bank_name: str
    file_name: str
    excel_config: Optional[ExcelSaveConfig] = None