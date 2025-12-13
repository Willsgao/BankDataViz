// @/api/file.js - 保持这样
import { http } from './index'

export const getFiles = () => {
  return http.get('/api/files')  // ✅ 正确 - 请求 /api/files
}

export const deleteFile = (filename) => {
  console.log('🗑️ API调用删除文件:', filename)
  return http.delete(`/api/file/${filename}`)  // ✅ 正确 - 请求 /api/file/...
}

export const getFileInfo = (filename) => {
  return http.get(`/api/file-info/${filename}`)  // ✅ 正确 - 请求 /api/file-info/...
}

export const searchPdf = (keyword) => {
  return http.get(`/api/search-pdf`, { params: { keyword } })  // ✅ 正确
}