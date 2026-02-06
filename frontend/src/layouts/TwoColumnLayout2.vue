<template>
  <div class="two-column-layout">
    <!-- 左侧：当前PDF的预览和操作区域 -->
    <div class="left-panel">
      <!-- 文件上传区域 -->
      <div class="upload-section">
        <file-upload @uploaded="$emit('load-files')"/>
      </div>

      <!-- 当前PDF预览区域 -->
      <div class="pdf-preview-section" v-if="currentPdf">
        <PdfPreview
          :pdf-files="pdfFiles"
          :current-pdf-index="currentPdfIndex"
          :crop-loading="cropLoading"
          :crop-results="cutResults"
          :converting="convertingObj"
          :convert-cache="convertCache"
          :batch-crop-loading="batchCropLoading"
          :joined-results="joinedResults"
          :table-type="tableType"
          :llm-loading="llmLoading"
          :parsing-progress-map="parsingProgressMap"
          :screened-images-map="hasScreenedImages"
          :screening-result-map="screeningResultMap"
          @switch-pdf="$emit('switch-pdf', $event)"
          @delete="handleDeleteFile"
          @screen-images="$emit('handle-screen-images', $event)"
          @convert="$emit('convert-and-preview', $event)"
          @batch-crop="$emit('handle-batch-crop', $event)"
          @parse-tables="$emit('parse-tables', $event)"
          @clear-cache="$emit('clear-cache', $event)"
          @smart-process-pdf="handleSmartProcess"
          @close-pdf="handleCloseCurrentPdf"
          @open-classification="$emit('handle-open-classification', $event)"
        />
      </div>

      <!-- 空状态提示 -->
      <div v-else class="empty-preview">
        <el-empty description="请选择一个PDF文件开始处理" :image-size="80">
          <p class="empty-tip">从右侧文件列表中选择一个PDF文件</p>
        </el-empty>
      </div>
    </div>

    <!-- 右侧：两栏布局 -->
    <div class="right-panel">
      <!-- 上栏：当前PDF状态和进度预览（带折叠控制） -->
      <div class="status-section" :class="{ 'collapsed': fileListExpanded }">
        <div class="status-header">
          <span class="status-title">当前PDF状态</span>
          <div class="collapse-control" @click="toggleFileList">
            <i :class="fileListExpanded ? 'el-icon-arrow-up' : 'el-icon-arrow-down'"></i>
            <span>{{ fileListExpanded ? '收起文件列表' : '展开文件列表' }}</span>
          </div>
        </div>
        <CurrentPdfStatus
          :current-pdf="currentPdf"
          :converting-obj="convertingObj"
          :convert-cache="convertCache"
          :has-screened-images="hasScreenedImages"
          :screening-result-map="screeningResultMap"
          :parsing-progress-map="parsingProgressMap"
          :is-screening="isScreening"
          :is-parsing="isParsing"
          :has-results="hasResults"
          :has-batch-results="hasBatchResults"
          @convert="$emit('convert-and-preview', $event)"
          @screen-images="$emit('handle-screen-images', $event)"
          @open-classification="$emit('handle-open-classification', $event)"
          @parse-tables="$emit('parse-tables', $event)"
          @clear-cache="$emit('clear-cache', $event)"
          class="status-content"
        />
      </div>

      <!-- 下栏：所有PDF文件列表（可折叠，按状态分组） -->
      <div class="file-manager-section" :class="{ 'expanded': fileListExpanded }">
        <div class="section-header">
          <div class="header-left">
            <span class="title">PDF文件管理器</span>
            <!-- 状态统计 -->
            <div class="status-summary" v-if="files.length > 0">
              <div class="summary-item completed">
                <span class="count">{{ completedCount }}</span>
                <span class="label">已完成</span>
              </div>
              <div class="summary-item processing">
                <span class="count">{{ processingCount }}</span>
                <span class="label">处理中</span>
              </div>
              <div class="summary-item pending">
                <span class="count">{{ pendingCount }}</span>
                <span class="label">待处理</span>
              </div>
            </div>
          </div>
          <div class="table-type-selector" v-if="files.length > 0">
            <el-radio-group
              :value="tableType"
              size="small"
              @change="$emit('table-type-change', $event)"
            >
            </el-radio-group>
          </div>
        </div>

        <div class="file-list-content">
          <!-- 当前PDF（特殊标记） -->
          <div v-if="currentPdf" class="current-pdf-item highlighted">
            <div class="file-info">
              <i class="el-icon-document"></i>
              <span class="file-name">{{ currentPdf.filename }}</span>
              <el-tag size="small" type="primary" class="current-tag">当前</el-tag>
              <el-tag
                v-if="getFileProgress(currentPdf.disk_name) === 100"
                size="small"
                type="success"
                class="status-tag"
              >
                已完成
              </el-tag>
            </div>
            <div class="file-actions">
              <el-button size="small" type="text" @click="$emit('convert-and-preview', currentPdf.disk_name)">
                <i :class="getHasConvertCache(currentPdf.disk_name) ? 'el-icon-picture' : 'el-icon-picture-outline'"></i>
              </el-button>
              <el-button size="small" type="text" @click="$emit('delete-file', currentPdf)">
                <i class="el-icon-delete"></i>
              </el-button>
            </div>
          </div>

          <!-- 分组显示其他文件 -->

          <!-- 1. 已完成 -->
          <div v-if="completedFiles.length > 0" class="file-group">
            <div class="group-title completed">
              <i class="el-icon-success"></i>
              <span>已完成 ({{ completedFiles.length }})</span>
            </div>
            <div
              v-for="pdf in completedFiles"
              :key="pdf.disk_name"
              class="pdf-file-item completed"
            >
              <div class="file-info" @click="$emit('switch-pdf', pdf)">
                <i class="el-icon-document"></i>
                <span class="file-name">{{ pdf.filename }}</span>
                <div class="file-status">
                  <el-tag size="small" type="success" class="status-tag">已完成</el-tag>
                </div>
              </div>
              <div class="file-actions">
                <el-button
                  size="small"
                  type="text"
                  @click="$emit('switch-pdf', pdf)"
                  title="切换到该PDF"
                >
                  <i class="el-icon-position"></i>
                </el-button>
                <el-button
                  size="small"
                  type="text"
                  @click="$emit('delete-file', pdf)"
                  title="删除"
                >
                  <i class="el-icon-delete"></i>
                </el-button>
              </div>
            </div>
          </div>

          <!-- 2. 处理中 -->
          <div v-if="processingFiles.length > 0" class="file-group">
            <div class="group-title processing">
              <i class="el-icon-loading"></i>
              <span>处理中 ({{ processingFiles.length }})</span>
            </div>
            <div
              v-for="pdf in processingFiles"
              :key="pdf.disk_name"
              class="pdf-file-item processing"
            >
              <div class="file-info" @click="$emit('switch-pdf', pdf)">
                <i class="el-icon-document"></i>
                <span class="file-name">{{ pdf.filename }}</span>
                <div class="file-status">
                  <el-tag size="small" type="warning" class="status-tag">
                    {{ getProcessingStatus(pdf.disk_name) }}
                  </el-tag>
                </div>
              </div>
              <div class="file-actions">
                <el-button
                  size="small"
                  type="text"
                  @click="$emit('switch-pdf', pdf)"
                  title="切换到该PDF"
                >
                  <i class="el-icon-position"></i>
                </el-button>
                <el-button
                  size="small"
                  type="text"
                  @click="$emit('delete-file', pdf)"
                  title="删除"
                  :disabled="isProcessing(pdf.disk_name)"
                >
                  <i class="el-icon-delete"></i>
                </el-button>
              </div>
            </div>
          </div>

          <!-- 3. 待处理 -->
          <div v-if="pendingFiles.length > 0" class="file-group">
            <div class="group-title pending">
              <i class="el-icon-clock"></i>
              <span>待处理 ({{ pendingFiles.length }})</span>
            </div>
            <div
              v-for="pdf in pendingFiles"
              :key="pdf.disk_name"
              class="pdf-file-item pending"
            >
              <div class="file-info" @click="$emit('switch-pdf', pdf)">
                <i class="el-icon-document"></i>
                <span class="file-name">{{ pdf.filename }}</span>
                <div class="file-status">
                  <el-tag size="small" type="info" class="status-tag">待处理</el-tag>
                </div>
              </div>
              <div class="file-actions">
                <el-button
                  size="small"
                  type="text"
                  @click="$emit('convert-and-preview', pdf.disk_name)"
                  title="开始处理"
                >
                  <i class="el-icon-picture-outline"></i>
                </el-button>
                <el-button
                  size="small"
                  type="text"
                  @click="$emit('switch-pdf', pdf)"
                  title="切换到该PDF"
                >
                  <i class="el-icon-position"></i>
                </el-button>
                <el-button
                  size="small"
                  type="text"
                  @click="$emit('delete-file', pdf)"
                  title="删除"
                >
                  <i class="el-icon-delete"></i>
                </el-button>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-if="files.length === 0" class="empty-file-list">
            <el-empty description="暂无PDF文件" :image-size="60">
              <p class="empty-tip">点击上方上传按钮添加PDF文件</p>
            </el-empty>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// 导入组件
import { ref, computed, watch } from 'vue'
import FileUpload from '@/components/file/FileUpload.vue'
import PdfPreview from '@/components/pdf/PdfPreview.vue'
import CurrentPdfStatus from '@/components/pdf/CurrentPdfStatus.vue'


// 控制文件列表展开状态
const fileListExpanded = ref(false)

// 切换文件列表展开状态
const toggleFileList = () => {
  fileListExpanded.value = !fileListExpanded.value
}


// 在 TwoColumnLayout.vue 中添加
const handleSmartProcess = (pdfDiskName) => {
  console.log('📡 TwoColumnLayout 收到智能处理请求:', pdfDiskName)
  // 触发最外层父组件（TwoColumnPage）的智能处理
  emit('smart-process-pdf', pdfDiskName)
}

// 第 190 行左右，修改 handleDeleteFile 函数
const handleDeleteFile = (file) => {
  console.log('🗑️ TwoColumnLayout 处理删除:', file)
  // 修改：使用 emit 而不是 props.onDeleteFile
  emit('delete-file', file)
}

// 定义props
const props = defineProps({
  files: Array,
  cropLoading: Object,
  cutResults: Object,
  convertingObj: Object,
  convertCache: Object,
  batchCropLoading: Object,
  joinedResults: Object,
  currentExcelData: Object,
  parsingProgressMap: {
    type: Object,
    default: () => ({})
  },
  hasScreenedImages: {
    type: Object,
    default: () => ({})
  },
  screeningResultMap: {
    type: Object,
    default: () => ({})
  },
  isScreening: {
    type: Boolean,
    default: false
  },
  isParsing: {
    type: Boolean,
    default: false
  },
  hasResults: {
    type: Boolean,
    default: false
  },
  hasBatchResults: {
    type: Boolean,
    default: false
  },
  llmLoading: {
    type: Object,
    default: () => ({})
  },
  tableType: {
    type: String,
    default: 'financial'
  },
  onDeleteFile: Function,
  // ✅ 正确定义pdfFiles和currentPdfIndex
  pdfFiles: {
    type: Array,
    default: () => []
  },
  currentPdfIndex: {
    type: Number,
    default: 0
  }
})


// 定义emit事件
defineEmits([
  'load-files',
  'delete-file',
  'cutTable',
  'convert-and-preview',
  'handleBatchCrop',
  'open-llm-config',
  'handleImageSelected',
  'handleOcrCompleted',
  'handleRecognizeTable',
  'handleExcelDataReceived',
  'manuallyTriggerExcelUpdate',
  'forceRefreshExcel',
  'openVisualization',
  'saveExcelData',
  'exportAllData',
  'updateExcelContent',
  'handleScreenImages',
  'handleScreenImagesCompleted',
  'handleOpenClassification',
  'handleUpdateScreeningStatus',
  'switch-pdf',
  'clearCache',
  'parseTables',
  'tableTypeChange'
])


// 工具函数：检查是否已转图
const getHasConvertCache = computed(() => {
  return (diskName) => {
    if (!diskName) return false
    const cacheKey = diskName.replace(/\.pdf$/i, '')
    const cacheData = props.convertCache[cacheKey]
    return cacheData && Array.isArray(cacheData) && cacheData.length > 0
  }
})

// 计算文件处理进度
const getFileProgress = (diskName) => {
  if (!diskName) return 0

  let progress = 0
  const cacheKey = diskName.replace(/\.pdf$/i, '')

  // 基础分：文件上传完成
  progress += 20

  // 已转图：+30分
  const cacheData = props.convertCache[cacheKey]
  if (cacheData && Array.isArray(cacheData) && cacheData.length > 0) {
    progress += 30
  }

  // 已筛选：+30分
  if (props.hasScreenedImages[diskName]) {
    progress += 30
  }

  // 解析完成：+20分
  if (props.parsingProgressMap[diskName]?.progress === 100) {
    progress += 20
  }

  return Math.min(Math.round(progress), 100)
}

// 获取处理状态描述
const getProcessingStatus = (diskName) => {
  const hasConverted = getHasConvertCache.value(diskName)
  const hasScreened = props.hasScreenedImages[diskName]
  const parsingProgress = props.parsingProgressMap[diskName]?.progress || 0

  if (parsingProgress > 0) {
    return `解析中 ${parsingProgress}%`
  } else if (hasScreened) {
    return '已筛选'
  } else if (hasConverted) {
    return '已转图'
  }
  return '处理中'
}

// 检查文件是否正在处理中（不可删除）
const isProcessing = (diskName) => {
  return props.convertingObj[diskName] ||
         props.parsingProgressMap[diskName]?.progress > 0 ||
         props.cropLoading[diskName]
}


// 分组：已完成（进度100%）
const completedFiles = computed(() => {
  return props.otherPdfs.filter(pdf => {
    const diskName = pdf.disk_name
    return getFileProgress(diskName) === 100
  })
})

// 分组：处理中（进度>20%且<100%）
const processingFiles = computed(() => {
  return props.otherPdfs.filter(pdf => {
    const diskName = pdf.disk_name
    const progress = getFileProgress(diskName)
    return progress > 20 && progress < 100
  })
})

// 分组：待处理（进度<=20%）
const pendingFiles = computed(() => {
  return props.otherPdfs.filter(pdf => {
    const diskName = pdf.disk_name
    const progress = getFileProgress(diskName)
    return progress <= 20
  })
})




// 统计数量
const completedCount = computed(() => {
  return completedFiles.value.length +
         (props.currentPdf && getFileProgress(props.currentPdf.disk_name) === 100 ? 1 : 0)
})

const processingCount = computed(() => {
  return processingFiles.value.length +
         (props.currentPdf && getFileProgress(props.currentPdf.disk_name) > 20 &&
          getFileProgress(props.currentPdf.disk_name) < 100 ? 1 : 0)
})

const pendingCount = computed(() => {
  return pendingFiles.value.length +
         (props.currentPdf && getFileProgress(props.currentPdf.disk_name) <= 20 ? 1 : 0)
})

// 处理关闭当前PDF
const handleCloseCurrentPdf = () => {
  console.log('关闭当前PDF预览')
}



const currentPdf = computed(() => {
  if (!props.pdfFiles || !Array.isArray(props.pdfFiles) || props.pdfFiles.length === 0) return null
  if (props.currentPdfIndex < 0 || props.currentPdfIndex >= props.pdfFiles.length) return null
  return props.pdfFiles[props.currentPdfIndex]
})


const otherPdfs = computed(() => {
  if (!props.pdfFiles || !Array.isArray(props.pdfFiles) || props.pdfFiles.length === 0) return []
  return props.pdfFiles.filter((_, index) => index !== props.currentPdfIndex)
})


// 添加watch监听
watch(() => props.currentPdf, (newPdf, oldPdf) => {
  console.log('🔄 currentPdf变化:', {
    from: oldPdf?.disk_name,
    to: newPdf?.disk_name
  })

  if (newPdf && newPdf.disk_name !== oldPdf?.disk_name) {
    console.log('📄📄 TwoColumnLayout: PDF发生变化', {
      from: oldPdf?.filename,
      to: newPdf.filename
    })
  }
}, { immediate: true })



</script>

<style scoped>
.two-column-layout {
  display: flex;
  height: 100vh;
  gap: 16px;
  padding: 16px;
  background: #f5f5f5;
  overflow: hidden;
}

/* 左侧面板 */
.left-panel {
  flex: 1.5;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.upload-section {
  padding: 12px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
}

.pdf-preview-section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.empty-preview {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 40px;
}

.empty-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

/* 右侧面板 */
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

/* 上栏：当前PDF状态（带折叠控制） */
.status-section {
  flex: 1;
  min-height: 300px;
  max-height: 500px;
  transition: all 0.3s ease;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
  flex-shrink: 0;
}

.status-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.collapse-control {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: #f0f9ff;
  border: 1px solid #b3e0ff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: #409eff;
  transition: all 0.2s;
}

.collapse-control:hover {
  background: #e6f7ff;
  border-color: #409eff;
}

.collapse-control i {
  font-size: 12px;
  transition: transform 0.3s;
}

.status-section.collapsed .collapse-control i {
  transform: rotate(180deg);
}

.status-section.collapsed {
  flex: 0 0 120px;
  max-height: 120px;
  overflow: hidden;
}

.status-content {
  flex: 1;
  overflow: hidden;
  padding: 16px;
}

/* 下栏：PDF文件管理器 */
.file-manager-section {
  flex: 0 0 200px;
  max-height: 300px;
  display: flex;
  flex-direction: column;
  border-top: 1px solid #e4e7ed;
  transition: all 0.3s ease;
  overflow: hidden;
}

.file-manager-section.expanded {
  flex: 1;
  max-height: 100%;
}

/* 增强的头部 */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.section-header .title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
}

/* 状态统计 */
.status-summary {
  display: flex;
  gap: 8px;
  align-items: center;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
}

.summary-item.completed {
  background: #f0f9eb;
  border: 1px solid #c2e7b0;
}

.summary-item.processing {
  background: #fdf6ec;
  border: 1px solid #f5dab1;
}

.summary-item.pending {
  background: #f4f4f5;
  border: 1px solid #dcdcdc;
}

.summary-item .count {
  font-weight: 600;
}

.summary-item.completed .count {
  color: #67c23a;
}

.summary-item.processing .count {
  color: #e6a23c;
}

.summary-item.pending .count {
  color: #909399;
}

.summary-item .label {
  color: #606266;
}

.table-type-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-list-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

/* 分组标题 */
.file-group {
  margin-bottom: 12px;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px 6px 12px;
  font-size: 12px;
  font-weight: 600;
  border-radius: 4px;
  margin-bottom: 6px;
}

.group-title i {
  font-size: 14px;
}

.group-title.completed {
  color: #67c23a;
  background: #f0f9eb;
}

.group-title.processing {
  color: #e6a23c;
  background: #fdf6ec;
}

.group-title.pending {
  color: #909399;
  background: #f4f4f5;
}

/* PDF文件项样式 */
.current-pdf-item,
.pdf-file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  margin-bottom: 4px;
  border-radius: 6px;
  transition: all 0.2s;
  cursor: pointer;
}

.current-pdf-item {
  background: #f0f9ff;
  border: 1px solid #b3e0ff;
}

.current-pdf-item.highlighted {
  background: linear-gradient(135deg, #f0f9ff 0%, #e6f7ff 100%);
}

.pdf-file-item.completed {
  border-left: 3px solid #67c23a;
  background: #f0f9eb;
}

.pdf-file-item.processing {
  border-left: 3px solid #e6a23c;
  background: #fdf6ec;
}

.pdf-file-item.pending {
  border-left: 3px solid #909399;
  background: #f4f4f5;
}

.pdf-file-item:hover {
  background: #f5f7fa !important;
}

.file-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.file-info i {
  color: #409eff;
  flex-shrink: 0;
}

.file-name {
  flex: 1;
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-status {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.current-tag,
.status-tag {
  font-size: 10px;
  height: 18px;
  line-height: 18px;
  padding: 0 4px;
}

.file-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.file-actions .el-button {
  padding: 4px;
  min-height: auto;
}

.empty-file-list {
  padding: 40px 20px;
  text-align: center;
}

.empty-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

/* 滚动条样式 */
.file-list-content::-webkit-scrollbar {
  width: 6px;
}

.file-list-content::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.file-list-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.file-list-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 当状态区域被压缩时的样式 */
.status-section.collapsed .status-content {
  padding: 8px 16px;
}

.status-section.collapsed .status-content :deep(.current-pdf-status .header) {
  display: none; /* 隐藏头部 */
}

.status-section.collapsed .status-content :deep(.current-pdf-status .status-items) {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.status-section.collapsed .status-content :deep(.current-pdf-status .status-item) {
  margin-bottom: 0;
  padding: 6px;
}

.status-section.collapsed .status-content :deep(.current-pdf-status .action-buttons) {
  display: none; /* 隐藏操作按钮 */
}
</style>