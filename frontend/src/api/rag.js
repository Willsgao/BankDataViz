// frontend/src/api/rag.js
import { http } from './index'

/**
 * 为指定文档构建 FAISS 索引
 * @param {string} pdfPath - PDF 文件的绝对路径
 * @param {boolean} rebuild - 是否强制重建
 */
export const buildIndex = (pdfPath, rebuild = false) => {
  return http.post('/api/rag/build-index', { pdf_path: pdfPath, rebuild })
}

/**
 * RAG 问答：提出问题并获取 AI 生成的答案
 * @param {string} question - 用户问题
 * @param {string} document - 指定文档名（可选）
 * @param {number} topK - 召回数量（默认5）
 */
export const queryRag = (question, document = '', topK = 5) => {
  return http.post('/api/rag/query', {
    question,
    document: document || undefined,
    top_k: topK
  })
}

/**
 * 获取 RAG 索引统计信息
 */
export const getRagStats = () => {
  return http.get('/api/rag/stats')
}

/**
 * 获取可用文档列表
 */
export const getDocuments = () => {
  return http.get('/api/rag/documents')
}
