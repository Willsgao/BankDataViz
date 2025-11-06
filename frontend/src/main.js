// frontend/src/main.js
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import { initConfig } from '@/utils/config'
import { updateApiBaseUrl } from '@/api/index'

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

// 启动应用
initApp()