<template>
  <div class="pdf-container">
    <iframe
      :src="pdfUrl"
      class="pdf-iframe"
      frameborder="0"
    ></iframe>
    <el-button
      size="small"
      circle
      icon="el-icon-close"
      class="close"
      @click="$emit('close')"
      title="关闭预览"
    />
  </div>
</template>

<script setup>
import { ref, watch, onUnmounted } from 'vue'

const props = defineProps({ file: Object })
const emit = defineEmits(['close'])

// 缓存对象，存储 fileId -> blobUrl 的映射
const pdfCache = new Map()
// 缓存最大数量，避免内存泄漏
const MAX_CACHE_SIZE = 10

const pdfUrl = ref('')

// 清理缓存函数
const clearCache = () => {
  pdfCache.forEach((blobUrl, fileId) => {
    URL.revokeObjectURL(blobUrl)
  })
  pdfCache.clear()
}

// 获取PDF文件并缓存
const loadPdfWithCache = async (file) => {
  if (!file) return ''

  const fileId = file.disk_name || file.filename

  // 检查缓存
  if (pdfCache.has(fileId)) {
    console.log('📦 使用缓存:', file.filename)
    return pdfCache.get(fileId)
  }

  try {
    const baseUrl = window.location.origin
    const apiUrl = `${baseUrl}/api/file/${fileId}`

    console.log('⬇️ 下载PDF:', file.filename)
    const response = await fetch(apiUrl)

    if (!response.ok) throw new Error('文件下载失败')

    const blob = await response.blob()
    const blobUrl = URL.createObjectURL(blob)

    // 添加到缓存
    pdfCache.set(fileId, blobUrl)

    // 清理过期的缓存（保持缓存数量在限制内）
    if (pdfCache.size > MAX_CACHE_SIZE) {
      const firstKey = pdfCache.keys().next().value
      URL.revokeObjectURL(pdfCache.get(firstKey))
      pdfCache.delete(firstKey)
      console.log('🗑️ 清理缓存:', firstKey)
    }

    return blobUrl

  } catch (error) {
    console.error('文件加载失败:', error)
    // 出错时回退到直接URL方式
    const baseUrl = window.location.origin
    return `${baseUrl}/api/file/${fileId}`
  }
}

// 原有的文件切换监听逻辑保持不变
watch(() => props.file, async (newFile) => {
  if (newFile) {
    pdfUrl.value = await loadPdfWithCache(newFile)
    console.log('📄 PDF文件切换:', newFile.filename)
  }
}, { immediate: true, deep: true })

// 组件卸载时清理缓存
onUnmounted(() => {
  clearCache()
  console.log('🧹 PDF查看器卸载，清理缓存')
})

// 原有的 getBackendUrl 导入和逻辑保持不变
import { getBackendUrl } from '@/utils/config'

// 保留原有的直接URL生成方式作为备用
const getDirectPdfUrl = (file) => {
  return getBackendUrl(`/api/file/${file.disk_name || file.filename}`)
}
</script>

<style scoped>
.pdf-container {
  position: relative;
  width: 100%;
  height: 100%;
  background: #f8f9fa;
  display: flex;
}

.pdf-iframe {
  width: 100%;
  height: 100%;
  border: none;
  flex: 1;
}

.close {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 10;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #dcdfe6;
}
</style>