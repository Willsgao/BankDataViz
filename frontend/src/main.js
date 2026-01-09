// frontend/src/main.js
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import { initConfig } from '@/utils/config'
import { updateApiBaseUrl } from '@/api/index'


// ✅ 全局历史修改池（最先初始化）
window.historyCells = new Set()

// 初始化配置并启动应用
const initApp = async () => {
  try {
    // 1. 初始化配置
    await initConfig()
    console.log('Configuration initialized')

    // 2. 更新API基础URL
    await updateApiBaseUrl()

    // 3. 创建Vue应用
    const app = createApp(App)

    // 注册Element Plus图标
    for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
      app.component(key, component)
    }

    app.use(ElementPlus)
    app.use(router)
    app.mount('#app')

    app.config.errorHandler = (err) => {
    console.error('Vue error:', err)
  }

    console.log('App mounted successfully')
  } catch (error) {
    console.error('Failed to initialize app:', error)
  }
}

// 创建一个错误处理工具
export const setupErrorHandler = (app) => {
  // 全局错误处理
  app.config.errorHandler = (err, vm, info) => {
    console.error('全局错误:', err, info)

    // 图片加载错误特别处理
    if (err.message && err.message.includes('img') && err.message.includes('load')) {
      console.log('图片加载错误，已处理')
      return // 不显示错误提示
    }

    // 网络错误
    if (err.message && err.message.includes('Network Error')) {
      ElMessage.error('网络连接失败，请检查网络')
      return
    }

    // API错误（状态码）
    if (err.response) {
      const status = err.response.status
      const message = err.response.data?.error || err.message

      switch (status) {
        case 401:
          ElMessage.error('未授权，请重新登录')
          break
        case 403:
          ElMessage.error('权限不足')
          break
        case 404:
          // 对于API未实现的情况，不显示错误
          if (err.config.url.includes('classified-images') ||
              err.config.url.includes('move-screened-image')) {
            console.log('API未实现，使用模拟功能')
            return
          }
          ElMessage.error('请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器内部错误')
          break
        default:
          ElMessage.error(`请求失败: ${message}`)
      }
      return
    }

    // 其他错误
    ElMessage.error(`系统错误: ${err.message}`)
  }

  // 添加未处理的Promise拒绝处理
  window.addEventListener('unhandledrejection', (event) => {
    console.error('未处理的Promise拒绝:', event.reason)

    // 如果是API错误，已经在上面的errorHandler中处理了
    if (event.reason && event.reason.response) {
      event.preventDefault()
      return
    }

    // 显示友好的错误消息
    const message = event.reason?.message || '未知错误'
    if (!message.includes('img') && !message.includes('load')) {
      ElMessage.error(`操作失败: ${message}`)
    }

    event.preventDefault()
  })
}

// 启动应用
initApp()

console.log('API_BASE:', process.env.VUE_APP_API_BASE)