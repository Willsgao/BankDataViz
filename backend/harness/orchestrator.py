"""
多 Agent 编排器 (Orchestrator)

实现 Agent Loop: 约束 → 执行 → 验证 → 纠错 → 收敛

核心职责:
  1. 接收任务，分发给 Agent
  2. 管理 Agent 间的执行顺序和数据流转
  3. 在每步执行后调用验证引擎
  4. 验证失败时触发纠错（回退/降级/重试）
  5. 检测收敛条件，输出最终结果
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .agent import Agent, Action, Observation, ReActAgent
from .tool_registry import ToolResult
from .verification import RuleEngine, RuleResult


@dataclass
class OrchestrationResult:
    """编排执行结果"""
    success: bool
    task: str
    data: Any = None
    error: Optional[str] = None
    trace: List[Dict[str, Any]] = field(default_factory=list)
    verification_results: List[RuleResult] = field(default_factory=list)
    total_steps: int = 0
    elapsed_seconds: float = 0.0
    summary: str = ""
    hitl_triggered: bool = False
    hitl_decision: Optional[str] = None
    react_trace: List[Dict[str, Any]] = field(default_factory=list)  # ReAct 推理链

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "success": self.success,
            "task": self.task,
            "data": self.data,
            "error": self.error,
            "trace": self.trace,
            "verification": [r.to_dict() for r in self.verification_results],
            "total_steps": self.total_steps,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "summary": self.summary,
            "hitl_triggered": self.hitl_triggered,
            "hitl_decision": self.hitl_decision,
        }
        if self.react_trace:
            result["react_trace"] = self.react_trace
        return result


class Orchestrator:
    """
    多 Agent 编排器

    约束 → 执行 → 验证 → 纠错 → 收敛

    支持:
      - 多 Agent 串行协作（前一个 Agent 的 final_data 自动注入下一个）
      - ReActAgent 的 think→act→observe 循环
      - HITL (Human-in-the-Loop) 回调：Tool 全部失败时触发人工介入

    Usage:
        orchestrator = Orchestrator(
            agents=[parsing_agent, audit_agent],
            verifier=RuleEngine(),
            max_loops=20,
            on_need_human=my_human_callback,   # HITL 回调
        )
        result = orchestrator.run(
            task="解析建设银行2024年报第35页",
            context={"image_path": "/data/page_35.png"},
        )
    """

    def __init__(
        self,
        agents: List[Agent],
        verifier: Optional[RuleEngine] = None,
        max_loops: int = 20,
        verbose: bool = True,
        on_need_human: Optional[callable] = None,
    ):
        self.agents = agents
        self.verifier = verifier or RuleEngine()
        self.max_loops = max_loops
        self.verbose = verbose
        self.on_need_human = on_need_human  # Callable[[str, Dict], str] 返回 "retry"|"skip"|"abort"

    def run(
        self,
        task: str,
        context: Dict[str, Any] = None,
        verify_after_each_step: bool = True,
    ) -> OrchestrationResult:
        """
        执行完整的 Agent Loop。

        Args:
            task: 任务描述
            context: 初始上下文数据
            verify_after_each_step: 是否每步后执行验证

        Returns:
            OrchestrationResult 包含执行结果、轨迹、验证报告
        """
        start_time = time.time()
        trace: List[Dict[str, Any]] = []
        verifications: List[RuleResult] = []
        react_trace: List[Dict[str, Any]] = []

        context = context or {}
        self._log(f"\n{'='*60}")
        self._log(f"Orchestrator 启动")
        self._log(f"任务: {task}")
        self._log(f"Agent: {[a.name for a in self.agents]}")
        self._log(f"最大循环: {self.max_loops}")
        self._log(f"{'='*60}\n")

        step = 0
        final_data = None
        final_error = None
        hitl_triggered = False
        hitl_decision = None

        for agent in self.agents:
            self._log(f"--- 激活 Agent: {agent.name} ---")

            while step < self.max_loops:
                step += 1

                # 1. 决策: Agent 决定下一步
                action = agent.decide_next_action(task, context)

                if not action.tool_name:
                    self._log(f"  Agent '{agent.name}' 无更多动作，收敛")
                    break

                self._log(f"  Step {step}: [{agent.name}] → {action.tool_name} ({action.reason[:60]})")

                # 2. 执行
                observation = agent.execute(action)
                trace_entry = {
                    "step": step,
                    "agent": agent.name,
                    "action": action.tool_name,
                    "success": observation.result.success,
                    "error": observation.result.error,
                    "retries": observation.result.retry_count,
                    "fallback": observation.result.metadata.get("fallback_from"),
                }
                trace.append(trace_entry)

                if observation.result.success:
                    context.update({"last_result": observation.result.data})
                    final_data = observation.result.data
                else:
                    self._log(f"    ⚠ 失败: {observation.result.error}")

                # 3. 验证
                if verify_after_each_step and observation.result.success:
                    rule_results = self.verifier.check(
                        tool_name=action.tool_name,
                        data=observation.result.data,
                        context=context,
                    )
                    for r in rule_results:
                        verifications.append(r)
                        if not r.passed:
                            self._log(f"    ❌ 验证未通过: {r.rule_name} - {r.message}")

                # 4. HITL 触发：Tool 全部重试+降级后仍失败
                if not observation.result.success and self.on_need_human:
                    hitl_triggered = True
                    self._log(f"    🧑 触发 HITL: Tool '{action.tool_name}' 所有重试+降级均已失败")
                    try:
                        hitl_decision = self.on_need_human(
                            f"Tool '{action.tool_name}' 失败: {observation.result.error}",
                            {"action": action.tool_name, "attempts": observation.result.retry_count + 1},
                        )
                        self._log(f"    👤 人工决策: {hitl_decision}")
                    except Exception as e:
                        self._log(f"    ⚠ HITL 回调异常: {e}")
                        hitl_decision = "abort"

                    if hitl_decision == "retry":
                        continue  # 重新进入循环重试
                    elif hitl_decision == "skip":
                        continue  # 跳过当前步骤
                    else:  # abort
                        final_error = f"HITL 终止: {observation.result.error}"
                        break

                # 5. 收敛判断
                if agent.should_converge(task):
                    self._log(f"  Agent '{agent.name}' 收敛")
                    break

            # 收集 ReAct 推理链
            if isinstance(agent, ReActAgent) and agent.react_trace:
                react_trace = agent.get_trace()
                if agent.final_answer:
                    final_data = {"answer": agent.final_answer, "steps": react_trace}

            # Agent 执行完成，检查是否有失败
            if agent.memory:
                last_result = agent.memory[-1].result
                if not last_result.success:
                    final_error = last_result.error

            # 多 Agent 协作：前一个 Agent 的输出注入下一个 Agent 的上下文
            if final_data and len(self.agents) > 1:
                context["previous_agent_output"] = final_data
                self._log(f"  → 传递上下文到下一个 Agent")

        elapsed = time.time() - start_time
        success = final_error is None

        # 生成摘要
        successful_steps = sum(1 for t in trace if t["success"])
        failed_steps = sum(1 for t in trace if not t["success"])
        verification_failures = sum(1 for v in verifications if not v.passed)

        summary_parts = [
            f"任务{'成功' if success else '失败'}",
            f"共 {len(trace)} 步 ({successful_steps} 成功, {failed_steps} 失败)",
        ]
        if verifications:
            summary_parts.append(
                f"验证: {len(verifications)} 条规则 "
                f"({len(verifications) - verification_failures} 通过, {verification_failures} 未通过)"
            )
        if hitl_triggered:
            summary_parts.append(f"HITL: {hitl_decision}")
        if final_error:
            summary_parts.append(f"错误: {final_error}")

        result = OrchestrationResult(
            success=success,
            task=task,
            data=final_data,
            error=final_error,
            trace=trace,
            verification_results=verifications,
            total_steps=len(trace),
            elapsed_seconds=elapsed,
            summary=" | ".join(summary_parts),
            hitl_triggered=hitl_triggered,
            hitl_decision=hitl_decision,
            react_trace=react_trace,
        )

        self._log(f"\n{'='*60}")
        self._log(f"Orchestrator 完成: {result.summary}")
        self._log(f"耗时: {elapsed:.3f}s")
        self._log(f"{'='*60}\n")

        return result

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)
