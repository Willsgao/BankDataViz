module.exports = {
  lintOnSave: false,          // 关闭保存时自动 lint
  devServer: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        pathRewrite: { '^/api': '' }
      }
    }
  }
}