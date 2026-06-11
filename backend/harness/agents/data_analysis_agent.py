"""
智能数据分析 Agent（ReAct 模式）

持有 DataQuery + Chart + RAG 三个 Tool，
通过 LLM 动态推理完成自然语言数据分析任务。

典型流程：
  用户: "比较工商银行和建设银行 2020-2024 的净利润趋势"
  → Think: 需要先查银行列表，找到工行和建行的 ID
  → Action: data_query (list_banks)
  → Observe: [{id:1, name:"工商银行"}, {id:2, name:"建设银行"}, ...]
  → Think: 拿到银行 ID 了，现在查净利润对比数据
  → Action: data_query (compare_banks, bank_ids=[1,2], indicator_name="净利润")
  → Observe: {工商银行: {2020:3159,...}, 建设银行: {2020:2710,...}}
  → Think: 数据拿到了，生成对比折线图
  → Action: generate_chart (line, "工行 vs 建行 净利润趋势", ...)
  → Observe: {chart_option: {...}}
  → Think: 图表已生成，给出总结
  → Final Answer: "2020-2024年间，工商银行净利润从3159亿增长至3658亿..."

Usage:
    from backend.harness.tools.data_query_tool import DataQueryTool
    from backend.harness.tools.chart_tool import ChartTool
    from backend.harness.tools.rag_tool import RAGTool

    agent = DataAnalysisAgent(llm_call=my_llm_function)
"""

from typing import Any, Dict

from ..agent import ReActAgent

from backend.harness.tools.data_query_tool import DataQueryTool
from backend.harness.tools.chart_tool import ChartTool
from backend.harness.tools.rag_tool import RAGTool


class DataAnalysisAgent(ReActAgent):
    """
    智能数据分析 Agent

    组合 DataQuery + Chart + RAG 三大能力，
    通过 ReAct 推理动态决定调用顺序。
    """

    SYSTEM_PROMPT = """你是金融数据分析助手，可以访问以下能力：
1. data_query: 查询银行数据库（列出银行、查指标趋势、多银行对比）
2. generate_chart: 生成 ECharts 图表配置（折线图/柱状图/饼图）
3. rag_search: 检索文档库中的相关资料

工作原则：
- 先理解用户意图，再决定调用哪个 Tool
- 数据查询和图表生成要配合使用
- 如果用户只问数据，给出数据即可；如果要求可视化，先生成图表配置
- 每步只调用一个 Tool，观察结果后再决定下一步
- 拿到足够信息后，给出简洁明了的最终回答
- 如无匹配数据，诚实告知用户"""

    def __init__(self, name: str = "data_analyst", llm_call=None, max_steps: int = 8):
        tools = [
            DataQueryTool(),
            ChartTool(),
            RAGTool(),
        ]
        super().__init__(
            name=name,
            tools=tools,
            system_prompt=self.SYSTEM_PROMPT,
            max_retries=2,
            max_steps=max_steps,
            llm_call=llm_call,
        )
