<!-- frontend/src/layouts/TwoColumnLayout.vue -->
<template>
  <div class="two-column-layout">
    <!-- 左侧：PDF预览和文件操作区域 -->
    <div class="left-panel">
      <file-upload @uploaded="$emit('loadFiles')"/>
      <file-list
        :files="files"
        :crop-loading="cropLoading"
        :crop-results="cutResults"
        :converting="convertingObj"
        :convert-cache="convertCache"
        :batch-crop-loading="batchCropLoading"
        :joined-results="joinedResults"
        :parsing-progress-map="parsingProgressMap"
        :has-screened-images="hasScreenedImages"
        :screening-result-map="screeningResultMap"
        @delete="$emit('deleteFile', $event)"
        @crop="$emit('cutTable', $event)"
        @convert="$emit('convertAndPreview', $event)"
        @batch-crop="$emit('handleBatchCrop', $event)"
        @open-llm-config="$emit('openLLMConfig')"
        @image-selected="$emit('handleImageSelected', $event)"
        @update-screening-status="$emit('handleUpdateScreeningStatus', $event)"
        @ocr-completed="(data) => {
          console.log('🧩 TwoColumnLayout 收到 ocr-completed:', data);
          $emit('handleOcrCompleted', data);
        }"
        @recognize-table="$emit('handleRecognizeTable', $event)"
        @excel-data-received="(data) => {
          console.log('🧩 TwoColumnLayout 收到并转发 excel-data-received:', data);
          $emit('handleExcelDataReceived', data);
        }"
        @screen-images-completed="(data) => {
          console.log('🧩 TwoColumnLayout 收到 screen-images-completed:', data);
          $emit('handleScreenImagesCompleted', data);
        }"
        @open-classification="$emit('handleOpenClassification', $event)"
      />
    </div>

    <!-- 右侧：新的两栏布局 -->
    <div class="right-panel">
      <!-- 上栏：当前PDF状态 -->
      <CurrentPdfStatus
        :current-pdf="currentPdf"
        :converting-obj="convertingObj"
        :convert-cache="convertCache"
        :has-screened-images="hasScreenedImages"
        :is-screening="isScreening"
        :screening-result-map="screeningResultMap"
        :is-parsing="isParsing"
        :has-results="hasResults"
        :parsing-progress-map="parsingProgressMap"
        :has-batch-results="hasBatchResults"
        @convert="$emit('convertAndPreview', $event)"
        @screen-images="handleScreenImages"
        @open-classification="$emit('handleOpenClassification', $event)"
        @parse-tables="handleParseTables"
        @clear-cache="$emit('clearCache', $event)"
        class="status-section"
      />

      <!-- 下栏：其他PDF列表 -->
      <OtherPdfsList
        :pdfs="otherPdfs"
        @switch-pdf="$emit('switchPdf', $event)"
        @delete="$emit('deleteFile', $event)"
        class="other-pdfs-section"
      />
    </div>
  </div>
</template>

<script setup>
// 导入组件
import FileUpload from '@/components/file/FileUpload.vue'
import FileList from '@/components/file/FileList.vue'
import CurrentPdfStatus from '@/components/pdf/CurrentPdfStatus.vue'  // 新增
import OtherPdfsList from '@/components/pdf/OtherPdfsList.vue'  // 新增（如果路径不同请调整）

// 定义props - 所有需要从父组件传递的数据
defineProps({
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
  }
})

// 定义emit事件
defineEmits([
  'loadFiles',
  'deleteFile',
  'cutTable',
  'convertAndPreview',
  'handleBatchCrop',
  'openLLMConfig',
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
  'switchPdf',  // 新增
  'clearCache',  // 新增
  'parseTables'  // 新增
])

// 处理图片筛选事件
const handleScreenImages = (pdfDiskName) => {
  // 这里可以添加一些处理逻辑，或者直接转发给父组件
  console.log('📸 触发图片筛选:', pdfDiskName)
  // 如果需要，可以在这里调用对应的emit
}

// 处理表格解析事件
const handleParseTables = (pdfDiskName) => {
  console.log('📊 触发表格解析:', pdfDiskName)
  // 如果需要，可以在这里调用对应的emit
}

// 处理关闭Excel事件
const handleCloseExcel = () => {
  // 如果需要在布局层处理Excel关闭，可以在这里添加逻辑
  console.log('❌ 关闭Excel查看器')
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

/* 下栏：其他PDF列表 */
.other-pdfs-section {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
</style>