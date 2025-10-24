// src/composables/useRotate.js
import { ref } from 'vue'
import { http } from '@/api/index' // 复用项目封装的http实例
import { ElMessage } from 'element-plus'

export function useRotate(previewFolder, refreshTimestamp) {
  // 存储图片旋转角度：{ 图片名: 旋转度数(如90/180/270) }
  const imageRotation = ref({})
  // 存储保存旋转状态：{ 图片名: 是否正在保存 }
  const saveLoading = ref({})

  /**
   * 旋转图片（内存中临时旋转，未保存到后端）
   * @param {string} pngName - 图片文件名
   * @param {number} angle - 旋转角度（通常为90的倍数，如90/-90）
   */
  function rotateImage(pngName, angle) {
    // 计算累计旋转角度（取模360确保在0-360范围内）
    imageRotation.value[pngName] = (imageRotation.value[pngName] || 0) + angle
    // 处理负角度（如-90转为270）
    if (imageRotation.value[pngName] < 0) {
      imageRotation.value[pngName] += 360
    }
    // 确保角度是0/90/180/270（避免超过360的无效值）
    imageRotation.value[pngName] %= 360
  }

  /**
   * 保存旋转状态到后端
   * @param {string} pngName - 图片文件名
   */
  async function saveRotatedImage(pngName) {
    saveLoading.value[pngName] = true
    try {
      const angle = imageRotation.value[pngName] || 0
      // 未旋转时无需请求后端
      if (angle === 0) {
        ElMessage.info('未进行旋转，无需保存')
        return
      }
      // 使用项目统一的http实例发送请求
      await http.post(`/api/png/rotate/${previewFolder.value}/${pngName}`, { angle })
      ElMessage.success('旋转角度已保存')
      // 重置内存中的旋转角度（已持久化到后端）
      imageRotation.value[pngName] = 0
      // 触发预览刷新（通过时间戳强制重新加载图片）
      refreshTimestamp.value = Date.now()
    } catch (error) {
      // 优先显示后端返回的错误信息
      const errorMsg = error.response?.data?.error || '保存旋转失败，请重试'
      ElMessage.error(errorMsg)
    } finally {
      // 无论成功失败，都结束加载状态
      saveLoading.value[pngName] = false
    }
  }

  return {
    imageRotation, // 旋转角度状态
    saveLoading,   // 保存加载状态
    rotateImage,   // 旋转图片方法
    saveRotatedImage // 保存旋转方法
  }
}