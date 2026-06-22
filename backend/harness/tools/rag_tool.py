"""
RAG Tool: 智能问答

包装 RAG 服务的 query_with_answer() 方法。
"""

from typing import Any, Dict

from backend.harness import Tool, ToolResult


class RAGTool(Tool):
    """基于 RAG 的智能问答，检索文档并生成答案"""

    name = "rag"
    description = "对已解析的银行年报文档执行智能问答，基于语义检索和 LLM 生成答案"
    input_schema = {
        "question": "用户问题 (str)",
        "top_k": "召回文档数量 (int, 默认 5)",
        "stream": "是否流式输出 (bool, 默认 False)",
    }

    def __init__(self, rag_service: Any = None):
        self._service = rag_service

    def _get_service(self) -> Any:
        if self._service is None:
            # RAG 服务是模块级函数，不需要实例化
            import backend.services.rag_service as rag_mod
            self._service = rag_mod
        return self._service

    def execute(self, question: str, top_k: int = 5, stream: bool = False, **kwargs) -> ToolResult:
        try:
            service = self._get_service()
            result = service.query_with_answer(
                question=question,
                top_k=top_k,
                stream=stream,
            )

            return ToolResult(
                success=True,
                data={
                    "answer": result.get("answer", ""),
                    "sources": result.get("sources", []),
                    "question": question,
                },
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"RAG 问答失败: {str(e)}",
                metadata={"question": question},
            )
