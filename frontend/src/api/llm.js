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


// 获取可视化分析数据
const getVisualizationData = async (excelUrl) => {
  try {
    console.log('🔄 获取可视化分析数据:', excelUrl)

    const response = await http.get('/api/llm/visualization-data', {
      params: {
        excel_url: excelUrl
      }
    })

    return response.data
  } catch (error) {
    console.error('❌ 获取可视化数据失败:', error)
    return {
      success: false,
      error: '获取可视化数据失败',
      message: error.message
    }
  }
}


const getTaskResult = async (taskId) => {
  try {
    console.log('🔍 查询任务结果:', taskId)
    const response = await http.get(`/api/llm/task-result/${taskId}`)
    return response.data
  } catch (error) {
    console.error('❌ 查询任务结果失败:', error)
    return {
      success: false,
      error: '查询任务结果失败',
      message: error.message
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




// 导出可视化报告
const exportVisualizationReport = async (data) => {
  try {
    console.log('🔄 导出可视化报告:', data)

    const response = await http.post('/api/visualization/export', data)
    return response.data
  } catch (error) {
    console.error('❌ 导出可视化报告失败:', error)
    return {
      success: false,
      error: '导出可视化报告失败',
      message: error.message
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

  getTaskResult,

  getVisualizationData,

  exportVisualizationReport,

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

    // ⭐⭐⭐ 确保URL是干净的，没有多余参数 ⭐⭐⭐
    let cleanUrl = excelUrl
    if (cleanUrl.includes('?')) {
      cleanUrl = cleanUrl.split('?')[0]
      console.log('🔧 清理时间戳后的URL:', cleanUrl)
    }

    const response = await http.get('/api/llm/get-excel-content', {
      params: {
        excel_url: cleanUrl
      }
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
  },

  // 只添加这个缺失的 API
    batchProcessNonFinancial: async (data) => {
      try {
        console.log('🔄 batchProcessNonFinancial 请求:', data)
        const response = await http.post('/api/llm/batch-process-non-financial', data)
        console.log('✅ batchProcessNonFinancial 响应:', response.data)

        // ⭐⭐⭐ 关键修复：无论success是true还是false，都返回完整响应 ⭐⭐⭐
        return response.data
      } catch (error) {
        console.error('❌ batchProcessNonFinancial 错误:', error)
        return {
          success: false,
          error: '批量处理失败',
          message: error.response?.data?.error || error.message
        }
      }
    }
}