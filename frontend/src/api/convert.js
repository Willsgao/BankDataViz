// frontend/src/api/convert.js
import { http } from './index'
import { getStaticUrl, getBackendUrl } from '@/utils/config'

/** 提交异步转图任务 */
export const convertPdf = pdfName =>
  http.post(`/convert-pdf-async/${pdfName}`).then(res => res.data)

/** 获取转图进度 */
export const getProgress = jobId =>
  http.get(`/progress/${jobId}`).then(res => res.data)

/** 获取某 PDF 的所有 PNG 文件名 */
export const getPngList = folder =>
  http.get(`/api/png-list/${folder}`).then(res => res.data)

/** 获取PNG图片URL */
export const getPngUrl = (folder, pngName) => {
  return getBackendUrl(`/api/png/${folder}/${pngName}`)
}

/** 获取静态资源URL */
export const getStaticResourceUrl = (path) => {
  return getStaticUrl(path)
}

// 在convert.js中确保有这个导出
export const screenTableImages = (pdfFolder, pngNames, options = {}) => {
  return http.post(`/screen-table-images/${pdfFolder}`, {
    png_names: pngNames,
    filter_only: options.filter_only || false,
    use_llm: options.use_llm !== false,
    audit_rate: options.audit_rate || 0.1,
    ...options
  }).then(res => res.data)
}