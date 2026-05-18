# backend/services/rag_service.py
"""
RAG (Retrieval-Augmented Generation) 智能检索服务

核心管线：
  PDF文档 → PyMuPDF提取文本 → 语义分块 → BGE-large-zh Embedding
  → FAISS IndexIVFFlat → 用户提问 → 向量检索 → LLM生成答案（支持流式SSE）

技术选型：
  - Embedding: BGE-large-zh (768维, sentence-transformers)
  - 向量检索: FAISS IndexIVFFlat (IVF1024聚类, nprobe=16)
  - LLM: 火山引擎 DeepSeek (复用现有 Ark API，支持 stream=True)
"""

import os
import re
import json
import time
import logging
import hashlib
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Generator

import fitz  # PyMuPDF
import numpy as np

from backend.configs.llm_config import RAG_API_KEY, RAG_BASE_URL, RAG_MODEL_ID

logger = logging.getLogger(__name__)

# =============================================================================
# 常量配置
# =============================================================================
CHUNK_SIZE = 512          # 分块大小（字符数）
CHUNK_OVERLAP = 128       # 分块重叠（字符数）
EMBEDDING_DIM = 768       # BGE-large-zh 向量维度
FAISS_NLIST = 1024         # IVF 聚类中心数
FAISS_NPROBE = 16         # 检索时搜索的聚类数
TOP_K = 5                  # 召回数量
INDEX_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "rag_indices"

INDEX_DIR.mkdir(parents=True, exist_ok=True)

# HuggingFace 模型缓存放到项目目录下，避免占用C盘
HF_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "models" / "huggingface"
HF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["HF_HOME"] = str(HF_CACHE_DIR)

# BGE-large-zh 模型路径（优先本地，自动回退到HF下载）
_BGE_LOCAL_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "models" / "bge-large-zh"
if _BGE_LOCAL_PATH.exists() and (_BGE_LOCAL_PATH / "config.json").exists():
    BGE_MODEL_NAME = str(_BGE_LOCAL_PATH)
    logger.info(f"使用本地 Embedding 模型: {BGE_MODEL_NAME}")
else:
    BGE_MODEL_NAME = "BAAI/bge-large-zh"
    logger.info("本地模型未找到，将从 HuggingFace 自动下载")


# =============================================================================
# 语义分块器
# =============================================================================
class SemanticChunker:
    """按语义边界切分文本，保留段落完整性和跨页上下文"""

    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """将长文本按段落边界 + 滑动窗口切分为语义块"""
        paragraphs = self._split_paragraphs(text)
        chunks = []

        current_chunk = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 如果当前块 + 新段落不超过限制，则追加
            if len(current_chunk) + len(para) <= self.chunk_size:
                current_chunk += para + "\n"
            else:
                # 保存当前块
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                # 重叠策略：保留上一块的尾巴
                if len(current_chunk) > self.chunk_overlap:
                    current_chunk = current_chunk[-self.chunk_overlap:] + para + "\n"
                else:
                    current_chunk = para + "\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        result = []
        for i, chunk_text in enumerate(chunks):
            chunk_meta = (metadata or {}).copy()
            chunk_meta["chunk_index"] = i
            chunk_meta["char_count"] = len(chunk_text)
            result.append({"text": chunk_text, "metadata": chunk_meta})

        return result

    def _split_paragraphs(self, text: str) -> List[str]:
        """按多种分隔符拆分段落"""
        # 先按双换行拆分
        raw = re.split(r'\n\s*\n', text)
        paragraphs = []
        for part in raw:
            # 对过长的单段按单换行再拆
            if len(part) > self.chunk_size:
                sub_parts = part.split('\n')
                paragraphs.extend(sub_parts)
            else:
                paragraphs.append(part)
        return paragraphs


# =============================================================================
# Embedding 服务
# =============================================================================
class EmbeddingService:
    """BGE-large-zh 向量化服务（单例 + 懒加载）"""

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self):
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer
        logger.info(f"正在加载 Embedding 模型: {BGE_MODEL_NAME}")
        self._model = SentenceTransformer(BGE_MODEL_NAME)
        logger.info(f"Embedding 模型加载完成，维度: {self._model.get_embedding_dimension()}")

    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """将文本列表编码为向量数组 (N, 768)"""
        self._load_model()
        # BGE 模型需要为查询添加前缀
        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return np.array(embeddings, dtype=np.float32)

    def encode_query(self, query: str) -> np.ndarray:
        """将查询文本编码为向量 (768,)"""
        self._load_model()
        embedding = self._model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return np.array(embedding[0], dtype=np.float32)


# =============================================================================
# FAISS 索引管理器
# =============================================================================
class FaissIndexManager:
    """FAISS IndexIVFFlat 索引管理：构建 / 加载 / 检索 / 持久化"""

    def __init__(self, dim: int = EMBEDDING_DIM, nlist: int = FAISS_NLIST):
        self.dim = dim
        self.nlist = nlist
        self.index = None
        self.chunks: List[Dict] = []         # 与索引对应的分块数据
        self.embeddings: Optional[np.ndarray] = None
        self._is_trained = False

    def train(self, train_vectors: np.ndarray) -> None:
        """用训练向量训练聚类中心"""
        import faiss
        if len(train_vectors) < self.nlist:
            logger.warning(f"训练向量不足 ({len(train_vectors)} < {self.nlist})，调整 nlist")
            nlist = max(1, len(train_vectors) // 2)
        else:
            nlist = self.nlist

        quantizer = faiss.IndexFlatIP(self.dim)   # 内积相似度（适合归一化向量）
        self.index = faiss.IndexIVFFlat(quantizer, self.dim, nlist, faiss.METRIC_INNER_PRODUCT)
        self.index.train(train_vectors)
        self.index.nprobe = FAISS_NPROBE
        self._is_trained = True
        logger.info(f"FAISS 索引训练完成: {nlist} 个聚类中心, nprobe={FAISS_NPROBE}")

    def add(self, vectors: np.ndarray, chunks: List[Dict]) -> None:
        """添加向量和分块数据到索引"""
        if self.index is None:
            self.train(vectors)
        self.index.add(vectors)
        self.embeddings = vectors
        self.chunks.extend(chunks)
        logger.info(f"已添加 {len(chunks)} 条数据到索引，当前总数: {self.index.ntotal}")

    def search(self, query_vector: np.ndarray, k: int = TOP_K) -> List[Dict]:
        """检索最相似的 Top-K 结果"""
        if self.index is None or self.index.ntotal == 0:
            return []
        query_vector = query_vector.reshape(1, -1).astype(np.float32)
        distances, indices = self.index.search(query_vector, min(k, self.index.ntotal))
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            results.append({
                "chunk": self.chunks[idx],
                "score": float(dist),
                "index": int(idx)
            })
        return results

    def save(self, filepath: str) -> None:
        """持久化索引到磁盘"""
        import faiss
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        # 保存 FAISS 索引
        faiss.write_index(self.index, str(path.with_suffix(".faiss")))
        # 保存分块元数据
        metadata = {
            "dim": self.dim,
            "nlist": self.nlist,
            "ntotal": self.index.ntotal if self.index else 0,
            "chunks": self.chunks
        }
        with open(path.with_suffix(".meta.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        logger.info(f"索引已保存: {path}")

    @classmethod
    def load(cls, filepath: str) -> Optional["FaissIndexManager"]:
        """从磁盘加载索引"""
        import faiss
        path = Path(filepath)
        faiss_path = path.with_suffix(".faiss")
        meta_path = path.with_suffix(".meta.json")

        if not faiss_path.exists() or not meta_path.exists():
            return None

        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        mgr = cls(dim=metadata["dim"], nlist=metadata["nlist"])
        mgr.index = faiss.read_index(str(faiss_path))
        mgr.index.nprobe = FAISS_NPROBE
        mgr.chunks = metadata["chunks"]
        mgr._is_trained = True
        logger.info(f"索引已加载: {faiss_path}, 共 {mgr.index.ntotal} 条")
        return mgr


# =============================================================================
# RAG 文档加载器
# =============================================================================
class RagDocumentLoader:
    """使用 PyMuPDF 从 PDF 中提取文本"""

    def __init__(self):
        self.chunker = SemanticChunker()
        self._file_cache: Dict[str, str] = {}

    def load_pdf(self, pdf_path: str) -> str:
        """加载 PDF 并提取纯文本"""
        cache_key = hashlib.md5(pdf_path.encode()).hexdigest()
        if cache_key in self._file_cache:
            return self._file_cache[cache_key]

        doc = fitz.open(pdf_path)
        full_text = ""
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text", sort=True)
            if text.strip():
                full_text += f"\n--- 第 {page_num + 1} 页 ---\n{text}"

        doc.close()
        self._file_cache[cache_key] = full_text
        return full_text

    def load_and_chunk(self, pdf_path: str, doc_name: str = "") -> List[Dict]:
        """加载 PDF 并返回语义分块列表"""
        text = self.load_pdf(pdf_path)
        metadata = {
            "source": doc_name or Path(pdf_path).name,
            "file_path": pdf_path,
            "total_chars": len(text)
        }
        chunks = self.chunker.split(text, metadata)
        logger.info(f"文档 {doc_name or pdf_path}: {len(text)} 字符 → {len(chunks)} 个分块")
        return chunks

    def get_available_documents(self) -> List[Dict]:
        """扫描 data 目录获取可用 PDF，并查找原始文件名"""
        from backend.utils.constants import MAIN_ROOT, UPLOAD_FOLDER, DATABASE
        import sqlite3
        pdf_files = []
        search_dirs = [
            Path(MAIN_ROOT) / "data" / "backend" / "static" / "excel_data",
            Path(MAIN_ROOT) / "data" / "backend" / "static" / "excel_output",
            Path(MAIN_ROOT) / UPLOAD_FOLDER,
        ]

        # 从数据库读取文件名映射 (disk_filename → raw_filename)
        filename_map = {}
        try:
            db_path = Path(MAIN_ROOT) / DATABASE
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cur = conn.cursor()
                cur.execute("SELECT filename, raw_filename FROM files WHERE COALESCE(deleted, 0) = 0")
                for row in cur.fetchall():
                    filename_map[row[0]] = row[1]
                conn.close()
        except Exception:
            pass  # 数据库不可用时降级为磁盘文件名

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            for pdf_path in search_dir.rglob("*.pdf"):
                disk_name = pdf_path.name
                # 优先使用原始文件名，回退到磁盘文件名
                display_name = filename_map.get(disk_name, disk_name)
                pdf_files.append({
                    "name": display_name,
                    "path": str(pdf_path.absolute()),
                    "size": pdf_path.stat().st_size
                })
        return pdf_files


# =============================================================================
# RAG 管线编排
# =============================================================================
class RagPipeline:
    """RAG 主管线：加载 → 分块 → 向量化 → 索引 → 检索 → 生成（支持流式 SSE + 多轮对话记忆）"""

    MAX_HISTORY_ROUNDS = 10  # 最多保留最近10轮对话

    def __init__(self):
        self.loader = RagDocumentLoader()
        self.embedder = EmbeddingService()
        self.index_mgr: Optional[FaissIndexManager] = None
        self._current_doc: Optional[str] = None
        self.conversations: Dict[str, List[Dict[str, str]]] = {}  # session_id → messages

    def build_index(self, pdf_path: str) -> Dict[str, Any]:
        """为指定 PDF 构建 FAISS 索引"""
        start_time = time.time()
        doc_name = Path(pdf_path).name

        # 1. 加载 + 分块
        chunks = self.loader.load_and_chunk(pdf_path, doc_name)
        if not chunks:
            return {"success": False, "error": "文档没有可提取的文本内容", "chunk_count": 0}

        chunk_texts = [c["text"] for c in chunks]

        # 2. Embedding
        vectors = self.embedder.encode(chunk_texts)

        # 3. FAISS 索引（使用向量实际维度，兼容不同模型）
        self.index_mgr = FaissIndexManager(dim=vectors.shape[1])
        self.index_mgr.train(vectors)
        self.index_mgr.add(vectors, chunks)

        # 4. 持久化
        index_path = INDEX_DIR / f"{doc_name}.index"
        self.index_mgr.save(str(index_path))
        self._current_doc = doc_name

        elapsed = time.time() - start_time
        return {
            "success": True,
            "document": doc_name,
            "chunk_count": len(chunks),
            "vector_count": int(self.index_mgr.index.ntotal),
            "index_path": str(index_path),
            "elapsed_seconds": round(elapsed, 3)
        }

    def load_index(self, doc_name: str) -> bool:
        """加载已存在的索引（自动处理显示名→UUID文件名映射）"""
        # 1. 直接匹配
        index_path = INDEX_DIR / f"{doc_name}.index"
        mgr = FaissIndexManager.load(str(index_path))
        if mgr:
            self.index_mgr = mgr
            self._current_doc = doc_name
            return True

        # 2. 如果直接匹配失败，尝试通过文档列表查找映射
        #    （前端传的是显示名，索引是按UUID文件名存的）
        docs = self.loader.get_available_documents()
        for d in docs:
            if d["name"] == doc_name:
                uuid_name = Path(d["path"]).name
                index_path = INDEX_DIR / f"{uuid_name}.index"
                mgr = FaissIndexManager.load(str(index_path))
                if mgr:
                    self.index_mgr = mgr
                    self._current_doc = uuid_name
                    logger.info(f"通过文档名映射加载索引: {doc_name} → {uuid_name}")
                    return True
                break
        return False

    def query(self, question: str, top_k: int = TOP_K) -> Dict[str, Any]:
        """执行 RAG 查询"""
        if self.index_mgr is None or self.index_mgr.index is None:
            return {"success": False, "error": "请先构建索引"}

        start_time = time.time()

        # 1. 向量检索
        query_vec = self.embedder.encode_query(question)
        results = self.index_mgr.search(query_vec, k=top_k)

        retrieval_time = (time.time() - start_time) * 1000

        # 2. 构建上下文
        context_parts = []
        sources = []
        for i, r in enumerate(results):
            chunk = r["chunk"]
            context_parts.append(f"[文档片段{i+1}] 来源: {chunk['metadata'].get('source', '未知')}\n{chunk['text']}")
            sources.append({
                "index": i + 1,
                "text": chunk["text"][:200] + ("..." if len(chunk["text"]) > 200 else ""),
                "score": round(r["score"], 4),
                "source": chunk["metadata"].get("source", "")
            })

        context = "\n\n".join(context_parts)
        return {
            "success": True,
            "question": question,
            "context": context,
            "sources": sources,
            "retrieval_time_ms": round(retrieval_time, 2),
            "result_count": len(results)
        }

    def _build_messages(self, question: str, context: str, session_id: str = "") -> List[Dict[str, str]]:
        """构建包含对话历史的 messages 列表"""
        system_msg = {"role": "system", "content": "你是一个专业的金融文档分析助手。"}

        user_prompt = f"""你是一个金融文档分析助手。请基于以下从银行年报/募集说明书中检索到的文档片段，回答用户的问题。

要求：
1. 只使用提供的文档片段信息回答，不要编造
2. 如果片段中没有相关信息，请明确说明"根据现有文档无法确定"
3. 回答要专业、准确，引用数据时注明来源
4. 使用中文回答

{context}

用户问题：{question}

请回答："""

        messages = [system_msg]

        # 拼接历史对话
        history = self.conversations.get(session_id, [])
        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": user_prompt})
        return messages

    def _append_history(self, session_id: str, question: str, answer: str) -> None:
        """将本轮问答追加到对话历史，超出上限自动截断"""
        if not session_id:
            return
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        history = self.conversations[session_id]
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
        # 截断：保留最近 N 轮（每轮2条消息）
        max_messages = self.MAX_HISTORY_ROUNDS * 2
        if len(history) > max_messages:
            self.conversations[session_id] = history[-max_messages:]

    def clear_history(self, session_id: str) -> bool:
        """清除指定 session 的对话历史"""
        if session_id in self.conversations:
            del self.conversations[session_id]
            return True
        return False

    def generate_answer(self, question: str, context: str, sources: List[Dict],
                        session_id: str = "") -> str:
        """使用 LLM 基于检索结果生成答案（同步版本）"""
        from openai import OpenAI

        messages = self._build_messages(question, context, session_id)

        client = OpenAI(
            base_url=RAG_BASE_URL,
            api_key=RAG_API_KEY
        )

        response = client.chat.completions.create(
            model=RAG_MODEL_ID,
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
            stream=False
        )

        answer = response.choices[0].message.content

        # 追加到对话历史
        self._append_history(session_id, question, answer)

        return answer

    def generate_answer_stream(self, question: str, context: str,
                               sources: List[Dict],
                               session_id: str = "") -> Generator[str, None, None]:
        """使用 LLM 流式生成答案，逐 token yield（SSE 数据行）

        用法：
            for sse_line in pipeline.generate_answer_stream(question, context, sources):
                yield sse_line  →  Flask SSE response
        """
        from openai import OpenAI

        messages = self._build_messages(question, context, session_id)

        client = OpenAI(
            base_url=RAG_BASE_URL,
            api_key=RAG_API_KEY
        )

        try:
            stream = client.chat.completions.create(
                model=RAG_MODEL_ID,
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
                stream=True
            )

            full_answer = ""
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_answer += token
                    yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"

            # 追加到对话历史
            self._append_history(session_id, question, full_answer)

            # 完成信号
            done_data = {
                "type": "done",
                "sources": [
                    {"index": s.get("index", i+1),
                     "text": (s.get("text", "")[:200] + "..." if len(s.get("text", "")) > 200 else s.get("text", "")),
                     "score": round(s.get("score", 0), 4),
                     "source": s.get("source", "")}
                    for i, s in enumerate(sources)
                ]
            }
            yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"LLM 流式生成失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'答案生成失败: {str(e)}'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    def query_with_answer(self, question: str, top_k: int = TOP_K,
                          session_id: str = "") -> Dict[str, Any]:
        """完整 RAG 流程：检索 + 生成"""
        result = self.query(question, top_k)
        if not result["success"]:
            return result

        answer_start = time.time()
        try:
            answer = self.generate_answer(
                question, result["context"], result["sources"], session_id
            )
            result["answer"] = answer
            result["answer_time_ms"] = round((time.time() - answer_start) * 1000, 2)
            result["total_time_ms"] = round(result["retrieval_time_ms"] + result["answer_time_ms"], 2)
        except Exception as e:
            logger.error(f"LLM 生成失败: {e}")
            result["answer"] = f"答案生成失败: {str(e)}"
            result["answer_time_ms"] = 0
            result["total_time_ms"] = result["retrieval_time_ms"]

        return result

    def get_stats(self) -> Dict[str, Any]:
        """获取当前索引统计信息"""
        stats = {
            "has_index": self.index_mgr is not None and self.index_mgr.index is not None,
            "current_document": self._current_doc,
            "total_vectors": 0,
            "index_type": None,
            "dimension": EMBEDDING_DIM,
        }
        if self.index_mgr and self.index_mgr.index:
            stats["total_vectors"] = int(self.index_mgr.index.ntotal)
            stats["index_type"] = "IndexIVFFlat"
            stats["nlist"] = FAISS_NLIST
            stats["nprobe"] = FAISS_NPROBE

        # 列出已保存的索引
        saved_indices = []
        if INDEX_DIR.exists():
            for f in INDEX_DIR.glob("*.faiss"):
                name = f.stem
                saved_indices.append({
                    "name": name,
                    "size_bytes": f.stat().st_size,
                    "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.stat().st_mtime))
                })
        stats["saved_indices"] = saved_indices
        return stats


# =============================================================================
# 全局单例 (懒初始化)
# =============================================================================
_rag_pipeline: Optional[RagPipeline] = None


def get_rag_pipeline() -> RagPipeline:
    """获取 RAG 管线全局单例"""
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RagPipeline()
    return _rag_pipeline
