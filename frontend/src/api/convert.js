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
  http.get(`/png-list/${folder}`).then(res => res.data)

/** 获取PNG图片URL */
export const getPngUrl = (folder, pngName) => {
  return getBackendUrl(`/api/png/${folder}/${pngName}`)
}

/** 获取静态资源URL */
export const getStaticResourceUrl = (path) => {
  return getStaticUrl(path)
}