// llm.js - 完全修复版本
import { http } from './index'

// 普通表格识别 - 修复版本
const processNonFinancialTable = async (data) => {
  try {
    console.log('🔄 processNonFinancialTable 请求:', data)

    // 使用正确的API路径
    const response = await http.post('/api/llm/process-non-financial-table', data)
    console.log('✅ processNonFinancialTable 响应:', response.data)
    return response.data
  } catch (error) {
    console.error('❌ processNonFinancialTable 错误:', error)
    // 直接返回错误对象，不要throw
    return {
      success: false,
      error: '普通表格识别失败',
      message: error.response?.data?.error || error.message
    }
  }
}

// 金融表格识别 - 修复版本
const processImage = async (data) => {
  try {
    console.log('🔄 processImage 请求:', data)
    const response = await http.post('/api/llm/process-image', data)
    console.log('✅ processImage 响应:', response.data)
    return response.data
  } catch (error) {
    console.error('❌ processImage 错误:', error)
    // 直接返回错误对象，不要使用 Promise.reject
    return {
      success: false,
      error: '处理失败',
      message: error.response?.data?.error || error.message
    }
  }
}

export const llmApi = {
  // LLM配置相关
  configure: async (data) => {
    try {
      const response = await http.post('/api/llm/configure', data)
      return response.data
    } catch (error) {
      console.error('❌ configure 错误:', error)
      return {
        success: false,
        error: '配置失败',
        message: error.message
      }
    }
  },

  processNonFinancialTable,
  processImage,

  // 批量处理
  batchProcess: async (data) => {
    try {
      const response = await http.post('/api/llm/batch-process', data)
      return response.data
    } catch (error) {
      console.error('❌ batchProcess 错误:', error)
      return {
        success: false,
        error: '批量处理失败',
        message: error.message
      }
    }
  },

  // 测试连接
  testConnection: async (data) => {
    try {
      const response = await http.post('/api/llm/test-connection', data)
      return response.data
    } catch (error) {
      console.error('❌ testConnection 错误:', error)
      return {
        success: false,
        error: '测试连接失败',
        message: error.message
      }
    }
  },

  // 获取状态
  getStatus: async () => {
    try {
      const response = await http.get('/api/llm/status')
      return response.data
    } catch (error) {
      console.error('❌ getStatus 错误:', error)
      return {
        success: false,
        error: '获取状态失败',
        message: error.message
      }
    }
  },

  // 获取可用模型
  getAvailableModels: async () => {
    try {
      const response = await http.get('/api/llm/available-models')
      return response.data
    } catch (error) {
      console.error('❌ getAvailableModels 错误:', error)
      return {
        success: false,
        error: '获取模型列表失败',
        message: error.message
      }
    }
  },

  // 获取Excel内容
  getExcelContent: async (excelUrl) => {
    try {
      console.log('🔄 llm.js getExcelContent 请求:', excelUrl)
      const response = await http.get('/api/llm/get-excel-content', {
        params: { excel_url: excelUrl }
      })
      console.log('🔍 llm.js 原始响应:', response)
      return response.data
    } catch (error) {
      console.error('❌ llm.js getExcelContent 错误:', error)
      return {
        success: false,
        error: '获取Excel内容失败',
        message: error.message
      }
    }
  },

  // 识别表格
  recognizeTable: async (data) => {
    try {
      const response = await http.post('/api/llm/recognize-table', data)
      return response.data
    } catch (error) {
      console.error('❌ recognizeTable 错误:', error)
      return {
        success: false,
        error: '识别表格失败',
        message: error.message
      }
    }
  },

  // 检查Excel是否存在
  checkExcel: async (filePath) => {
    try {
      const response = await http.get('/api/llm/check-excel', {
        params: { path: filePath }
      })
      return response.data
    } catch (error) {
      console.error('❌ checkExcel 错误:', error)
      return {
        success: false,
        error: '检查Excel失败',
        message: error.message
      }
    }
  },

  // 健康检查
  healthCheck: async () => {
    try {
      const response = await http.get('/api/llm/health')
      return response.data
    } catch (error) {
      console.error('❌ healthCheck 错误:', error)
      return {
        success: false,
        error: '健康检查失败',
        message: error.message
      }
    }
  }
}