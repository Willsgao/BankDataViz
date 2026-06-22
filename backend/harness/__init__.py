"""
BankDataViz Harness 层

从 harnessloop (pip 包) 导入所有核心框架类，
同时注册 BankDataViz 专属的 Tool 和 Agent 实现。

核心框架由 harnessloop v0.2.0 提供:
  - Tool / ToolRegistry / Agent / ReActAgent / Orchestrator / RuleEngine
  - Loop Engineering: Terminator / SmartRetry / LoopState / HITLManager / PlanAgent

业务实现由本目录提供:
  - Tools: OCRTool / LLMAnalysisTool / RebuildTool / AuditTool / RAGTool / DataQueryTool / ChartTool
  - Agents: TableParsingAgent / AuditAgent / DataAnalysisAgent
"""

# ---- 核心框架（由 harnessloop pip 包提供） ----
from harnessloop import (
    Tool, ToolResult, ToolRegistry,
    Agent, Action, Observation,
    ReActAgent, ReActStep,
    Orchestrator, OrchestrationResult,
    Rule, RuleEngine, RuleResult,
    # Loop Engineering
    LoopConfig,
    Terminator, TermReason, TermDecision,
    SmartRetry, ErrorCategory, DeadLetter, RetryResult,
    LoopState, AttemptRecord, Strategy, AttemptOutcome,
    HITLManager, HITLRequest, HITLDecision, HITLStatus,
    PlanAgent, PlanStep,
)

# ---- 银行专属业务 ----
from backend.harness.tools import OCRTool, LLMAnalysisTool, RebuildTool, AuditTool, RAGTool
from backend.harness.tools.data_query_tool import DataQueryTool
from backend.harness.tools.chart_tool import ChartTool
from backend.harness.agents import TableParsingAgent
from backend.harness.agents.audit_agent import AuditAgent
from backend.harness.agents.data_analysis_agent import DataAnalysisAgent

__all__ = [
    # 核心框架
    "Tool", "ToolResult", "ToolRegistry",
    "Agent", "Action", "Observation",
    "ReActAgent", "ReActStep",
    "Orchestrator", "OrchestrationResult",
    "Rule", "RuleEngine", "RuleResult",
    # Loop Engineering
    "LoopConfig",
    "Terminator", "TermReason", "TermDecision",
    "SmartRetry", "ErrorCategory", "DeadLetter", "RetryResult",
    "LoopState", "AttemptRecord", "Strategy", "AttemptOutcome",
    "HITLManager", "HITLRequest", "HITLDecision", "HITLStatus",
    "PlanAgent", "PlanStep",
    # 银行专属
    "OCRTool", "LLMAnalysisTool", "RebuildTool", "AuditTool", "RAGTool",
    "DataQueryTool", "ChartTool",
    "TableParsingAgent", "AuditAgent", "DataAnalysisAgent",
]
