"""
Rebuild Tool: 表格结构重建

包装 TableReconstructor 的 process_all_tables() 方法。
"""

from typing import Any, Dict

from backend.harness import Tool, ToolResult


class RebuildTool(Tool):
    """8步表格重建引擎，将 OCR+LLM 结果转为结构化 Excel"""

    name = "rebuild"
    description = "将 OCR 和 LLM 分析结果重构为结构化表格数据，支持列匹配、行合并、跨页合并"
    input_schema = {
        "ocr_result": "OCR 识别结果 (dict)",
        "llm_result": "LLM 表头分析结果 (dict)",
        "output_file": "输出 Excel 文件路径 (str)",
        "image_path": "原始图片路径 (str, 可选)",
        "bank_name": "银行名称 (str, 可选)",
    }

    def __init__(self, reconstructor: Any = None):
        self._reconstructor = reconstructor

    def _get_reconstructor(self) -> Any:
        if self._reconstructor is None:
            from backend.core.table_processor.table_rebuilder import TableReconstructor
            self._reconstructor = TableReconstructor()
        return self._reconstructor

    def execute(
        self,
        ocr_result: Dict[str, Any],
        llm_result: Dict[str, Any],
        output_file: str = None,
        image_path: str = "",
        bank_name: str = "",
        **kwargs,
    ) -> ToolResult:
        try:
            reconstructor = self._get_reconstructor()

            # 如果没给 output_file，使用默认路径
            if output_file is None:
                from pathlib import Path
                from backend.configs.config import tableconfig
                output_dir = Path(tableconfig.output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                output_file = str(output_dir / "reconstructed_output.xlsx")

            result = reconstructor.process_all_tables(
                ocr_result=ocr_result,
                llm_result=llm_result,
                output_file=output_file,
                image_path=image_path,
                bank_name=bank_name,
            )

            return ToolResult(
                success=True,
                data={
                    "output_file": output_file,
                    "reconstruction_result": result,
                    "bank_name": bank_name,
                },
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"表格重建失败: {str(e)}",
                metadata={"output_file": output_file, "image_path": image_path},
            )
