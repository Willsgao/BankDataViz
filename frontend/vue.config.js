// vue.config.js
const { defineConfig } = require('@vue/cli-service')
const path = require('path')

// 后端地址：优先读环境变量，本地默认 localhost:5000
//const API_BASE = process.env.API_BASE || 'http://localhost:5000'
// 直接写死成服务器内网地址
const API_BASE = 'http://172.17.0.1:5000'

module.exports = defineConfig({
  lintOnSave: false,
  devServer: {
    port: 8080,
    proxy: {
      '/api': {
        target: API_BASE,
        changeOrigin: true,
        secure: false,
        pathRewrite: { '^/api': '/api' },
        logLevel: 'debug'
      },
      '/file': {
        target: API_BASE,
        changeOrigin: true,
        secure: false
      },
      '/upload': {               // 别忘了上传接口
        target: API_BASE,
        changeOrigin: true,
        secure: false
      },
      '/convert': {
        target: API_BASE,
        changeOrigin: true,
        secure: false
      },
      '/static/joined_tables': {
        target: API_BASE,
        changeOrigin: true,
        secure: false,
        logLevel: 'debug'
      },
      '/static/excel_output': {
        target: API_BASE,
        changeOrigin: true,
        secure: false,
        logLevel: 'debug'
      },
      '/static/excel_data': {
        target: API_BASE,
        changeOrigin: true,
        secure: false,
        logLevel: 'debug'
      }
    }
  },
  configureWebpack: {
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
        '@components': path.resolve(__dirname, 'src/components'),
        '@composables': path.resolve(__dirname, 'src/composables'),
        '@api': path.resolve(__dirname, 'src/api'),
        '@utils': path.resolve(__dirname, 'src/utils'),
        '@layouts': path.resolve(__dirname, 'src/layouts'),
        '@views': path.resolve(__dirname, 'src/views')
      }
    }
  }
})