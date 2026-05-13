<template>
  <div class="two-column-layout">
    <!-- 左侧：当前PDF的预览和操作区域 -->
    <div class="left-panel">
      <!-- PDF 上传区域 -->
      <div class="upload-section">
        <file-upload @uploaded="$emit('load-files')" />
      </div>

      <!-- 当前PDF预览区域 -->
      <div
        v-if="currentPdf"
        class="pdf-preview-section"
      >
        <PdfPreview
          :pdf-files="files"
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
          :persistent-file-status="persistentFileStatus"
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
      <div
        v-else
        class="empty-preview"
      >
        <el-empty
          description="请选择一个PDF文件开始处理"
          :image-size="80"
        >
          <p class="empty-tip">
            从右侧文件列表中选择一个PDF文件
          </p>
        </el-empty>
      </div>
    </div>

    <!-- 右侧：两栏布局 -->
    <div class="right-panel">
      <!-- 上栏：当前PDF状态和进度预览（带折叠控制） -->
      <div
        class="status-section"
        :class="{ 'collapsed': fileListExpanded }"
      >
        <div class="status-header">
          <span class="status-title">当前PDF状态</span>
          <div
            class="collapse-control"
            @click="toggleFileList"
          >
            <i :class="fileListExpanded ? 'el-icon-arrow-up' : 'el-icon-arrow-down'" />
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
          :persistent-file-status="persistentFileStatus"
          class="status-content"
          @convert="$emit('convert-and-preview', $event)"
          @screen-images="$emit('handle-screen-images', $event)"
          @open-classification="$emit('handle-open-classification', $event)"
          @parse-tables="$emit('parse-tables', $event)"
          @clear-cache="$emit('clear-cache', $event)"
        />
      </div>

      <!-- 下栏：所有PDF文件列表（可折叠，按状态分组） -->
      <div
        class="file-manager-section"
        :class="{ 'expanded': fileListExpanded }"
      >
        <div class="section-header">
          <div class="header-left">
            <span class="title">PDF文件管理器</span>
            <!-- 状态统计 -->
            <div
              v-if="files.length > 0"
              class="status-summary"
            >
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
          <div class="header-right">
            <!-- 搜索任务输入框 -->
            <el-input
              v-model="taskSearchKeyword"
              size="small"
              placeholder="搜索任务..."
              prefix-icon="el-icon-search"
              clearable
              style="width: 160px; margin-right: 10px;"
              @keyup.enter="handleSearchTasks"
              @clear="handleClearSearch"
            >
              <template #append>
                <el-button
                  icon="el-icon-search"
                  @click="handleSearchTasks"
                />
              </template>
            </el-input>

            <!-- 新增：查看解析进度按钮 -->
            <el-button
              size="small"
              type="text"
              icon="el-icon-data-line"
              class="progress-monitor-btn"
              title="查看所有PDF的解析进度"
              @click="$emit('show-progress-dialog')"
            >
              解析进度
              <el-badge
                v-if="activeTaskCount > 0"
                :value="activeTaskCount"
                :max="99"
                class="task-badge"
              />
            </el-button>

            <div
              v-if="files.length > 0"
              class="table-type-selector"
            >
              <el-radio-group
                :value="tableType"
                size="small"
                @change="$emit('table-type-change', $event)"
              />
            </div>
          </div>
        </div>

        <div class="file-list-content">
          <!-- 当前PDF（特殊标记） -->
          <div
            v-if="currentPdf"
            class="current-pdf-item highlighted"
          >
            <div class="file-info">
              <i class="el-icon-document" />
              <span class="file-name">{{ currentPdf.filename }}</span>
              <el-tag
                size="small"
                type="primary"
                class="current-tag"
              >
                当前
              </el-tag>
              <el-tag
                v-if="getFileProgress(currentPdf.disk_name) === 100"
                size="small"
                type="success"
                class="status-tag"
              >
                {{ getProcessingStatus(currentPdf.disk_name) }}
              </el-tag>
            </div>
            <div class="file-actions">
              <el-button
                size="small"
                type="text"
                @click="$emit('convert-and-preview', currentPdf.disk_name)"
              >
                <i :class="getHasConvertCache(currentPdf.disk_name) ? 'el-icon-picture' : 'el-icon-picture-outline'" />
              </el-button>
              <el-button
                size="small"
                type="text"
                @click="$emit('delete-file', currentPdf)"
              >
                <i class="el-icon-delete" />
              </el-button>
            </div>
          </div>

          <!-- 分组显示其他文件 -->

          <!-- 1. 已完成 -->
          <div
            v-if="completedFiles.length > 0"
            class="file-group"
          >
            <div class="group-title completed">
              <i class="el-icon-success" />
              <span>已完成 ({{ completedFiles.length }})</span>
            </div>
            <div
              v-for="pdf in completedFiles"
              :key="pdf.disk_name"
              class="pdf-file-item completed"
            >
              <div
                class="file-info"
                @click="$emit('switch-pdf', pdf)"
              >
                <i class="el-icon-document" />
                <span class="file-name">{{ pdf.filename }}</span>
                <div class="file-status">
                  <el-tag
                    size="small"
                    type="success"
                    class="status-tag"
                  >
                    {{ getProcessingStatus(pdf.disk_name) }}
                  </el-tag>
                </div>
              </div>
              <div class="file-actions">
                <el-button
                  size="small"
                  type="text"
                  title="切换到该PDF"
                  @click="$emit('switch-pdf', pdf)"
                >
                  <i class="el-icon-position" />
                </el-button>
                <el-button
                  size="small"
                  type="text"
                  title="删除"
                  @click="$emit('delete-file', pdf)"
                >
                  <i class="el-icon-delete" />
                </el-button>
              </div>
            </div>
          </div>

          <!-- 2. 处理中 -->
          <div
            v-if="processingFiles.length > 0"
            class="file-group"
          >
            <div class="group-title processing">
              <i class="el-icon-loading" />
              <span>处理中 ({{ processingFiles.length }})</span>
            </div>
            <div
              v-for="pdf in processingFiles"
              :key="pdf.disk_name"
              class="pdf-file-item processing"
            >
              <div
                class="file-info"
                @click="$emit('switch-pdf', pdf)"
              >
                <i class="el-icon-document" />
                <span class="file-name">{{ pdf.filename }}</span>
                <div class="file-status">
                  <el-tag
                    size="small"
                    type="warning"
                    class="status-tag"
                  >
                    {{ getProcessingStatus(pdf.disk_name) }}
                  </el-tag>
                </div>
              </div>
              <div class="file-actions">
                <el-button
                  size="small"
                  type="text"
                  title="切换到该PDF"
                  @click="$emit('switch-pdf', pdf)"
                >
                  <i class="el-icon-position" />
                </el-button>
                <el-button
                  size="small"
                  type="text"
                  title="删除"
                  :disabled="isProcessing(pdf.disk_name)"
                  @click="$emit('delete-file', pdf)"
                >
                  <i class="el-icon-delete" />
                </el-button>
              </div>
            </div>
          </div>

          <!-- 3. 待处理 -->
          <div
            v-if="pendingFiles.length > 0"
            class="file-group"
          >
            <div class="group-title pending">
              <i class="el-icon-clock" />
              <span>待处理 ({{ pendingFiles.length }})</span>
            </div>
            <div
              v-for="pdf in pendingFiles"
              :key="pdf.disk_name"
              class="pdf-file-item pending"
            >
              <div
                class="file-info"
                @click="$emit('switch-pdf', pdf)"
              >
                <i class="el-icon-document" />
                <span class="file-name">{{ pdf.filename }}</span>
                <div class="file-status">
                  <el-tag
                    size="small"
                    type="info"
                    class="status-tag"
                  >
                    待处理
                  </el-tag>
                </div>
              </div>
              <div class="file-actions">
                <el-button
                  size="small"
                  type="text"
                  title="开始处理"
                  @click="$emit('convert-and-preview', pdf.disk_name)"
                >
                  <i class="el-icon-picture-outline" />
                </el-button>
                <el-button
                  size="small"
                  type="text"
                  title="切换到该PDF"
                  @click="$emit('switch-pdf', pdf)"
                >
                  <i class="el-icon-position" />
                </el-button>
                <el-button
                  size="small"
                  type="text"
                  title="删除"
                  @click="$emit('delete-file', pdf)"
                >
                  <i class="el-icon-delete" />
                </el-button>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <div
            v-if="files.length === 0"
            class="empty-file-list"
          >
            <el-empty
              description="暂无PDF文件"
              :image-size="60"
            >
              <p class="empty-tip">
                点击上方上传按钮添加PDF文件
              </p>
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
import { Upload } from '@element-plus/icons-vue'

// Tab 切换状态 (已移除成品文件Tab，只保留待处理文件)

// 控制文件列表展开状态
const fileListExpanded = ref(false)
const taskSearchKeyword = ref('')  // 任务搜索关键词

// 搜索任务
const handleSearchTasks = () => {
  if (taskSearchKeyword.value) {
    // 触发搜索事件，让父组件打开弹窗并传入搜索关键词
    emit('search-tasks', taskSearchKeyword.value)
  }
}

// 清除搜索
const handleClearSearch = () => {
  taskSearchKeyword.value = ''
  emit('clear-task-search')
}

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
  currentPdfIndex: {
    type: Number,
    default: 0
  },
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
  currentPdf: {
    type: Object,
    default: null
  },
  otherPdfs: {
    type: Array,
    default: () => []
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
  persistentFileStatus: {  // ✅ 新增
    type: Object,
    default: () => ({})
  },
  stepStatuses: {
    type: Object,
    default: () => ({})
  }
})


// 定义emit事件
defineEmits([
  'load-files',
  'load-excel-files',
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
  'parse-tables',
  'parseTables',
  'tableTypeChange',
  'show-progress-dialog',
  'search-tasks',
  'clear-task-search'
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


// 计算属性：活跃任务数量
const activeTaskCount = computed(() => {
  if (!props.parsingProgressMap) return 0

  let count = 0
  Object.values(props.parsingProgressMap).forEach(task => {
    if (task) {
      const status = task.status || task.original_status
      if (status === 'processing' || status === 'queued') {
        count++
      }
    }
  })
  return count
})


// 修复第434行的 getFileProgress 函数
const getFileProgress = (diskName) => {
  if (!diskName) return 0

  // ✅ 1. 首先检查持久化状态
  const persistentStatus = props.persistentFileStatus?.[diskName]
  if (persistentStatus && persistentStatus.status === 'completed') {
    return 100
  }

  // ✅ 2. 检查步骤完成时间 - 添加安全访问
  const stepTimes = props.stepCompletionTime?.[diskName]  // 添加 ?. 可选链
  if (stepTimes) {
    // 如果有解析完成时间，表示100%完成
    if (stepTimes.parse) {
      return 100
    }
    // 如果有筛选完成时间，表示至少50%完成
    if (stepTimes.screen) {
      return 50
    }
    // 如果有转图完成时间，表示至少20%完成
    if (stepTimes.convert) {
      return 20
    }
  }

  // 原有的进度计算逻辑...
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


// 修改 completedFiles 计算属性
const completedFiles = computed(() => {
  return props.otherPdfs.filter(pdf => {
    const diskName = pdf.disk_name

    // 条件1：检查步骤完成时间（有解析完成时间就表示已完成）
    const stepTimes = props.stepCompletionTime?.[diskName]
    if (stepTimes?.parse) {
      return true
    }

    // 条件2：检查持久化状态
    const persistentStatus = props.persistentFileStatus?.[diskName]
    if (persistentStatus && persistentStatus.status === 'completed') {
      return true
    }

    // 条件3：检查进度是否为100%
    if (getFileProgress(diskName) === 100) {
      return true
    }

    return false
  })
})




// 修改 processingFiles 计算属性
const processingFiles = computed(() => {
  return props.otherPdfs.filter(pdf => {
    const diskName = pdf.disk_name

    // 首先排除已完成文件
    if (completedFiles.value.includes(pdf)) {
      return false
    }

    const progress = getFileProgress(diskName)
    return progress > 20 && progress < 100
  })
})


// 分组：待处理（进度<=20% 且 不在处理中）
const pendingFiles = computed(() => {
  return props.otherPdfs.filter(pdf => {
    const diskName = pdf.disk_name

    // 首先排除已完成和处理中的文件
    if (completedFiles.value.includes(pdf) || processingFiles.value.includes(pdf)) {
      return false
    }

    // 然后检查进度
    const progress = getFileProgress(diskName)
    return progress <= 20
  })
})


// 简化版本，只使用后端实际返回的字段
const getProcessingStatus = (diskName) => {
  // ✅ 0. 先检查步骤完成时间
  const stepTimes = props.stepCompletionTime?.[diskName]
  if (stepTimes?.parse) {
    return '已完成'  // 如果有解析完成时间，直接显示已完成
  }

  // 🔴 1. 优先检查持久化状态（长期保存的状态）
  const persistentStatus = props.persistentFileStatus?.[diskName]
  if (persistentStatus) {
    // 尝试从持久化状态中获取进度显示
    if (persistentStatus.progress_display) {
      return persistentStatus.progress_display
    }

    // 如果状态是 completed 或 success，显示"已完成"
    if (persistentStatus.status === 'completed' || persistentStatus.status === 'success') {
      return '已完成'
    }

    // 尝试从消息中提取
    if (persistentStatus.message) {
      const newMatch = persistentStatus.message.match(/处理 (\d+) 张新图片/)
      const skipMatch = persistentStatus.message.match(/跳过 (\d+) 张/)
      if (newMatch && skipMatch) {
        const newProcessed = parseInt(newMatch[1])
        const skipped = parseInt(skipMatch[1])
        return `${newProcessed}+${skipped}/${newProcessed + skipped}`
      }
    }
  }

  // 2. 检查实时进度数据
  const progressData = props.parsingProgressMap[diskName]
  const hasConverted = getHasConvertCache.value(diskName)
  const hasScreened = props.hasScreenedImages[diskName]

  // 🔴 简化调试信息
  if (process.env.NODE_ENV === 'development') {
    console.log('🔍 getProcessingStatus 调用:', {
      diskName,
      hasPersistent: !!persistentStatus,
      hasProgressData: !!progressData
    })
  }

  // 3. 如果有进度显示格式，直接使用
  if (progressData?.progress_display) {
    return progressData.progress_display
  }

  // 4. ✅ 修复：只使用后端实际返回的字段
  const processed = progressData?.processed_images || 0
  const skipped = progressData?.skipped_images || 0
  const totalImages = progressData?.total_images || 0

  // 计算实际总数
  const actualTotal = totalImages > 0 ? totalImages : (processed + skipped)

  if (process.env.NODE_ENV === 'development') {
    console.log('📊 后端字段值:', { processed, skipped, totalImages, actualTotal })
  }

  // 5. 处理中状态 - 使用后端返回的progress字段
  if (progressData && progressData.progress > 0 && progressData.progress < 100) {
    if (actualTotal > 0) {
      return `处理中 ${processed}/${actualTotal}`
    }
    return `处理中 ${progressData.progress}%`
  }

  // 6. 已完成状态
  if (progressData?.progress === 100 || progressData?.status === 'completed' || progressData?.status === 'success') {
    if (actualTotal > 0) {
      return `${processed}/${actualTotal}`
    }
    return '已完成'
  }

  // 7. 失败状态
  if (progressData?.status === 'failed' || progressData?.status === 'exception') {
    return '处理失败'
  }

  // 8. 如果已有持久化状态但状态不确定
  if (persistentStatus) {
    return persistentStatus.status === 'completed' ? '已完成' : '处理中'
  }

  // 9. 其他状态
  if (hasScreened) {
    return '已筛选'
  } else if (hasConverted) {
    return '已转图'
  }

  return '待处理'
}


// 获取进度百分比
const getProcessingProgress = (diskName) => {
  const progressData = props.parsingProgressMap[diskName]
  if (progressData?.percentage !== undefined) {
    return progressData.percentage
  }

  // 原有的分阶段进度计算
  return getFileProgress(diskName)
}


// 检查文件是否正在处理中（不可删除）
const isProcessing = (diskName) => {
  return props.convertingObj[diskName] ||
         props.parsingProgressMap[diskName]?.progress > 0 ||
         props.cropLoading[diskName]
}


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

.upload-tabs {
  padding: 12px 12px 0 12px;
  background: #fafafa;
}

.upload-tabs :deep(.el-radio-group) {
  display: flex;
  width: 100%;
}

.upload-tabs :deep(.el-radio-button) {
  flex: 1;
}

.upload-tabs :deep(.el-radio-button__inner) {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

/* .excel-section 已移除 */

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
  gap: 12px;
  align-items: center;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.summary-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.summary-item.completed {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border: none;
}

.summary-item.completed .count {
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.summary-item.completed .label {
  color: rgba(255, 255, 255, 0.9);
}

.summary-item.processing {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
  border: none;
}

.summary-item.processing .count {
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.summary-item.processing .label {
  color: rgba(255, 255, 255, 0.9);
}

.summary-item.pending {
  background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
  color: white;
  border: none;
}

.summary-item.pending .count {
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.summary-item.pending .label {
  color: rgba(255, 255, 255, 0.9);
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
  margin-bottom: 16px;
  animation: fade-in 0.6s ease-out;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.5px;
  border-radius: 8px;
  margin-bottom: 8px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
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
  padding: 12px 16px;
  margin-bottom: 6px;
  border-radius: 12px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

.current-pdf-item {
  background: linear-gradient(135deg, #e6f7ff 0%, #d0ebff 100%);
  border: 2px solid #91d5ff;
  box-shadow: 0 4px 12px rgba(145, 213, 255, 0.2);
}

.current-pdf-item.highlighted {
  background: linear-gradient(135deg, #d0ebff 0%, #b3e0ff 100%);
  animation: pulse-glow 3s infinite alternate;
}

.current-pdf-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
  transition: left 0.5s ease;
}

.current-pdf-item:hover::before {
  left: 100%;
}

.pdf-file-item.completed {
  background: linear-gradient(135deg, #f0f9eb 0%, #e1f7d9 100%);
  border: 2px solid #b3e0a8;
  box-shadow: 0 4px 12px rgba(179, 224, 168, 0.2);
  border-left: 4px solid #67c23a;
}

.pdf-file-item.processing {
  background: linear-gradient(135deg, #fdf6ec 0%, #f9e8c9 100%);
  border: 2px solid #f5dab1;
  box-shadow: 0 4px 12px rgba(245, 218, 177, 0.2);
  border-left: 4px solid #e6a23c;
}

.pdf-file-item.pending {
  background: linear-gradient(135deg, #f4f4f5 0%, #e8e8e9 100%);
  border: 2px solid #dcdcdc;
  box-shadow: 0 4px 12px rgba(220, 220, 220, 0.2);
  border-left: 4px solid #909399;
}

.pdf-file-item:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
  border-color: #3b82f6 !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.current-pdf-item:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 12px 24px rgba(59, 130, 246, 0.2);
  border-color: #2563eb;
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