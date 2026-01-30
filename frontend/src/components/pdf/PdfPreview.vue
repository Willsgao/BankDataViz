<template>
  <div class="pdf-preview-container">
    <div v-if="selectedPdf" class="pdf-viewer">
      <div class="pdf-header">
        <h3>{{ selectedPdf.name }}</h3>
        <div class="header-actions">
          <el-button
            type="primary"
            size="small"
            @click="$emit('download-pdf', selectedPdf)"
            :loading="downloadLoading"
          >
            <el-icon><Download /></el-icon>
            下载PDF
          </el-button>
        </div>
      </div>
      <div class="pdf-content">
        <!-- PDF.js渲染区域 -->
        <div v-if="pdfDocument" class="pdf-render-area">
          <canvas ref="pdfCanvas"></canvas>

          <!-- 页面导航控件 -->
          <div class="page-navigation">
            <el-button
              size="small"
              :disabled="currentPage <= 1"
              @click="handlePageChange(currentPage - 1)"
            >
              <el-icon><ArrowLeft /></el-icon>
            </el-button>

            <span class="page-info">第 {{ currentPage }} 页 / 共 {{ totalPages }} 页</span>

            <el-button
              size="small"
              :disabled="currentPage >= totalPages"
              @click="handlePageChange(currentPage + 1)"
            >
              <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>
        </div>

        <div v-else-if="loadingPdf" class="loading-state">
          <el-icon class="is-loading"><Loading /></el-icon>
          加载PDF中...
        </div>

        <div v-else class="no-preview">
          <el-icon><Document /></el-icon>
          <p>无法加载PDF预览</p>
        </div>
      </div>
    </div>

    <div v-else class="pdf-placeholder">
      <el-icon><Document /></el-icon>
      <p>请从右侧选择PDF文件进行预览</p>
    </div>
  </div>
</template>

<script setup>
import { Download, Document, Loading, ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import { ref, defineProps, defineEmits, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  selectedPdf: Object,
  pdfUrl: String,
  currentPage: {
    type: Number,
    default: 1
  },
  downloadLoading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['download-pdf', 'pdf-loaded', 'page-change'])

// PDF.js相关变量
const pdfCanvas = ref(null)
const pdfDocument = ref(null)
const loadingPdf = ref(false)
const totalPages = ref(0)
const scale = ref(1.5)

// 暴露给父组件的方法 - 真正的无刷新跳转
const jumpToPage = async (pageNumber) => {
  if (!pdfDocument.value || pageNumber < 1 || pageNumber > totalPages.value) {
    console.warn('❌ 跳转参数无效')
    return false
  }

  try {
    await renderPage(pageNumber)
    console.log(`✅ PDF页面无刷新跳转成功: 第${pageNumber}页`)
    emit('page-change', pageNumber)
    return true
  } catch (error) {
    console.error('❌ PDF页面跳转失败:', error)
    return false
  }
}

// 渲染指定页面 - 无网络请求
const renderPage = async (pageNum) => {
  const page = await pdfDocument.value.getPage(pageNum)
  const canvas = pdfCanvas.value
  const ctx = canvas.getContext('2d')

  const viewport = page.getViewport({ scale: scale.value })
  canvas.width = viewport.width
  canvas.height = viewport.height

  const renderContext = {
    canvasContext: ctx,
    viewport: viewport
  }

  await page.render(renderContext).promise
}

// 本地页面切换处理
const handlePageChange = (newPage) => {
  if (newPage >= 1 && newPage <= totalPages.value) {
    jumpToPage(newPage)
  }
}

// 加载PDF文档 - 只执行一次
const loadPdf = async () => {
  if (!props.pdfUrl) return

  try {
    loadingPdf.value = true

    // 动态导入PDF.js
    const pdfjsLib = await import('pdfjs-dist')

    // 设置worker路径
    const pdfjsVersion = '3.11.174'
    pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsVersion}/pdf.worker.min.js`

    // 加载PDF文档（只执行一次）
    const loadingTask = pdfjsLib.getDocument(props.pdfUrl)
    pdfDocument.value = await loadingTask.promise
    totalPages.value = pdfDocument.value.numPages

    // 初始渲染当前页面
    await renderPage(props.currentPage)
    loadingPdf.value = false

    emit('pdf-loaded')
    console.log('✅ PDF加载完成，总页数:', totalPages.value)

  } catch (error) {
    console.error('❌ PDF加载失败:', error)
    loadingPdf.value = false
  }
}

// 监听PDF URL变化（只在PDF切换时重新加载）
watch(() => props.pdfUrl, (newUrl, oldUrl) => {
  if (newUrl && newUrl !== oldUrl) {
    console.log('🔄 切换PDF文件，重新加载')
    loadPdf()
  }
}, { immediate: true })

// 监听页面变化（无刷新跳转）
watch(() => props.currentPage, (newPage, oldPage) => {
  if (pdfDocument.value && newPage >= 1 && newPage <= totalPages.value && newPage !== oldPage) {
    console.log('🔄 接收到页面跳转请求:', newPage)
    jumpToPage(newPage)
  }
})

// 清理资源
onUnmounted(() => {
  if (pdfDocument.value) {
    pdfDocument.value.destroy()
    console.log('🧹 PDF资源已清理')
  }
})

// 暴露方法给父组件
defineExpose({
  jumpToPage,
  getTotalPages: () => totalPages.value,
  getCurrentPage: () => props.currentPage
})
</script>

<style scoped>
.pdf-preview-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.pdf-viewer {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.pdf-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #fafafa;
  border-bottom: 1px solid #e4e7ed;
}

.pdf-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pdf-content {
  flex: 1;
  min-height: 0;
  background: #f8f9fa;
  display: flex;
  flex-direction: column;
}

.pdf-render-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: auto;
  padding: 20px;
}

.pdf-render-area canvas {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border: 1px solid #e0e0e0;
  max-width: 100%;
  height: auto;
}

.page-navigation {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 16px;
  padding: 8px 16px;
  background: white;
  border-radius: 6px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.page-info {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}

.loading-state .el-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.no-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}

.no-preview .el-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.pdf-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
  text-align: center;
  padding: 20px;
}

.pdf-placeholder .el-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}
</style>