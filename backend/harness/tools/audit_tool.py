"""
Audit Tool: 会计勾稽验证

包装 audit_engine 的 run_audit() 函数。
"""

from typing import Any, Dict

from backend.harness import Tool, ToolResult


class AuditTool(Tool):
    """会计勾稽规则引擎，验证财务数据的勾稽关系"""

    name = "audit"
    description = "对导出的 Excel 数据执行会计勾稽校验，检查公式、合计、期间一致性"
    input_schema = {
        "file_id": "文件 ID (str)",
        "file_name": "文件名称 (str)",
        "excel_path": "Excel 文件路径 (str, 可选)",
    }

    def execute(
        self,
        file_id: str = "",
        file_name: str = "",
        excel_path: str = None,
        **kwargs,
    ) -> ToolResult:
        try:
            from backend.services.audit_engine import run_audit

            result = run_audit(
                file_id=file_id,
                file_name=file_name,
                excel_path=excel_path,
            )

            return ToolResult(
                success=result.get("success", False),
                data=result,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"审计验证失败: {str(e)}",
                metadata={"file_id": file_id},
            )
