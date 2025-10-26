// @/api/file.js
import { http } from './index'

export const getFiles = () => {
  return http.get('/files').then(res => res.data)
}

export const deleteFile = (filename) => {
  return http.delete(`/file/${encodeURIComponent(filename)}`)
}