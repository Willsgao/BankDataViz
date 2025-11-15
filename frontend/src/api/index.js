// frontend/src/api/index.js
import axios from 'axios'
import { getBackendUrl } from '@/utils/config'

// 创建axios实例 - 使用不包含 /api 的基础URL
export const http = axios.create({
  baseURL: getBackendUrl(),  // 修改这里：移除 /api，变成 http://127.0.0.1:5000
  timeout: 100000,
  withCredentials: true
})

// 在配置初始化后更新baseURL的函数
export const updateApiBaseUrl = async () => {
  try {
    const { initConfig, getBackendUrl } = await import('@/utils/config')
    await initConfig()
    http.defaults.baseURL = getBackendUrl()  // 修改这里：移除 /api
    console.log('API baseURL updated:', http.defaults.baseURL)
  } catch (error) {
    console.error('Failed to update API baseURL:', error)
  }
}

// 请求拦截器
http.interceptors.request.use(
  config => {
    console.log('🚀 发起请求:', config.method?.toUpperCase(), config.url)
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
http.interceptors.response.use(
  response => {
    console.log('✅ 收到响应:', response.status, response.config.url)
    return response.data
  },
  error => {
    console.error('❌ API 错误：', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// 添加默认导出
export default http

// 其他API模块导出
export * from './file'
export * from './convert'
export * from './layout'
export * from './llm'
export * from './text'