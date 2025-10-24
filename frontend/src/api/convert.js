import { http } from './index'

/** 提交异步转图任务 */
export const convertPdf = pdfName =>
  http.post(`/api/convert-pdf-async/${pdfName}`).then(res => res.data)

/** 获取转图进度 */
export const getProgress = jobId =>
  http.get(`/api/progress/${jobId}`).then(res => res.data)

/** 获取某 PDF 的所有 PNG 文件名 */
export const getPngList = folder =>
  http.get(`/api/png-list/${folder}`).then(res => res.data)
