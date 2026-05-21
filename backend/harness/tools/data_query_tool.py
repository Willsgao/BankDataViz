"""
DataQuery Tool —— 封装 BankDataService，供 Agent 查询银行数据

支持的查询类型：
  - list_banks: 列出所有银行
  - search_banks: 按关键字搜索银行
  - get_trend: 获取单个指标的趋势数据
  - compare_banks: 多银行单指标对比
  - get_statistics: 获取数据仓库统计

Usage:
    tool = DataQueryTool()
    result = tool.execute(query_type="list_banks")
    result = tool.execute(query_type="get_trend", bank_id=1, indicator_name="净利润")
"""

from typing import Any, Dict

from harness.tool_registry import Tool, ToolResult

from backend.services.bank_data_service import BankDataService


class DataQueryTool(Tool):
    name = "data_query"
    description = "查询银行财务数据库：列出银行、搜索银行、查询指标趋势、多银行对比、获取统计信息"
    input_schema = {
        "query_type": "str  (list_banks | search_banks | get_trend | compare_banks | get_statistics)",
        "bank_id": "int  (可选)",
        "bank_ids": "list[int]  (可选)",
        "indicator_name": "str  (可选，如'净利润'、'营业收入'、'总资产')",
        "keyword": "str  (可选，搜索关键字)",
        "year": "int  (可选，指定年份)",
    }

    def __init__(self):
        self._service = None

    @property
    def service(self) -> BankDataService:
        if self._service is None:
            self._service = BankDataService()
        return self._service

    def execute(self, query_type: str = "list_banks", **kwargs) -> ToolResult:
        try:
            if query_type == "list_banks":
                banks = self.service.get_all_banks(status="active")
                names = [{"id": b["id"], "name": b["bank_name"], "code": b.get("bank_code", ""), "type": b.get("bank_type", "")} for b in banks]
                return ToolResult(success=True, data={"banks": names, "count": len(names)})

            elif query_type == "search_banks":
                keyword = kwargs.get("keyword", "")
                banks = self.service.search_banks(keyword)
                names = [{"id": b["id"], "name": b["bank_name"], "code": b.get("bank_code", "")} for b in banks]
                return ToolResult(success=True, data={"banks": names, "count": len(names)})

            elif query_type == "get_trend":
                bank_id = kwargs.get("bank_id", 1)
                indicator = kwargs.get("indicator_name", "净利润")
                result = self.service.get_indicator_trend(bank_id, indicator)
                return ToolResult(success=True, data=result)

            elif query_type == "compare_banks":
                bank_ids = kwargs.get("bank_ids", [1, 2])
                indicator = kwargs.get("indicator_name", "净利润")
                year = kwargs.get("year")
                result = self.service.get_multiple_banks_indicator(bank_ids, indicator, year)
                return ToolResult(success=True, data=result)

            elif query_type == "get_statistics":
                stats = self.service.get_bank_statistics()
                return ToolResult(success=True, data=stats)

            else:
                return ToolResult(success=False, error=f"不支持的查询类型: {query_type}")

        except Exception as e:
            return ToolResult(success=False, error=str(e))
