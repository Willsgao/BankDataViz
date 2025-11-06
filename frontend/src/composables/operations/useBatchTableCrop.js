// composables/useBatchTableCrop.js
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { getApiUrl } from '@/utils/config'

export function useBatchTableCrop(joinedResults) {
  const batchCropLoading = ref({})

  async function cutTablesForPDF(pdfDiskName, convertCache) {
    console.log('开始批量裁切PDF:', pdfDiskName)

    // 设置加载状态
    batchCropLoading.value[pdfDiskName] = true

    try {
      // ========== 新增：缓存检查逻辑 ==========
      // 1. 先检查内存中是否有结果
      if (joinedResults.value[pdfDiskName] && joinedResults.value[pdfDiskName].length > 0) {
        console.log('使用内存中的裁切结果，跳过处理')
        ElMessage.info('已使用缓存的裁切结果')
        return {
          success: true,
          images: joinedResults.value[pdfDiskName],
          total: joinedResults.value[pdfDiskName].length,
          message: '使用缓存结果',
          fromCache: true
        }
      }

      // 2. 检查本地存储中是否有结果
      const cacheKey = pdfDiskName.replace('.pdf', '')
      const storageKey = `batch_crop_${cacheKey}`
      const cachedResult = localStorage.getItem(storageKey)

      if (cachedResult) {
        try {
          const parsedResult = JSON.parse(cachedResult)
          // 验证缓存是否有效（比如检查时间戳，这里简单检查是否有图片）
          if (parsedResult.images && parsedResult.images.length > 0) {
            console.log('使用本地存储的裁切结果')
            // 更新内存中的结果
            joinedResults.value[pdfDiskName] = parsedResult.images
            ElMessage.info('已使用缓存的裁切结果')
            return {
              ...parsedResult,
              fromCache: true
            }
          }
        } catch (e) {
          console.warn('解析缓存结果失败:', e)
          localStorage.removeItem(storageKey) // 清除无效缓存
        }
      }
      // ========== 缓存检查结束 ==========

      // 检查是否已经有转换好的PNG图片
      const pngList = convertCache[cacheKey]

      if (!pngList || pngList.length === 0) {
        throw new Error('请先转换PDF为图片再进行批量裁切')
      }

      console.log('找到PNG图片列表:', pngList.length)

      // 使用正确的后端接口
      const taskId = uuidv4()
      const response = await axios.post(getApiUrl(`/batch-cut-table/${taskId}`),
      {
        pdf_folder: cacheKey,
        png_names: pngList
      })

      console.log('批量裁切API响应:', response.data)

      if (response.data.success) {
        // 关键修改：使用 absolute_path 构建图片URL
        const baseURL = 'http://localhost:5000/'
        let imageUrls = []

        if (response.data.data && response.data.data.joined_tables_folder) {
          // 使用 absolute_path 构建URL
          const absolutePath = response.data.data.joined_tables_folder
          // 从绝对路径中提取相对路径部分
          const relativePath = extractRelativePath(absolutePath)

          // 使用 joined 数组中的文件名构建完整URL
          if (response.data.data.joined && response.data.data.joined.length > 0) {
            imageUrls = response.data.data.joined.map(filename => {
              // 从文件名中提取基本名称，构建完整路径
              const fullPath = `${relativePath}/${filename.split('/').pop()}`
              return `${baseURL}${fullPath}`
            })
          }
        } else if (response.data.data && response.data.data.joined) {
          // 备用方案：如果只有 joined 数组
          imageUrls = response.data.data.joined.map(relativePath => {
            return `${baseURL}${relativePath}`
          })
        }

        console.log('生成的完整图片URL:', imageUrls)

        // 存储到 joinedResults 中
        if (imageUrls.length > 0) {
          joinedResults.value[pdfDiskName] = imageUrls

          // ========== 新增：缓存到本地存储 ==========
          const resultToCache = {
            success: true,
            images: imageUrls,
            total: imageUrls.length,
            message: response.data.message || '批量裁切完成',
            rawResponse: response.data,
            timestamp: Date.now() // 添加时间戳以便后续验证缓存新鲜度
          }
          localStorage.setItem(storageKey, JSON.stringify(resultToCache))
          console.log('结果已缓存到本地存储')
          // ========== 缓存结束 ==========
        }

        console.log('更新后的 joinedResults:', joinedResults.value)

        ElMessage.success(`批量裁切完成，生成 ${imageUrls.length} 个表格`)

        return {
          success: true,
          images: imageUrls,
          total: imageUrls.length,
          message: response.data.message || '批量裁切完成',
          rawResponse: response.data,
          fromCache: false // 标记这不是缓存结果
        }
      } else {
        throw new Error(response.data.message || response.data.error || '批量裁切失败')
      }

    } catch (error) {
      console.error('批量裁切失败:', error)

      let errorMessage = '批量裁切失败'
      if (error.response?.data?.error) {
        errorMessage = error.response.data.error
      } else if (error.message) {
        errorMessage = error.message
      }

      ElMessage.error(errorMessage)

      return {
        success: false,
        error: errorMessage,
        images: [],
        total: 0,
        fromCache: false
      }
    } finally {
      // 清除加载状态
      batchCropLoading.value[pdfDiskName] = false
    }
  }

  // 从绝对路径提取相对路径
  function extractRelativePath(absolutePath) {
    // 根据你的项目结构，从绝对路径中提取相对路径
    // 例如: E:\Datas\base_pros\EduPDF-TableVision\backend\static\joined_tables\057bde4fe7fe351b24eb4d8b2b489c44
    // 提取为: static/joined_tables/057bde4fe7fe351b24eb4d8b2b489c44

    const paths = absolutePath.split('\\')
    // 找到 'static' 文件夹之后的部分
    const staticIndex = paths.indexOf('static')
    if (staticIndex !== -1) {
      return paths.slice(staticIndex).join('/')
    }

    // 如果找不到 static，尝试其他方式
    if (absolutePath.includes('joined_tables')) {
      const joinedIndex = paths.indexOf('joined_tables')
      if (joinedIndex !== -1) {
        return paths.slice(joinedIndex - 1).join('/') // 包含 static
      }
    }

    // 默认返回 joined_tables 部分
    return 'static/joined_tables/' + absolutePath.split('\\').pop()
  }

  // 生成简单的UUID
  function uuidv4() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0
      const v = c == 'x' ? r : (r & 0x3 | 0x8)
      return v.toString(16)
    })
  }

  // 清理指定PDF的裁切结果
  function clearResultsForPDF(pdfDiskName) {
    if (joinedResults.value[pdfDiskName]) {
      delete joinedResults.value[pdfDiskName]
    }
  }

  // 清理所有裁切结果
  function clearAllResults() {
    joinedResults.value = {}
  }

  return {
    cutTablesForPDF,
    batchCropLoading,
    clearResultsForPDF,
    clearAllResults
  }
}