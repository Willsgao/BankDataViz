"""
Agent 基类

定义 Agent 的核心循环: think → act → observe
Agent 持有 Tool 集合，通过思维链决定下一步行动，并执行对应工具。

设计原则:
  - Agent 本身不调用 LLM —— 由 Orchestrator 注入 reasoning 能力
  - Agent 只负责: 决定动作 → 执行 Tool → 记录观察 → 判断收敛
"""

import concurrent.futures
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .tool_registry import Tool, ToolResult, ToolRegistry


@dataclass
class Action:
    """Agent 决定执行的行动"""
    tool_name: str
    params: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass
class Observation:
    """执行后的观察结果"""
    action: Action
    result: ToolResult
    timestamp: float = 0.0


class Agent:
    """
    Agent 基类

    Usage:
        agent = Agent(
            name="table_parser",
            tools=[ocr_tool, llm_analysis_tool, rebuild_tool],
            system_prompt="你是银行年报表格解析专家..."
        )
        action = agent.decide_next_action(task, memory)
        observation = agent.execute(action)
        done = agent.should_converge(task, memory)
    """

    def __init__(
        self,
        name: str,
        tools: List[Tool],
        system_prompt: str = "",
        max_retries: int = 3,
        tool_fallbacks: Dict[str, str] = None,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.max_retries = max_retries

        # 工具降级映射: { 主 Tool 名: 备用 Tool 名 }
        # 当主 Tool 重试耗尽仍失败时，自动切换到备用 Tool
        self.tool_fallbacks: Dict[str, str] = tool_fallbacks or {}

        # 初始化工具注册中心
        self.registry = ToolRegistry()
        for tool in tools:
            self.registry.register(tool)

        # 操作记忆（observation 历史）
        self.memory: List[Observation] = []

    def decide_next_action(self, task: str, context: Dict[str, Any] = None) -> Action:
        """
        决定下一步行动。

        子类可覆盖此方法接入 LLM reasoning。
        默认返回: 按工具注册顺序逐个执行（适用于固定 Pipeline）。

        Args:
            task: 当前任务描述
            context: 额外上下文（如已有的 OCR 结果）

        Returns:
            下一个要执行的 Action
        """
        # 默认策略：找出尚未执行过的第一个工具
        executed_tools = {obs.action.tool_name for obs in self.memory}
        for tool_name in self.registry._tools:
            if tool_name not in executed_tools:
                tool = self.registry.get(tool_name)
                return Action(
                    tool_name=tool_name,
                    params=context or {},
                    reason=f"执行 Pipeline 下一步: {tool.description}",
                )

        return Action(tool_name="", reason="所有工具已执行完毕")

    def execute(self, action: Action) -> Observation:
        """
        执行一个 Action：调用对应 Tool 的 execute()

        内置重试 + 超时机制:
          - 单次调用超时由 Tool.timeout 控制，超时后抛出 TimeoutError
          - 超时也计入一次重试，最终耗尽 max_retries 后降级返回失败
        """
        import time

        tool = self.registry.get(action.tool_name)
        if not tool:
            result = ToolResult(
                success=False,
                error=f"Tool '{action.tool_name}' not found",
            )
            obs = Observation(action=action, result=result, timestamp=time.time())
            self.memory.append(obs)
            return obs

        last_error = None
        timeout = getattr(tool, 'timeout', 30.0)

        for attempt in range(self.max_retries):
            try:
                # 在独立线程中执行 Tool，支持超时中断
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(tool.execute, **action.params)
                    result = future.result(timeout=timeout)

                result.retry_count = attempt
                if result.success:
                    break
                last_error = result.error
            except concurrent.futures.TimeoutError:
                last_error = f"Tool '{action.tool_name}' 超时 ({timeout}s)"
                result = ToolResult(
                    success=False,
                    error=last_error,
                    retry_count=attempt,
                )
            except Exception as e:
                last_error = str(e)
                result = ToolResult(success=False, error=str(e), retry_count=attempt)

        if not result.success:
            result.error = last_error or result.error

            # Fallback 降级：主 Tool 失败 → 自动切换到备用 Tool
            fallback_name = self.tool_fallbacks.get(action.tool_name)
            if fallback_name and self.registry.get(fallback_name):
                fallback_tool = self.registry.get(fallback_name)
                fb_timeout = getattr(fallback_tool, 'timeout', 30.0)
                print(f"  ⚠ [{self.name}] Tool '{action.tool_name}' 失败，降级到 '{fallback_name}'")
                for fb_attempt in range(self.max_retries):
                    try:
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                            fb_future = executor.submit(fallback_tool.execute, **action.params)
                            result = fb_future.result(timeout=fb_timeout)
                        result.retry_count = fb_attempt
                        if result.success:
                            result.metadata["fallback_from"] = action.tool_name
                            break
                    except concurrent.futures.TimeoutError:
                        result = ToolResult(
                            success=False,
                            error=f"Fallback '{fallback_name}' 超时 ({fb_timeout}s)",
                            retry_count=fb_attempt,
                        )
                    except Exception as e:
                        result = ToolResult(success=False, error=str(e), retry_count=fb_attempt)

                if not result.success:
                    result.metadata["fallback_from"] = action.tool_name

        obs = Observation(action=action, result=result, timestamp=time.time())
        self.memory.append(obs)
        return obs

    def should_converge(self, task: str) -> bool:
        """
        判断是否已收敛（任务完成）。

        默认策略:
          - 所有工具均已被执行过 → 收敛
          - 最近一次 Tool 执行失败且无其他工具 → 收敛（降级）
        """
        available_tools = set(self.registry._tools.keys())

        if not available_tools:
            return True

        executed_tools = {obs.action.tool_name for obs in self.memory}
        if executed_tools >= available_tools:
            return True

        if self.memory:
            last_obs = self.memory[-1]
            if not last_obs.result.success and executed_tools >= available_tools:
                return True

        return False

    def get_trace(self) -> List[Dict[str, Any]]:
        """获取完整执行轨迹"""
        return [
            {
                "step": i + 1,
                "tool": obs.action.tool_name,
                "success": obs.result.success,
                "error": obs.result.error,
                "retries": obs.result.retry_count,
            }
            for i, obs in enumerate(self.memory)
        ]

    @property
    def tool_names(self) -> List[str]:
        """已注册的工具名称列表"""
        return list(self.registry._tools.keys())


# ============================================================
# ReActAgent —— LLM 驱动的动态推理 Agent
# ============================================================

@dataclass
class ReActStep:
    """ReAct 推理链中的一步"""
    step: int
    thought: str = ""
    action: Optional[str] = None
    action_input: Dict[str, Any] = field(default_factory=dict)
    observation: str = ""
    is_final: bool = False
    final_answer: str = ""


class ReActAgent(Agent):
    """
    ReAct (Reasoning + Acting) Agent

    与基类 Agent（固定 Pipeline）不同，ReActAgent 每步都调用 LLM
    来推理「下一步应该调用哪个 Tool」或「是否已经可以给出最终答案」。

    核心循环: think → act → observe → (think → ...) → final answer

    Usage:
        def my_llm(prompt: str) -> str:
            # 调用你的 LLM API
            return response

        agent = ReActAgent(
            name="data_analyst",
            tools=[rag_tool, query_tool, chart_tool],
            system_prompt="你是金融数据分析助手...",
            llm_call=my_llm,
            max_steps=10,
        )
    """

    def __init__(
        self,
        name: str,
        tools: List[Tool],
        system_prompt: str = "",
        max_retries: int = 3,
        tool_fallbacks: Dict[str, str] = None,
        llm_call: Any = None,
        max_steps: int = 10,
    ):
        super().__init__(
            name=name,
            tools=tools,
            system_prompt=system_prompt,
            max_retries=max_retries,
            tool_fallbacks=tool_fallbacks,
        )
        self.llm_call = llm_call  # Callable[[str], str]
        self.max_steps = max_steps

        # ReAct 推理链（比 memory 更丰富）
        self.react_trace: List[ReActStep] = []

        # 最终答案
        self.final_answer: str = ""

    def decide_next_action(self, task: str, context: Dict[str, Any] = None) -> Action:
        """
        ReAct 核心：调用 LLM 推理下一步行动。

        构建包含 Tool 列表 + 历史步骤 + 当前任务 的 prompt，
        由 LLM 返回结构化的下一步骤。
        """
        context = context or {}

        # 构建 ReAct prompt
        prompt = self._build_react_prompt(task, context)

        # 调用 LLM
        if not self.llm_call:
            return Action(
                tool_name="",
                reason="ReActAgent 未配置 llm_call，无法推理",
            )

        llm_response = self.llm_call(prompt)

        # 解析 LLM 输出
        parsed = self._parse_react_response(llm_response)

        step = ReActStep(
            step=len(self.react_trace) + 1,
            thought=parsed.get("thought", ""),
            action=parsed.get("action"),
            action_input=parsed.get("action_input", {}),
            is_final=parsed.get("is_final", False),
            final_answer=parsed.get("final_answer", ""),
        )
        self.react_trace.append(step)

        if step.is_final:
            self.final_answer = step.final_answer
            return Action(tool_name="", reason=f"Final Answer: {step.final_answer[:80]}...")

        if not step.action:
            return Action(tool_name="", reason="LLM 未返回有效 action")

        return Action(
            tool_name=step.action,
            params=step.action_input,
            reason=step.thought,
        )

    def should_converge(self, task: str) -> bool:
        """
        ReAct 收敛条件:
          1. LLM 返回了 Final Answer
          2. 达到 max_steps 上限
          3. 所有 Tool 都已执行过且最后一次失败
        """
        if self.final_answer:
            return True

        if len(self.react_trace) >= self.max_steps:
            self.final_answer = f"达到最大步数限制 ({self.max_steps})，停止推理"
            return True

        # 降级：所有工具都试过了，最近一次也没成功
        if self.memory:
            executed = {obs.action.tool_name for obs in self.memory}
            all_tried = executed >= set(self.registry._tools.keys())
            if all_tried and not self.memory[-1].result.success:
                self.final_answer = "所有工具均已尝试，未能完成任务"
                return True

        return False

    def get_trace(self) -> List[Dict[str, Any]]:
        """获取完整 ReAct 推理链（含 thought）"""
        return [
            {
                "step": s.step,
                "thought": s.thought,
                "tool": s.action,
                "action_input": s.action_input,
                "observation": s.observation,
                "is_final": s.is_final,
                "final_answer": s.final_answer,
            }
            for s in self.react_trace
        ]

    def _build_react_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """构建 ReAct 推理 prompt"""
        # Tool 列表
        tools_desc_str = ""
        for name, info in self.registry.list_all().items():
            tools_desc_str += (
                f"\n  - {name}: {info['description']} "
                f"(inputs: {info['input_schema']}, timeout: {info.get('timeout', 30)}s)"
            )

        # 历史步骤
        history_str = ""
        for s in self.react_trace:
            history_str += f"\nStep {s.step}:"
            history_str += f"\n  Thought: {s.thought}"
            if s.action:
                history_str += f"\n  Action: {s.action}({s.action_input})"
                history_str += f"\n  Observation: {s.observation}"
            if s.is_final:
                history_str += f"\n  Final Answer: {s.final_answer}"

        # 最近的 Tool 执行观察
        recent_obs_str = ""
        for obs in self.memory[-3:]:
            status = "OK" if obs.result.success else "FAIL"
            snippet = str(obs.result.data)[:200] if obs.result.data else "null"
            recent_obs_str += f"\n  [{obs.action.tool_name}] {status} data={snippet}"
            if obs.result.error:
                recent_obs_str += f" error={obs.result.error}"

        context_str = str(context)[:500]

        prompt = self.system_prompt + "\n\n"
        prompt += "## Available Tools\n" + tools_desc_str + "\n\n"
        prompt += "## Task\n" + task + "\n\n"
        prompt += "## Context\n" + context_str + "\n\n"
        if history_str:
            prompt += "## Previous Reasoning Steps\n" + history_str + "\n\n"
        if recent_obs_str:
            prompt += "## Recent Tool Results\n" + recent_obs_str + "\n\n"
        prompt += """## Instruction
Based on the above, decide the NEXT step. Respond ONLY in JSON:
{
  "thought": "your reasoning about what to do next",
  "action": "tool_name or final_answer",
  "action_input": {}
}

If you have enough information to answer the task, set action to "final_answer" and provide the answer in the "thought" field."""
        return prompt

    def _parse_react_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 的 ReAct 响应，支持 JSON 和文本格式"""
        import json

        # 尝试直接解析 JSON
        try:
            data = json.loads(response)
            return {
                "thought": data.get("thought", ""),
                "action": data.get("action"),
                "action_input": data.get("action_input", {}),
                "is_final": data.get("action") == "final_answer",
                "final_answer": data.get("thought", "") if data.get("action") == "final_answer" else "",
            }
        except (json.JSONDecodeError, TypeError):
            pass

        # 尝试从文本中提取 JSON 块
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return {
                    "thought": data.get("thought", ""),
                    "action": data.get("action"),
                    "action_input": data.get("action_input", {}),
                    "is_final": data.get("action") == "final_answer",
                    "final_answer": data.get("thought", "") if data.get("action") == "final_answer" else "",
                }
            except json.JSONDecodeError:
                pass

        # 降级：把整个响应当作 final_answer
        return {
            "thought": response,
            "is_final": True,
            "final_answer": response,
        }
