// vue.config.js
const { defineConfig } = require('@vue/cli-service')
const path = require('path')

module.exports = defineConfig({
  lintOnSave: false,
  devServer: {
    port: 8080,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
        pathRewrite: {
          '^/api': '/api'  // 明确指定路径重写
        },
        logLevel: 'debug'  // 添加调试日志
      },
      '/file': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false
      },
      '/convert': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false
      },
      '/static/joined_tables': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
        logLevel: 'debug'
      },
      '/static/excel_output': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
        logLevel: 'debug'
      },
      '/static/excel_data': {
        target: 'http://localhost:5000',
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