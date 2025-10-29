<template>
  <div class="file-list">
    <!-- 表格类型选择器 -->
    <div class="table-type-selector" v-if="hasPDF">
      <!-- 现有代码保持不变 -->
    </div>

    <!-- PDF区域 - 添加折叠功能 -->
    <div class="pdf-sections-container">
      <!-- PDF预览区域 -->
      <CollapsibleSection
        title="PDF预览"
        :collapsed="sections.pdfPreview.collapsed"
        @toggle="toggleSection('pdfPreview')"
      >
        <PdfPreviewSection
          v-if="hasPDF && !sections.pdfPreview.collapsed"
          ref="pdfPreviewRef"
          :pdf-files="pdfFiles"
          :current-pdf-index="currentPdfIndex"
          :crop-loading="cropLoading"
          :crop-results="cropResults"
          :converting="converting"
          :convert-cache="convertCache"
          :batch-crop-loading="batchCropLoading"
          :joined-results="safeJoinedResults"
          :llm-configured="llmConfigured"
          :llm-loading="llmLoading"
          :recognize-loading="recognizeLoading"
          :table-type="tableType"
          :current-excel-data="currentExcelData"
          @switch-pdf="switchToPDF"
          @delete="handleDelete"
          @crop="handleCrop"
          @convert="handleConvert"
          @batch-crop="handleBatchCrop"
          @clear-cache="handleClearCache"
          @close-pdf="switchToNextPDF"
          @preview-image="previewImage"
          @llm-process="handleLLMProcess"
          @single-llm-process="handleSingleLLMProcess"
          @recognize-table="handleRecognizeTable"
          @recognize-non-financial-table="handleRecognizeNonFinancialTable"
          @set-excel-pdf-mapping="handleSetExcelPdfMapping"
        />
      </CollapsibleSection>

      <!-- 批量裁切结果区域 -->
      <CollapsibleSection
        v-if="hasPDF && hasBatchCropResults"
        title="批量裁切结果"
        :collapsed="sections.batchCrop.collapsed"
        @toggle="toggleSection('batchCrop')"
      >
        <BatchCropResults
          v-if="!sections.batchCrop.collapsed"
          :pdf="currentPdfFile"
          :images="currentBatchCropImages"
          @preview-image="previewImage"
          @single-llm-process="handleSingleLLMProcess"
          @clear-cache="handleClearCache"
        />
      </CollapsibleSection>

      <!-- 其他PDF文件区域 -->
      <CollapsibleSection
        v-if="otherPdfFiles.length > 0"
        title="其他PDF文件"
        :collapsed="sections.otherPdfs.collapsed"
        @toggle="toggleSection('otherPdfs')"
      >
        <OtherPdfFilesSection
          v-if="!sections.otherPdfs.collapsed"
          :files="otherPdfFiles"
          :current-pdf-index="currentPdfIndex"
          @switch-pdf="switchToPDF"
          @delete="handleDelete"
          @convert="handleConvert"
        />
      </CollapsibleSection>
    </div>

    <!-- 非PDF文件 -->
    <NonPdfFilesSection
      v-if="nonPdfFiles.length > 0"
      :files="nonPdfFiles"
      :crop-loading="cropLoading"
      :crop-results="cropResults"
      @delete="handleDelete"
      @crop="handleCrop"
    />

    <!-- 空状态 -->
    <EmptyState v-if="files.length === 0" />

    <!-- 其他对话框保持不变 -->
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { llmApi } from '@/api/llm'
import { getBackendUrl, getStaticUrl, getFullUrl, getConfig } from '@/utils/config'
import PdfPreviewSection from './PdfPreviewSection.vue'
import NonPdfFilesSection from './NonPdfFilesSection.vue'
import EmptyState from './EmptyState.vue'
import ImagePreviewDialog from './ImagePreviewDialog.vue'
import ExcelPdfMappingDialog from './ExcelPdfMappingDialog.vue'
import CollapsibleSection from './CollapsibleSection.vue'
import BatchCropResults from './BatchCropResults.vue'
import OtherPdfFilesSection from './OtherPdfFilesSection.vue'

// 新增：折叠状态管理
const sections = ref({
  pdfPreview: {
    collapsed: false,
    title: 'PDF预览'
  },
  batchCrop: {
    collapsed: false,
    title: '批量裁切结果'
  },
  otherPdfs: {
    collapsed: false,
    title: '其他PDF文件'
  }
})

// 新增：切换折叠状态
const toggleSection = (sectionKey) => {
  sections.value[sectionKey].collapsed = !sections.value[sectionKey].collapsed
  // 保存到本地存储
  saveCollapseState()
}

// 新增：保存折叠状态到本地存储
const saveCollapseState = () => {
  const state = {}
  Object.keys(sections.value).forEach(key => {
    state[key] = sections.value[key].collapsed
  })
  localStorage.setItem('pdfSectionsCollapseState', JSON.stringify(state))
}

// 新增：从本地存储加载折叠状态
const loadCollapseState = () => {
  try {
    const saved = localStorage.getItem('pdfSectionsCollapseState')
    if (saved) {
      const state = JSON.parse(saved)
      Object.keys(state).forEach(key => {
        if (sections.value[key]) {
          sections.value[key].collapsed = state[key]
        }
      })
    }
  } catch (error) {
    console.error('加载折叠状态失败:', error)
  }
}

// 新增：计算属性
const hasBatchCropResults = computed(() => {
  const currentPdf = pdfFiles.value[currentPdfIndex.value]
  return currentPdf && safeJoinedResults.value[currentPdf.disk_name]?.length > 0
})

const currentPdfFile = computed(() => {
  return pdfFiles.value[currentPdfIndex.value] || null
})

const currentBatchCropImages = computed(() => {
  const currentPdf = currentPdfFile.value
  return currentPdf ? safeJoinedResults.value[currentPdf.disk_name] || [] : []
})

const otherPdfFiles = computed(() => {
  return pdfFiles.value.filter((_, index) => index !== currentPdfIndex.value)
})

// 在 onMounted 中加载折叠状态
onMounted(() => {
  loadCollapseState()
})

// 其他现有代码保持不变...
</script>

<style scoped>
.file-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.pdf-sections-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-height: 0;
}

/* 当PDF预览区域展开时，其他区域折叠时，PDF预览区域自动放大 */
.pdf-sections-container:has(.collapsible-section:not(.collapsed):first-child) {
  flex: 1;
}
</style>