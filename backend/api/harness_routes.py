"""
Harness API 路由

提供 Agent 驱动的文档解析、RAG 问答、智能数据分析等接口。

端点:
  GET  /api/harness/tools      列出所有可用工具
  POST /api/harness/parse      Agent 驱动的端到端表格解析
  POST /api/harness/rag        RAG 智能问答
  POST /api/harness/analyze    ReAct 智能数据分析（自然语言驱动多 Tool 协作）
"""

from flask import Blueprint, request, jsonify

from backend.harness import Orchestrator, RuleEngine
from harnessloop.verification import NotNullRule, ColumnConsistencyRule, TableCountRule

from backend.harness import TableParsingAgent, DataAnalysisAgent
from backend.harness.tools.rag_tool import RAGTool
from backend.configs.llm_config import RAG_API_KEY, RAG_BASE_URL, RAG_MODEL_ID

# =============================================================================
# 蓝图
# =============================================================================
harness_bp = Blueprint("harness", __name__, url_prefix="/api/harness")


# =============================================================================
# 全局资源（延迟初始化）
# =============================================================================
_parsing_agent = None
_verifier = None


def get_parsing_agent() -> TableParsingAgent:
    global _parsing_agent
    if _parsing_agent is None:
        _parsing_agent = TableParsingAgent()
    return _parsing_agent


def get_verifier() -> RuleEngine:
    global _verifier
    if _verifier is None:
        _verifier = RuleEngine()
        _verifier.register(NotNullRule())
        _verifier.register(ColumnConsistencyRule())
        _verifier.register(TableCountRule())
    return _verifier


# =============================================================================
# 路由
# =============================================================================


@harness_bp.route("/tools", methods=["GET"])
def list_tools():
    """列出所有已注册的工具"""
    agent = get_parsing_agent()
    tools = agent.registry.list_all()
    return jsonify({"success": True, "tools": tools, "count": len(tools)})


@harness_bp.route("/parse", methods=["POST"])
def agent_parse():
    """
    Agent 驱动的端到端表格解析

    Request JSON:
        {
            "image_path": "/path/to/page.png",
            "output_file": "/path/to/output.xlsx",   // 可选
            "bank_name": "建设银行"                     // 可选
        }

    Response:
        {
            "success": true,
            "data": {...},
            "trace": [...],
            "verification": [...],
            "summary": "..."
        }
    """
    data = request.get_json(silent=True) or {}
    image_path = data.get("image_path", "")
    output_file = data.get("output_file")
    bank_name = data.get("bank_name", "")

    if not image_path:
        return jsonify({"success": False, "error": "缺少 image_path 参数"}), 400

    context = {
        "image_path": image_path,
        "output_file": output_file,
        "bank_name": bank_name,
    }

    agent = get_parsing_agent()
    verifier = get_verifier()

    orchestrator = Orchestrator(
        agents=[agent],
        verifier=verifier,
        max_loops=20,
    )

    result = orchestrator.run(
        task=f"解析图片表格: {image_path}",
        context=context,
        verify_after_each_step=True,
    )

    return jsonify(result.to_dict())


@harness_bp.route("/rag", methods=["POST"])
def agent_rag():
    """
    RAG 智能问答

    Request JSON:
        {
            "question": "建设银行2024年净利润是多少？",
            "top_k": 5
        }

    Response:
        {
            "success": true,
            "data": {"answer": "...", "sources": [...]}
        }
    """
    data = request.get_json(silent=True) or {}
    question = data.get("question", "")
    top_k = data.get("top_k", 5)

    if not question:
        return jsonify({"success": False, "error": "缺少 question 参数"}), 400

    rag_tool = RAGTool()
    result = rag_tool.execute(question=question, top_k=top_k)

    return jsonify({
        "success": result.success,
        "data": result.data,
        "error": result.error,
    })


# =============================================================================
# LLM 调用函数（供 ReActAgent 使用）
# =============================================================================

def _react_llm_call(prompt: str) -> str:
    """ReActAgent 的 LLM 推理回调，复用 DeepSeek API"""
    from openai import OpenAI

    client = OpenAI(base_url=RAG_BASE_URL, api_key=RAG_API_KEY)
    response = client.chat.completions.create(
        model=RAG_MODEL_ID,
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Always respond in valid JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=2000,
    )
    return response.choices[0].message.content or ""


# =============================================================================
# /analyze —— ReAct 智能数据分析
# =============================================================================

@harness_bp.route("/analyze", methods=["POST"])
def agent_analyze():
    """
    ReAct Agent 驱动的智能数据分析

    Request JSON:
        {
            "question": "比较工商银行和建设银行 2020-2024 的净利润趋势"
        }

    Response:
        {
            "success": true,
            "data": {"answer": "...", "steps": [...]},
            "trace": [...],
            "react_trace": [...],     // ReAct 推理链
            "verification": [...],
            "summary": "..."
        }
    """
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"success": False, "error": "缺少 question 参数"}), 400

    agent = DataAnalysisAgent(llm_call=_react_llm_call, max_steps=8)

    orchestrator = Orchestrator(
        agents=[agent],
        verifier=RuleEngine(),
        max_loops=20,
    )

    result = orchestrator.run(
        task=question,
        context={},
        verify_after_each_step=False,  # ReAct 模式不每步校验（由 LLM 自主判断）
    )

    return jsonify(result.to_dict())
