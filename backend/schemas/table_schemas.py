# backend/schemas/table_schemas.py
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class AssessmentResult(BaseModel):
    complexity: str
    reason: str
    is_financial_table: bool = True

class ProcessingResult(BaseModel):
    status: str
    complexity: str
    mode: str
    assessment_reason: str
    table_name: str = ""
    error_message: str = ""

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