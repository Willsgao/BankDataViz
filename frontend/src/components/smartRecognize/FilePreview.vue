<template>
  <div class="file-preview">
    <!-- 上传区（无文件时） -->
    <div v-if="!currentFile && !imageSrc" class="upload-zone" @click="triggerUpload">
      <el-icon class="upload-icon"><UploadFilled /></el-icon>
      <div class="upload-text">点击上传文件</div>
      <div class="upload-hint">支持 PDF、Excel、图片（上传后自动检测表格区域）</div>
      <input
        ref="fileInputRef"
        type="file"
        accept=".pdf,.xlsx,.xls,.csv,.png,.jpg,.jpeg,.gif,.bmp"
        style="display:none"
        @change="onFileSelected"
      />
    </div>

    <!-- 预览区（有文件时） -->
    <div v-else class="preview-container">
      <!-- 文件信息栏 -->
      <div class="file-info-bar">
        <span class="file-name">{{ currentFile?.name || '检测结果' }}</span>
        <el-tag size="small" :type="fileTypeTag" effect="plain">{{ fileTypeLabel }}</el-tag>
        <span v-if="detectionInfo" class="detection-info">
          <el-icon color="#67c23a"><SuccessFilled /></el-icon>
          检测到 {{ detectionInfo.total_tables }} 个表格
        </span>
        <el-button size="small" text type="primary" @click="triggerUpload">更换文件</el-button>
        <el-button v-if="imageSrc" size="small" text type="primary" @click="autoScrollPreview">
          <el-icon><Rank /></el-icon>自动滚动预览
        </el-button>
        <input
          ref="fileInputRef"
          type="file"
          accept=".pdf,.xlsx,.xls,.csv,.png,.jpg,.jpeg,.gif,.bmp"
          style="display:none"
          @change="onFileSelected"
        />
      </div>

      <!-- 预览内容（AreaSelector 会覆盖在这里） -->
      <div class="preview-area" ref="previewAreaRef">
        <AreaSelector
          ref="areaSelectorRef"
          :enabled="!processing"
          :image-src="imageSrc"
          :initial-boxes="initialBoxes"
          :loading="processing"
          :loading-text="processingText"
          @confirm="onBoxesConfirmed"
        />
      </div>

      <!-- 左右大号翻页按钮（多页 PDF 时） -->
      <template v-if="totalPages > 1">
        <!-- 左侧上一页 -->
        <button
          v-show="currentPage > 0"
          class="page-flip-btn page-flip-prev"
          @click="switchPage(-1)"
          title="上一页"
        >‹</button>

        <!-- 右侧下一页 -->
        <button
          v-show="currentPage < totalPages - 1"
          class="page-flip-btn page-flip-next"
          @click="switchPage(1)"
          title="下一页"
        >›</button>

        <!-- 页码指示器 -->
        <div class="page-indicator-overlay">{{ currentPage + 1 }} / {{ totalPages }}</div>
      </template>
    </div>

    <!-- 错误提示 -->
    <div v-if="errorMsg" class="error-bar">
      <el-icon color="#f56c6c"><WarningFilled /></el-icon>
      <span>{{ errorMsg }}</span>
      <el-button size="small" text @click="errorMsg = ''">关闭</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled, SuccessFilled, WarningFilled, Rank } from '@element-plus/icons-vue'
import { detectTables } from '@/api/smartRecognize'
import AreaSelector from './AreaSelector.vue'

const emit = defineEmits([
  'file-loaded',      // { file, type, imageSrc, detectionInfo }
  'boxes-confirmed',  // [{ id, label, x, y, w, h, image_base64 }]
])

// ---- Refs ----
const fileInputRef = ref(null)
const areaSelectorRef = ref(null)
const previewAreaRef = ref(null)

// ---- 状态 ----
const currentFile = ref(null)
const currentFileMeta = ref({ name: '', size: 0 }) // 用于检测重复上传
const fileType = ref('')   // 'pdf' | 'excel' | 'image'
const imageSrc = ref('')    // 当前显示的渲染图片
const processing = ref(false)
const processingText = ref('')
const errorMsg = ref('')
const currentPage = ref(0)
const totalPages = ref(0)
const detectionInfo = ref(null) // 后端返回的检测结果
const pageBoxes = ref(new Map()) // 每页的框，独立存储

// ---- 计算属性 ----
const fileTypeLabel = computed(() => {
  const map = { pdf: 'PDF', excel: 'Excel', image: '图片' }
  return map[fileType.value] || '未知'
})

const fileTypeTag = computed(() => {
  const map = { pdf: 'warning', excel: 'success', image: '' }
  return map[fileType.value] || 'info'
})

const initialBoxes = computed(() => {
  if (!detectionInfo.value) return []
  const pageInfo = detectionInfo.value.pages?.find(p => p.page_idx === currentPage.value)
  if (!pageInfo) return []
  return pageInfo.tables.map((t, i) => ({
    id: `detected-${currentPage.value}-${t.id}`,
    label: `选区 ${i + 1}`,
    x: t.bbox_pixel?.[0] || t.bbox_pdf?.[0] || 0,
    y: t.bbox_pixel?.[1] || t.bbox_pdf?.[1] || 0,
    w: t.bbox_pixel ? t.bbox_pixel[2] - t.bbox_pixel[0] : 100,
    h: t.bbox_pixel ? t.bbox_pixel[3] - t.bbox_pixel[1] : 80,
    bbox_pdf: t.bbox_pdf,
    bbox_pixel: t.bbox_pixel,
  }))
})

const pageTableCount = computed(() => {
  const pageInfo = detectionInfo.value?.pages?.find(p => p.page_idx === currentPage.value)
  return pageInfo?.table_count || 0
})

// ---- 上传入口 ----
function triggerUpload() {
  fileInputRef.value?.click()
}

// ---- 文件选择 ----
async function onFileSelected(e) {
  const file = e.target.files?.[0]
  if (!file) return
  e.target.value = ''

  // 检测重复上传（文件名 + 文件大小都相同）
  if (file.name === currentFileMeta.value.name && file.size === currentFileMeta.value.size) {
    const confirmed = await ElMessageBox.confirm(
      `"${file.name}" 已经打开，是否重新上传并检测？`,
      '文件已存在',
      { confirmButtonText: '重新检测', cancelButtonText: '取消', type: 'warning' }
    ).catch(() => false)
    if (!confirmed) return
  }

  errorMsg.value = ''
  currentFileMeta.value = { name: file.name, size: file.size }
  currentFile.value = file

  const ext = file.name.split('.').pop().toLowerCase()
  if (['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'].includes(ext)) {
    fileType.value = 'image'
    // 图片直接本地显示，无需后端处理
    imageSrc.value = URL.createObjectURL(file)
    detectionInfo.value = null
    totalPages.value = 1
    currentPage.value = 0
    emit('file-loaded', {
      file,
      type: 'image',
      imageSrc: imageSrc.value,
      detectionInfo: null,
    })
  } else {
    // PDF / Excel → 上传到后端检测
    await uploadAndDetect(file)
  }
}

// ---- 上传到后端检测表格 ----
async function uploadAndDetect(file) {
  processing.value = true
  processingText.value = '上传文件并检测表格区域...'
  errorMsg.value = ''

  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('dpi', '150')

    const res = await detectTables(formData)

    if (res.success) {
      detectionInfo.value = res

      // 取第一页渲染图显示
      const firstPage = res.pages?.[0]
      if (firstPage?.render?.image_base64) {
        imageSrc.value = firstPage.render.image_base64
        totalPages.value = res.total_pages
        currentPage.value = 0
      } else if (fileType.value === 'excel') {
        // Excel 没有 render image，从 data URL 显示
        imageSrc.value = URL.createObjectURL(file)
        totalPages.value = res.total_pages || 1
        currentPage.value = 0
      } else {
        imageSrc.value = ''
        ElMessage.warning('未能获取渲染图，请尝试其他文件')
      }

      emit('file-loaded', {
        file,
        type: fileType.value,
        imageSrc: imageSrc.value,
        detectionInfo: res,
      })

      // 重置每页框存储
      pageBoxes.value = new Map()

      // AreaSelector 的 watch(initialBoxes) 会自动初始化第一页的框
      if (res.cached) {
        ElMessage.success(`[缓存] 检测到 ${res.total_tables} 个表格（文件未变动，直接复用）`)
      } else if (res.total_tables === 0) {
        ElMessage.info('未自动检测到表格区域，请手动框选')
      } else {
        ElMessage.success(`检测到 ${res.total_tables} 个表格，可拖拽调整区域`)
      }
    } else {
      errorMsg.value = res.error || '检测失败'
      ElMessage.error('表格检测失败: ' + (res.error || ''))
    }
  } catch (err) {
    console.error('上传检测失败:', err)
    errorMsg.value = err.message || '网络请求失败'
    ElMessage.error('上传失败: ' + (err.message || ''))
  } finally {
    processing.value = false
    processingText.value = ''
  }
}

// ---- 翻页（多页 PDF） ----
async function switchPage(delta) {
  const newPage = currentPage.value + delta
  if (newPage < 0 || newPage >= totalPages.value) return

  // 保存当前页的框到 Map
  if (areaSelectorRef.value) {
    const currentBoxes = areaSelectorRef.value.getCurrentBoxes()
    pageBoxes.value.set(currentPage.value, currentBoxes)
  }

  currentPage.value = newPage
  const pageInfo = detectionInfo.value?.pages?.find(p => p.page_idx === newPage)

  if (pageInfo?.render?.image_base64) {
    imageSrc.value = pageInfo.render.image_base64
    processing.value = true
    processingText.value = '加载页面...'
    setTimeout(() => {
      processing.value = false
    }, 100)
  }

  // 加载新页的框（从 Map 恢复，或等 watcher 自动注入）
  await nextTick()
  if (areaSelectorRef.value) {
    const savedBoxes = pageBoxes.value.get(newPage)
    if (savedBoxes && savedBoxes.length > 0) {
      areaSelectorRef.value.loadPageBoxes(savedBoxes)
    }
  }
}

// ---- 框选确认 ----
function onBoxesConfirmed(confirmedItems) {
  emit('boxes-confirmed', confirmedItems)
}

// ---- 自动滚动预览 ----
async function autoScrollPreview() {
  await nextTick()
  const areaSelector = areaSelectorRef.value
  if (!areaSelector) return

  // 调用 AreaSelector 暴露的 autoScrollPreview 方法
  if (typeof areaSelector.autoScrollPreview === 'function') {
    await areaSelector.autoScrollPreview()
  } else {
    ElMessage.warning('自动滚动功能暂不可用')
  }
}

// 监听 imageSrc 变化，加载后自动滚动一次
watch(imageSrc, async (src) => {
  if (!src) return
  await nextTick()
  // 等图片真正渲染完再滚动
  setTimeout(() => autoScrollPreview(), 1200)
})

// ---- 暴露方法 ----
function getAreaSelector() {
  return areaSelectorRef.value
}

// 供外部获取当前页已确认的截图
function getCurrentPageConfirmedItems() {
  return areaSelectorRef.value?.getConfirmedBoxes() || []
}

function reset() {
  currentFile.value = null
  currentFileMeta.value = { name: '', size: 0 }
  fileType.value = ''
  imageSrc.value = ''
  detectionInfo.value = null
  currentPage.value = 0
  totalPages.value = 0
  errorMsg.value = ''
  pageBoxes.value = new Map()
}

// ---- 键盘翻页 ----
function handleKeydown(e) {
  if (!totalPages.value) return
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
  if (e.key === 'ArrowLeft') switchPage(-1)
  if (e.key === 'ArrowRight') switchPage(1)
}
onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))

defineExpose({ getAreaSelector, reset, getCurrentPageConfirmedItems })
</script>

<style scoped>
.file-preview {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 0;
}

/* 上传区 */
.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  padding: 48px 20px;
  cursor: pointer;
  transition: border-color 0.2s;
  height: 100%;
  min-height: 300px;
}

.upload-zone:hover {
  border-color: #1890ff;
}

.upload-icon {
  font-size: 48px;
  color: #909399;
  margin-bottom: 12px;
}

.upload-text {
  font-size: 16px;
  color: #303133;
  margin-bottom: 8px;
}

.upload-hint {
  font-size: 12px;
  color: #909399;
}

/* 预览区 */
.preview-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  position: relative;
}

.file-info-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: #f0f2f5;
  border-radius: 6px 6px 0 0;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.file-name {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detection-info {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #67c23a;
  background: #f0f9eb;
  padding: 2px 8px;
  border-radius: 10px;
}

.preview-area {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* 大号翻页三角按钮 */
.page-flip-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 20;
  width: 44px;
  height: 80px;
  border: none;
  border-radius: 8px;
  background: rgba(64, 158, 255, 0.18);
  color: #409eff;
  font-size: 36px;
  font-weight: 300;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, opacity 0.2s;
  user-select: none;
  line-height: 1;
}

.page-flip-btn:hover {
  background: rgba(64, 158, 255, 0.32);
}

.page-flip-btn:active {
  background: rgba(64, 158, 255, 0.45);
}

.page-flip-prev {
  left: 12px;
}

.page-flip-next {
  right: 12px;
}

/* 页码指示器浮层 */
.page-indicator-overlay {
  position: absolute;
  bottom: 14px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 20;
  padding: 4px 14px;
  background: rgba(0, 0, 0, 0.52);
  color: #fff;
  font-size: 13px;
  border-radius: 14px;
  pointer-events: none;
  user-select: none;
}




/* 错误栏 */
.error-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #fef0f0;
  color: #f56c6c;
  font-size: 12px;
  border-radius: 4px;
  margin-top: 4px;
}
</style>
