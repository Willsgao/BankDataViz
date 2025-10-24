import { http } from './index'

/** 对单张 PNG 做版面检测 */
export const layoutDetect = (folder, pngName) =>
  http.get(`/api/layout/${folder}/${pngName}`).then(res => res.data)

/** 拉取单张 PNG 原始 Blob（用于裁切） */
export const fetchPngBlob = (folder, pngName) =>
  http.get(`/api/png/${folder}/${pngName}`, { responseType: 'blob' }).then(res => res.data)
