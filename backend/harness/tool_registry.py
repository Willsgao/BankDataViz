"""
Tool 注册中心

提供统一的工具抽象和注册/发现机制。
每个 Tool 封装一个独立的能力单元（OCR、LLM分析、表格重建等），
通过标准化的 execute() 接口被 Agent 调用。
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class Tool:
    """
    工具基类

    所有能力单元的统一抽象。每个具体工具只需实现 execute() 方法。

    Usage:
        class OCRTool(Tool):
            name = "ocr"
            description = "对图片执行 OCR 识别，返回结构化文本"
            input_schema = {"image_path": "str"}

            def execute(self, image_path: str, **kwargs) -> ToolResult:
                ...
    """

    # --- 子类必须定义 ---
    name: str = ""
    description: str = ""
    input_schema: Dict[str, str] = {}
    timeout: float = 30.0  # 超时秒数，子类可按需覆盖（OCR 等慢服务可设更大值）

    def execute(self, **kwargs) -> ToolResult:
        """
        执行工具逻辑。

        子类必须实现此方法。返回 ToolResult 表示执行结果。
        若执行失败，应返回 ToolResult(success=False, error="...")。
        """
        raise NotImplementedError(f"Tool '{self.name}' must implement execute()")

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典，供 Agent 的 system prompt 使用"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "timeout": self.timeout,
        }


class ToolRegistry:
    """
    工具注册中心

    管理所有 Tool 的生命周期：注册、查找、列表。

    Usage:
        registry = ToolRegistry()
        registry.register(OCRTool())
        registry.register(LLMAnalysisTool())
        tool = registry.get("ocr")
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """注册一个工具"""
        if not tool.name:
            raise ValueError("Tool must have a non-empty name")
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """按名称获取工具"""
        return self._tools.get(name)

    def list_all(self) -> Dict[str, Dict[str, Any]]:
        """列出所有已注册的工具"""
        return {name: tool.to_dict() for name, tool in self._tools.items()}

    def count(self) -> int:
        """已注册工具数量"""
        return len(self._tools)
