import { http } from './index'

/** 获取文件列表 */
export const getFiles = () => http.get('/files').then(res => res.data)

/** 删除文件（软删） */
export const deleteFile = filename => http.delete(`/file/${filename}`).then(res => res.data)

/** 把文件拉成 Blob（用于裁切前转 base64） */
export const fetchFileBlob = filename =>
  http.get(`/file/${filename}`, { responseType: 'blob' }).then(res => res.data)
