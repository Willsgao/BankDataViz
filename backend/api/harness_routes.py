"""
Harness API 路由

提供 Agent 驱动的文档解析、RAG 问答等接口。

端点:
  POST /api/harness/parse      Agent 驱动的文档解析
  GET  /api/harness/tools      列出所有可用工具
  POST /api/harness/rag        RAG 智能问答
"""

from flask import Blueprint, request, jsonify

from harness import Orchestrator, RuleEngine
from harness.verification import NotNullRule, ColumnConsistencyRule, TableCountRule

from backend.harness.agents.table_parsing_agent import TableParsingAgent
from backend.harness.tools.rag_tool import RAGTool

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
