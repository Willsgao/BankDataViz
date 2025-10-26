// @/api/llm.js
import { http } from './index'

export const llmApi = {
  // LLM配置相关
  configure: (data) => {
    return http.post('/api/llm/configure', data)
  },



  // 批量处理
  batchProcess: (data) => {
    return http.post('/api/llm/batch-process', data)
  },

  // 测试连接
  testConnection: (data) => {
    return http.post('/api/llm/test-connection', data)
  },

  // 获取状态
  getStatus: () => {
    return http.get('/api/llm/status')
  },

  // 获取可用模型
  getAvailableModels: () => {
    return http.get('/api/llm/available-models')
  },

  // 读取Excel内容
  getExcelContent: (excelUrl) => {
    return http.get('/api/llm/get-excel-content', {
      params: { excel_url: excelUrl }
    })
  },

  // 在 llm.js 中检查 processImage 方法
processImage: (data) => {
  return http.post('/api/llm/process-image', data)
    .then(res => {
      console.log('🔍 llm.js processImage 原始响应:', res)
      console.log('🔍 res.data:', res.data)
      return res.data // 确保返回的是 res.data
    })
    .catch(error => {
      console.error('❌ llm.js processImage 错误:', error)
      throw error
    })
},

  // 识别表格
  recognizeTable: (data) => {
    return http.post('/api/llm/recognize-table', data)
  },

  // 检查Excel是否存在
  checkExcel: (filePath) => {
    return http.get('/api/llm/check-excel', {
      params: { path: filePath }
    })
  },

  // 健康检查
  healthCheck: () => {
    return http.get('/api/llm/health')
  }
}