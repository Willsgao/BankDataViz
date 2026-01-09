// vue.config.js
const { defineConfig } = require('@vue/cli-service')
const path = require('path')

// vue.config.js
//const API_BASE = process.env.VUE_APP_API_BASE || 'http://localhost:5000'
const API_BASE = process.env.VUE_APP_API_BASE || 'http://122.51.196.65:5000'


module.exports = defineConfig({
  lintOnSave: false,
  devServer: {
    port: 8080,
    proxy: {
      '/api': {
        target: API_BASE,
        changeOrigin: true,
        secure: false,
        logLevel: 'debug'
      },
      '/filtered-tables-image': {
        target: API_BASE,
        changeOrigin: true,
        secure: false,
        logLevel: 'debug'
      },
      '/file': {
        target: API_BASE,
        changeOrigin: true,
        secure: false
      },
      '/upload': {
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