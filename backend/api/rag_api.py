# backend/api/rag_api.py
"""
RAG API Blueprint

端点：
  POST /api/rag/build-index    - 为指定文档构建 FAISS 索引
  POST /api/rag/query          - 提交自然语言问题并获取答案
  GET  /api/rag/stats          - 获取索引统计信息
  GET  /api/rag/documents      - 获取可用文档列表
"""

import logging
from flask import Blueprint, request, jsonify

from backend.services.rag_service import get_rag_pipeline

logger = logging.getLogger(__name__)

rag_bp = Blueprint("rag", __name__, url_prefix="/api/rag")


@rag_bp.route("/build-index", methods=["POST"])
def build_index():
    """为指定 PDF 文档构建 FAISS 索引

    Body (JSON):
        pdf_path: str  - PDF 文件的绝对路径（必填）
        rebuild: bool  - 是否强制重建（可选，默认 false）

    Returns:
        { success, document, chunk_count, vector_count, elapsed_seconds }
    """
    data = request.get_json(silent=True) or {}
    pdf_path = data.get("pdf_path", "").strip()
    rebuild = data.get("rebuild", False)

    if not pdf_path:
        return jsonify({"success": False, "error": "缺少 pdf_path 参数"}), 400

    import os
    if not os.path.exists(pdf_path):
        return jsonify({"success": False, "error": f"文件不存在: {pdf_path}"}), 404

    pipeline = get_rag_pipeline()

    # 如果已有索引且不强制重建，先尝试加载
    if not rebuild:
        doc_name = os.path.basename(pdf_path)
        if pipeline.load_index(doc_name):
            stats = pipeline.get_stats()
            return jsonify({
                "success": True,
                "message": "索引已存在，直接加载",
                "document": doc_name,
                "total_vectors": stats["total_vectors"]
            })

    result = pipeline.build_index(pdf_path)
    if result["success"]:
        return jsonify(result)
    return jsonify(result), 500


@rag_bp.route("/query", methods=["POST"])
def query():
    """提交自然语言问题，执行 RAG 检索 + LLM 生成

    Body (JSON):
        question: str        - 用户问题（必填）
        document: str        - 指定文档名（可选，默认使用当前索引）
        top_k: int           - 召回数量（可选，默认5）

    Returns:
        { success, question, answer, sources, retrieval_time_ms, answer_time_ms, total_time_ms }
    """
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    document = data.get("document", "").strip()
    top_k = int(data.get("top_k", 5))

    if not question:
        return jsonify({"success": False, "error": "缺少 question 参数"}), 400

    pipeline = get_rag_pipeline()

    # 如果指定了文档，尝试切换索引
    if document:
        if not pipeline.load_index(document):
            return jsonify({
                "success": False,
                "error": f"文档 '{document}' 的索引不存在，请先构建索引"
            }), 404

    if pipeline.index_mgr is None or pipeline.index_mgr.index is None:
        return jsonify({
            "success": False,
            "error": "未加载任何索引，请先构建索引"
        }), 400

    result = pipeline.query_with_answer(question, top_k=top_k)
    if result["success"]:
        return jsonify(result)
    return jsonify(result), 500


@rag_bp.route("/documents", methods=["GET"])
def list_documents():
    """获取可构建索引的 PDF 文档列表

    Returns:
        { success, documents: [{ name, path, size }] }
    """
    pipeline = get_rag_pipeline()
    docs = pipeline.loader.get_available_documents()
    return jsonify({"success": True, "documents": docs})


@rag_bp.route("/stats", methods=["GET"])
def get_stats():
    """获取当前 RAG 索引的统计信息

    Returns:
        { success, stats: { has_index, total_vectors, index_type, dimension,
                           nlist, nprobe, saved_indices, current_document } }
    """
    pipeline = get_rag_pipeline()
    stats = pipeline.get_stats()
    return jsonify({"success": True, "stats": stats})
