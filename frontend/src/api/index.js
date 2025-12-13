// frontend/src/api/index.js
import axios from 'axios'
import { getBackendUrl } from '@/utils/config'


// ① 后端地址：环境变量 > 默认 localhost
const backendBase = process.env.VUE_APP_API_BASE || 'http://localhost:5000'

export const http = axios.create({
  baseURL: backendBase,   // ② 不再出现 127.0.0.1
  timeout: 100000,
  withCredentials: true
})

export const updateApiBaseUrl = async () => {
  // ③ 同步更新
  http.defaults.baseURL = backendBase
  console.log('API baseURL updated:', http.defaults.baseURL)
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