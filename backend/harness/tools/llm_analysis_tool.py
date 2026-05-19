"""
LLM Analysis Tool: LLM 表格结构分析

包装 EnhancedFinancialTableAnalyzer，提供标准化 Tool 接口。
"""

from typing import Any, Dict

from harness.tool_registry import Tool, ToolResult


class LLMAnalysisTool(Tool):
    """使用 LLM (火山引擎 Doubao Vision) 分析表格表头结构"""

    name = "llm_analysis"
    description = "使用大模型分析银行年报表格的表头结构，识别列名、层级、合并单元格等"
    input_schema = {
        "image_path": "原始图片路径 (str)",
        "ocr_result": "OCR 识别结果 (dict)",
    }

    def __init__(self, analyzer: Any = None):
        self._analyzer = analyzer

    def _get_analyzer(self) -> Any:
        if self._analyzer is None:
            from backend.core.table_processor.llm_table_structure_parser import (
                EnhancedFinancialTableAnalyzer,
            )
            self._analyzer = EnhancedFinancialTableAnalyzer()
        return self._analyzer

    def execute(self, image_path: str, ocr_result: Dict[str, Any], **kwargs) -> ToolResult:
        try:
            analyzer = self._get_analyzer()
            result = analyzer.analyze_image(image_path, ocr_result)

            if not result.get("success"):
                return ToolResult(
                    success=False,
                    error=f"LLM 分析失败: {result.get('error', '未知错误')}",
                )

            table_count = result.get("processing_stats", {}).get("visual_tables_count", 0)
            return ToolResult(
                success=True,
                data={
                    "llm_result": result,
                    "table_count": table_count,
                    "image_path": image_path,
                },
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"LLM 分析异常: {str(e)}",
                metadata={"image_path": image_path},
            )
