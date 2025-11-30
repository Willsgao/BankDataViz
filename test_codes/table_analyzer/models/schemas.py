from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class TableField(BaseModel):
    """表格字段模型"""
    field_path: str
    is_statistical: bool = False

class TableData(BaseModel):
    """表格数据模型"""
    table_id: Optional[int] = None
    is_financial: bool = False
    table_title: str = ""
    currency: str = ""
    reporting_period: str = ""
    horizontal_hierarchy_fields: List[TableField] = []
    vertical_hierarchy_fields: List[TableField] = []
    location: Dict[str, Any] = {}
    confidence: float = 0.8

class ImageAnalysisResult(BaseModel):
    """图片分析结果模型"""
    image_path: str
    image_id: str
    page_number: int
    has_table: bool = False
    tables: List[TableData] = []
    analysis_time_sec: float = 0.0
    token_usage: Dict[str, int] = {}
    tables_count: int = 0
    financial_tables_count: int = 0

class AnalysisSummary(BaseModel):
    """分析汇总模型"""
    total_tables: int = 0
    total_financial_tables: int = 0
    total_analysis_time_sec: float = 0.0
    total_token_usage: Dict[str, int] = {}

class AlignmentResult(BaseModel):
    """对齐结果模型"""
    table_id: Optional[int] = None
    table_title: str = ""
    is_financial: bool = False
    currency: str = ""
    reporting_period: str = ""
    similarity_score: float = 0.0
    llm_hierarchy: Dict[str, List[TableField]] = {}
    ocr_data: Dict[str, Any] = {}
    location: Dict[str, Any] = {}