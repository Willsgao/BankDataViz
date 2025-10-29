// frontend/src/api/index.js
import axios from 'axios'
import { getBackendUrl } from '@/utils/config'

// 创建axios实例 - 使用纯后端地址，不包含 /api
export const http = axios.create({
  baseURL: getBackendUrl(),  // http://127.0.0.1:5000
  timeout: 30000,
  withCredentials: true
})

// 在配置初始化后更新baseURL的函数
export const updateApiBaseUrl = async () => {
  try {
    const { initConfig, getBackendUrl } = await import('@/utils/config')
    await initConfig()
    http.defaults.baseURL = getBackendUrl()  // 更新为纯后端地址
    console.log('API baseURL updated:', http.defaults.baseURL)
  } catch (error) {
    console.error('Failed to update API baseURL:', error)
  }
}

// 请求拦截器
http.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
http.interceptors.response.use(
  response => {
    return response
  },
  error => {
    console.error('API 错误：', error.response?.data || error.message)
    return Promise.Reject(error)
  }
)

export default http