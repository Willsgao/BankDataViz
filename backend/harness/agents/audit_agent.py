"""
会计勾稽审计 Agent

在 Orchestrator 调度下，作为 TableParsingAgent 的后置审计环节，
形成「解析 → 审计」多 Agent 协作流水线。

Usage:
    orchestrator = Orchestrator(
        agents=[TableParsingAgent(), AuditAgent()],
        verifier=RuleEngine(),
    )
    result = orchestrator.run(task="解析并审计建设银行2024年报")
"""

from typing import Any, Dict

from harness.agent import Agent, Action

from backend.harness.tools.audit_tool import AuditTool


class AuditAgent(Agent):
    """
    会计勾稽审计 Agent

    从上一个 Agent（TableParsingAgent）的输出中提取表格数据，
    调用 AuditTool 执行会计勾稽校验。

    固定 Pipeline: 单步 (audit)
    """

    SYSTEM_PROMPT = """
你是银行年报审计专家。你的任务是对已解析的财务报表执行会计勾稽校验：
1. 从前一个 Agent 的输出中提取表格数据
2. 按财务公式对指标进行勾稽计算
3. 输出校验结果（通过/不通过/差异值）
"""

    def __init__(self, name: str = "auditor"):
        tools = [AuditTool()]
        super().__init__(
            name=name,
            tools=tools,
            system_prompt=self.SYSTEM_PROMPT,
            max_retries=2,
        )

    def decide_next_action(self, task: str, context: Dict[str, Any] = None) -> Action:
        """
        接收上一个 Agent 的输出，注入到 AuditTool 参数中。
        """
        context = context or {}
        executed_tools = {obs.action.tool_name for obs in self.memory}

        if "audit" not in executed_tools:
            params = dict(context)
            # 尝试从上一个 Agent 的输出中提取表格数据
            prev_output = context.get("previous_agent_output") or context.get("last_result")
            if prev_output:
                params["table_data"] = prev_output
            if context.get("bank_name"):
                params["bank_name"] = context["bank_name"]
            return Action(
                tool_name="audit",
                params=params,
                reason="对解析结果执行会计勾稽校验",
            )

        return Action(tool_name="", reason="审计已完成")
