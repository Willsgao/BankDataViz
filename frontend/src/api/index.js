import axios from 'axios'


export const http = axios.create({
  baseURL: 'http://127.0.0.1:5000',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
})

// 请求拦截器
http.interceptors.request.use(
  config => {
    // 可以在这里添加token等
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

    // 统一错误处理
    if (error.response?.status === 401) {
      // 处理未授权
      console.error('未授权访问')
    } else if (error.response?.status === 500) {
      console.error('服务器内部错误')
    } else if (error.code === 'ECONNABORTED') {
      console.error('请求超时')
    }

    return Promise.reject(error)
  }
)