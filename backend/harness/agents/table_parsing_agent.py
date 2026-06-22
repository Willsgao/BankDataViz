"""
表格解析 Agent

组合 OCR → LLM分析 → 重建 三个 Tool，
在 Orchestrator 调度下完成端到端银行年报表格解析。

关键改进:
  - decide_next_action 覆盖基类，实现工具间的正确参数传递
  - OCR 结果自动注入到 LLM Tool，LLM 结果自动注入到 Rebuild Tool
"""

from typing import Any, Dict

from backend.harness import Agent, Action

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

    def decide_next_action(self, task: str, context: Dict[str, Any] = None) -> Action:
        """
        覆盖基类方法，实现 Pipeline 工具链的正确参数传递。

        参数传递链:
          1. OCR Tool ← params: {image_path, force_refresh}
          2. LLM Tool   ← params: {image_path, ocr_result}  (注入 OCR 输出)
          3. Rebuild Tool ← params: {ocr_result, llm_result, image_path, output_file, bank_name}
        """
        context = context or {}

        # 收集已完成步骤的输出
        step_outputs: Dict[str, Dict] = {}
        for obs in self.memory:
            if obs.result.success and obs.result.data:
                step_outputs[obs.action.tool_name] = obs.result.data

        executed_tools = set(step_outputs.keys())

        for tool_name in self.registry._tools:
            if tool_name not in executed_tools:
                tool = self.registry.get(tool_name)
                params = dict(context)  # 复制基础上下文

                if tool_name == "llm_analysis":
                    # 注入 OCR 结果
                    if "ocr" in step_outputs:
                        params["ocr_result"] = step_outputs["ocr"]
                        params["image_path"] = context.get("image_path", "")

                elif tool_name == "rebuild":
                    # 注入 OCR + LLM 结果
                    if "ocr" in step_outputs:
                        params["ocr_result"] = step_outputs["ocr"]
                    if "llm_analysis" in step_outputs:
                        params["llm_result"] = step_outputs["llm_analysis"]
                    params["image_path"] = context.get("image_path", "")
                    params["output_file"] = context.get("output_file")
                    params["bank_name"] = context.get("bank_name", "")

                return Action(
                    tool_name=tool_name,
                    params=params,
                    reason=f"执行 Pipeline 下一步: {tool.description}",
                )

        return Action(tool_name="", reason="所有工具已执行完毕")
