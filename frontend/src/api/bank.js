// frontend/src/api/bank.js
// 银行数据仓库 API 封装

import http from './index'

// ============================================================
// 种子数据
// ============================================================

/**
 * 写入演示种子数据
 * @param {boolean} force - 是否强制重新写入
 */
export const seedDemoData = (force = false) =>
  http.post(`/api/bank/seed?force=${force}`)

// ============================================================
// 银行信息
// ============================================================

/**
 * 获取银行列表
 * @param {object} params - { bank_type, listed_only, page, page_size }
 */
export const getBankList = (params = {}) =>
  http.get('/api/bank/list', { params })

/**
 * 搜索银行
 * @param {string} keyword
 * @param {number} limit
 */
export const searchBanks = (keyword, limit = 20) =>
  http.get('/api/bank/search', { params: { keyword, limit } })

/**
 * 获取银行详情
 * @param {number} bankId
 */
export const getBankDetail = (bankId) =>
  http.get(`/api/bank/${bankId}`)

/**
 * 获取统计信息
 */
export const getBankStatistics = () =>
  http.get('/api/bank/statistics')

// ============================================================
// 报告
// ============================================================

/**
 * 获取银行的报告列表
 * @param {number} bankId
 * @param {object} params - { report_type, year }
 */
export const getBankReports = (bankId, params = {}) =>
  http.get(`/api/bank/${bankId}/reports`, { params })

/**
 * 获取报告详情
 * @param {number} reportId
 */
export const getReportDetail = (reportId) =>
  http.get(`/api/bank/report/${reportId}`)

/**
 * 获取报告包含的表格列表
 * @param {number} reportId
 */
export const getReportTables = (reportId) =>
  http.get(`/api/bank/report/${reportId}/tables`)

/**
 * 获取表格指标数据
 * @param {number} reportId
 * @param {string} tableName
 */
export const getTableIndicators = (reportId, tableName) =>
  http.get(`/api/bank/report/${reportId}/table/${encodeURIComponent(tableName)}`)

// ============================================================
// 分析
// ============================================================

/**
 * 获取指标趋势（单银行历年）
 * @param {number} bankId
 * @param {string} indicatorName
 * @param {string} years - 逗号分隔，如 "2020,2021,2022,2023,2024"
 */
export const getIndicatorTrend = (bankId, indicatorName, years = '2020,2021,2022,2023,2024') =>
  http.get('/api/bank/analysis/trend', {
    params: { bank_id: bankId, indicator_name: indicatorName, years }
  })

/**
 * 多银行横向对比
 * @param {string} bankIds - 逗号分隔，如 "1,2,3"
 * @param {string} indicatorName
 * @param {number} year
 */
export const compareMultipleBanks = (bankIds, indicatorName, year) =>
  http.get('/api/bank/analysis/compare', {
    params: { bank_ids: bankIds, indicator_name: indicatorName, year }
  })

/**
 * 指标排名
 * @param {string} indicatorName
 * @param {number} year
 * @param {string} bankType
 * @param {number} limit
 */
export const getIndicatorRanking = (indicatorName, year, bankType, limit = 20) =>
  http.get('/api/bank/analysis/ranking', {
    params: { indicator_name: indicatorName, year, bank_type: bankType, limit }
  })

// ============================================================
// 数据溯源 & 版本
// ============================================================

/**
 * 获取数据溯源信息
 * @param {number} tableDataId
 */
export const getDataSources = (tableDataId) =>
  http.get(`/api/bank/data/${tableDataId}/sources`)

/**
 * 获取数据版本历史
 * @param {number} tableDataId
 */
export const getDataVersions = (tableDataId) =>
  http.get(`/api/bank/data/${tableDataId}/versions`)
