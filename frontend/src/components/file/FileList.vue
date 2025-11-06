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
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { llmApi } from '@/api/llm'
import { getBackendUrl, getStaticUrl, getFullUrl, getConfig } from '@/utils/config'  // 导入统一配置

import PdfPreviewSection from '@/components/pdf/PdfPreview.vue'
import NonPdfFilesSection from '@/components/file/NonPdfFilesSection.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ImagePreviewDialog from '@/components/common/ImagePreviewDialog.vue'


// WebSocket 相关状态
const websocket = ref(null)
const websocketTimeout = ref(null)
const connectionStatus = ref('disconnected')
const isWebSocketConnected = ref(false)
const batchLlmLoading = ref(false)
const ACTIVE_CONNECTIONS = ref({})
const websocketConnected = ref(false)


// 在 FileList.vue 中改进 initWebSocket 函数
const initWebSocket = (taskId, pdfDiskName) => {
  return new Promise((resolve, reject) => {
    const config = getConfig()
    const backendBaseUrl = config.backend.baseUrl
    let wsUrl

    if (backendBaseUrl.startsWith('https://')) {
      wsUrl = backendBaseUrl.replace('https://', 'wss://')
    } else {
      wsUrl = backendBaseUrl.replace('http://', 'ws://')
    }

    wsUrl = `${wsUrl}/ws/task-status/${taskId}`

    console.log('🔗 连接WebSocket:', wsUrl)

    try {
      const ws = new WebSocket(wsUrl)

      // 设置连接超时
      const connectionTimeout = setTimeout(() => {
        if (ws.readyState !== WebSocket.OPEN) {
          console.error('⏰ WebSocket连接超时')
          ws.close()
          reject(new Error('WebSocket连接超时'))
        }
      }, 10000)

      ws.onopen = () => {
        console.log('✅ WebSocket连接已建立')
        clearTimeout(connectionTimeout)
        ACTIVE_CONNECTIONS.value[taskId] = ws
        isWebSocketConnected.value = true
        connectionStatus.value = 'connected'

        // 发送ping消息确认连接
        ws.send(JSON.stringify({ type: 'ping' }))
        resolve(ws)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('📨 收到WebSocket消息:', data)

          // ⭐⭐⭐ 处理任务完成消息 ⭐⭐⭐
          if (data.type === 'task_completed' || data.processing_completed || data.status === 'completed') {
            console.log('🎉 收到任务完成通知')

            // 立即发送excel-data-received事件
            if (data.excel_url || (data.data && data.data.excel_url)) {
              const excelUrl = data.excel_url || data.data.excel_url
              const tableType = data.table_type || data.data?.table_type || 'non_financial'

              console.log('📤 通过WebSocket发送excel-data-received事件:', {
                excelUrl,
                tableType,
                pdfDiskName
              })

              let cleanExcelUrl = excelUrl
              if (cleanExcelUrl.includes('?')) {
                cleanExcelUrl = cleanExcelUrl.split('?')[0]
              }

              // ⭐⭐⭐ 直接发送事件到App.vue ⭐⭐⭐
              emit('excel-data-received', {
                excelUrl: cleanExcelUrl,
                tableName: `批量处理结果 - ${pdfDiskName}`,
                fromCache: false,
                tableType: tableType
              })

              console.log('✅ WebSocket事件发送完成')
            }

            // 关闭WebSocket连接
            if (ws.readyState === WebSocket.OPEN) {
              ws.close()
            }

            // 重置loading状态
            resetLoadingState(pdfDiskName)
          }

          // 处理错误消息
          else if (data.type === 'task_error' || data.status === 'error') {
            console.log('❌ 收到任务错误通知')
            ElMessage.error(data.error || '处理失败')

            if (ws.readyState === WebSocket.OPEN) {
              ws.close()
            }
            resetLoadingState(pdfDiskName)
          }

          // 处理进度消息
          else if (data.type === 'task_progress') {
            console.log(`📊 处理进度: ${data.progress}% - ${data.message}`)
          }

        } catch (error) {
          console.error('❌ 解析WebSocket消息失败:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('❌ WebSocket连接错误:', error)
        clearTimeout(connectionTimeout)
        isWebSocketConnected.value = false
        connectionStatus.value = 'error'
        reject(error)
      }

      ws.onclose = (event) => {
        console.log('🔗 WebSocket连接已关闭', {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean
        })
        clearTimeout(connectionTimeout)
        isWebSocketConnected.value = false
        connectionStatus.value = 'disconnected'

        if (ACTIVE_CONNECTIONS.value[taskId]) {
          delete ACTIVE_CONNECTIONS.value[taskId]
        }

        // 连接关闭时重置loading状态
        if (llmLoading.value[pdfDiskName]) {
          console.log('🔄 WebSocket连接关闭，重置loading状态')
          resetLoadingState(pdfDiskName)
        }
      }

    } catch (error) {
      console.error('💥 创建WebSocket失败:', error)
      reject(error)
    }
  })
}


// 改进 handleTaskCompleted 函数
const handleTaskCompleted = (data, pdfDiskName) => {
  console.log('🎉 任务完成:', data)

  // ⭐⭐⭐ 关键修复：确保无论如何都重置loading状态 ⭐⭐⭐
  resetLoadingState(pdfDiskName)

  ElMessage.success('表格识别完成！')

  // 如果有数据，处理返回的结果
  if (data.data) {
    const result = data.data
    console.log('📊 处理结果数据:', result)

    // 如果有Excel URL，可以在这里处理
    if (result.excel_url) {
      console.log('📄 生成的Excel文件:', result.excel_url)
      emit('excel-data-received', {
        excelUrl: result.excel_url,
        tableName: `批量处理结果`,
        fromCache: false,
        tableType: result.table_type || 'financial'
      })
    }
  }
}

// 改进 handleTaskError 函数
const handleTaskError = (data, pdfDiskName) => {
  console.error('❌ 任务出错:', data)

  // ⭐⭐⭐ 关键修复：错误时也要重置loading状态 ⭐⭐⭐
  resetLoadingState(pdfDiskName)

  ElMessage.error(`处理失败: ${data.error || '未知错误'}`)
}



// 简化 resetLoadingState 函数
const resetLoadingState = (pdfDiskName) => {
  console.log('🔄 重置loading状态', { pdfDiskName })

  if (pdfDiskName) {
    // ⭐⭐⭐ 简化：直接使用响应式赋值 ⭐⭐⭐
    llmLoading.value[pdfDiskName] = false

    console.log('✅ 成功重置loading状态:', pdfDiskName, '当前状态:', llmLoading.value[pdfDiskName])
  }

  // ⭐⭐⭐ 移除不存在的 websocketTimeout 相关代码 ⭐⭐⭐
}


// 在 handleWebSocketMessage 函数中，确保能处理各种完成状态
const handleWebSocketMessage = (data, taskId, pdfDiskName) => {
  const { type, status, message, error, excel_url, table_type, processing_completed } = data

  console.log('🔍 处理WebSocket消息详情:', {
    type, taskId, pdfDiskName, processing_completed,
    currentLoadingState: pdfDiskName ? llmLoading.value[pdfDiskName] : 'undefined'
  })

  // ⭐⭐⭐ 关键：如果收到 processing_completed 标记，立即重置状态 ⭐⭐⭐
  if (processing_completed || type === 'task_completed' || type === 'task_error') {
    console.log('✅ 收到完成状态消息，重置loading')
    resetLoadingState(pdfDiskName)
  }

  switch (type) {
    case 'connection_established':
      console.log('✅ WebSocket连接确认')
      break

    case 'task_completed':
      console.log('🎉 收到后端任务完成通知')
      ElMessage.success(message || '批量处理完成！')

      if (excel_url) {
        emit('excel-data-received', {
          excelUrl: excel_url,
          tableName: `批量处理结果`,
          fromCache: false,
          tableType: status.table_type || 'financial'
        })
      }
      break

    case 'task_error':
      console.log('❌ 收到后端任务错误通知')
      ElMessage.error(error || '处理失败')
      break

    case 'task_progress':
      console.log(`📊 收到后端进度更新: ${data.progress}% - ${data.message}`)
      // 可以在这里更新进度条
      if (data.progress % 20 === 0) { // 每20%显示一次进度
        ElMessage.info(`处理进度: ${data.progress}% - ${data.message}`)
      }
      break

    case 'task_started':
      console.log('🚀 收到后端任务开始通知')
      break

    default:
      console.log('❓ 未知消息类型:', type)
  }
}

// 添加强制刷新方法
const forceRefreshExcel = () => {
  if (currentExcelData.value) {
    const excelInfo = {
      excelUrl: currentExcelData.value.originalExcelPath,
      tableName: currentExcelData.value.tableName,
      tableType: currentExcelData.value.tableType
    }
    handleExcelDataReceived(excelInfo)
    ElMessage.info('正在强制刷新Excel数据...')
  }
}

// 改进关闭WebSocket函数
const closeWebSocket = () => {
  Object.keys(ACTIVE_CONNECTIONS.value).forEach(taskId => {
    const ws = ACTIVE_CONNECTIONS.value[taskId]
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close()
    }
    delete ACTIVE_CONNECTIONS.value[taskId]
  })
  console.log('🔗 关闭所有WebSocket连接')
}


// 组件卸载时清理
onUnmounted(() => {
  closeWebSocket()
})


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
  let pdfDiskName = ''
  let taskId = ''

  try {
    // 解析参数
    if (typeof params === 'object' && params !== null) {
      pdfDiskName = params.pdfName || params.pdfDiskName
    } else {
      pdfDiskName = params
    }

    console.log('🔄 开始批量LLM处理:', { params, pdfDiskName })

    // 设置 loading 状态
    llmLoading.value[pdfDiskName] = true

    // 检查LLM配置状态
    await checkLLMStatus()

    if (!llmConfigured.value) {
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
      llmLoading.value[pdfDiskName] = false
      return
    }

    // 获取裁切的图片路径
    const imageResults = safeJoinedResults.value[pdfDiskName]
    if (!imageResults || imageResults.length === 0) {
      ElMessage.warning('没有可用的裁切图片进行识别')
      llmLoading.value[pdfDiskName] = false
      return
    }

    // 转换图片路径
    const imagePaths = imageResults.map(url => {
      let processedUrl = url
      if (processedUrl.startsWith('http')) {
        try {
          const urlObj = new URL(processedUrl)
          processedUrl = urlObj.pathname
        } catch (error) {
          processedUrl = processedUrl.replace(/^https?:\/\/[^/]+/, '')
        }
      }
      if (processedUrl.startsWith(config.backend.baseUrl)) {
        processedUrl = processedUrl.replace(config.backend.baseUrl, '')
      }
      processedUrl = processedUrl.replace(/^\//, '')
      return processedUrl
    })

    // 构建PDF特定的输出目录
    const pdfStem = pdfDiskName.replace('.pdf', '')
    const outputDir = `static/excel_data/${pdfStem}`

    // 根据表格类型选择API
    const currentTableType = params.tableType || tableType.value
    const apiCall = currentTableType === 'financial'
      ? llmApi.batchProcess
      : llmApi.batchProcessNonFinancial

    console.log('🔄 批量识别 - 表格类型:', currentTableType)

    // 构建请求数据
    const requestData = {
      image_paths: imagePaths,
      output_dir: outputDir,
      bank_name: currentTableType === 'financial' ? '未知银行' : '未知机构',
      table_type: currentTableType
    }

    console.log('🔄 批量识别 - 请求数据:', requestData)

    ElMessage.info('开始批量表格识别，请等待处理完成...')

    // 调用API开始处理
    const response = await apiCall(requestData)
    console.log('🔍 批量识别 - API响应:', response)

    // 获取任务ID
    taskId = response.task_id

    // ⭐⭐⭐ 关键修复：改进响应处理逻辑 ⭐⭐⭐
    if (response && response.task_id) {
      // 如果有task_id，说明任务已提交，不管success是true还是false
      taskId = response.task_id
      console.log('🎯 获取到任务ID:', taskId)

      // 启动轮询检查任务结果
      startSimplePolling(taskId, pdfDiskName, currentTableType)

    } else if (response && response.success === false) {
      // 如果明确失败且没有task_id
      console.error('❌ API调用明确失败:', response.error)
      resetLoadingState(pdfDiskName)
      ElMessage.error(`表格识别失败: ${response.error}`)

    } else {
      // 其他情况
      console.warn('⚠️ 无法处理API响应:', response)
      resetLoadingState(pdfDiskName)
      ElMessage.error('处理失败：未知响应格式')
    }

  } catch (error) {
    console.error('💥 批量LLM处理失败:', error)
    ElMessage.error('批量表格识别异常: ' + (error.response?.data?.error || error.message))
    resetLoadingState(pdfDiskName)
  }
}


const startSimplePolling = (taskId, pdfDiskName, tableType) => {
  console.log('🔄 启动轮询检查任务结果:', { taskId, pdfDiskName, tableType })

  let pollCount = 0
  const maxPollCount = 60

  const pollInterval = setInterval(async () => {
    pollCount++

    try {
      console.log(`🔍 第${pollCount}次检查任务: ${taskId}`)
      const response = await llmApi.getTaskResult(taskId)

      console.log('📊 任务结果响应:', response)

      // ⭐⭐⭐ 改进响应处理：支持多种格式 ⭐⭐⭐
      if (response && response.data) {
        const result = response.data

        console.log('📊 任务状态详情:', {
          status: result.status,
          processing_completed: result.processing_completed,
          hasData: !!result.data,
          hasExcelUrl: !!(result.data?.excel_url)
        })

        // 检查任务是否完成
        if (result.status === 'completed' || result.processing_completed) {
          console.log('✅ 任务完成，停止轮询')
          clearInterval(pollInterval)

          // 发送excel-data-received事件
          if (result.data?.excel_url) {
            let cleanExcelUrl = result.data.excel_url
            if (cleanExcelUrl.includes('?')) {
              cleanExcelUrl = cleanExcelUrl.split('?')[0]
            }

            console.log('📤 发送事件 - Excel URL:', cleanExcelUrl)

            emit('excel-data-received', {
              excelUrl: cleanExcelUrl,
              tableName: `批量处理结果 - ${pdfDiskName}`,
              fromCache: false,
              tableType: result.data.table_type || tableType || 'non_financial'
            })

            console.log('✅ 事件发送完成')
          }

          resetLoadingState(pdfDiskName)
          ElMessage.success('批量处理完成！')
          return
        }

        if (result.status === 'error') {
          console.log('❌ 任务出错')
          clearInterval(pollInterval)
          resetLoadingState(pdfDiskName)
          ElMessage.error(result.error || '处理失败')
          return
        }

        console.log('⏳ 任务处理中...')

      } else if (response && response.success === false) {
        // 如果查询任务结果失败
        console.error('❌ 查询任务结果失败:', response.error)

        if (pollCount > 5) {
          console.error('❌ 多次查询失败，停止轮询')
          clearInterval(pollInterval)
          resetLoadingState(pdfDiskName)
          ElMessage.error('获取任务结果失败')
        }
      } else {
        console.warn('⚠️ 无法识别的响应格式:', response)
      }

      // 检查是否达到最大轮询次数
      if (pollCount >= maxPollCount) {
        console.warn('⚠️ 达到最大轮询次数，停止轮询')
        clearInterval(pollInterval)
        resetLoadingState(pdfDiskName)
        ElMessage.warning('处理时间过长，请检查后台状态')
      }

    } catch (error) {
      console.error('❌ 轮询异常:', error)

      if (pollCount > 10) {
        console.error('❌ 多次轮询异常，停止轮询')
        clearInterval(pollInterval)
        resetLoadingState(pdfDiskName)
        ElMessage.error('获取任务结果异常')
      }
    }
  }, 3000)
}


// 在 FileList.vue 的 setup 中添加
const handleForceResetLoading = (data) => {
  console.log('🔄 收到强制重置请求:', data)
  if (data.pdfName) {
    llmLoading.value[data.pdfName] = false
  }
}

// 改进的状态轮询函数
const startStatusPolling = (taskId, pdfDiskName) => {
  console.log('🔄 启动状态轮询，任务ID:', taskId)

  let pollCount = 0
  const maxPollCount = 300 // 最多轮询50分钟（10s * 300 = 3000s = 50min）
  let lastProgress = 0

  const pollInterval = setInterval(async () => {
    pollCount++

    try {
      console.log(`🔍 第${pollCount}次轮询任务状态: ${taskId}`)
      const response = await llmApi.getProcessingStatus(taskId)

      if (response.success && response.data) {
        const status = response.data

        console.log(`📊 任务状态详情:`, status)

        // ⭐⭐⭐ 更强的完成检测逻辑 ⭐⭐⭐
        const isCompleted = status.processing_completed ||
                           status.status === 'completed' ||
                           status.status === 'error' ||
                           (status.progress === 100 && status.status === 'processing')

        if (isCompleted) {
          console.log('✅ 轮询检测到任务已完成，立即返回结果')
          clearInterval(pollInterval)
          resetLoadingState(pdfDiskName)

          // 根据状态显示不同消息
          if (status.status === 'completed' || status.processing_completed) {
            ElMessage.success(status.message || '批量处理完成！')
            console.log('🎉 批量处理完成，成功重置loading状态')

            if (status.excel_url) {
              emit('excel-data-received', {
                excelUrl: status.excel_url,
                tableName: `批量处理结果`,
                fromCache: false,
                tableType: status.table_type || 'financial'
              })
            }
          } else if (status.status === 'error') {
            ElMessage.error(status.message || '处理失败')
          }
          return
        }

        // 显示进度变化
        if (status.status === 'processing' && status.progress !== lastProgress) {
          lastProgress = status.progress
          console.log(`⏳ 处理进度: ${status.progress}% - ${status.message}`)

          // 每20%或进度有显著变化时显示提示
          if (status.progress % 20 === 0 || status.progress - lastProgress >= 10) {
            ElMessage.info(`处理进度: ${status.progress}% - ${status.message}`)
          }
        }

        // 检查是否达到最大轮询次数
        if (pollCount >= maxPollCount) {
          console.warn('⚠️ 达到最大轮询次数，强制结束')
          clearInterval(pollInterval)
          resetLoadingState(pdfDiskName)
          ElMessage.warning('处理时间过长，请检查后台处理状态')
        }

      } else {
        console.error('❌ 获取任务状态失败:', response.error)
        // 连续多次获取状态失败则停止
        if (pollCount > 10) {
          console.error('❌ 多次获取状态失败，停止轮询')
          clearInterval(pollInterval)
          resetLoadingState(pdfDiskName)
          ElMessage.error('获取处理状态失败，请检查网络连接')
        }
      }

    } catch (error) {
      console.error('轮询状态失败:', error)

      // 连续多次轮询失败则停止
      if (pollCount > 15) {
        console.error('❌ 多次轮询失败，停止轮询')
        clearInterval(pollInterval)
        resetLoadingState(pdfDiskName)
        ElMessage.error('获取处理状态失败，请检查网络连接')
      }
    }
  }, 5000) // ⭐⭐⭐ 改为5秒轮询一次，更快响应 ⭐⭐⭐
}


const checkTaskResult = (taskId, pdfDiskName, tableType) => {
  console.log('🔄 启动任务结果检查:', { taskId, pdfDiskName, tableType })

  let pollCount = 0
  const maxPollCount = 60 // 最多轮询5分钟

  const pollInterval = setInterval(async () => {
    pollCount++

    try {
      console.log(`🔍 第${pollCount}次检查任务结果: ${taskId}`)
      const response = await llmApi.getTaskResult(taskId)

      if (response.success && response.data) {
        const result = response.data

        console.log('📊 任务结果详情:', {
          status: result.status,
          processing_completed: result.processing_completed,
          hasExcelUrl: !!(result.data?.excel_url),
          excelUrl: result.data?.excel_url,
          tableType: result.data?.table_type
        })

        // 检查任务是否完成
        const isCompleted = result.status === 'completed' || result.processing_completed

        if (isCompleted) {
          console.log('✅ 任务已完成，停止轮询')
          clearInterval(pollInterval)

          // ⭐⭐⭐ 关键修复：确保使用新的Excel URL ⭐⭐⭐
          if (result.data?.excel_url) {
            let cleanExcelUrl = result.data.excel_url
            if (cleanExcelUrl.includes('?')) {
              cleanExcelUrl = cleanExcelUrl.split('?')[0]
            }

            console.log('📤 发送excel-data-received事件:', {
              excelUrl: cleanExcelUrl,
              expectedType: tableType,
              actualType: result.data.table_type
            })

            // ⭐⭐⭐ 确保发送正确的事件 ⭐⭐⭐
            emit('excel-data-received', {
              excelUrl: cleanExcelUrl,
              tableName: `批量处理结果 - ${pdfDiskName}`,
              fromCache: false,
              tableType: result.data.table_type || tableType || 'non_financial'
            })

            console.log('✅ 事件发送完成')
          } else {
            console.warn('⚠️ 任务完成但没有excel_url')
          }

          resetLoadingState(pdfDiskName)
          ElMessage.success(result.data?.message || '批量处理完成！')
          return
        }

        if (result.status === 'error') {
          console.log('❌ 任务出错')
          clearInterval(pollInterval)
          resetLoadingState(pdfDiskName)
          ElMessage.error(result.error || '处理失败')
          return
        }

        console.log('⏳ 任务处理中...')

      } else {
        console.error('❌ 查询任务结果失败:', response.error)

        // 如果多次失败，停止轮询
        if (pollCount > 10) {
          console.error('❌ 多次查询失败，停止轮询')
          clearInterval(pollInterval)
          resetLoadingState(pdfDiskName)
          ElMessage.error('获取任务结果失败')
        }
      }

      // 检查是否达到最大轮询次数
      if (pollCount >= maxPollCount) {
        console.warn('⚠️ 达到最大轮询次数，停止轮询')
        clearInterval(pollInterval)
        resetLoadingState(pdfDiskName)
        ElMessage.warning('处理时间过长，请检查后台状态')
      }

    } catch (error) {
      console.error('❌ 检查任务结果异常:', error)

      if (pollCount > 15) {
        console.error('❌ 多次异常，停止轮询')
        clearInterval(pollInterval)
        resetLoadingState(pdfDiskName)
        ElMessage.error('检查任务结果异常')
      }
    }
  }, 3000) // 3秒轮询一次，更快响应
}

const cleanupTask = (taskId) => {
  if (ACTIVE_CONNECTIONS.value[taskId]) {
    const ws = ACTIVE_CONNECTIONS.value[taskId]
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close()
    }
    delete ACTIVE_CONNECTIONS.value[taskId]
  }
}

const emergencyReset = () => {
  console.log('🚨 执行紧急重置')
  Object.keys(llmLoading.value).forEach(key => {
    llmLoading.value[key] = false
  })
  ElMessage.info('已强制重置所有loading状态')
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