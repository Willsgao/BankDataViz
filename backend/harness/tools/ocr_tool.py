"""
OCR Tool: 表格 OCR 识别

包装 TableOCRService，提供标准化 Tool 接口。
"""

from typing import Any, Dict

from ..tool_registry import Tool, ToolResult


class OCRTool(Tool):
    """对 PDF 渲染图片执行 OCR，提取表格文本坐标"""

    name = "ocr"
    description = "对银行年报 PDF 页面图片执行 OCR 识别，返回结构化表格文本和坐标信息"
    input_schema = {
        "image_path": "图片文件路径 (str)",
        "force_refresh": "是否强制刷新缓存 (bool, 默认 False)",
    }

    def __init__(self, ocr_service: Any = None):
        """
        Args:
            ocr_service: TableOCRService 实例，为空时延迟导入
        """
        self._service = ocr_service

    def _get_service(self) -> Any:
        """延迟导入 OCR 服务"""
        if self._service is None:
            from backend.core.table_processor.ocr_gateway import TableOCRService
            self._service = TableOCRService()
        return self._service

    def execute(self, image_path: str, force_refresh: bool = False, **kwargs) -> ToolResult:
        try:
            service = self._get_service()
            result = service.recognize_table(image_path, force_refresh=force_refresh)

            table_count = len(result.get("tables_result", []))
            return ToolResult(
                success=True,
                data={
                    "ocr_result": result,
                    "table_count": table_count,
                    "image_path": image_path,
                },
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"OCR 识别失败: {str(e)}",
                metadata={"image_path": image_path},
            )
