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
          :pdf-files="[currentPdf]"
          :current-pdf-index="0"
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
          @delete="$emit('delete-file', $event)"
          @screen-images="$emit('handle-screen-images', $event)"
          @convert="$emit('convert-and-preview', $event)"
          @batch-crop="$emit('handle-batch-crop', $event)"
          @parse-tables="$emit('parse-tables', $event)"
          @clear-cache="$emit('clear-cache', $event)"
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
      <!-- 上栏：当前PDF状态和进度预览 -->
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
        class="status-section"
      />

      <!-- 下栏：所有PDF文件列表 -->
      <div class="file-manager-section">
        <div class="section-header">
          <span class="title">PDF文件管理器</span>
          <div class="table-type-selector" v-if="files.length > 0">
            <el-radio-group
              :value="tableType"
              size="small"
              @change="$emit('table-type-change', $event)"
            >
              <el-radio-button label="financial">金融表格</el-radio-button>
              <el-radio-button label="non_financial">普通表格</el-radio-button>
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
            </div>
            <div class="file-actions">
              <el-button size="small" type="text" @click="$emit('convert-and-preview', currentPdf.disk_name)">
                <i class="el-icon-picture-outline"></i>
              </el-button>
              <el-button size="small" type="text" @click="$emit('delete-file', currentPdf)">
                <i class="el-icon-delete"></i>
              </el-button>
            </div>
          </div>

          <!-- 其他PDF文件 -->
          <div
            v-for="pdf in otherPdfs"
            :key="pdf.disk_name"
            class="pdf-file-item"
            :class="{ 'has-converted': getHasConvertCache(pdf.disk_name) }"
          >
            <div class="file-info" @click="$emit('switch-pdf', pdf)">
              <i class="el-icon-document"></i>
              <span class="file-name">{{ pdf.filename }}</span>
              <div class="file-status">
                <el-tag
                  v-if="hasConvertCache(pdf.disk_name)"
                  size="small"
                  type="success"
                  class="converted-tag"
                >
                  已转图
                </el-tag>
                <el-tag
                  v-if="hasScreenedImages[pdf.disk_name]"
                  size="small"
                  type="primary"
                  class="screened-tag"
                >
                  已筛选
                </el-tag>
              </div>
            </div>
            <div class="file-actions">
              <el-button
                size="small"
                type="text"
                @click="$emit('convert-and-preview', pdf.disk_name)"
                :title="getHasConvertCache(pdf.disk_name) ? '重新转图' : '转图'"
              >
                <i :class="hasConvertCache(pdf.disk_name) ? 'el-icon-picture' : 'el-icon-picture-outline'"></i>
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
import { computed } from 'vue'
import FileUpload from '@/components/file/FileUpload.vue'
import PdfPreview from '@/components/pdf/PdfPreview.vue'
import CurrentPdfStatus from '@/components/pdf/CurrentPdfStatus.vue'

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
  // 新增props
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
  }
})

// 定义emit事件
defineEmits([
  'load-files',
  'deleteFile',
  'cutTable',
  'convertAndPreview',
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
  'switchPdf',
  'clearCache',
  'parseTables',
  'tableTypeChange'
])


// 工具函数：检查是否已转图
const hasConvertCache = computed(() => {
  return (diskName) => {
    if (!diskName) return false
    const cacheKey = diskName.replace(/\.pdf$/i, '')
    const cacheData = props.convertCache[cacheKey] // 现在props已定义
    return cacheData && Array.isArray(cacheData) && cacheData.length > 0
  }
})

// 工具函数：检查是否已转图
const getHasConvertCache = computed(() => {
  return (diskName) => {
    if (!diskName) return false
    const cacheKey = diskName.replace(/\.pdf$/i, '')
    const cacheData = props.convertCache[cacheKey]
    return cacheData && Array.isArray(cacheData) && cacheData.length > 0
  }
})

// 处理关闭当前PDF
const handleCloseCurrentPdf = () => {
  console.log('关闭当前PDF预览')
  // 这里可以触发事件告诉父组件清空当前PDF
}
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

/* 上栏：当前PDF状态 */
.status-section {
  flex-shrink: 0;
  border-bottom: 1px solid #e4e7ed;
}

/* 下栏：PDF文件管理器 */
.file-manager-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
  flex-shrink: 0;
}

.section-header .title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
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

.pdf-file-item:hover {
  background: #f5f7fa;
}

.pdf-file-item.has-converted {
  border-left: 3px solid #67c23a;
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
.converted-tag,
.screened-tag {
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
</style>