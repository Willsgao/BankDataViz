"""
Chart Tool —— 生成 ECharts 图表配置 JSON

支持图表类型：
  - line: 折线图（趋势分析）
  - bar: 柱状图（多银行对比）
  - pie: 饼图（分布分析）

返回的 option 可直接由前端 ECharts 实例渲染，无需二次处理。

Usage:
    tool = ChartTool()
    result = tool.execute(
        chart_type="line",
        title="工商银行 净利润趋势",
        x_data=["2020", "2021", "2022", "2023", "2024"],
        series=[{"name": "净利润", "data": [3159, 3483, 3604, 3639, 3658]}]
    )
"""

from typing import Any, Dict, List

from harness.tool_registry import Tool, ToolResult


class ChartTool(Tool):
    name = "generate_chart"
    description = (
        "生成 ECharts 图表配置 JSON。支持 line(折线图)、bar(柱状图)、pie(饼图)。"
        "传入 title, x_data/y_data, series 即可自动生成完整的 ECharts option。"
    )
    input_schema = {
        "chart_type": "str  (line | bar | pie)",
        "title": "str  图表标题",
        "x_data": "list[str]  X 轴数据（折线图/柱状图）",
        "y_data": "list[float]  Y 轴数据（单系列简写）",
        "series": "list[dict]  多系列数据 [{name, data}]",
        "data": "list[dict]  饼图数据 [{name, value}]",
    }

    # 图表配色方案
    COLORS = [
        "#409eff", "#67c23a", "#e6a23c", "#f56c6c", "#909399",
        "#b37feb", "#36cfc9", "#ff85c0", "#ffc069", "#95de64",
    ]

    def execute(self, chart_type: str = "line", **kwargs) -> ToolResult:
        try:
            title = kwargs.get("title", "图表")
            x_data = kwargs.get("x_data", [])
            y_data = kwargs.get("y_data")
            series = kwargs.get("series")
            pie_data = kwargs.get("data")

            option = {
                "title": {"text": title, "left": "center", "textStyle": {"fontSize": 16}},
                "tooltip": {"trigger": "axis" if chart_type != "pie" else "item"},
                "color": self.COLORS,
            }

            if chart_type in ("line", "bar"):
                option["xAxis"] = {"type": "category", "data": x_data}
                option["yAxis"] = {"type": "value"}

                if series:
                    option["series"] = [
                        {
                            "name": s.get("name", ""),
                            "type": chart_type,
                            "data": s.get("data", []),
                            "smooth": chart_type == "line",
                        }
                        for s in series
                    ]
                elif y_data:
                    option["series"] = [{"name": title, "type": chart_type, "data": y_data, "smooth": chart_type == "line"}]

            elif chart_type == "pie":
                option["tooltip"] = {"trigger": "item", "formatter": "{b}: {c} ({d}%)"}
                option["series"] = [{
                    "type": "pie",
                    "radius": "60%",
                    "data": pie_data or [{"name": k, "value": v} for k, v in kwargs.items() if isinstance(v, (int, float))],
                }]

            else:
                return ToolResult(success=False, error=f"不支持的图表类型: {chart_type}")

            option["grid"] = {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True}

            return ToolResult(success=True, data={"chart_option": option, "chart_type": chart_type})

        except Exception as e:
            return ToolResult(success=False, error=str(e))
