// frontend/src/api/rag.js
import { http } from './index'
import { getBackendUrl } from '@/utils/config'

/**
 * 为指定文档构建 FAISS 索引
 * @param {string} pdfPath - PDF 文件的绝对路径
 * @param {boolean} rebuild - 是否强制重建
 */
export const buildIndex = (pdfPath, rebuild = false) => {
  return http.post('/api/rag/build-index', { pdf_path: pdfPath, rebuild })
}

/**
 * RAG 问答：提出问题并获取 AI 生成的答案（非流式）
 * @param {string} question - 用户问题
 * @param {string} document - 指定文档名（可选）
 * @param {number} topK - 召回数量（默认5）
 * @param {string} sessionId - 会话ID（可选，用于多轮对话）
 */
export const queryRag = (question, document = '', topK = 5, sessionId = '') => {
  return http.post('/api/rag/query', {
    question,
    document: document || undefined,
    top_k: topK,
    session_id: sessionId || undefined
  })
}

/**
 * RAG 流式问答：SSE 流式获取 AI 生成的答案
 * @param {string} question - 用户问题
 * @param {string} document - 指定文档名（可选）
 * @param {number} topK - 召回数量（默认5）
 * @param {string} sessionId - 会话ID（可选）
 * @param {object} callbacks - 回调函数 { onToken, onDone, onRetrieval, onError }
 * @returns {AbortController} 用于取消请求
 */
export const queryRagStream = (question, document = '', topK = 5, sessionId = '', callbacks = {}) => {
  const { onToken, onDone, onRetrieval, onError } = callbacks
  const controller = new AbortController()
  const backendBase = getBackendUrl('')

  fetch(`${backendBase}/api/rag/query-stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      document: document || undefined,
      top_k: topK,
      session_id: sessionId || undefined
    }),
    signal: controller.signal
  }).then(async (response) => {
    if (!response.ok) {
      onError && onError(`HTTP ${response.status}`)
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    // eslint-disable-next-line no-constant-condition
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6).trim()
          if (dataStr === '[DONE]') return

          try {
            const data = JSON.parse(dataStr)
            switch (data.type) {
              case 'retrieval':
                onRetrieval && onRetrieval(data)
                break
              case 'token':
                onToken && onToken(data.content)
                break
              case 'done':
                onDone && onDone(data)
                break
              case 'error':
                onError && onError(data.message)
                break
            }
          } catch (e) {
            // 忽略非 JSON 行
          }
        }
      }
    }
  }).catch((err) => {
    if (err.name !== 'AbortError') {
      onError && onError(err.message || '网络请求失败')
    }
  })

  return controller
}

/**
 * 清除指定会话的对话历史
 * @param {string} sessionId - 会话ID
 */
export const clearHistory = (sessionId) => {
  return http.post('/api/rag/clear-history', { session_id: sessionId })
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
