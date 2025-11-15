// @/api/file.js
import { http } from './index'

export const getFiles = () => {
  return http.get('/files')  // 尝试移除 /api 前缀
}

export const deleteFile = (filename) => {
  console.log('🗑️ API调用删除文件:', filename)
  return http.delete(`/file/${filename}`)  // 尝试移除 /api 前缀
}