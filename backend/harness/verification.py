"""
可插拔验证规则引擎

提供规则注册、执行、结果收集的标准化机制。

内置规则:
  - not_null: 数据不为空
  - column_consistency: 表格列数一致性检查
  - value_range: 数值范围检查

Usage:
    engine = RuleEngine()
    engine.register(NotNullRule())
    engine.register(ColumnConsistencyRule())
    results = engine.check("rebuild", data={"columns": 5, "rows": 100}, context={})
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RuleResult:
    """单条规则的验证结果"""
    rule_name: str
    passed: bool
    message: str = ""
    detail: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule_name,
            "passed": self.passed,
            "message": self.message,
            "detail": self.detail,
        }


class Rule:
    """
    验证规则基类

    子类只需实现 check() 方法。

    Usage:
        class ColumnConsistencyRule(Rule):
            name = "column_consistency"
            description = "验证表格列数在全文中一致"
            applies_to = ["rebuild"]

            def check(self, data, context) -> RuleResult:
                columns = data.get("columns", 0)
                if columns > 0:
                    return RuleResult(rule_name=self.name, passed=True)
                return RuleResult(rule_name=self.name, passed=False, message="列数为0")
    """

    name: str = ""
    description: str = ""
    applies_to: List[str] = field(default_factory=list)  # 适用的 Tool 名称列表，空=全局

    def check(self, data: Any, context: Dict[str, Any]) -> RuleResult:
        """执行验证。data 是 Tool 的输出，context 是全局上下文。"""
        raise NotImplementedError(f"Rule '{self.name}' must implement check()")


class RuleEngine:
    """
    可插拔验证规则引擎

    - 注册/卸载规则
    - 按 Tool 名称过滤执行
    - 收集所有规则的验证结果
    """

    def __init__(self):
        self._rules: List[Rule] = []

    def register(self, rule: Rule) -> None:
        """注册一条验证规则"""
        if not rule.name:
            raise ValueError("Rule must have a non-empty name")
        self._rules.append(rule)

    def unregister(self, rule_name: str) -> None:
        """按名称卸载规则"""
        self._rules = [r for r in self._rules if r.name != rule_name]

    def list_rules(self) -> List[Dict[str, Any]]:
        """列出所有已注册规则"""
        return [
            {"name": r.name, "description": r.description, "applies_to": r.applies_to}
            for r in self._rules
        ]

    def check(
        self,
        tool_name: str,
        data: Any,
        context: Dict[str, Any],
    ) -> List[RuleResult]:
        """
        对指定 Tool 的输出执行所有适用的验证规则。

        Args:
            tool_name: 当前执行的 Tool 名称
            data: Tool 的输出数据
            context: 全局上下文（包含之前步骤的结果）

        Returns:
            所有适用的规则的验证结果列表
        """
        results = []
        for rule in self._rules:
            # 过滤：规则有 applies_to 且不包含当前 tool_name → 跳过
            if rule.applies_to and tool_name not in rule.applies_to:
                continue
            try:
                result = rule.check(data, context)
            except Exception as e:
                result = RuleResult(
                    rule_name=rule.name,
                    passed=False,
                    message=f"规则执行异常: {str(e)}",
                )
            results.append(result)
        return results


# ============================================================
# 内置通用规则
# ============================================================

class NotNullRule(Rule):
    """数据不为空"""
    name = "not_null"
    description = "验证输出数据不为空"
    applies_to = []  # 全局适用

    def check(self, data: Any, context: Dict[str, Any]) -> RuleResult:
        if data is None:
            return RuleResult(rule_name=self.name, passed=False, message="数据为空")
        if isinstance(data, (list, dict, str)) and len(data) == 0:
            return RuleResult(rule_name=self.name, passed=False, message="数据为空容器")
        return RuleResult(rule_name=self.name, passed=True)


class ColumnConsistencyRule(Rule):
    """表格列数检查"""
    name = "column_consistency"
    description = "验证表格列数非零且合理"
    applies_to = ["rebuild", "llm_analysis"]

    def check(self, data: Any, context: Dict[str, Any]) -> RuleResult:
        columns = None
        if isinstance(data, dict):
            columns = data.get("columns") or data.get("col_count")
        if columns is None:
            return RuleResult(rule_name=self.name, passed=True, message="无列数信息，跳过")
        if not isinstance(columns, (int, float)):
            return RuleResult(rule_name=self.name, passed=False, message=f"列数类型异常: {type(columns)}")
        if columns <= 0:
            return RuleResult(rule_name=self.name, passed=False, message="列数为0或负数")
        if columns > 100:
            return RuleResult(rule_name=self.name, passed=False, message=f"列数异常大: {columns}")
        return RuleResult(rule_name=self.name, passed=True)


class TableCountRule(Rule):
    """检查识别到的表格数量"""
    name = "table_count"
    description = "验证至少识别到1个表格"
    applies_to = ["ocr", "table_detection"]

    def check(self, data: Any, context: Dict[str, Any]) -> RuleResult:
        count = None
        if isinstance(data, dict):
            count = data.get("table_count") or data.get("tables_count")
        if count is not None and count == 0:
            return RuleResult(rule_name=self.name, passed=False, message="未识别到任何表格")
        return RuleResult(rule_name=self.name, passed=True)
