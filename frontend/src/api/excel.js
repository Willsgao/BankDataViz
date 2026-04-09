// frontend/src/api/excel.js
// Excel 文件管理 API 封装

import http from './index'

// ============================================================
// Excel 文件上传
// ============================================================

/**
 * 上传 Excel 文件
 * @param {File} file - 文件对象
 * @param {string} description - 文件描述（可选）
 */
export const uploadExcel = (file, description = '') => {
  const formData = new FormData()
  formData.append('file', file)
  if (description) {
    formData.append('description', description)
  }
  return http.post('/api/excel/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// ============================================================
// Excel 文件列表
// ============================================================

/**
 * 获取 Excel 文件列表
 * @param {object} params - { filename, uploader_name, start_date, end_date, page, page_size }
 */
export const getExcelList = (params = {}) =>
  http.get('/api/excel/list', { params })

/**
 * 获取单个 Excel 文件信息
 * @param {number} fileId - 文件 ID
 */
export const getExcelFile = (fileId) =>
  http.get(`/api/excel/${fileId}`)

// ============================================================
// Excel 文件下载
// ============================================================

/**
 * 下载 Excel 文件
 * @param {number} fileId - 文件 ID
 */
export const downloadExcel = (fileId) =>
  http.get(`/api/excel/download/${fileId}`, {
    responseType: 'blob'
  })

/**
 * 获取 Excel 下载地址
 * @param {number} fileId - 文件 ID
 * @returns {string} 下载 URL
 */
export const getExcelDownloadUrl = (fileId) => {
  return http.defaults.baseURL + `/api/excel/download/${fileId}`
}

// ============================================================
// Excel 文件管理
// ============================================================

/**
 * 删除 Excel 文件
 * @param {number} fileId - 文件 ID
 */
export const deleteExcelFile = (fileId) =>
  http.delete(`/api/excel/${fileId}`)

/**
 * 更新 Excel 文件描述
 * @param {number} fileId - 文件 ID
 * @param {string} description - 新描述
 */
export const updateExcelDescription = (fileId, description) =>
  http.patch(`/api/excel/${fileId}`, { description })

// ============================================================
// Excel 异常检测（审核后台使用）
// ============================================================

/**
 * 检测 Excel 文件的异常
 * @param {string} fileId - PDF文件ID (或 disk_name)
 * @param {string} excelFile - 可选，指定要检测的 Excel 文件名
 * @returns {Promise} 包含检测结果
 */
export const detectExcelSheets = (fileId, excelFile = null) => {
  const data = excelFile ? { excel_file: excelFile } : {}
  return http.post(`/api/excel-detect/${fileId}`, data)
}
