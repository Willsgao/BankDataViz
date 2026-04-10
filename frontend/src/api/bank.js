// @/api/bank.js - 银行数据相关API
import { http } from './index'

// 获取银行列表
export const getBankList = (params) => {
  return http.get('/api/bank/list', { params })
}

// 获取银行详情
export const getBankDetail = (bankId) => {
  return http.get(`/api/bank/${bankId}`)
}

// 获取银行报告列表
export const getBankReports = (bankId) => {
  return http.get(`/api/bank/${bankId}/reports`)
}

// 获取报告表格列表
export const getReportTables = (reportId) => {
  return http.get(`/api/bank/report/${reportId}/tables`)
}

// 获取表格指标数据
export const getTableIndicators = (reportId, tableName) => {
  return http.get(`/api/bank/report/${reportId}/table/${tableName}/indicators`)
}

// 获取指标趋势
export const getIndicatorTrend = (bankId, indicator) => {
  return http.get('/api/bank/analysis/trend', { params: { bank_id: bankId, indicator } })
}

// 多银行横向对比
export const compareMultipleBanks = (bankIds, indicator, year) => {
  return http.get('/api/bank/analysis/compare', { params: { bank_ids: bankIds, indicator, year } })
}

// 写入演示数据
export const seedDemoData = (force = false) => {
  return http.post('/api/bank/seed', { force })
}

// 搜索银行
export const searchBanks = (keyword, limit = 50) => {
  return http.get('/api/bank/search', { params: { keyword, limit } })
}

// 获取银行统计信息
export const getBankStatistics = () => {
  return http.get('/api/bank/statistics')
}

// Excel文件相关API
export const getExcelList = (params) => {
  return http.get('/api/bank/excel/list', { params })
}

export const getExcelDownloadUrl = (fileId) => {
  return `${http.defaults?.baseURL || ''}/api/excel/download/${fileId}`
}

export const updateExcelReview = (fileId, data) => {
  return http.post(`/api/bank/excel/${fileId}/review`, data)
}

export const getExcelFileDetail = (fileId) => {
  return http.get(`/api/bank/excel/${fileId}`)
}

// 重新检测单个 Excel 文件异常
export const detectExcelAnomalies = (fileId) => {
  return http.post(`/api/bank/excel/${fileId}/detect`)
}

// 批量检测 Excel 文件异常
export const batchDetectExcelAnomalies = (fileIds) => {
  return http.post('/api/bank/excel/detect-batch', { file_ids: fileIds })
}

// ============================================================
// 银行数据文档 API (独立的文档管理接口)
// ============================================================

// 获取银行数据文档列表
export const getBankDocList = (params) => {
  return http.get('/api/bank-doc/list', { params })
}

// 获取银行数据文档详情
export const getBankDocDetail = (docId) => {
  return http.get(`/api/bank-doc/${docId}`)
}

// 获取银行数据文档下载URL
export const getBankDocDownloadUrl = (docId) => {
  return `${http.defaults?.baseURL || ''}/api/bank-doc/download/${docId}`
}

// 获取银行数据文档统计信息
export const getBankDocStats = () => {
  return http.get('/api/bank-doc/stats')
}

// 获取文档分类列表
export const getBankDocCategories = () => {
  return http.get('/api/bank-doc/categories')
}

// 更新银行数据文档信息
export const updateBankDoc = (docId, data) => {
  return http.patch(`/api/bank-doc/${docId}`, data)
}

// 删除银行数据文档
export const deleteBankDoc = (docId) => {
  return http.delete(`/api/bank-doc/${docId}`)
}

// 上传银行数据文档（返回上传URL，供 el-upload 使用）
export const getBankDocUploadUrl = () => {
  return `${http.defaults?.baseURL || ''}/api/bank-doc/upload`
}
