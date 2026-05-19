"""
表格解析 Agent

组合 OCR → LLM分析 → 重建 三个 Tool，
在 Orchestrator 调度下完成端到端银行年报表格解析。
"""

from harness.agent import Agent

from backend.harness.tools.ocr_tool import OCRTool
from backend.harness.tools.llm_analysis_tool import LLMAnalysisTool
from backend.harness.tools.rebuild_tool import RebuildTool


class TableParsingAgent(Agent):
    """
    银行年报表格解析 Agent

    持有 OCR、LLM 分析、表格重建三个 Tool，
    由 Orchestrator 调度执行完整 Pipeline。

    Usage:
        agent = TableParsingAgent()
        agent.execute(Action(tool_name="ocr", params={"image_path": "..."}))
    """

    SYSTEM_PROMPT = """
你是银行年报表格解析专家。你的任务是:
1. 对 PDF 页面执行 OCR 识别，提取表格文本
2. 使用 LLM 分析表格表头结构，识别列名、层级
3. 将 OCR 和 LLM 结果重构为结构化表格

执行顺序固定: OCR → LLM分析 → 重建。
如果某步失败，记录错误并尝试继续下一步。
"""

    def __init__(self, name: str = "table_parser"):
        tools = [
            OCRTool(),
            LLMAnalysisTool(),
            RebuildTool(),
        ]
        super().__init__(
            name=name,
            tools=tools,
            system_prompt=self.SYSTEM_PROMPT,
            max_retries=3,
        )
