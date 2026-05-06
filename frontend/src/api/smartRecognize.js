/**
 * 智能识别 API
 * 封装 /api/smart-recognize/* 接口
 */
import http from './index'

/**
 * 上传文件并检测表格区域
 * @param {FormData} formData - 包含 file 和 dpi 字段
 */
export const detectTables = (formData) => {
  return http.post('/api/smart-recognize/detect-tables', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

/**
 * 批量发送多个截图到 DeepSeek 自动化识别
 * @param {object} data - { regions: [{id, image_base64, label}], prompt, user_data_dir }
 */
export const batchRecognize = (data) => {
  return http.post('/api/smart-recognize/batch-recognize', data, { timeout: 300000 })
}

/**
 * 批量保存多个区域的识别结果为 Excel
 * @param {object} data - { results: [{id, label, result}], filename }
 */
export const batchSaveExcel = (data) => {
  return http.post('/api/smart-recognize/batch-save-excel', data)
}

/**
 * 发送截图到 DeepSeek（单个，用于单次识别场景）
 * @param {object} data - { image_base64, prompt, user_data_dir }
 */
export const sendToDeepSeek = (data) => {
  return http.post('/api/smart-recognize/send', data)
}

/**
 * 保存识别结果为 Excel（单个）
 * @param {object} data - { content, filename, sheet_name }
 */
export const saveToExcel = (data) => {
  return http.post('/api/smart-recognize/save-excel', data)
}

export default {
  detectTables,
  batchRecognize,
  batchSaveExcel,
  sendToDeepSeek,
  saveToExcel
}
