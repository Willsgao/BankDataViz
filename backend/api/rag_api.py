# backend/api/rag_api.py
"""
RAG API Blueprint

端点：
  POST /api/rag/build-index    - 为指定文档构建 FAISS 索引
  POST /api/rag/query          - 提交自然语言问题并获取答案
  POST /api/rag/query-stream   - 提交问题，SSE 流式返回答案（支持多轮对话）
  POST /api/rag/clear-history  - 清除指定会话的对话历史
  GET  /api/rag/stats          - 获取索引统计信息
  GET  /api/rag/documents      - 获取可用文档列表
"""

import json
import logging
from flask import Blueprint, request, jsonify, Response, stream_with_context

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
        session_id: str      - 会话ID（可选，用于多轮对话记忆）

    Returns:
        { success, question, answer, sources, retrieval_time_ms, answer_time_ms, total_time_ms }
    """
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    document = data.get("document", "").strip()
    top_k = int(data.get("top_k", 5))
    session_id = data.get("session_id", "").strip()

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

    result = pipeline.query_with_answer(question, top_k=top_k, session_id=session_id)
    if result["success"]:
        return jsonify(result)
    return jsonify(result), 500


@rag_bp.route("/query-stream", methods=["POST"])
def query_stream():
    """提交自然语言问题，SSE 流式返回 RAG 检索 + LLM 生成结果

    Body (JSON):
        question: str        - 用户问题（必填）
        document: str        - 指定文档名（可选，默认使用当前索引）
        top_k: int           - 召回数量（可选，默认5）
        session_id: str      - 会话ID（可选，用于多轮对话记忆，不传自动生成）

    SSE 事件格式：
        data: {"type":"token","content":"..."}    — 逐 token 推送
        data: {"type":"done","sources":[...]}      — 生成完成 + 来源引用
        data: {"type":"error","message":"..."}     — 错误信息
        data: [DONE]                               — 流结束
    """
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    document = data.get("document", "").strip()
    top_k = int(data.get("top_k", 5))
    session_id = data.get("session_id", "").strip()

    if not question:
        def _error_stream(msg):
            yield f"data: {json.dumps({'type': 'error', 'message': msg}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        return Response(
            stream_with_context(_error_stream("缺少 question 参数")),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive"
            }
        )

    pipeline = get_rag_pipeline()

    if document:
        if not pipeline.load_index(document):
            def _err_no_doc():
                err_msg = "文档 '{}' 的索引不存在，请先构建索引".format(document)
                yield f"data: {json.dumps({'type': 'error', 'message': err_msg}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
            return Response(
                stream_with_context(_err_no_doc()),
                mimetype="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}
            )

    if pipeline.index_mgr is None or pipeline.index_mgr.index is None:
        def _err_no_index():
            yield f"data: {json.dumps({'type': 'error', 'message': '未加载任何索引，请先构建索引'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        return Response(
            stream_with_context(_err_no_index()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}
        )

    # 1. 检索（一次性完成）
    import time
    search_result = pipeline.query(question, top_k)
    if not search_result["success"]:
        def _err_search():
            yield f"data: {json.dumps({'type': 'error', 'message': search_result.get('error', '检索失败')}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        return Response(
            stream_with_context(_err_search()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}
        )

    # 先发送检索统计
    retrieval_info = {
        "type": "retrieval",
        "retrieval_time_ms": search_result.get("retrieval_time_ms", 0),
        "result_count": search_result.get("result_count", 0)
    }

    def generate():
        """SSE 生成器"""
        yield f"data: {json.dumps(retrieval_info, ensure_ascii=False)}\n\n"

        # 2. 流式生成
        for sse_line in pipeline.generate_answer_stream(
            question=question,
            context=search_result["context"],
            sources=search_result["sources"],
            session_id=session_id
        ):
            yield sse_line

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@rag_bp.route("/clear-history", methods=["POST"])
def clear_history():
    """清除指定会话的对话历史

    Body (JSON):
        session_id: str  - 会话ID（必填）

    Returns:
        { success, message }
    """
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id", "").strip()

    if not session_id:
        return jsonify({"success": False, "error": "缺少 session_id 参数"}), 400

    pipeline = get_rag_pipeline()
    cleared = pipeline.clear_history(session_id)
    return jsonify({
        "success": True,
        "message": "对话历史已清除" if cleared else "未找到该会话的历史记录"
    })


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
