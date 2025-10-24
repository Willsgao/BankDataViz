import axios from 'axios'

export const http = axios.create({
  baseURL: 'http://127.0.0.1:5000',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
})

// 请求拦截器（可选：统一 token、错误提示）
http.interceptors.response.use(
  res => res,
  err => {
    console.error('API 错误：', err.response?.data || err.message)
    return Promise.reject(err)
  }
)