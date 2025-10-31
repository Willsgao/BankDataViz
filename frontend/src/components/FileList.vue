<template>
  <div class="file-list">
    <!-- 表格类型选择器 -->
    <div class="table-type-selector" v-if="hasPDF">
      <div class="selector-label">表格类型:</div>
      <el-radio-group v-model="tableType" size="small" @change="onTableTypeChange">
        <el-radio-button label="financial">金融表格</el-radio-button>
        <el-radio-button label="non_financial">普通表格</el-radio-button>
      </el-radio-group>
      <div class="type-description">
        {{ tableType === 'financial' ? '识别银行财务报表等金融数据' : '识别普通数据表格、产品清单等' }}
      </div>
    </div>

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
      :table-type="tableType"
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
import { getBackendUrl, getStaticUrl, getFullUrl, getConfig } from '@/utils/config'  // 导入统一配置
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

const emit = defineEmits([
  'delete', 'crop', 'convert', 'batchCrop', 'clearCache', 'openLLMConfig',
  'recognize-table', 'excel-data-received'
])

// 表格类型状态
const tableType = ref('financial') // 默认金融表格

// 计算属性
const pdfFiles = computed(() => props.files.filter(f => isPDF(f.filename)))
const nonPdfFiles = computed(() => props.files.filter(f => !isPDF(f.filename)))
const hasPDF = computed(() => pdfFiles.value.length > 0)
const safeJoinedResults = computed(() => props.joinedResults || {})

// 获取配置
const config = getConfig()

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

// 表格类型变化处理
const onTableTypeChange = (type) => {
  console.log(`表格类型切换为: ${type === 'financial' ? '金融表格' : '普通表格'}`)
  ElMessage.info(`已切换到${type === 'financial' ? '金融表格' : '普通表格'}识别模式`)
}

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
    console.log('🖼️ 打开图片预览:', { index, total: currentPreviewTotal.value })
  }
}


// 关闭预览对话框
const closePreview = () => {
  previewDialogVisible.value = false
  console.log('🖼️ 关闭图片预览')
}


// 上一张图片
const prevImage = () => {
  if (currentPreviewIndex.value > 0) {
    currentPreviewIndex.value--
    currentPreviewImage.value = currentPreviewList.value[currentPreviewIndex.value]
    console.log('🖼️ 切换到上一张:', currentPreviewIndex.value)
  }
}

// 下一张图片
const nextImage = () => {
  if (currentPreviewIndex.value < currentPreviewTotal.value - 1) {
    currentPreviewIndex.value++
    currentPreviewImage.value = currentPreviewList.value[currentPreviewIndex.value]
    console.log('🖼️ 切换到下一张:', currentPreviewIndex.value)
  }
}


// 重置预览状态
const resetPreview = () => {
  currentPreviewImage.value = ''
  currentPreviewIndex.value = 0
  currentPreviewTotal.value = 0
  currentPreviewList.value = []
}

// 监听对话框显示状态变化
watch(previewDialogVisible, (newVal) => {
  console.log('🖼️ 预览对话框状态:', newVal ? '打开' : '关闭')
  if (!newVal) {
    // 对话框关闭时重置状态
    resetPreview()
  }
})



// 识别表格处理 - 根据表格类型分发
const handleRecognizeTable = async (tableInfo) => {
  const loadingKey = `${tableInfo.pdfName}_${tableInfo.index}`
  recognizeLoading.value[loadingKey] = true

  try {
    if (tableType.value === 'financial') {
      // 金融表格识别
      emit('recognize-table', {
        pdfName: tableInfo.pdfName,
        imageUrl: tableInfo.imageUrl,
        index: tableInfo.index,
        tableName: tableInfo.tableName || `表格_${tableInfo.index + 1}`,
        tableType: 'financial'
      })
    } else {
      // 普通表格识别
      await handleRecognizeNonFinancialTable(tableInfo)
    }
  } catch (error) {
    console.error('识别失败:', error)
    ElMessage.error('识别失败')
  } finally {
    recognizeLoading.value[loadingKey] = false
  }
}



// 在 handleRecognizeNonFinancialTable 方法中修改输出路径
const handleRecognizeNonFinancialTable = async (tableInfo) => {
  const loadingKey = `${tableInfo.pdfName}_${tableInfo.index}`
  recognizeLoading.value[loadingKey] = true

  try {
    console.log('开始普通表格识别:', tableInfo)

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
      emit('open-llm-config')
      return
    }

    // 使用统一配置处理图片路径
    let imagePath = tableInfo.imageUrl

    // 移除基础URL部分，只保留相对路径
    if (imagePath.startsWith(config.backend.baseUrl)) {
      imagePath = imagePath.replace(config.backend.baseUrl, '')
    }

    // 确保是相对路径
    if (imagePath.startsWith('/')) {
      imagePath = imagePath.substring(1)
    }

    // 构建PDF特定的输出路径
    const pdfStem = tableInfo.pdfName.replace('.pdf', '')
    const outputDir = `static/excel_data/${pdfStem}`
    const outputPath = `${outputDir}/table_${tableInfo.index + 1}.xlsx`

    console.log('普通表格识别参数:', {
      imagePath,
      outputPath,
      pdfStem,
      tableName: tableInfo.tableName,
      index: tableInfo.index
    })

    // 调用普通表格识别API
    const response = await llmApi.processNonFinancialTable({
      image_path: imagePath,
      output_path: outputPath,
      sheet_name: tableInfo.tableName || `普通表格_${tableInfo.index + 1}`,
      bank_name: '未知机构',
      file_name: `table_${tableInfo.index + 1}`
    })

    console.log('普通表格识别响应:', response)

    if (response.success) {
      ElMessage.success('普通表格识别完成')

      // 处理返回的Excel数据
      if (response.excel_url) {
        emit('excel-data-received', {
          excelUrl: response.excel_url,
          tableName: tableInfo.tableName || `普通表格_${tableInfo.index + 1}`,
          fromCache: response.from_cache || false,
          tableType: 'non_financial'
        })
      }
    } else {
      ElMessage.error(`普通表格识别失败: ${response.error}`)
    }

  } catch (error) {
    console.error('普通表格识别异常:', error)
    ElMessage.error(`普通表格识别异常: ${error.message}`)
  } finally {
    recognizeLoading.value[loadingKey] = false
  }
}


const handleLLMProcess = async (params) => {
  try {
    console.log('🔄 开始批量LLM处理:', params)

    // 解析参数
    let pdfDiskName, tableTypeFromParams

    if (typeof params === 'object' && params !== null) {
      pdfDiskName = params.pdfName || params.pdfDiskName
      tableTypeFromParams = params.tableType
    } else {
      pdfDiskName = params
      tableTypeFromParams = tableType.value
    }

    const currentTableType = tableTypeFromParams || tableType.value
    console.log('🔄 当前表格类型:', currentTableType)
    console.log('🔄 PDF文件名:', pdfDiskName)

    // 先检查LLM配置状态
    await checkLLMStatus()
    console.log('🔍 批量识别 - LLM配置状态:', llmConfigured.value)

    if (!llmConfigured.value) {
      console.log('❌ 批量识别 - LLM未配置，弹出配置对话框')
      const result = await ElMessageBox.confirm(
        'LLM未配置，请先配置大模型参数后才能进行批量表格识别',
        '提示',
        {
          confirmButtonText: '去配置',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )

      if (result) {
        emit('openLLMConfig')
      }
      return
    }

    // ⭐⭐⭐ 开始处理时设置 loading 状态 ⭐⭐⭐
    llmLoading.value[pdfDiskName] = true

    // 获取裁切的图片路径
    const imageResults = safeJoinedResults.value[pdfDiskName]
    if (!imageResults || imageResults.length === 0) {
      ElMessage.warning('没有可用的裁切图片进行识别')
      llmLoading.value[pdfDiskName] = false // 重置loading状态
      return
    }

    // 将URL转换为文件系统路径 - 简洁版本
const imagePaths = imageResults.map(url => {
  console.log('🔄 处理图片URL:', url)

  let processedUrl = url

  // 如果是HTTP URL，提取路径部分
  if (processedUrl.startsWith('http')) {
    try {
      const urlObj = new URL(processedUrl)
      processedUrl = urlObj.pathname
    } catch (error) {
      // 如果URL解析失败，尝试字符串替换
      processedUrl = processedUrl.replace(/^https?:\/\/[^/]+/, '')
    }
  }

  // 移除基础URL（如果存在）
  if (processedUrl.startsWith(config.backend.baseUrl)) {
    processedUrl = processedUrl.replace(config.backend.baseUrl, '')
  }

  // 确保没有开头的斜杠
  processedUrl = processedUrl.replace(/^\//, '')

  console.log('✅ 转换后路径:', processedUrl)
  return processedUrl
})

    console.log('🔄 批量识别 - 处理后的图片路径:', imagePaths)
    console.log('🔄 批量识别 - 准备处理的图片数量:', imagePaths.length)

    // 构建PDF特定的输出目录
    const pdfStem = pdfDiskName.replace('.pdf', '')
    const outputDir = `static/excel_data/${pdfStem}`

    // 根据表格类型选择API
    const apiCall = currentTableType === 'financial'
      ? llmApi.batchProcess
      : llmApi.batchProcessNonFinancial

    console.log('🔄 批量识别 - 调用API:', currentTableType === 'financial' ? '金融表格' : '普通表格')
    console.log('🔄 批量识别 - API路径:', currentTableType === 'financial' ? '/llm/batch-process' : '/llm/batch-process-non-financial')

    // 构建请求数据
    const requestData = {
      image_paths: imagePaths,
      output_dir: outputDir,
      bank_name: currentTableType === 'financial' ? '未知银行' : '未知机构'
    }

    console.log('🔄 批量识别 - 请求数据:', requestData)

    // 显示处理中的提示
    ElMessage.info('开始批量表格识别，请稍候...')

    const response = await apiCall(requestData)

    console.log('🔍 批量识别 - API响应:', response)

    if (response.success) {
      ElMessage.success(`表格识别完成！成功处理 ${response.data.success} 个文件`)

      // 批量处理完成后，可以加载第一个表格到预览区域
      if (response.data.excel_url) {
        emit('excel-data-received', {
          excelUrl: response.data.excel_url,
          tableName: `批量处理结果`,
          fromCache: false,
          tableType: currentTableType
        })
      } else {
        // 兼容旧的数据结构
        const firstSuccess = response.data.results?.find(r => r.status === 'success')
        if (firstSuccess?.excel_url) {
          emit('excel-data-received', {
            excelUrl: firstSuccess.excel_url,
            tableName: `批量处理结果`,
            fromCache: false,
            tableType: currentTableType
          })
        }
      }
    } else {
      ElMessage.error(`表格识别失败: ${response.error}`)
    }

  } catch (error) {
    console.error('💥 批量LLM处理失败:', error)
    // 如果是配置问题，重新检查状态
    if (error.message?.includes('配置') || error.response?.data?.error?.includes('配置')) {
      llmConfigured.value = false
      console.log('🔄 批量识别 - 检测到配置错误，重置配置状态')
    }
    ElMessage.error('批量表格识别异常: ' + (error.response?.data?.error || error.message))
  } finally {
    // ⭐⭐⭐ 关键：无论成功失败，都要重置 loading 状态 ⭐⭐⭐
    if (typeof params === 'object' && params.pdfName) {
      llmLoading.value[params.pdfName] = false
    } else if (typeof params === 'object' && params.pdfDiskName) {
      llmLoading.value[params.pdfDiskName] = false
    } else {
      llmLoading.value[params] = false
    }

    console.log('🔄 批量处理完成，重置loading状态')
  }
}


const handleSingleLLMProcess = async (params) => {
  try {
    console.log('🔍 FileList接收到的参数:', params)

    // 解析参数
    let excelUrl, index

    if (typeof params === 'object' && params !== null) {
      excelUrl = params.excelUrl || params.excel_url
      index = params.index
    } else {
      console.warn('⚠️ 使用旧版参数格式')
      excelUrl = params
      index = 0
    }

    console.log('🟡 解析后的Excel URL:', excelUrl)
    console.log('🟡 解析后的索引:', index)

    if (!excelUrl) {
      console.error('❌ Excel URL参数丢失')
      ElMessage.error('处理错误：Excel URL丢失')
      return
    }

    // 使用统一配置处理URL转换
    let finalExcelUrl = excelUrl

    // 如果包含完整的后端地址，移除基础URL部分
    if (excelUrl.startsWith(config.backend.baseUrl)) {
      finalExcelUrl = excelUrl.replace(config.backend.baseUrl, '')
    }

    // 确保是相对路径（以/开头）
    if (!finalExcelUrl.startsWith('/')) {
      finalExcelUrl = '/' + finalExcelUrl
    }

    // 将 /static/excel_data/ 转换为 /api/excel-data/
    if (finalExcelUrl.includes('/static/excel_data/')) {
      finalExcelUrl = finalExcelUrl.replace('/static/excel_data/', '/api/excel-data/')
    }

    console.log('🔧 转换后的Excel URL:', finalExcelUrl)

    console.log('📤 发送excel-data-received事件，数据:', {
      excelUrl: finalExcelUrl,
      tableName: `表格${index + 1}`,
      fromCache: true,
      tableType: tableType.value
    })

    // 直接发射到App.vue
    emit('excel-data-received', {
      excelUrl: finalExcelUrl,
      tableName: `表格${index + 1}`,
      fromCache: true,
      tableType: tableType.value
    })

  } catch (error) {
    if (error !== 'cancel') {
      console.error('💥 单张LLM处理失败:', error)
      ElMessage.error('单张表格识别异常: ' + (error.response?.data?.error || error.message))
    }
  }
}



// 检查LLM配置状态 - 修改为更可靠的方法
const checkLLMStatus = async () => {
  try {
    console.log('🔄 检查LLM配置状态...')
    const response = await llmApi.getStatus()
    console.log('🔍 LLM状态响应:', response)

    if (response.success) {
      llmConfigured.value = response.data.client_configured
      console.log(`✅ LLM配置状态: ${llmConfigured.value ? '已配置' : '未配置'}`)
    } else {
      console.error('❌ 获取LLM状态失败:', response.error)
      llmConfigured.value = false
    }
  } catch (error) {
    console.error('💥 检查LLM状态失败:', error)
    llmConfigured.value = false
  }
}

// 监听配置完成事件
const onLLMConfigured = (success = true) => {
  console.log('🎯 收到LLM配置完成事件:', success)
  if (success) {
    // 重新检查LLM状态
    checkLLMStatus()
    ElMessage.success('LLM配置已更新，现在可以识别表格了！')
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

// 监听配置对话框事件
const handleOpenLLMConfig = () => {
  llmConfigRef.value?.open()
}

</script>

<style scoped>
.file-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.table-type-selector {
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  gap: 12px;
}

.selector-label {
  font-weight: 500;
  color: #606266;
  font-size: 14px;
}

.type-description {
  color: #909399;
  font-size: 12px;
  margin-left: auto;
}

/* 新增：防止图片预览对话框闪烁 */
:deep(.el-dialog) {
  transition: none !important;
}

:deep(.image-preview-dialog) {
  animation: none !important;
}

:deep(.preview-image) {
  display: block;
  background: #f5f5f5;
}
</style>