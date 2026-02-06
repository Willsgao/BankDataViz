<template>
  <div class="pdf-container">
    <!-- 折叠控制头部 -->
    <div class="section-header" v-if="currentPDF">
      <div class="header-left">
        <el-button
          type="text"
          @click="toggleCollapse"
          :icon="isCollapsed ? 'el-icon-arrow-down' : 'el-icon-arrow-up'"
          class="collapse-btn"
          size="small"
        >
          {{ isCollapsed ? '展开PDF预览' : '折叠PDF预览' }}
        </el-button>
        <span class="section-title">PDF预览 - {{ currentPDF.filename }}</span>
      </div>
      <div class="header-actions">
        <el-button
          v-if="isCollapsed"
          type="text"
          @click="toggleCollapse"
          size="small"
        >
          展开查看
        </el-button>
      </div>
    </div>

    <!-- PDF预览内容 -->
    <div v-show="!isCollapsed" class="pdf-content">
      <!-- 当前PDF预览 -->
      <div class="pdf-preview-section" v-if="currentPDF">
        <PdfViewer
          :file="currentPDF"
          @close="$emit('close-pdf')"
        />

        <PdfControls
          :pdf="currentPDF"
          :crop-loading="cropLoading"
          :converting="converting"
          :convert-cache="convertCache"
          :batch-crop-loading="batchCropLoading"
          :has-batch-results="hasBatchCropResults(currentPDF.disk_name)"
          :parsing-progress="getParsingProgress(currentPDF.disk_name)"
          :has-screened-images="hasScreenedImages[currentPDF.disk_name] || false"
          :screening-result="screeningResultMap?.[currentPDF.disk_name] || null"
          @delete="$emit('delete', currentPDF.filename)"
          @convert="$emit('convert', $event)"
          @screen-images="$emit('screen-images', currentPDF.disk_name)"
          @batch-crop="$emit('batch-crop', currentPDF.disk_name)"
          @parse-tables="$emit('parse-tables', currentPDF.disk_name)"
          @clear-cache="$emit('clear-cache', currentPDF.disk_name)"
          @open-classification="$emit('open-classification', currentPDF.disk_name)"
        />
      </div>

      <!-- 其他PDF列表 -->
      <OtherPdfsList
        v-if="otherPDFs.length > 0"
        :pdfs="otherPDFs"
        @switch-pdf="$emit('switch-pdf', $event)"
        @delete="$emit('delete', $event)"
      />
    </div>

    <!-- 折叠状态提示 -->
    <div v-show="isCollapsed && currentPDF" class="collapsed-hint">
      <el-text type="info">PDF预览已折叠</el-text>
      <div class="hint-actions">
        <el-button type="text" @click="toggleCollapse" size="small">
          点击展开查看PDF
        </el-button>
        <el-text type="info" size="small">
          当前PDF: {{ currentPDF.filename }}
        </el-text>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import PdfViewer from './PdfViewer.vue'  // 导入现有的PdfViewer组件
import PdfControls from './PdfControls.vue'
import OtherPdfsList from './OtherPdfsList.vue'

const props = defineProps({
  pdfFiles: {
    type: Array,
    default: () => []
  },
  currentPdfIndex: {
    type: Number,
    default: 0
  },
  cropLoading: {
    type: Object,
    default: () => ({})
  },
  cropResults: {
    type: Object,
    default: () => ({})
  },
  converting: {
    type: Object,
    default: () => ({})
  },
  convertCache: {
    type: Object,
    default: () => ({})
  },
  batchCropLoading: {
    type: Object,
    default: () => ({})
  },
  joinedResults: {
    type: Object,
    default: () => ({})
  },
  tableType: {
    type: String,
    default: 'financial'
  },
  llmLoading: {
    type: Object,
    default: () => ({})
  },
  parsingProgressMap: {
    type: Object,
    default: () => ({})
  },
  screenedImagesMap: {
    type: Object,
    default: () => ({})
  },
  screeningResultMap: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits([
  'switch-pdf',
  'delete',
  'screen-images',
  'convert',
  'batch-crop',
  'clear-cache',
  'close-pdf',
  'preview-image',
  'llm-process',
  'single-llm-process',
  'open-llm-config',
  'update:llmLoading',
  'ocr-completed',
  'parse-tables'
])

// 折叠状态
const isCollapsed = ref(false)

// 图片筛选状态管理
const hasScreenedImages = ref({})

// 切换折叠状态
const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

// 计算属性
const currentPDF = computed(() => props.pdfFiles[props.currentPdfIndex] || null)
const otherPDFs = computed(() => props.pdfFiles.filter((_, index) => index !== props.currentPdfIndex))

// 安全访问 joinedResults
const safeJoinedResults = computed(() => {
  return props.joinedResults || {}
})

// 工具函数
const hasBatchCropResults = (pdfDiskName) => {
  return pdfDiskName &&
         props.joinedResults &&
         props.joinedResults[pdfDiskName] &&
         props.joinedResults[pdfDiskName].length > 0
}

const getParsingProgress = (diskName) => {
  if (!diskName || !props.parsingProgressMap) return null
  const key = diskName.replace(/\.pdf$/i, '')
  return props.parsingProgressMap[key] || null
}

// 监听父组件传递的图片筛选状态
watch(() => props.screenedImagesMap, (newMap) => {
  console.log('PdfPreview 收到图片筛选状态更新:', newMap)
  hasScreenedImages.value = { ...newMap }
}, { deep: true })

// 监听批量裁切完成，自动展开
watch(() => props.joinedResults, (newVal) => {
  if (newVal && Object.keys(newVal).length > 0) {
    // 如果有新的裁切结果，自动展开
    isCollapsed.value = false
  }
}, { deep: true })

// 监听当前PDF变化，重置折叠状态
watch(() => props.currentPdfIndex, () => {
  isCollapsed.value = false
})

watch(
  () => currentPDF.value,
  () => {
    console.log('PdfPreview 当前PDF变化:', currentPDF.value)
  },
  { immediate: true }
)
</script>

<style scoped>
.pdf-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  background: white;
  margin: 16px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
  border-radius: 8px 8px 0 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.collapse-btn {
  padding: 4px 8px;
}

.section-title {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.pdf-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.pdf-preview-section {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.collapsed-hint {
  padding: 20px;
  text-align: center;
  background: #f8f9fa;
  border-radius: 0 0 8px 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
}

.hint-actions {
  display: flex;
  gap: 16px;
  align-items: center;
}
</style>