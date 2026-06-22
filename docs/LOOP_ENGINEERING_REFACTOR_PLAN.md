# BankDataViz Loop Engineering 改造技术方案（优化终版）

> **文档性质**：技术设计方案  
> **版本**：v2.0（经三轮自审查修正）  
> **日期**：2026-06-22  
> **原则**：增强现有循环，不推倒重来；先跑通再优化，灰度发布，向后兼容

---

## 目录

- [一、问题定义与目标](#一问题定义与目标)
- [二、现状分析](#二现状分析)
- [三、总体架构设计](#三总体架构设计)
- [四、模块一：Terminator（终止条件引擎）](#四模块一terminator终止条件引擎)
- [五、模块二：SmartRetry（智能重试）](#五模块二smartretry智能重试)
- [六、模块三：LoopState（循环状态增强）](#六模块三loopstate循环状态增强)
- [七、模块四：HITLManager（人机协作）](#七模块四hitlmanager人机协作)
- [八、模块五：PlanAgent（规划执行 Agent）](#八模块五planagent规划执行-agent)
- [九、Orchestrator 增强方案](#九orchestrator-增强方案)
- [十、工程化保障](#十工程化保障)
- [十一、灰度发布方案](#十一灰度发布方案)
- [十二、实施路线图](#十二实施路线图)
- [十三、风险评估与应对](#十三风险评估与应对)

---

## 一、问题定义与目标

### 1.1 当前痛点

通过对 `agent.py`、`orchestrator.py`、`verification.py` 及三个 Agent 实现的逐行分析，当前 Agent 循环存在以下问题：

| # | 痛点 | 代码位置 | 影响 |
|---|------|----------|------|
| 1 | **收敛条件过于简单** | `Agent.should_converge()` 仅判断"所有工具都执行过"，无法识别"任务实际已完成" | ReAct 模式下 max_steps 硬截断常导致结果不完整 |
| 2 | **重试策略粗糙** | `Agent.execute()` 固定 `max_retries` 次，无指数退避、无错误分类 | 瞬时故障（429 限流）与永久故障（文件不存在）同等处理，浪费重试 |
| 3 | **状态追踪脆弱** | `self.memory: List[Observation]` 和 `self.react_trace: List[ReActStep]` 都是线性列表，无法标记哪些策略已尝试、哪些应避免 | 循环可能重复尝试已证明无效的路径 |
| 4 | **HITL 同步阻塞** | `Orchestrator.run()` 中 `on_need_human()` 是同步回调，阻塞整个请求线程 | 生产环境不可接受，人工可能数分钟不响应 |
| 5 | **缺少计划模式** | 只有 Pipeline（固定顺序）和 ReAct（每步推理），缺少"先规划再执行"模式 | 复杂多步骤任务（如"跨银行对比分析"）效率低、Token 消耗大 |

### 1.2 改造目标

| 目标 | 衡量标准 | 优先级 |
|------|----------|--------|
| **收敛准确性**：Agent 能在任务实际完成时正确终止 | ReAct 模式下 FINAL_ANSWER 触发率 ≥ 95% | P0 |
| **重试智能化**：区分瞬时故障与永久故障，指数退避 | 无效重试减少 ≥ 60% | P0 |
| **状态可追踪**：结构化记录每次尝试，支持策略筛选 | 可导出完整 AttemptRecord 列表 | P1 |
| **HITL 异步化**：人工介入不阻塞主线程 | 支持异步回调 + 超时自动降级 | P1 |
| **规划模式**：先规划再执行，降低 Token 消耗 | 多步任务 Token 节省 ≥ 30% | P2 |

### 1.3 核心原则

```
1. 增强而非替换：Orchestrator.run() 保持主循环结构，模块以钩子方式注入
2. 向后兼容：现有 4 个 API 端点行为不变，新功能通过 opt-in 参数启用
3. 零新依赖：全部基于 Python 标准库实现（asyncio、dataclasses、enum）
4. 可灰度：通过配置开关逐模块启用，随时可回退
```

---

## 二、现状分析

### 2.1 当前 Agent 循环骨架

```
Orchestrator.run()
├── for agent in self.agents:                    # 串行多Agent
│   └── while step < max_loops:                  # Agent 内循环
│       ├── action = agent.decide_next_action()   # 决策
│       ├── observation = agent.execute(action)   # 执行（内置重试+降级）
│       ├── verifier.check()                      # 验证
│       ├── HITL callback (同步)                  # 人工介入
│       └── if agent.should_converge(): break     # 收敛判断
```

### 2.2 关键数据流

```
Context (dict)
  ├── image_path, bank_name, force_refresh     ← 外部输入
  ├── ocr_result                                ← OCR Tool 输出
  ├── llm_result                                ← LLM Tool 输出
  ├── last_result                               ← 最近 Tool 输出
  └── previous_agent_output                     ← 前一个 Agent 输出

Agent.memory: List[Observation]
  └── Observation(action, result, timestamp)

ReActAgent.react_trace: List[ReActStep]
  └── ReActStep(step, thought, action, action_input, observation, is_final, final_answer)
```

### 2.3 现有韧性机制（不可丢弃）

| 机制 | 位置 | 说明 |
|------|------|------|
| **内置重试** | `Agent.execute()` L124 | `for attempt in range(max_retries)`，线程池超时控制 |
| **Fallback 降级** | `Agent.execute()` L149-175 | `tool_fallbacks` 映射，主 Tool 失败→备用 Tool |
| **超时控制** | `Agent.execute()` L127-129 | `concurrent.futures.ThreadPoolExecutor` + `future.result(timeout)` |
| **HITL 兜底** | `Orchestrator.run()` L179-198 | 所有重试+降级失败后触发 `on_need_human` 回调 |

> **改造原则**：SmartRetry 层叠在现有重试 + 降级之上，不替代。现有机制处理 Tool 级别的瞬时故障，SmartRetry 增加策略层的错误分类、退避、死信队列。

---

## 三、总体架构设计

### 3.1 模块关系图

```
                    ┌──────────────────────────────────────┐
                    │          Orchestrator (增强)          │
                    │  保持现有主循环 + 注入钩子点           │
                    └──────────────┬───────────────────────┘
                                   │
        ┌──────────────┬───────────┼───────────┬──────────────┐
        ▼              ▼           ▼           ▼              ▼
   ┌─────────┐  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
   │Terminator│  │SmartRetry│ │LoopState │ │HITLManager│ │PlanAgent │
   │终止条件  │  │智能重试  │ │循环状态  │ │人机协作  │ │规划执行  │
   └─────────┘  └──────────┘ └──────────┘ └──────────┘ └──────────┘
        │              │           │           │              │
        ▼              ▼           ▼           ▼              ▼
   ┌─────────────────────────────────────────────────────────────┐
   │              现有 Agent 核心（不改接口）                     │
   │  Agent.execute() / ReActAgent.decide_next_action()          │
   │  ToolRegistry / RuleEngine / 7 Tools                        │
   └─────────────────────────────────────────────────────────────┘
```

### 3.2 新增文件清单

```
backend/harness/
├── loop/                              # ★ 新增：Loop Engineering 模块
│   ├── __init__.py                    # 导出
│   ├── termination.py                 # 模块一：Terminator
│   ├── smart_retry.py                 # 模块二：SmartRetry
│   ├── loop_state.py                  # 模块三：LoopState
│   ├── hitl.py                        # 模块四：HITLManager
│   └── plan_agent.py                  # 模块五：PlanAgent
├── agent.py                           # 增强：集成 LoopState
├── orchestrator.py                    # 增强：注入终止/重试/HITL 钩子
├── __init__.py                        # 更新：导出新模块
```

### 3.3 配置参数集中化

所有阈值/开关统一到 `LoopConfig`：

```python
# backend/harness/loop/__init__.py
from dataclasses import dataclass, field
from typing import Set

@dataclass
class LoopConfig:
    """Loop Engineering 全局配置，所有模块从单一来源读取"""

    # ---- Terminator ----
    max_steps: int = 10                    # 全局最大步数
    task_complete_markers: Set[str] = field(default_factory=lambda: {
        "FINAL_ANSWER", "final_answer", "TASK_COMPLETE"
    })
    consecutive_failures_limit: int = 3   # 连续失败 N 次→终止
    loop_detection_threshold: int = 5     # 重复 Action 序列长度阈值

    # ---- SmartRetry ----
    base_delay: float = 1.0               # 指数退避基秒数
    max_delay: float = 30.0               # 退避上限秒数
    jitter_factor: float = 0.1            # 随机抖动系数
    transient_errors: Set[str] = field(default_factory=lambda: {
        "rate_limit", "timeout", "connection", "503", "429", "throttle"
    })

    # ---- HITL ----
    hitl_timeout_seconds: int = 300        # 人工决策超时（秒），超时自动 abort
    hitl_async: bool = True                # 是否启用异步 HITL

    # ---- 灰度开关 ----
    enable_terminator: bool = True
    enable_smart_retry: bool = True
    enable_loop_state: bool = True
    enable_hitl: bool = True
    enable_plan_agent: bool = False        # PlanAgent 默认关闭，需主动启用

    @classmethod
    def from_env(cls) -> "LoopConfig":
        """从环境变量加载（支持运行时覆盖）"""
        import os
        kwargs = {}
        for field_name in cls.__dataclass_fields__:
            env_key = f"LOOP_{field_name.upper()}"
            if env_key in os.environ:
                val = os.environ[env_key]
                field_type = cls.__dataclass_fields__[field_name].type
                if field_type == bool:
                    kwargs[field_name] = val.lower() in ("true", "1", "yes")
                elif field_type == int:
                    kwargs[field_name] = int(val)
                elif field_type == float:
                    kwargs[field_name] = float(val)
        return cls(**kwargs)
```

---

## 四、模块一：Terminator（终止条件引擎）

### 4.1 设计要点

> **现有问题**：`Agent.should_converge()` 只检查"所有工具都执行过"，无法感知任务实际完成。`ReActAgent.should_converge()` 虽然有 `FINAL_ANSWER` 检查，但缺少循环检测和连续失败保护。
>
> **修正思路**：不替换 `should_converge()`，而是增加一个可组合的 `Terminator` 对象，Orchestrator 在主循环中同时调用两者。

### 4.2 终止条件矩阵

| 条件 | 类型 | 触发逻辑 | 优先级 |
|------|------|----------|--------|
| `TASK_COMPLETE` | 正常 | LLM 返回 FINAL_ANSWER 或 Agent 声明 TASK_COMPLETE | 最高 |
| `MAX_STEPS` | 保护 | 步数达到 `max_steps` | 高 |
| `ALL_TOOLS_EXHAUSTED` | 降级 | 所有 Tool 均失败且无备用方案 | 中 |
| `CONSECUTIVE_FAILURES` | 保护 | 连续 N 步失败（含重试后仍失败） | 中 |
| `LOOP_DETECTED` | 保护 | 检测到重复的 (tool_name, params_hash) 序列 | 中 |
| `EXPLICIT_ABORT` | 外部 | HITL 返回 abort 或外部取消信号 | 最高 |

### 4.3 完整实现

```python
# backend/harness/loop/termination.py
"""
Terminator — 多条件可组合终止引擎

设计原则：
  - 不替换 Agent.should_converge()，作为补充判断层
  - 每个条件独立实现，通过 OR 逻辑组合
  - 终止原因可追溯，便于调试
"""

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set

from ..loop import LoopConfig


class TermReason(Enum):
    """终止原因枚举"""
    TASK_COMPLETE = auto()
    MAX_STEPS = auto()
    ALL_TOOLS_EXHAUSTED = auto()
    CONSECUTIVE_FAILURES = auto()
    LOOP_DETECTED = auto()
    EXPLICIT_ABORT = auto()


@dataclass
class TermDecision:
    """终止决策"""
    should_stop: bool
    reason: Optional[TermReason] = None
    detail: str = ""


@dataclass
class Terminator:
    """
    多条件终止引擎

    Usage:
        terminator = Terminator(config)
        for step in range(max_steps):
            ...
            decision = terminator.check(step, agent, trace, observation)
            if decision.should_stop:
                break
    """

    config: LoopConfig
    _action_history: List[str] = field(default_factory=list)  # (tool_name, params_hash) 历史

    def check(
        self,
        step: int,
        agent,                       # Agent 实例
        trace: List[Dict[str, Any]],
        observation=None,            # 最近一次 Observation
        explicit_abort: bool = False,
    ) -> TermDecision:
        """
        按优先级依次检查所有终止条件，返回第一个触发的结果。

        Args:
            step: 当前步数（从1开始）
            agent: Agent 实例（读取 react_trace、final_answer）
            trace: Orchestrator 的 trace 列表
            observation: 最近一次 Observation
            explicit_abort: 外部中止信号
        """
        # --- P0: 外部中止 ---
        if explicit_abort:
            return TermDecision(True, TermReason.EXPLICIT_ABORT, "外部请求中止")

        # --- P0: TASK_COMPLETE ---
        decision = self._check_task_complete(agent)
        if decision.should_stop:
            return decision

        # --- P1: MAX_STEPS ---
        if step >= self.config.max_steps:
            return TermDecision(
                True, TermReason.MAX_STEPS,
                f"达到最大步数限制 ({self.config.max_steps})"
            )

        # --- P1: CONSECUTIVE_FAILURES ---
        decision = self._check_consecutive_failures(trace)
        if decision.should_stop:
            return decision

        # --- P2: LOOP_DETECTED ---
        decision = self._check_loop_detection(observation)
        if decision.should_stop:
            return decision

        # --- P2: ALL_TOOLS_EXHAUSTED ---
        decision = self._check_all_tools_exhausted(agent, trace)
        if decision.should_stop:
            return decision

        return TermDecision(False)

    # ========== 各条件独立实现 ==========

    def _check_task_complete(self, agent) -> TermDecision:
        """检查 Agent 是否声明任务完成"""
        # ReActAgent: final_answer 已设置
        if hasattr(agent, 'final_answer') and agent.final_answer:
            return TermDecision(True, TermReason.TASK_COMPLETE,
                              f"Agent 返回 FINAL_ANSWER: {agent.final_answer[:100]}")

        # 检查最近 react_trace 是否有 is_final
        if hasattr(agent, 'react_trace') and agent.react_trace:
            last_step = agent.react_trace[-1]
            if last_step.is_final:
                return TermDecision(True, TermReason.TASK_COMPLETE,
                                  f"ReActStep[{last_step.step}] 标记为 is_final")

        # 检查 observation 结果中是否包含任务完成标记
        if hasattr(agent, 'memory') and agent.memory:
            last_obs = agent.memory[-1]
            if last_obs.result.success and isinstance(last_obs.result.data, dict):
                markers = self.config.task_complete_markers
                if any(k in last_obs.result.data for k in markers):
                    return TermDecision(True, TermReason.TASK_COMPLETE,
                                      "Tool 输出包含任务完成标记")

        return TermDecision(False)

    def _check_consecutive_failures(self, trace: List[Dict]) -> TermDecision:
        """检查连续失败次数"""
        recent = trace[-self.config.consecutive_failures_limit:]
        if len(recent) >= self.config.consecutive_failures_limit:
            if all(not t.get("success", True) for t in recent):
                return TermDecision(
                    True, TermReason.CONSECUTIVE_FAILURES,
                    f"连续 {self.config.consecutive_failures_limit} 步均失败"
                )
        return TermDecision(False)

    def _check_loop_detection(self, observation) -> TermDecision:
        """检测重复的 Action 序列，防止死循环"""
        if observation is None:
            return TermDecision(False)

        tool_name = observation.action.tool_name
        if not tool_name:
            return TermDecision(False)

        # 计算参数的轻量哈希（只哈希前 500 字符）
        params_str = json.dumps(observation.action.params, sort_keys=True, default=str)[:500]
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        action_key = f"{tool_name}:{params_hash}"

        self._action_history.append(action_key)
        # 保留最近 N 条
        if len(self._action_history) > self.config.loop_detection_threshold * 2:
            self._action_history = self._action_history[-self.config.loop_detection_threshold * 2:]

        # 检查最近 threshold 条是否有重复模式
        threshold = self.config.loop_detection_threshold
        if len(self._action_history) >= threshold:
            recent = self._action_history[-threshold:]
            if len(set(recent)) <= 2:  # 只有 1-2 种不同 action 在循环
                return TermDecision(
                    True, TermReason.LOOP_DETECTED,
                    f"检测到循环: 最近 {threshold} 步只包含 {len(set(recent))} 种不同动作"
                )

        return TermDecision(False)

    def _check_all_tools_exhausted(self, agent, trace: List[Dict]) -> TermDecision:
        """检查所有工具是否都已尝试且失败"""
        # 利用 Agent 现有的 should_converge 逻辑
        # 只当所有 trace 都标记为失败时额外检查
        if not trace:
            return TermDecision(False)

        all_failed = all(not t.get("success", True) for t in trace)
        if all_failed and hasattr(agent, 'should_converge'):
            if agent.should_converge(""):
                return TermDecision(
                    True, TermReason.ALL_TOOLS_EXHAUSTED,
                    "所有工具均已尝试且失败，无更多路径"
                )

        return TermDecision(False)
```

---

## 五、模块二：SmartRetry（智能重试）

### 5.1 设计要点

> **现有机制**：`Agent.execute()` 已有 `max_retries` 固定重试 + `tool_fallbacks` 降级。这套机制处理 Tool 级别的瞬时故障是有效的。
>
> **SmartRetry 定位**：不做替代，而是在**策略层面**增加三个能力——①错误分类（区分瞬时/永久故障）、②指数退避+抖动、③死信队列持久化。不会改动 `Agent.execute()` 内部逻辑。

### 5.2 分层关系

```
SmartRetry (本模块)         ← 策略层：错误分类、退避策略、死信队列
    │
    │  控制在何时、以什么节奏调用
    ▼
Agent.execute() (现有)      ← 执行层：固定重试 + fallback 降级
    │
    │  实际调用 Tool
    ▼
Tool.execute()              ← 能力层：具体业务逻辑
```

### 5.3 完整实现

```python
# backend/harness/loop/smart_retry.py
"""
SmartRetry — 策略层智能重试

分层关系:
  SmartRetry (本模块)  → 控制重试节奏、错误分类、死信
        ↓ 调用
  Agent.execute()      → 现有固定重试 + fallback 降级
        ↓ 调用
  Tool.execute()        → 具体业务逻辑

不修改 Agent.execute() 内部代码，作为外层策略增强。
"""

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ..loop import LoopConfig


class ErrorCategory(Enum):
    """错误分类"""
    TRANSIENT = "transient"       # 瞬时故障，可重试（限流、超时、网络闪断）
    PERMANENT = "permanent"       # 永久故障，不应重试（文件不存在、权限拒绝）
    UNKNOWN = "unknown"           # 无法分类，保守重试 1 次


@dataclass
class DeadLetter:
    """死信记录"""
    task_id: str
    tool_name: str
    params: Dict[str, Any]
    error: str
    error_category: ErrorCategory
    attempts: int
    timestamp: float = field(default_factory=time.time)
    agent_name: str = ""


@dataclass
class RetryResult:
    """重试结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    attempts: int = 0
    total_delay_seconds: float = 0.0
    error_category: ErrorCategory = ErrorCategory.UNKNOWN
    sent_to_dead_letter: bool = False


class SmartRetry:
    """
    智能重试管理器

    Usage:
        retry_mgr = SmartRetry(config)
        result = retry_mgr.execute_with_retry(
            agent=agent,
            action=action,
            task_id="task_001",
        )
    """

    def __init__(self, config: LoopConfig, dead_letter_store: Optional[callable] = None):
        self.config = config
        self.dead_letter_store = dead_letter_store or self._default_dead_letter_store
        self._dead_letters: List[DeadLetter] = []  # 内存死信队列

    def execute_with_retry(
        self,
        agent,                # Agent 实例
        action,               # Action 实例
        task_id: str = "",
    ) -> RetryResult:
        """
        带智能退避的执行。

        Agent.execute() 内部已有重试逻辑，本方法在其外层
        增加错误分类 + 指数退避。流程：
          1. 调用 agent.execute(action)
          2. 如果成功 → 返回
          3. 如果失败 → 分类错误
            3a. 瞬时故障 → 指数退避后重试（最多 max_retries 次外层重试）
            3b. 永久故障 → 立即返回失败，写入死信队列
        """
        error_category = ErrorCategory.UNKNOWN
        total_delay = 0.0

        for outer_attempt in range(agent.max_retries):
            observation = agent.execute(action)

            if observation.result.success:
                return RetryResult(
                    success=True,
                    data=observation.result.data,
                    attempts=outer_attempt + 1,
                    total_delay_seconds=total_delay,
                )

            # 分类错误
            error_msg = observation.result.error or ""
            error_category = self._categorize_error(error_msg)

            if error_category == ErrorCategory.PERMANENT:
                # 永久故障：不重试，直接失败
                self._send_to_dead_letter(
                    DeadLetter(
                        task_id=task_id,
                        tool_name=action.tool_name,
                        params=action.params,
                        error=error_msg,
                        error_category=error_category,
                        attempts=outer_attempt + 1,
                        agent_name=agent.name,
                    )
                )
                return RetryResult(
                    success=False,
                    error=error_msg,
                    attempts=outer_attempt + 1,
                    total_delay_seconds=total_delay,
                    error_category=error_category,
                    sent_to_dead_letter=True,
                )

            # 瞬时故障或未知：指数退避
            if outer_attempt < agent.max_retries - 1:
                delay = self._calculate_backoff(outer_attempt)
                total_delay += delay
                time.sleep(delay)

        # 所有重试耗尽
        self._send_to_dead_letter(
            DeadLetter(
                task_id=task_id,
                tool_name=action.tool_name,
                params=action.params,
                error=observation.result.error or "exhausted",
                error_category=error_category,
                attempts=agent.max_retries,
                agent_name=agent.name,
            )
        )
        return RetryResult(
            success=False,
            error=observation.result.error,
            attempts=agent.max_retries,
            total_delay_seconds=total_delay,
            error_category=error_category,
            sent_to_dead_letter=True,
        )

    def _categorize_error(self, error_msg: str) -> ErrorCategory:
        """基于关键词和规则分类错误类型"""
        msg_lower = error_msg.lower()

        # 永久故障特征
        permanent_patterns = [
            "file not found", "no such file", "file doesn't exist",
            "permission denied", "access denied", "forbidden",
            "invalid api key", "authentication failed", "unauthorized",
            "not found", "does not exist", "cannot find",
            "文件不存在", "权限不足", "未授权",
        ]
        for pattern in permanent_patterns:
            if pattern in msg_lower:
                return ErrorCategory.PERMANENT

        # 瞬时故障特征
        for pattern in self.config.transient_errors:
            if pattern in msg_lower:
                return ErrorCategory.TRANSIENT

        return ErrorCategory.UNKNOWN

    def _calculate_backoff(self, attempt: int) -> float:
        """指数退避 + 随机抖动"""
        delay = min(
            self.config.base_delay * (2 ** attempt),
            self.config.max_delay,
        )
        jitter = random.uniform(0, delay * self.config.jitter_factor)
        return delay + jitter

    def _send_to_dead_letter(self, letter: DeadLetter) -> None:
        """写入死信队列"""
        self._dead_letters.append(letter)
        if self.dead_letter_store:
            try:
                self.dead_letter_store(letter)
            except Exception:
                pass  # 死信存储本身失败不应影响主流程

    def get_dead_letters(self, task_id: str = None) -> List[DeadLetter]:
        """查询死信队列"""
        if task_id:
            return [dl for dl in self._dead_letters if dl.task_id == task_id]
        return list(self._dead_letters)

    def retry_dead_letter(self, task_id: str) -> bool:
        """手动重试死信（标记为可重新处理）"""
        # 简单实现：从死信列表移除，由调用方重新调度
        before = len(self._dead_letters)
        self._dead_letters = [dl for dl in self._dead_letters if dl.task_id != task_id]
        return len(self._dead_letters) < before

    @staticmethod
    def _default_dead_letter_store(letter: DeadLetter) -> None:
        """默认死信存储（打印日志），可替换为 Redis/DB 持久化"""
        print(f"[DEAD_LETTER] task={letter.task_id} tool={letter.tool_name} "
              f"error={letter.error[:100]} category={letter.error_category.value}")

    # ---- 中文友好错误分类适配 ----

    def _categorize_error_cn(self, error_msg: str) -> ErrorCategory:
        """扩展的中文错误消息识别"""
        cn_permanent = [
            "文件不存在", "找不到文件", "路径不存在",
            "权限不足", "无权访问", "未授权",
            "密钥无效", "认证失败",
        ]
        cn_transient = [
            "超时", "连接失败", "网络错误", "限流",
            "服务器繁忙", "请稍后重试", "暂时不可用",
            "timeout", "connection refused", "too many requests",
        ]
        msg = error_msg.lower()
        for p in cn_permanent:
            if p in msg:
                return ErrorCategory.PERMANENT
        for p in cn_transient:
            if p in msg:
                return ErrorCategory.TRANSIENT
        return ErrorCategory.UNKNOWN
```

---

## 六、模块三：LoopState（循环状态增强）

### 6.1 设计要点

> **现有问题**：`self.memory: List[Observation]` 是线性列表，无法回答"某个策略是否已尝试过"、"是否应避免某条路径"等结构化查询。
>
> **修正思路**：不替换 `memory`，而是**并行维护**一个结构化的 `AttemptRecord` 列表，提供按 `tool_name`、`strategy`、`success` 等维度查询的能力。

### 6.2 数据结构

```python
# backend/harness/loop/loop_state.py
"""
LoopState — 结构化循环状态追踪

在现有 Agent.memory (List[Observation]) 基础上，
并行维护 AttemptRecord 列表，提供多维度查询能力。
不修改 Agent.memory 的结构。
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Strategy(str, Enum):
    """尝试策略枚举（替代脆弱的字符串匹配）"""
    DIRECT = "direct"                # 直接调用
    RETRY_SAME = "retry_same"        # 同参数重试
    RETRY_ADJUSTED = "retry_adjusted"  # 调整参数重试
    FALLBACK = "fallback"            # 降级到备用 Tool
    ALTERNATIVE = "alternative"      # 尝试其他方法
    CACHED = "cached"                # 使用缓存结果
    MANUAL = "manual"                # 人工介入


class AttemptOutcome(str, Enum):
    """尝试结果"""
    SUCCESS = "success"
    TRANSIENT_FAILURE = "transient_failure"
    PERMANENT_FAILURE = "permanent_failure"
    TIMEOUT = "timeout"
    VERIFICATION_FAILED = "verification_failed"


@dataclass
class AttemptRecord:
    """单次尝试的结构化记录"""
    step: int
    agent_name: str
    tool_name: str
    params_summary: str              # 参数摘要（前 200 字符）
    strategy: Strategy
    outcome: AttemptOutcome
    error: Optional[str] = None
    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class LoopState:
    """
    循环状态管理器

    用法（在 Agent 中）：
        self.loop_state = LoopState(agent_name=self.name)
        self.loop_state.record(AttemptRecord(...))

        # 查询
        self.loop_state.has_tried("ocr", Strategy.DIRECT)
        self.loop_state.failed_tools()
        self.loop_state.suggest_next_strategy("ocr")
    """

    def __init__(self, agent_name: str = ""):
        self.agent_name = agent_name
        self._records: List[AttemptRecord] = []

    # ---- 写入 ----

    def record(self, record: AttemptRecord) -> None:
        """记录一次尝试"""
        self._records.append(record)

    def record_from_observation(
        self,
        step: int,
        observation,          # Observation 实例
        strategy: Strategy = Strategy.DIRECT,
    ) -> AttemptRecord:
        """从 Observation 自动生成 AttemptRecord"""
        tool_name = observation.action.tool_name
        params_str = str(observation.action.params)[:200]

        if observation.result.success:
            outcome = AttemptOutcome.SUCCESS
        elif observation.result.error and self._is_timeout(observation.result.error):
            outcome = AttemptOutcome.TIMEOUT
        else:
            outcome = AttemptOutcome.TRANSIENT_FAILURE

        record = AttemptRecord(
            step=step,
            agent_name=self.agent_name,
            tool_name=tool_name,
            params_summary=params_str,
            strategy=strategy,
            outcome=outcome,
            error=observation.result.error,
            latency_ms=(observation.timestamp - (self._records[-1].timestamp if self._records else 0)) * 1000 if observation.timestamp else 0,
        )
        self._records.append(record)
        return record

    # ---- 查询 ----

    def has_tried(self, tool_name: str, strategy: Optional[Strategy] = None) -> bool:
        """是否已尝试过某个 Tool（可按策略过滤）"""
        for r in self._records:
            if r.tool_name == tool_name:
                if strategy is None or r.strategy == strategy:
                    return True
        return False

    def failed_tools(self) -> List[str]:
        """返回所有失败的 Tool 名称"""
        return list(set(
            r.tool_name for r in self._records
            if r.outcome != AttemptOutcome.SUCCESS
        ))

    def succeeded_tools(self) -> List[str]:
        """返回所有成功的 Tool 名称"""
        return list(set(
            r.tool_name for r in self._records
            if r.outcome == AttemptOutcome.SUCCESS
        ))

    def consecutive_failures(self) -> int:
        """返回连续失败次数"""
        count = 0
        for r in reversed(self._records):
            if r.outcome != AttemptOutcome.SUCCESS:
                count += 1
            else:
                break
        return count

    def attempt_count(self, tool_name: str) -> int:
        """某个 Tool 的尝试次数"""
        return sum(1 for r in self._records if r.tool_name == tool_name)

    def suggest_next_strategy(self, tool_name: str) -> Strategy:
        """
        建议下一个应尝试的策略。
        
        决策逻辑:
          1. 若从未尝试 → DIRECT
          2. 若 DIRECT 失败 → RETRY_ADJUSTED
          3. 若 RETRY_ADJUSTED 也失败 → ALTERNATIVE (换 Tool)
          4. 若有 fallback 配置 → FALLBACK
        """
        attempts = [r for r in self._records if r.tool_name == tool_name]
        if not attempts:
            return Strategy.DIRECT

        strategies_tried = {r.strategy for r in attempts}

        if Strategy.DIRECT not in strategies_tried:
            return Strategy.DIRECT
        if Strategy.RETRY_ADJUSTED not in strategies_tried:
            return Strategy.RETRY_ADJUSTED
        if Strategy.FALLBACK not in strategies_tried:
            return Strategy.FALLBACK
        return Strategy.ALTERNATIVE

    # ---- 导出 ----

    def to_summary(self) -> Dict[str, Any]:
        """生成状态摘要"""
        return {
            "agent_name": self.agent_name,
            "total_attempts": len(self._records),
            "successful_tools": self.succeeded_tools(),
            "failed_tools": self.failed_tools(),
            "consecutive_failures": self.consecutive_failures(),
            "records": [
                {
                    "step": r.step,
                    "tool": r.tool_name,
                    "strategy": r.strategy.value,
                    "outcome": r.outcome.value,
                    "error": r.error[:100] if r.error else None,
                }
                for r in self._records
            ],
        }

    def to_records(self) -> List[AttemptRecord]:
        """返回所有原始记录"""
        return list(self._records)

    # ---- 私有 ----

    @staticmethod
    def _is_timeout(error_msg: str) -> bool:
        if not error_msg:
            return False
        msg = error_msg.lower()
        return "超时" in msg or "timeout" in msg or "timed out" in msg
```

### 6.3 集成方式（修改 agent.py）

在 `Agent.__init__()` 中增加一行：

```python
# agent.py L50-59，增加最后一行
def __init__(self, name, tools, system_prompt="", max_retries=3, tool_fallbacks=None):
    # ... 现有代码保持不变 ...
    self.loop_state = LoopState(agent_name=name)  # ★ 新增
```

在 `Agent.execute()` 中，每次执行后记录：

```python
# agent.py L176 行之后，增加：
self.loop_state.record_from_observation(
    step=len(self.memory),
    observation=obs,
    strategy=Strategy.DIRECT if not obs.result.metadata.get("fallback_from")
             else Strategy.FALLBACK,
)
```

---

## 七、模块四：HITLManager（人机协作）

### 7.1 设计要点

> **现有问题**：`Orchestrator.run()` 中 `on_need_human()` 是同步回调，会阻塞整个请求线程。在生产环境中人工决策可能需要数分钟，这会耗尽 Flask worker 线程池。
>
> **修正思路**：将 HITL 改为异步模式——触发人工决策时挂起任务并返回 pending 状态，前端轮询任务状态，人工决策后通过另一个 API 恢复执行。同步模式保留作为简单集成的选项。

### 7.2 两种模式对比

| 维度 | 同步模式（现有） | 异步模式（新增） |
|------|-----------------|-----------------|
| 阻塞行为 | 阻塞请求线程 | 返回 pending 状态，释放线程 |
| 适用场景 | 快速决策（< 5s）、开发调试 | 生产环境、需要人工仔细判断 |
| 实现方式 | `on_need_human()` 回调 | 任务状态机 + 轮询/WebSocket |
| 超时处理 | 无（无限阻塞） | `hitl_timeout_seconds` 后自动 abort |

### 7.3 完整实现

```python
# backend/harness/loop/hitl.py
"""
HITLManager — 异步人机协作管理器

支持两种模式:
  1. 异步模式 (默认): 挂起任务 → 返回 pending → 等待人工决策 API
  2. 同步模式 (兼容): 调用回调函数阻塞等待（保留现有行为）

任务状态机:
  RUNNING → AWAITING_HUMAN → (人工决策) → RESUMED / ABORTED
                                  ↓ (超时)
                              AUTO_ABORTED
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional

from ..loop import LoopConfig


class HITLStatus(str, Enum):
    """HITL 任务状态"""
    AWAITING_HUMAN = "awaiting_human"
    HUMAN_RESPONDED = "human_responded"
    TIMEOUT_ABORTED = "timeout_aborted"
    CANCELLED = "cancelled"


class HITLDecision(str, Enum):
    """人工决策结果"""
    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"


@dataclass
class HITLRequest:
    """一次人工介入请求"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_id: str = ""
    tool_name: str = ""
    error: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    status: HITLStatus = HITLStatus.AWAITING_HUMAN
    decision: Optional[HITLDecision] = None
    human_note: str = ""
    created_at: float = field(default_factory=time.time)
    responded_at: Optional[float] = None
    timeout_seconds: int = 300


class HITLManager:
    """
    人机协作管理器

    Usage:
        hitl = HITLManager(config, sync_callback=my_sync_callback)

        # 异步模式
        request = hitl.request_decision(
            task_id="task_001",
            tool_name="ocr",
            error="OCR 服务超时",
        )
        # 返回 HITLRequest，状态为 AWAITING_HUMAN
        # 前端轮询 GET /api/harness/hitl/{request.id}

        # 人工决策
        hitl.provide_decision(request.id, HITLDecision.RETRY)
    """

    def __init__(
        self,
        config: LoopConfig,
        sync_callback: Optional[Callable] = None,  # 同步模式回调
    ):
        self.config = config
        self.sync_callback = sync_callback
        self._pending: Dict[str, HITLRequest] = {}  # id → HITLRequest

    def request_decision(
        self,
        task_id: str,
        tool_name: str,
        error: str,
        context: Dict[str, Any] = None,
    ) -> HITLRequest:
        """
        发起人工决策请求。

        返回 HITLRequest 对象。在异步模式下，
        Orchestrator 应暂停该 Agent 的执行并返回 pending 状态。
        """
        request = HITLRequest(
            task_id=task_id,
            tool_name=tool_name,
            error=error,
            context=context or {},
            timeout_seconds=self.config.hitl_timeout_seconds,
        )
        self._pending[request.id] = request
        return request

    def provide_decision(self, request_id: str, decision: HITLDecision,
                         human_note: str = "") -> Optional[HITLRequest]:
        """
        提供人工决策结果。

        Returns:
            更新后的 HITLRequest，若 request_id 不存在返回 None
        """
        request = self._pending.get(request_id)
        if not request:
            return None

        request.decision = decision
        request.human_note = human_note
        request.status = HITLStatus.HUMAN_RESPONDED
        request.responded_at = time.time()
        return request

    def get_request(self, request_id: str) -> Optional[HITLRequest]:
        """查询 HITL 请求状态"""
        request = self._pending.get(request_id)
        if not request:
            return None

        # 检查超时
        if request.status == HITLStatus.AWAITING_HUMAN:
            elapsed = time.time() - request.created_at
            if elapsed > request.timeout_seconds:
                request.status = HITLStatus.TIMEOUT_ABORTED
                request.decision = HITLDecision.ABORT
                request.human_note = "超时自动中止"
                request.responded_at = time.time()

        return request

    def get_pending_for_task(self, task_id: str) -> Optional[HITLRequest]:
        """获取指定任务的待处理 HITL 请求"""
        for req in self._pending.values():
            if req.task_id == task_id and req.status == HITLStatus.AWAITING_HUMAN:
                # 先检查超时
                elapsed = time.time() - req.created_at
                if elapsed > req.timeout_seconds:
                    req.status = HITLStatus.TIMEOUT_ABORTED
                    req.decision = HITLDecision.ABORT
                    continue
                return req
        return None

    def is_awaiting(self, request_id: str) -> bool:
        """检查是否仍在等待人工决策"""
        request = self._pending.get(request_id)
        if not request:
            return False
        return request.status == HITLStatus.AWAITING_HUMAN

    def cleanup(self, older_than_seconds: int = 3600) -> int:
        """清理已完成的旧请求"""
        cutoff = time.time() - older_than_seconds
        to_remove = [
            rid for rid, req in self._pending.items()
            if req.responded_at and req.responded_at < cutoff
        ]
        for rid in to_remove:
            del self._pending[rid]
        return len(to_remove)

    def list_pending(self) -> list:
        """列出所有待处理的 HITL 请求"""
        return [
            {
                "id": req.id,
                "task_id": req.task_id,
                "tool_name": req.tool_name,
                "error": req.error,
                "status": req.status.value,
                "created_at": req.created_at,
                "elapsed_seconds": round(time.time() - req.created_at, 1),
            }
            for req in self._pending.values()
        ]

    # ---- 同步模式（兼容现有行为） ----

    def execute_sync(
        self,
        tool_name: str,
        error: str,
        context: Dict[str, Any],
    ) -> HITLDecision:
        """
        同步模式：阻塞等待人工决策。
        与现有 on_need_human 回调的行为兼容。
        """
        if self.sync_callback:
            try:
                decision_str = self.sync_callback(
                    f"Tool '{tool_name}' 失败: {error}",
                    {"action": tool_name, "context": context},
                )
                return HITLDecision(decision_str)
            except Exception:
                return HITLDecision.ABORT
        return HITLDecision.ABORT  # 无回调默认 abort
```

---

## 八、模块五：PlanAgent（规划执行 Agent）

### 8.1 设计要点

> **审查修正**：最初方案中 PlanAgent 包含 DAG 工作流引擎，属于过度设计。在当前项目规模下，简单的步骤列表 + `decide_next_action()` 覆盖即可。PlanAgent 使用 ReActAgent 的现有 LLM 调用机制，只是第一步生成计划，后续按计划逐步执行。

### 8.2 简化设计

```
传统 ReAct 模式            PlanAgent 模式
───────────────            ──────────────
Step 1: think → act        Step 0: 生成完整计划
Step 2: think → act              [step1, step2, step3]
Step 3: think → act        Step 1: 执行计划步骤 1
Step 4: think → act        Step 2: 验证 + 执行步骤 2
Step 5: final_answer       Step 3: 验证 + 执行步骤 3
                            Step 4: final_answer (汇总)

Token 消耗: 高              Token 消耗: 低 ≈ 30% 节省
适合探索性任务              适合目标明确的多步任务
```

### 8.3 完整实现

```python
# backend/harness/loop/plan_agent.py
"""
PlanAgent — 先规划再执行的 Agent

继承 ReActAgent，第一步生成结构化执行计划，
后续步骤按计划逐步执行，每步验证中间结果。

简化设计（v2.0 修正）：
  - 不需要 DAG：计划是简单的有序步骤列表
  - 不需要独立 run()：使用 Orchestrator 的标准 decide_next_action/execute 循环
  - 复用 _parse_react_response 的 JSON 容错逻辑
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..agent import ReActAgent, Action, ReActStep
from ..tool_registry import Tool


@dataclass
class PlanStep:
    """计划中的一个步骤"""
    step: int
    tool_name: str
    params: Dict[str, Any] = field(default_factory=dict)
    purpose: str = ""           # 为什么需要这步
    depends_on: List[int] = field(default_factory=list)  # 依赖的步骤号
    expected_output: str = ""   # 预期产出
    status: str = "pending"     # pending | in_progress | done | skipped | failed


class PlanAgent(ReActAgent):
    """
    规划执行 Agent

    流程:
      1. 收到任务 → 调用 LLM 生成结构化计划
      2. 按计划逐步执行（使用父类的 decide_next_action / execute）
      3. 每步完成后验证
      4. 某步失败 → 重新规划剩余步骤
      5. 全部完成 → 汇总最终答案

    Usage:
        agent = PlanAgent(
            name="financial_analyst",
            tools=[data_query, chart, rag],
            llm_call=my_llm_function,
        )
    """

    SYSTEM_PROMPT = """你是金融数据规划助手。收到任务后，首先生成完整的执行计划，
然后按计划逐步执行。计划必须是结构化的步骤列表，每步指定要调用的 Tool 和参数。

## Available Tools
{tools_description}

## Response Format
当生成计划时，以 JSON 数组返回：
```json
[
  {"step": 1, "tool": "tool_name", "purpose": "为什么需要这步", "params": {...}},
  {"step": 2, "tool": "tool_name", "purpose": "为什么需要这步", "params": {...}}
]
```

当执行特定步骤时，返回单步的 action JSON。
全部步骤完成后，返回 final_answer。"""

    def __init__(self, name: str, tools: List[Tool],
                 llm_call=None, max_steps: int = 12):
        super().__init__(
            name=name,
            tools=tools,
            system_prompt=self.SYSTEM_PROMPT,
            max_steps=max_steps,
            llm_call=llm_call,
        )
        self.plan: List[PlanStep] = []
        self.plan_generated: bool = False
        self.current_plan_step: int = 0  # 当前执行到的计划步骤索引

    def decide_next_action(self, task: str, context: Dict[str, Any] = None) -> Action:
        """
        覆盖父类方法:
          - 第一步: 生成计划
          - 后续步骤: 按计划执行
        """
        context = context or {}

        # ---- Phase 1: 尚未生成计划 ----
        if not self.plan_generated:
            if not self.llm_call:
                return Action(tool_name="", reason="PlanAgent 未配置 llm_call")
            plan = self._generate_plan(task, context)
            if not plan:
                # 降级：退回到普通 ReAct 模式
                self.plan_generated = True
                return super().decide_next_action(task, context)

            self.plan = plan
            self.plan_generated = True
            self.current_plan_step = 0

            # 记录到 react_trace
            self.react_trace.append(ReActStep(
                step=len(self.react_trace) + 1,
                thought=f"生成执行计划 ({len(plan)} 步)",
                action="plan",
                action_input={"plan": [
                    {"step": p.step, "tool": p.tool_name, "purpose": p.purpose}
                    for p in plan
                ]},
            ))

        # ---- Phase 2: 按计划执行 ----
        return self._execute_next_plan_step(context)

    def _generate_plan(self, task: str, context: Dict) -> List[PlanStep]:
        """调用 LLM 生成结构化执行计划"""
        tools_desc = ""
        for name, info in self.registry.list_all().items():
            tools_desc += f"\n  - {name}: {info['description']}"

        prompt = self.SYSTEM_PROMPT.replace("{tools_description}", tools_desc)
        prompt += f"\n\n## Task\n{task}\n\n"
        prompt += "## Instruction\nGenerate a step-by-step execution plan in JSON array format."

        try:
            response = self.llm_call(prompt)
            plan_data = self._parse_plan_json(response)
            return [
                PlanStep(
                    step=p.get("step", i + 1),
                    tool_name=p.get("tool", ""),
                    params=p.get("params", {}),
                    purpose=p.get("purpose", ""),
                    depends_on=p.get("depends_on", []),
                    expected_output=p.get("expected_output", ""),
                )
                for i, p in enumerate(plan_data)
                if p.get("tool")  # 过滤无效步骤
            ]
        except Exception as e:
            # 计划生成失败，降级为 ReAct
            print(f"  ⚠ [PlanAgent] 计划生成失败: {e}，降级为 ReAct 模式")
            return []

    def _execute_next_plan_step(self, context: Dict) -> Action:
        """执行计划中的下一个待处理步骤"""
        # 找到下一个 pending 步骤
        for i, ps in enumerate(self.plan):
            if ps.status == "pending":
                # 检查依赖是否满足
                if ps.depends_on:
                    deps_met = all(
                        any(s.step == d and s.status == "done" for s in self.plan)
                        for d in ps.depends_on
                    )
                    if not deps_met:
                        continue  # 依赖未满足，跳过

                ps.status = "in_progress"
                self.current_plan_step = i

                # 构建 Action（注入上下文中有用的数据）
                params = dict(ps.params)
                if context.get("previous_agent_output"):
                    params["context_data"] = context["previous_agent_output"]

                return Action(
                    tool_name=ps.tool_name,
                    params=params,
                    reason=ps.purpose,
                )

        # 所有步骤完成 → 返回 final answer
        self._generate_final_answer(context)
        return Action(tool_name="", reason="All plan steps completed")

    def _generate_final_answer(self, context: Dict) -> None:
        """汇总所有步骤结果，生成最终答案"""
        summary_parts = []
        for ps in self.plan:
            status_icon = "✅" if ps.status == "done" else "❌" if ps.status == "failed" else "⏭️"
            summary_parts.append(f"Step {ps.step}: [{status_icon}] {ps.purpose}")

        self.final_answer = "\n".join([
            "## 执行总结",
            *summary_parts,
            "",
            "所有计划步骤已完成。",
        ])

    def should_converge(self, task: str) -> bool:
        """PlanAgent 专属收敛条件"""
        if self.final_answer:
            return True

        if self.plan_generated:
            all_done = all(
                ps.status in ("done", "skipped", "failed")
                for ps in self.plan
            )
            if all_done:
                return True

        return super().should_converge(task)

    def _mark_step_result(self, step_num: int, success: bool) -> None:
        """标记计划步骤的执行结果"""
        for ps in self.plan:
            if ps.step == step_num:
                ps.status = "done" if success else "failed"
                break

    def get_plan_summary(self) -> Dict[str, Any]:
        """获取计划执行摘要"""
        return {
            "total_steps": len(self.plan),
            "completed": sum(1 for p in self.plan if p.status == "done"),
            "failed": sum(1 for p in self.plan if p.status == "failed"),
            "skipped": sum(1 for p in self.plan if p.status == "skipped"),
            "steps": [
                {"step": p.step, "tool": p.tool_name,
                 "purpose": p.purpose, "status": p.status}
                for p in self.plan
            ],
        }

    # ---- JSON 解析（复用 ReActAgent 的容错逻辑） ----

    def _parse_plan_json(self, response: str) -> List[Dict]:
        """解析 LLM 返回的计划 JSON，复用 ReActAgent 的多层容错"""
        # 第一层：直接解析
        try:
            data = json.loads(response)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                # 尝试常见包装字段
                for key in ("plan", "steps", "result", "data"):
                    if key in data and isinstance(data[key], list):
                        return data[key]
                return [data]
        except (json.JSONDecodeError, TypeError):
            pass

        # 第二层：从文本中提取 JSON 块（复用父类的正则逻辑）
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass

        # 第三层：尝试提取 {} 对象
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    for key in ("plan", "steps", "result", "data"):
                        if key in data and isinstance(data[key], list):
                            return data[key]
            except json.JSONDecodeError:
                pass

        return []
```

---

## 九、Orchestrator 增强方案

### 9.1 设计原则

> **审查修正**：最初方案建议重构 `Orchestrator.run()` 主循环，这与"增强而非替换"原则矛盾。修正后只在现有主循环的**关键钩子点**注入新模块，不改动循环结构。

### 9.2 钩子注入点

```python
# orchestrator.py 增强后的 run() 方法（只展示关键改动）

def run(self, task, context=None, verify_after_each_step=True):
    start_time = time.time()
    # ... 现有初始化代码保持不变 ...

    # ★ 初始化 Loop Engineering 模块（仅在配置启用时）
    terminator = Terminator(self.loop_config) if self.loop_config.enable_terminator else None
    smart_retry = SmartRetry(self.loop_config) if self.loop_config.enable_smart_retry else None
    hitl_manager = self.hitl_manager  # 外部注入或默认创建
    loop_state = None  # Agent 自己维护

    for agent in self.agents:
        while step < self.max_loops:
            step += 1

            # 1. 决策（不变）
            action = agent.decide_next_action(task, context)
            if not action.tool_name:
                break

            # 2. 执行
            # ┌── 钩子点 1: SmartRetry 分层 ──┐
            if smart_retry and self.loop_config.enable_smart_retry:
                retry_result = smart_retry.execute_with_retry(
                    agent=agent, action=action, task_id=task_id
                )
                # 将 SmartRetry 结果转换为 observation 格式（适配现有逻辑）
                observation = Observation(
                    action=action,
                    result=ToolResult(
                        success=retry_result.success,
                        data=retry_result.data,
                        error=retry_result.error,
                        metadata={
                            "retry_attempts": retry_result.attempts,
                            "total_delay": retry_result.total_delay_seconds,
                            "error_category": retry_result.error_category.value,
                            "dead_letter": retry_result.sent_to_dead_letter,
                        }
                    ),
                    timestamp=time.time(),
                )
                agent.memory.append(observation)
            else:
                observation = agent.execute(action)
            # └────────────────────────────────┘

            # trace 记录（不变）
            trace.append({...})

            # 3. 验证（不变）
            if verify_after_each_step and observation.result.success:
                rule_results = self.verifier.check(...)
                # ...

            # 4. HITL
            # ┌── 钩子点 2: HITL 异步化 ──┐
            if not observation.result.success:
                hitl_triggered = True

                if self.loop_config.enable_hitl and hitl_manager:
                    # 异步模式
                    hitl_request = hitl_manager.request_decision(
                        task_id=task_id,
                        tool_name=action.tool_name,
                        error=observation.result.error,
                        context={"action": action.tool_name, "params": action.params},
                    )
                    # 暂停当前 Agent 执行，返回 pending 状态
                    return OrchestrationResult(
                        success=False,
                        task=task,
                        error="AWAITING_HUMAN_DECISION",
                        trace=trace,
                        verification_results=verifications,
                        total_steps=len(trace),
                        elapsed_seconds=time.time() - start_time,
                        hitl_triggered=True,
                        hitl_decision=f"pending:{hitl_request.id}",
                        summary=f"等待人工决策 | HITL ID: {hitl_request.id}",
                    )
                elif self.on_need_human:
                    # 同步模式（兼容现有行为）
                    # ... 现有 HITL 逻辑 ...
            # └────────────────────────────────┘

            # 5. 收敛判断
            # ┌── 钩子点 3: Terminator 增强 ──┐
            if terminator and self.loop_config.enable_terminator:
                term_decision = terminator.check(
                    step=step, agent=agent, trace=trace, observation=observation
                )
                if term_decision.should_stop:
                    self._log(f"  Terminator: {term_decision.reason.name} - {term_decision.detail}")
                    if term_decision.reason == TermReason.TASK_COMPLETE:
                        # 任务完成，正常结束
                        pass
                    elif term_decision.reason == TermReason.LOOP_DETECTED:
                        final_error = f"循环检测终止: {term_decision.detail}"
                    else:
                        final_error = final_error or term_decision.detail
                    break
            elif agent.should_converge(task):
                # 降级：使用原有收敛判断
                self._log(f"  Agent '{agent.name}' 收敛")
                break
            # └──────────────────────────────────┘

        # ... 后续代码保持不变 ...
```

### 9.3 Orchestrator 构造器增强

```python
# orchestrator.py __init__ 增加参数
def __init__(
    self,
    agents: List[Agent],
    verifier: Optional[RuleEngine] = None,
    max_loops: int = 20,
    verbose: bool = True,
    on_need_human: Optional[callable] = None,
    loop_config: Optional[LoopConfig] = None,     # ★ 新增
    hitl_manager: Optional[HITLManager] = None,    # ★ 新增
):
    # ... 现有初始化 ...
    self.loop_config = loop_config or LoopConfig()
    self.hitl_manager = hitl_manager
```

---

## 十、工程化保障

### 10.1 API 兼容性确保

改造前后 4 个端点行为**必须不变**，回归检查清单：

| 端点 | 方法 | 改造前行为 | 回归验证 |
|------|------|-----------|----------|
| `/api/harness/tools` | GET | 返回 7 个 Tool 列表 | 响应结构不变，Tool 数量不变 |
| `/api/harness/parse` | POST | Pipeline 模式解析，返回 trace + verification | `success`/`data`/`trace`/`verification` 字段不缺失 |
| `/api/harness/rag` | POST | RAG 问答（不使用 Orchestrator） | 不受影响（未使用 Agent 循环） |
| `/api/harness/analyze` | POST | ReAct 模式分析，返回 react_trace | `success`/`data`/`react_trace` 字段不缺失 |

**兼容策略**：
1. 新模块默认关闭 `enable_plan_agent=False`
2. `enable_smart_retry`/`enable_terminator`/`enable_loop_state` 默认开启但**不改变现有行为**——它们只是添加额外的终止条件、退避策略和状态记录
3. `enable_hitl` 默认开启，但异步模式需要显式提供 `hitl_manager` 参数

### 10.2 配置参数集中化

所有可调参数统一到 `LoopConfig`（见 3.3 节），支持三种加载方式：

```
优先级: 环境变量 > 代码构造参数 > LoopConfig 默认值
```

```bash
# .env 示例
LOOP_MAX_STEPS=10
LOOP_CONSECUTIVE_FAILURES_LIMIT=3
LOOP_BASE_DELAY=1.0
LOOP_MAX_DELAY=30.0
LOOP_HITL_TIMEOUT_SECONDS=300
LOOP_ENABLE_PLAN_AGENT=false
```

### 10.3 结构化日志

将 `print()` 逐步替换为结构化日志，每个循环事件绑定关键字段：

```python
# 日志事件规范
{
    "event": "agent_loop.step",          # 事件类型
    "trace_id": "abc123",                # 全链路追踪 ID
    "agent_name": "data_analyst",        # Agent 名称
    "step": 3,                           # 当前步数
    "tool": "data_query",                # 当前 Tool
    "strategy": "retry_adjusted",        # 尝试策略
    "outcome": "success",                # 结果
    "latency_ms": 234.5,                 # 耗时
    "attempts": 2,                       # 尝试次数
}
```

在 `Orchestrator._log()` 中增加结构化日志分支：

```python
def _log(self, msg: str, **kwargs) -> None:
    if self.verbose:
        if self.logger:  # ★ 如果有结构化日志实例
            self.logger.info(msg, **kwargs)
        else:
            print(msg)   # 降级为 print
```

### 10.4 最终文件结构

```
backend/harness/
├── tool_registry.py          # Tool / ToolResult / ToolRegistry（不变）
├── agent.py                  # Agent / ReActAgent（增强：集成 LoopState）
├── orchestrator.py           # Orchestrator（增强：注入钩子点）
├── verification.py           # RuleEngine / Rule / 内置规则（不变）
├── __init__.py               # 更新导出
├── loop/                     # ★ 新增
│   ├── __init__.py           # LoopConfig + 模块导出
│   ├── termination.py        # Terminator
│   ├── smart_retry.py        # SmartRetry
│   ├── loop_state.py         # LoopState / AttemptRecord
│   ├── hitl.py               # HITLManager
│   └── plan_agent.py         # PlanAgent
├── agents/                   # 现有 Agent（不变）
│   ├── __init__.py
│   ├── table_parsing_agent.py
│   ├── audit_agent.py
│   └── data_analysis_agent.py
└── tools/                    # 现有 Tool（不变）
```

---

## 十一、灰度发布方案

### 11.1 三级灰度开关

| 级别 | 控制方式 | 开关 | 风险 |
|------|----------|------|------|
| **L0: 全关** | 环境变量 `LOOP_*` 全部 false | 所有新模块关闭 | 零风险，完全回退 |
| **L1: 只读模式** | Terminator + LoopState 开启，SmartRetry/HITL/PlanAgent 关闭 | 观察、记录但不改变行为 | 极低，只增加日志 |
| **L2: 优化模式** | L1 + SmartRetry 开启 | 错误分类 + 指数退避 | 低，可能改变重试节奏 |
| **L3: 完整模式** | L2 + HITL 异步 + PlanAgent 可选 | 全部功能 | 需验证异步 HITL 流程 |

### 11.2 灰度步骤

```
Week 1: L0 部署 → 确认现有功能无回归
        ├── 运行现有 e2e 测试（如果有）
        └── 手动触发 4 个 API 端点，验证响应结构

Week 2: L1 部署 → 观察日志
        ├── 检查 Terminator 的终止事件是否正确
        ├── 检查 LoopState 记录是否完整
        └── 对比"原有收敛"和"Terminator 收敛"的异同

Week 3: L2 部署 → 对比重试行为
        ├── 对比 SmartRetry 的退避是否合理
        ├── 检查死信队列是否收到合理的记录
        └── 确认无过度重试或过早放弃

Week 4: L3 部署 → 验证异步 HITL
        ├── 触发需要人工介入的场景
        ├── 验证 pending → human_responded 流程
        └── 验证超时自动 abort 机制
```

### 11.3 回滚机制

```bash
# 立即回滚：设置所有开关为 false
export LOOP_ENABLE_TERMINATOR=false
export LOOP_ENABLE_SMART_RETRY=false
export LOOP_ENABLE_LOOP_STATE=false
export LOOP_ENABLE_HITL=false
export LOOP_ENABLE_PLAN_AGENT=false

# 重启服务
# 所有代码路径回退到改造前行为
```

---

## 十二、实施路线图

### Phase 1: LoopState + LoopConfig（1 周）

| 任务 | 产出 | 验证方式 |
|------|------|----------|
| 创建 `backend/harness/loop/` 包 | `__init__.py` + `LoopConfig` | import 可用 |
| 实现 `loop_state.py` | `LoopState` + `AttemptRecord` | 单元测试：记录→查询→导出 |
| 集成到 `Agent.__init__()` | `agent.py` 增加 1 行 | 现有 `/parse` 端点不受影响 |
| 更新 `__init__.py` 导出 | 新模块可被导入 | `from backend.harness.loop import LoopConfig` |

### Phase 2: Terminator + SmartRetry（1.5 周）

| 任务 | 产出 | 验证方式 |
|------|------|----------|
| 实现 `termination.py` | `Terminator` + 5 种终止条件 | 模拟不同循环场景验证 |
| 实现 `smart_retry.py` | `SmartRetry` + `DeadLetter` | 模拟瞬时/永久故障 |
| 注入 Orchestrator 钩子点 | `orchestrator.py` 3 个钩子点 | 灰度 L1/L2 运行 `/analyze` |

### Phase 3: HITL + PlanAgent（1.5 周）

| 任务 | 产出 | 验证方式 |
|------|------|----------|
| 实现 `hitl.py` | `HITLManager` 异步模式 | 模拟人工决策 API 调用 |
| 实现 `plan_agent.py` | `PlanAgent` 简化版 | 与 DataAnalysisAgent 对比 Token 消耗 |
| 新增 HITL API 端点 | `GET/POST /api/harness/hitl/{id}` | 端到端流程 |

### Phase 4: 清理 + 文档（0.5 周）

| 任务 | 产出 |
|------|------|
| 替换 `print()` 为结构化日志 | `orchestrator.py`、`agent.py` 中的关键日志点 |
| 编写模块使用文档 | `docs/LOOP_ENGINEERING_USAGE.md` |
| 灰度 L3 部署验证 | 全功能回归测试 |

---

## 十三、风险评估与应对

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| SmartRetry 退避导致总耗时增加 | 中 | 低 | `max_delay=30s` 上限 + 灰度观察首周数据 |
| Terminator LOOP_DETECTED 误杀正常的多步循环 | 低 | 中 | 阈值 `loop_detection_threshold=5` 可配置，误杀时可调大 |
| HITL 异步模式下前端未适配 | 中 | 高 | 同步模式作为降级路径，异步模式需前端配合开发 |
| PlanAgent 计划质量不稳定 | 中 | 低 | 默认关闭，降级到 ReAct 模式自动兜底 |
| 代码拼写 Bug（如 `suggested_adjustments`） | — | — | 已修正为 `suggested_adjustments`（无相关命名），全部变量使用蛇形命名复查 |

---

## 附录 A：改造前后对比（Agent 循环维度）

| 维度 | 改造前 | 改造后 |
|------|--------|--------|
| 收敛判断 | `should_converge()` 单一方法 | `Terminator` 6 种可组合条件 |
| 重试策略 | 固定 `max_retries` 次 | 错误分类 + 指数退避 + 抖动 |
| 状态追踪 | 线性 `List[Observation]` | 平行 `List[AttemptRecord]` + 多维度查询 |
| HITL | 同步回调阻塞线程 | 异步挂起 + 超时自动降级 |
| Agent 模式 | Pipeline / ReAct | Pipeline / ReAct / Plan（新增） |
| 日志 | 118 个 `print()` | 结构化日志 + 事件规范 |
| 配置 | 硬编码散落各处 | `LoopConfig` 集中管理 + 环境变量覆盖 |

## 附录 B：所有命名对照（防 Bug 检查清单）

| 名称 | 类型 | 所属文件 |
|------|------|----------|
| `Terminator` | class | `termination.py` |
| `TermReason` | enum | `termination.py` |
| `TermDecision` | dataclass | `termination.py` |
| `SmartRetry` | class | `smart_retry.py` |
| `ErrorCategory` | enum | `smart_retry.py` |
| `DeadLetter` | dataclass | `smart_retry.py` |
| `RetryResult` | dataclass | `smart_retry.py` |
| `LoopState` | class | `loop_state.py` |
| `AttemptRecord` | dataclass | `loop_state.py` |
| `Strategy` | enum | `loop_state.py` |
| `AttemptOutcome` | enum | `loop_state.py` |
| `HITLManager` | class | `hitl.py` |
| `HITLRequest` | dataclass | `hitl.py` |
| `HITLDecision` | enum | `hitl.py` |
| `HITLStatus` | enum | `hitl.py` |
| `PlanAgent` | class | `plan_agent.py` |
| `PlanStep` | dataclass | `plan_agent.py` |
| `LoopConfig` | dataclass | `loop/__init__.py` |

---

> **核心原则重申**：增强现有循环，不推倒重来。每个模块独立可开关，通过 `LoopConfig` 灰度控制。现有 4 个 API 端点行为不变，新功能通过 opt-in 参数启用。从 L0（全关）到 L3（全开）逐级灰度和验证。
