// @/api/baiduOcr.js
import axios from 'axios'

export const baiduOcrApi = {
  // 单个图片识别
  async recognizeTable(imageFile) {
    const formData = new FormData()
    formData.append('file', imageFile)

    const response = await axios.post('/api/baidu-ocr/recognize-table', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 60000  // 设置较长超时时间
    })
    return response.data
  },

  // 批量识别
  async batchRecognize(files) {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })

    const response = await axios.post('/api/baidu-ocr/batch-recognize', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  },

  // 健康检查
  async healthCheck() {
    const response = await axios.get('/api/baidu-ocr/health')
    return response.data
  }
}