// vue.config.js
const { defineConfig } = require('@vue/cli-service')
const path = require('path')

module.exports = defineConfig({
  lintOnSave: false,
  devServer: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        pathRewrite: { '^/api': '' }
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
        '@layouts': path.resolve(__dirname, 'src/layouts'),  // 修正路径
        '@views': path.resolve(__dirname, 'src/views')       // 添加views别名
      }
    }
  },
  // 添加构建过程日志
  chainWebpack: config => {
    config.plugin('define').tap(args => {
      args[0]['process.env'].NODE_ENV = JSON.stringify(process.env.NODE_ENV)
      return args
    })

    // 添加文件处理日志
    config.module
      .rule('vue')
      .use('vue-loader')
      .tap(options => {
        console.log('Vue loader processing files...')
        return options
      })
  }
})