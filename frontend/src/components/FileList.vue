<template>
  <div class="file-list">
    <!-- PDF区域 -->
    <PdfPreviewSection
      v-if="hasPDF"
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
    />

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

    <!-- 图片预览对话框 -->
    <ImagePreviewDialog
      :visible="previewDialogVisible"
      :image="currentPreviewImage"
      :index="currentPreviewIndex"
      :total="currentPreviewTotal"
      @update:visible="previewDialogVisible = $event"
      @prev="prevImage"
      @next="nextImage"
    />

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { llmApi } from '@/api/llm'
import PdfPreviewSection from './PdfPreviewSection.vue'
import NonPdfFilesSection from './NonPdfFilesSection.vue'
import EmptyState from './EmptyState.vue'
import ImagePreviewDialog from './ImagePreviewDialog.vue'

const props = defineProps({
  files: {
    type: Array,
    default: () => []
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
  }
})

const emit = defineEmits(['delete', 'crop', 'convert', 'batchCrop', 'clearCache', 'openLLMConfig', 'recognize-table'])

// 或者在需要的地方直接调用
const openLLMConfig = () => {
  // 这里可以通过 provide/inject 或者事件总线来打开配置
}

// 在事件处理部分添加
const handleOpenLLMConfig = () => {
  emit('open-llm-config')
}

// 计算属性
const pdfFiles = computed(() => props.files.filter(f => isPDF(f.filename)))
const nonPdfFiles = computed(() => props.files.filter(f => !isPDF(f.filename)))
const hasPDF = computed(() => pdfFiles.value.length > 0)
const safeJoinedResults = computed(() => props.joinedResults || {})

// 状态
const currentPdfIndex = ref(0)
const previewDialogVisible = ref(false)
const currentPreviewImage = ref('')
const currentPreviewIndex = ref(0)
const currentPreviewTotal = ref(0)
const currentPreviewList = ref([])

// LLM相关状态
const llmLoading = ref({})
const llmConfigured = ref(false)
// 识别相关状态
const recognizeLoading = ref({})

// 工具函数
const isPDF = (filename) => filename.toLowerCase().endsWith('.pdf')

// 事件处理
const handleDelete = (filename) => emit('delete', filename)
const handleCrop = (filename) => emit('crop', filename)
const handleConvert = (diskName) => emit('convert', diskName)
const handleBatchCrop = (diskName) => emit('batchCrop', diskName)
const handleClearCache = (diskName) => emit('clearCache', diskName)

// PDF切换
const switchToPDF = (pdfFile) => {
  const index = pdfFiles.value.findIndex(f => f.id === pdfFile.id)
  if (index !== -1) {
    currentPdfIndex.value = index
  }
}

const switchToNextPDF = () => {
  if (pdfFiles.value.length <= 1) {
    currentPdfIndex.value = -1
  } else {
    currentPdfIndex.value = (currentPdfIndex.value + 1) % pdfFiles.value.length
  }
}

// 图片预览
const previewImage = (imgUrl, index) => {
  const fileKey = Object.keys(safeJoinedResults.value).find(key =>
    safeJoinedResults.value[key].includes(imgUrl)
  )
  if (fileKey) {
    currentPreviewList.value = safeJoinedResults.value[fileKey]
    currentPreviewImage.value = imgUrl
    currentPreviewIndex.value = index
    currentPreviewTotal.value = currentPreviewList.value.length
    previewDialogVisible.value = true
  }
}

const prevImage = () => {
  if (currentPreviewIndex.value > 0) {
    currentPreviewIndex.value--
    currentPreviewImage.value = currentPreviewList.value[currentPreviewIndex.value]
  }
}

const nextImage = () => {
  if (currentPreviewIndex.value < currentPreviewTotal.value - 1) {
    currentPreviewIndex.value++
    currentPreviewImage.value = currentPreviewList.value[currentPreviewIndex.value]
  }
}


// 识别表格处理
const handleRecognizeTable = async (tableInfo) => {
  const loadingKey = `${tableInfo.pdfName}_${tableInfo.index}`
  recognizeLoading.value[loadingKey] = true

  try {
    // 发射识别事件到父组件（App.vue）
    emit('recognize-table', {
      pdfName: tableInfo.pdfName,
      imageUrl: tableInfo.imageUrl,
      index: tableInfo.index,
      tableName: tableInfo.tableName || `表格_${tableInfo.index + 1}`
    })
  } catch (error) {
    console.error('识别失败:', error)
    ElMessage.error('识别失败')
  } finally {
    recognizeLoading.value[loadingKey] = false
  }
}

// LLM处理函数
const handleLLMProcess = async (pdfDiskName) => {
  try {
    llmLoading.value[pdfDiskName] = true

    // 检查LLM配置
    if (!llmConfigured.value) {
      await ElMessageBox.confirm(
        'LLM未配置，请先配置大模型参数后再进行表格识别',
        '提示',
        {
          confirmButtonText: '去配置',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
      return
    }

    // 获取裁切的图片路径
    const imagePaths = safeJoinedResults.value[pdfDiskName].map(url => {
      const urlObj = new URL(url)
      return urlObj.pathname.replace('/static/', 'static/')
    })

    if (imagePaths.length === 0) {
      ElMessage.warning('没有可用的裁切图片进行识别')
      return
    }

    const outputDir = `./output/llm_results/${pdfDiskName.replace('.pdf', '')}`
    const response = await llmApi.batchProcess({
      image_paths: imagePaths,
      output_dir: outputDir,
      bank_name: '未知银行'
    })

    if (response.success) {
      ElMessage.success(`表格识别完成！成功处理 ${response.data.success} 个文件`)
    } else {
      ElMessage.error(`表格识别失败: ${response.error}`)
    }

  } catch (error) {
    console.error('LLM处理失败:', error)
    ElMessage.error('LLM处理异常')
  } finally {
    llmLoading.value[pdfDiskName] = false
  }
}

const handleSingleLLMProcess = async (params) => {
  try {
    console.log('🔍 接收到的参数:', params)

    // 解析参数
    let excelPath, index

    if (typeof params === 'object' && params !== null) {
      // 参数是对象格式
      excelPath = params.excelPath || params.excel_path
      index = params.index
    } else {
      // 参数是其他格式（兼容旧版本）
      console.warn('⚠️ 使用旧版参数格式')
      excelPath = params
      index = 0 // 默认索引
    }

    console.log('🟡 解析后的Excel路径:', excelPath)
    console.log('🟡 解析后的索引:', index)

    // 参数验证
    if (index === undefined || index === null) {
      console.warn('⚠️ 索引参数缺失，使用默认值0')
      index = 0
    }

    if (!excelPath) {
      console.error('❌ Excel路径参数丢失')
      ElMessage.error('处理错误：Excel路径丢失')
      return
    }

    if (!llmConfigured.value) {
      const result = await ElMessageBox.confirm(
        'LLM未配置，请先配置大模型参数后再进行表格识别',
        '提示',
        {
          confirmButtonText: '去配置',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
      if (!result) {
        return // 用户点击取消
      }
      return
    }

    // 处理Excel路径转换
    let excelUrl
    if (excelPath.includes('static/excel_data/')) {
      // 提取 static/excel_data/ 之后的部分
      const staticIndex = excelPath.indexOf('static/excel_data/')
      excelUrl = '/' + excelPath.substring(staticIndex)
      console.log('🔧 转换后的Excel URL:', excelUrl)
    } else if (excelPath.startsWith('http')) {
      // 已经是URL格式
      excelUrl = excelPath
    } else {
      // 其他情况，直接使用
      excelUrl = excelPath
    }

    console.log('📤 发送excel-data-received事件，数据:', {
      excelUrl: excelUrl,
      tableName: `表格${index + 1}`,
      fromCache: true
    })

    emit('excel-data-received', {
      excelUrl: excelUrl,
      tableName: `表格${index + 1}`,
      fromCache: true
    })

    console.log('📤 事件发送完成')

  } catch (error) {
    if (error !== 'cancel') {
      console.error('💥 单张LLM处理失败:', error)
      console.error('💥 错误详情:', error.response?.data || error.message)
      ElMessage.error('单张表格识别异常: ' + (error.response?.data?.error || error.message))
    }
  }
}


// 检查LLM配置状态
const checkLLMStatus = async () => {
  try {
    const response = await llmApi.getStatus()
    if (response.success) {
      llmConfigured.value = response.data.client_configured
    }
  } catch (error) {
    console.error('检查LLM状态失败:', error)
  }
}

// 监听器
watch(pdfFiles, (newPdfs) => {
  if (newPdfs.length > 0 && currentPdfIndex.value >= newPdfs.length) {
    currentPdfIndex.value = 0
  }
})

onMounted(() => {
  checkLLMStatus()
})
</script>

<style scoped>
.file-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  height: 100%;
}
</style>