<!-- frontend/src/views/TwoColumnPage.vue -->
<template>
  <TwoColumnLayout
      :files="files"
      :crop-loading="cropLoading"
      :cut-results="cutResults"
      :converting-obj="convertingObj"
      :convert-cache="convertCache"
      :batch-crop-loading="batchCropLoading"
      :joined-results="joinedResults"
      :current-excel-data="currentExcelData"
      :has-screened-images="hasScreenedImages"
      :screening-result-map="screeningResultMap"
      :current-pdf="currentPdf"
      :other-pdfs="otherPdfs"
      :is-screening="isScreening"
      :is-parsing="isParsing"
      :has-results="hasResults"
      :has-batch-results="hasBatchResults"
      :llm-loading="llmLoading"
      :table-type="tableType"
      :step-completion-time="stepCompletionTime"
      :step-statuses="stepStatuses"
      :parsing-progress-map="parsingProgressMap"
      @load-files="loadFiles"
      @delete-file="deleteFile"
      @cut-table="cutTable"
      @convert-and-preview="convertAndPreview"
      @handle-batch-crop="handleBatchCrop"
      @handle-screen-images="handleScreenImages"
      @handle-open-classification="handleOpenClassification"
      @switch-pdf="switchToPdf"
      @clear-cache="handleClearCache"
      @parse-tables="handleParseTables"
      @table-type-change="handleTableTypeChange"
      @screen-images-completed="handleScreenImagesCompleted"
      @parse-tables-completed="handleParseTablesCompleted"
    />

  <!-- 确保全局组件在正确的位置 -->
    <ProgressDialog v-model="progressVisible" :percent="progressPercent" :status="progressStatus" :msg="progressMsg"/>
    <PdfPagePreview
      v-model:visible="previewVisible"
      :folder="previewFolder"
      :pngs="previewPngs"
    />
    <LLMConfig ref="llmConfigRef" @configured="onLLMConfigured" />
    <VisualizationPanel
      :visible="visualizationVisible"
      @update:visible="visualizationVisible = $event"
      :excel-data="currentExcelData"
      :key="visualizationKey"
    />

    <!-- 图片分类管理器对话框 -->
    <el-dialog
      v-model="screeningVisible"
      title="图片分类管理"
      width="95%"
      top="2vh"
      destroy-on-close
      class="screening-manager-dialog"
      :close-on-click-modal="false"
    >
      <!-- ⭐⭐ 简化条件：只要对话框可见且有当前PDF就显示 -->
      <ImageScreeningManager
        v-if="screeningVisible && currentScreeningPdf"
        :pdf-disk-name="currentScreeningPdf"
        :classified-images="screeningData[currentScreeningPdf] || { tables: [], no_tables: [], uncertain: [] }"
        :stats="screeningStats[currentScreeningPdf] || {}"
        :get-image-url-fn="getImageUrl"
        @close="closeImageClassification"
        @refresh="handleRefreshClassification"
        @move-image="handleMoveImage"
        @redetect-image="handleRedetectImage"
        @finish="handleFinishClassification"
        @image-error="handleImageError"
      />

      <!-- 加载状态 -->
      <div v-else class="loading-container">
        <el-skeleton :rows="10" animated />
      </div>
    </el-dialog>



</template>

<script setup>
import { ref, onMounted, nextTick, computed, watch } from 'vue'  // 添加了 watch 导入
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
// 在现有的import部分添加
import { screeningApi } from '@/api/screening'
// 或者使用 convertApi 中的方法
import { convertApi } from '@/api/convert'
// 在已有的import语句后面添加
import ImageScreeningManager from '@/components/pdf/ImageScreeningManager.vue'

// 组件导入
import TwoColumnLayout from '@/layouts/TwoColumnLayout.vue'
import LLMConfig from '@/components/common/LLMConfig.vue'
import PdfPagePreview from '@/components/pdf/PdfPagePreview.vue'
import ProgressDialog from '@/components/processing/ProgressDialog.vue'
import VisualizationPanel from '@/components/pdf/VisualizationPanel.vue'


// API导入
import { getFiles, deleteFile as delApi } from '@/api/file'
import { getPngList } from '@/api/convert'

// Composables导入
import { useCrop } from '@/composables/useCrop'
import { useBatchTableCrop } from '@/composables/useBatchTableCrop'
import { llmApi } from '@/api/llm'
import { baiduOcrApi } from '@/api/baiduOcr'

// 工具函数导入
import { getBackendUrl, getStaticUrl } from '@/utils/config'


// ---------------- 数据声明（从App.vue迁移过来） ----------------
const files = ref([])
const cropLoading = ref({})
const cutResults = ref({})
const convertCache = ref({})
const convertingObj = ref({})
const progressVisible = ref(false)
const progressPercent = ref(0)
const progressStatus = ref('')
const progressMsg = ref('')
const previewVisible = ref(false)
const previewFolder = ref('')
const previewPngs = ref([])
const currentExcelData = ref(null)
const llmConfigRef = ref()
const joinedResults = ref({})
const visualizationVisible = ref(false)
const visualizationKey = ref(0)
const excelViewerKey = ref(0)
const screeningResultMap = ref({})

const screeningData = ref({}) // 分类图片数据：{ pdfName: { tables: [], no_tables: [] } }
const screeningVisible = ref(false) // 筛选管理器可见性
const currentScreeningPdf = ref('') // 当前正在管理的PDF
const screeningStats = ref({}) // 筛选统计信息
// 新增：图片筛选状态（用于PdfControls显示）
const hasScreenedImages = ref({}) // { pdfName: true/false }

// ---------------- 初始化 composables ----------------
const { cutTablesForPDF, batchCropLoading } = useBatchTableCrop(joinedResults)

// ---------------- 新增：当前PDF相关状态 ----------------
const currentPdfDiskName = ref('') // 当前处理的PDF（disk_name格式）
const lastOperationTime = ref({})  // 记录每个PDF的最后操作时间 {pdfDiskName: timestamp}

// ---------------- 新增：其他必要的状态 ----------------
const isScreening = ref(false)  // 筛选loading状态
const isParsing = ref(false)    // 解析loading状态
const hasResults = ref(false)   // 是否有解析结果
const hasBatchResults = ref(false) // 是否有批量裁切结果
const stepCompletionTime = ref({})
const stepStatuses = ref({})
const llmLoading = ref({})  // LLM加载状态
const tableType = ref('financial')  // 表格类型
const parsingProgressMap = ref({})


// 添加 defineEmits
const emit = defineEmits([
  'load-files',
  'delete-file',
  'cut-table',
  'convert-and-preview',
  'handle-batch-crop',
  'handle-screen-images',
  'handle-open-classification',
  'switch-pdf',
  'clear-cache',
  'parse-tables',
  'table-type-change',
  'screen-images-completed',
  'parse-tables-completed',
  'update-step-status'
])


// ---------------- 生命周期 ----------------
onMounted(async () => {
  await loadFiles()
  // 检查百度OCR服务状态
  await checkBaiduOCRHealth()
})

// ---------------- 百度OCR相关函数 ----------------
async function checkBaiduOCRHealth() {
  try {
    const result = await baiduOcrApi.healthCheck()
    if (result.success) {
      console.log('✅ 百度OCR服务正常')
      ElMessage.success('百度OCR服务已就绪')
    } else {
      console.warn('⚠️ 百度OCR服务异常:', result.error)
      ElMessage.warning('百度OCR服务异常，识别功能可能不可用')
    }
  } catch (error) {
    console.error('❌ 百度OCR健康检查失败:', error)
    ElMessage.error('百度OCR服务连接失败')
  }
}

// 新增：处理OCR完成事件
async function handleOcrCompleted(ocrResult) {
  try {
    console.log('🎯 TwoColumnPage 收到 OCR 完成事件:', ocrResult)

    if (!ocrResult.success) {
      ElMessage.error(`OCR识别失败: ${ocrResult.error}`)
      return
    }

    // 构建excelInfo，触发Excel数据加载
    const excelInfo = {
      excelUrl: ocrResult.excelUrl,
      tableName: ocrResult.tableName || '百度OCR识别结果',
      tableType: 'baidu_ocr',
      originalFilename: ocrResult.originalFilename
    }

    console.log('🔄 开始加载OCR识别结果:', excelInfo)
    await handleExcelDataReceived(excelInfo)

  } catch (error) {
    console.error('💥 处理OCR结果失败:', error)
    ElMessage.error('处理识别结果失败: ' + error.message)
  }
}




// 处理清除缓存
const handleClearCache = (pdfDiskName) => {
  console.log('🔄 清除缓存:', pdfDiskName)
  // 清除相关缓存
  const cacheKey = pdfDiskName.replace('.pdf', '')
  if (convertCache.value[cacheKey]) {
    delete convertCache.value[cacheKey]
    ElMessage.success('已清除缓存')
  }

  // 清除转图状态
  if (convertingObj.value[pdfDiskName]) {
    delete convertingObj.value[pdfDiskName]
  }
}

// 处理表格类型变化
const handleTableTypeChange = (newType) => {
  console.log('📊 表格类型变化:', newType)
  tableType.value = newType
  ElMessage.info(`表格类型已切换为: ${newType === 'financial' ? '财务报表' : '非财务报表'}`)
}

// 处理图片筛选
const handleScreenImages = (pdfDiskName) => {
  console.log('🖼️ 开始图片筛选:', pdfDiskName)

  // 更新当前PDF
  updateCurrentPdf(pdfDiskName)

  // 设置筛选中状态
  isScreening.value = true

  // 显示进度对话框
  progressVisible.value = true
  progressPercent.value = 0
  progressStatus.value = ''
  progressMsg.value = '正在筛选图片...'

  // 模拟筛选过程（实际应该调用API）
  setTimeout(() => {
    // 模拟筛选完成
    const screeningResult = {
      success: true,
      pdfDiskName: pdfDiskName,
      total_count: 43,
      has_table_count: 15,
      no_table_count: 28
    }

    // 调用完成回调
    handleScreenImagesCompleted({
      pdfDiskName: pdfDiskName,
      hasScreened: true,
      screeningResult: screeningResult
    })

    // 关闭进度对话框
    progressVisible.value = false
    isScreening.value = false

  }, 2000)
}



// 修改：加载分类数据的函数 - 移除 ElMessage.info
const loadClassificationData = async (pdfDiskName) => {
  try {
    console.log('🔄 加载分类数据:', pdfDiskName)
    const pdfFolder = pdfDiskName.replace('.pdf', '')

    // 移除加载状态的 ElMessage.info，因为它可能会导致组件创建问题
    // 如果需要显示加载状态，可以使用其他方式，比如设置一个 loading 变量

    // 调用真实的API获取分类数据
    const response = await screeningApi.getClassifiedImages(pdfFolder)

    if (response.success) {
      console.log('✅ API返回的分类数据:', response)

      // 处理图片数据，使用原有的 getImageUrl 函数
      const processImages = (images, type) => {
        return (images || []).map(img => {
          const processedImg = {
            ...img,
            // 确保图片有正确的URL
            url: img.url || getImageUrl(img, pdfFolder),
            // 如果没有type，根据分类设置
            type: img.type || type,
            // 如果没有name但有path，从path中提取name
            name: img.name || (img.path ? img.path.split('/').pop() : '')
          }

          // 确保URL是字符串
          if (typeof processedImg.url !== 'string') {
            console.warn('⚠️ 图片URL不是字符串:', processedImg.url)
            processedImg.url = getImageUrl(processedImg, pdfFolder)
          }

          return processedImg
        })
      }

      const processedData = {
        tables: processImages(response.data?.tables, 'tables'),
        no_tables: processImages(response.data?.no_tables, 'no_tables'),
        uncertain: processImages(response.data?.uncertain, 'uncertain')
      }

      screeningData.value[pdfDiskName] = processedData
      screeningStats.value[pdfDiskName] = response.stats || {
        total: 0,
        tables_count: 0,
        no_tables_count: 0,
        uncertain_count: 0
      }

      // 强制响应式更新
      screeningData.value = { ...screeningData.value }
      screeningStats.value = { ...screeningStats.value }

      console.log('✅ 分类数据加载完成:', {
        pdfFolder,
        tables: processedData.tables?.length || 0,
        no_tables: processedData.no_tables?.length || 0,
        uncertain: processedData.uncertain?.length || 0,
        stats: screeningStats.value[pdfDiskName],
        sampleTableUrl: processedData.tables[0]?.url || '无表格图片'
      })

      // 检查图片URL是否正确
      if (processedData.tables.length > 0) {
        console.log('🔍 检查表格图片URL:', {
          name: processedData.tables[0].name,
          path: processedData.tables[0].path,
          url: processedData.tables[0].url,
          type: processedData.tables[0].type
        })
      }

      return true

    } else {
      throw new Error(response.error || '获取分类数据失败')
    }

  } catch (error) {
    console.error('❌ 加载分类数据失败:', error)

    // 使用延迟调用，避免在组件挂载过程中调用 ElMessage
    setTimeout(() => {
      ElMessage.error(`加载分类数据失败: ${error.message}`)
    }, 100)

    // 如果API调用失败，可以提供一个空的数据结构
    screeningData.value[pdfDiskName] = {
      tables: [],
      no_tables: [],
      uncertain: []
    }
    screeningStats.value[pdfDiskName] = {
      total: 0,
      tables_count: 0,
      no_tables_count: 0,
      uncertain_count: 0
    }

    return false
  }
}

// 同时，修改 handleOpenClassification 函数
const handleOpenClassification = async (pdfDiskName) => {
  console.log('📁 打开图片分类管理:', pdfDiskName)

  // 更新当前PDF
  updateCurrentPdf(pdfDiskName)

  // 设置当前管理的PDF
  currentScreeningPdf.value = pdfDiskName

  // 打开对话框
  screeningVisible.value = true

  // 在对话框打开后加载分类数据
  // 使用 nextTick 确保对话框已经渲染
  await nextTick()

  // 加载分类数据
  await loadClassificationData(pdfDiskName)
}


// 监听对话框显示状态
watch(screeningVisible, async (newVal) => {
  if (newVal && currentScreeningPdf.value) {
    // 对话框打开且当前PDF存在时，加载数据
    console.log('📁 对话框打开，加载分类数据:', currentScreeningPdf.value)
    await loadClassificationData(currentScreeningPdf.value)
  }
})

// 简化 getImageUrl 函数，确保它始终返回字符串
const getImageUrl = (imageData, pdfFolder) => {
  try {
    if (!imageData) return ''

    // 优先使用已有的URL
    if (imageData.url && typeof imageData.url === 'string') {
      return imageData.url
    }

    // 如果有path，优先处理path
    if (imageData.path && typeof imageData.path === 'string') {
      // 处理路径
      if (imageData.path.startsWith('http')) return imageData.path
      if (imageData.path.startsWith('/')) return imageData.path

      // 构建完整URL
      const baseUrl = window.location.origin

      // 尝试不同的路径模式
      if (imageData.path.includes('filtered_tables')) {
        return `${baseUrl}/api/${imageData.path}`
      } else if (imageData.path.includes('png_output')) {
        return `${baseUrl}/api/${imageData.path}`
      } else {
        // 如果path不是标准格式，尝试提取文件名
        const fileName = imageData.path.split('/').pop()
        if (fileName) {
          return `${baseUrl}/api/png/${pdfFolder}/${fileName}`
        }
      }
    }

    // 如果有name但没有path
    if (imageData.name && typeof imageData.name === 'string') {
      const baseUrl = window.location.origin
      const type = imageData.type || 'tables'

      // 根据图片类型构建URL
      if (type === 'tables' || type === 'no_tables' || type === 'uncertain') {
        // 分类图片
        return `${baseUrl}/api/filtered-tables-image/${pdfFolder}/${type}/${imageData.name}`
      } else {
        // 普通PNG图片
        return `${baseUrl}/api/png/${pdfFolder}/${imageData.name}`
      }
    }

    // 最后的回退方案
    console.warn('⚠️ 无法生成图片URL:', { imageData, pdfFolder })
    return ''
  } catch (error) {
    console.error('❌ 生成图片URL时出错:', error)
    return ''
  }
}



// 添加图片错误处理函数
const handleImageError = (image, event) => {
  console.error('🖼️ 图片加载失败:', {
    imageName: image?.name,
    imageUrl: image?.url,
    eventTargetSrc: event?.target?.src,
    pdfFolder: currentScreeningPdf.value?.replace('.pdf', '')
  })

  // 尝试使用备用方案重新生成URL
  if (image && event?.target) {
    const pdfFolder = currentScreeningPdf.value?.replace('.pdf', '') || ''
    const backupUrl = getImageUrl(image, pdfFolder)

    console.log('🔄 尝试备用URL:', backupUrl)

    // 如果备份URL与当前不同，尝试加载
    if (backupUrl && backupUrl !== event.target.src) {
      event.target.src = backupUrl
    }
  }
}




// ---------------- 辅助函数：更新当前PDF ----------------
const updateCurrentPdf = (pdfDiskName) => {
  if (!pdfDiskName) return

  currentPdfDiskName.value = pdfDiskName
  lastOperationTime.value[pdfDiskName] = Date.now()

  console.log('📌 更新当前PDF:', pdfDiskName, {
    timestamp: new Date().toISOString(),
    operationCount: Object.keys(lastOperationTime.value).length
  })
}

// ---------------- 计算属性：获取当前PDF对象 ----------------
const currentPdf = computed(() => {
  if (!currentPdfDiskName.value || files.value.length === 0) return null

  return files.value.find(f => f.disk_name === currentPdfDiskName.value) || null
})

const otherPdfs = computed(() => {
  if (!currentPdfDiskName.value) return files.value

  return files.value.filter(f => f.disk_name !== currentPdfDiskName.value)
})



// ---------------- 修改现有的操作函数 ----------------
// 1. 修改 loadFiles 函数，设置默认当前PDF
// 修改 loadFiles 函数中访问 currentPdf 的部分
async function loadFiles() {
  try {
    files.value = await getFiles()
    console.log('📁 加载的文件列表:', files.value)

    // 设置默认当前PDF：第一个文件或最后操作的文件
    if (files.value.length > 0) {
      let defaultPdf = null

      // 如果有最后操作时间记录，找到最近操作的文件
      if (Object.keys(lastOperationTime.value).length > 0) {
        // 按时间排序，找到最近操作的文件
        const sorted = Object.entries(lastOperationTime.value)
          .sort((a, b) => b[1] - a[1]) // 降序，最新的在前

        const latestPdfDiskName = sorted[0][0]
        defaultPdf = files.value.find(f => f.disk_name === latestPdfDiskName)

        console.log('🔍 查找最近操作的PDF:', {
          latestPdfDiskName,
          found: !!defaultPdf,
          sortedEntries: sorted.slice(0, 3) // 显示前3个最近的
        })
      }

      // 如果没找到，使用第一个文件
      if (!defaultPdf) {
        defaultPdf = files.value[0]
        console.log('📌 使用第一个文件作为默认PDF:', defaultPdf.filename)
      }

      if (defaultPdf) {
        updateCurrentPdf(defaultPdf.disk_name)
        console.log('✅ 已设置当前PDF:', {
          name: defaultPdf.filename,
          diskName: defaultPdf.disk_name,
          timestamp: new Date(lastOperationTime.value[defaultPdf.disk_name] || Date.now()).toISOString()
        })
      }
    } else {
      // 没有文件，清空当前PDF
      currentPdfDiskName.value = ''
      console.log('📭 没有PDF文件，清空当前PDF')
    }

    // 原有的文件访问测试代码
    if (files.value.length > 0) {
      const firstFile = files.value[0]

      // 构建正确的 URL（使用当前页面的协议和主机名）
      const baseUrl = window.location.origin // 'http://localhost:8080'
      const testUrl = `${baseUrl}/api/file-info/${firstFile.disk_name}`

      console.log('🔗 测试URL:', testUrl)

      try {
        const testResponse = await fetch(testUrl)
        console.log('✅ 文件访问测试:', testResponse.ok)

        if (!testResponse.ok) {
          console.warn('⚠️ 文件访问测试失败，状态码:', testResponse.status)
        }
      } catch (error) {
        console.error('❌ 文件访问测试失败:', error)
      }
    }

    // 输出当前状态摘要 - 修复这里，使用 currentPdfDiskName 而不是 currentPdf
    console.log('📊 文件加载完成，状态摘要:', {
      totalFiles: files.value.length,
      currentPdfDiskName: currentPdfDiskName.value, // 修复这里：使用 currentPdfDiskName.value
      otherPdfsCount: files.value.filter(f => f.disk_name !== currentPdfDiskName.value).length,
      lastOperationTimeRecords: Object.keys(lastOperationTime.value).length
    })

  } catch (error) {
    console.error('加载文件失败:', error)
    ElMessage.error('加载文件失败: ' + (error.message || '未知错误'))

    // 错误时也清空相关状态
    files.value = []
    currentPdfDiskName.value = ''
    console.error('❌ 加载文件失败，已清空状态:', error)
  }
}



// 2. 修改 deleteFile 函数，更新当前PDF
async function deleteFile(file) {
  try {
    console.log('🔍 删除文件函数被调用，参数:', file)

    // ... 原有的文件名提取逻辑保持不变 ...
    let filenameToDelete
    if (typeof file === 'string') {
      filenameToDelete = file
    } else if (file && file.disk_name) {
      filenameToDelete = file.disk_name
    } else if (file && file.filename) {
      filenameToDelete = file.filename
    } else {
      console.error('❌ 无效的文件参数:', file)
      ElMessage.error('文件信息无效')
      return
    }

    console.log('🎯 实际要删除的文件名:', filenameToDelete)

    await ElMessageBox.confirm(
      '确定删除该文件吗？',
      '删除确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await delApi(filenameToDelete)
    ElMessage.success('已删除')

    // 如果删除的是当前PDF，需要更新当前PDF
    if (currentPdfDiskName.value === filenameToDelete) {
      const remainingFiles = files.value.filter(f => f.disk_name !== filenameToDelete)
      if (remainingFiles.length > 0) {
        // 设置下一个当前PDF（可以是第一个文件，或者找最近操作的其他文件）
        const nextPdf = remainingFiles[0]
        updateCurrentPdf(nextPdf.disk_name)
      } else {
        // 没有文件了，清空当前PDF
        currentPdfDiskName.value = ''
      }
    }

    await loadFiles()
  } catch (err) {
    if (err !== 'cancel') {
      console.error('❌ 删除失败:', err)
      ElMessage.error('删除失败：' + (err.response?.data?.error || err.message))
    }
  }
}

// 3. 添加PDF切换函数（供OtherPdfsList使用）
const switchToPdf = (pdf) => {
  console.log('🔄 切换到PDF:', pdf.filename, pdf.disk_name)
  updateCurrentPdf(pdf.disk_name)
}


// 4. 修改 convertAndPreview 函数，更新操作时间
async function convertAndPreview(pdfDiskName) {
  console.log('🔄 开始转图预览，文件名:', pdfDiskName)

  // 更新当前PDF和操作时间
  updateCurrentPdf(pdfDiskName)

  const cacheKey = pdfDiskName.replace('.pdf', '')
  convertingObj.value[pdfDiskName] = true
  progressVisible.value = true
  progressPercent.value = 0
  progressStatus.value = ''
  progressMsg.value = '正在检查缓存...'

  // 辅助函数：记录步骤完成时间
  const recordStepTime = (step) => {
    if (!stepCompletionTime.value[pdfDiskName]) {
      stepCompletionTime.value[pdfDiskName] = {}
    }
    stepCompletionTime.value[pdfDiskName][step] = Date.now()
    // 深拷贝以确保响应式更新
    stepCompletionTime.value = { ...stepCompletionTime.value }
    console.log(`✅ 记录${step}步骤完成时间:`, {
      pdfDiskName,
      step,
      time: new Date(stepCompletionTime.value[pdfDiskName][step]).toLocaleTimeString(),
      fullRecord: stepCompletionTime.value[pdfDiskName]
    })
  }

  // 如果是缓存命中，直接记录完成时间
  if (convertCache.value[cacheKey]) {
    console.log('📦 转图缓存命中，自动记录完成时间')
    recordStepTime('convert')

    previewFolder.value = pdfDiskName.replace(/\.pdf$/i, '')
    previewPngs.value = convertCache.value[cacheKey]
    progressVisible.value = false
    previewVisible.value = true
    convertingObj.value[pdfDiskName] = false
    delete convertingObj.value[pdfDiskName]

    // 更新状态：转图已完成
    updateStepStatus(pdfDiskName, 'convert', 'done')

    return
  }

  try {
    progressMsg.value = '正在提交任务...'

    // 使用相对路径，让代理处理
    console.log('🔗 调用转图API:', `/api/convert-pdf-async/${pdfDiskName}`)

    const { data } = await axios.post(`/api/convert-pdf-async/${pdfDiskName}`)

    // API缓存命中
    if (data.hitCache) {
      console.log('📦 API缓存命中')
      recordStepTime('convert')

      convertCache.value[cacheKey] = data.pngs
      previewFolder.value = pdfDiskName.replace(/\.pdf$/i, '')
      previewPngs.value = data.pngs
      progressVisible.value = false
      previewVisible.value = true
      convertingObj.value[pdfDiskName] = false
      delete convertingObj.value[pdfDiskName]

      // 更新状态：转图已完成
      updateStepStatus(pdfDiskName, 'convert', 'done')

      return
    }

    progressMsg.value = '任务已提交，正在转图...'
    await pollProgress(data.jobId)

    if (progressStatus.value === 'success') {
      // 转图成功，记录完成时间
      recordStepTime('convert')

      const list = await getPngList(pdfDiskName.replace(/\.pdf$/i, ''))
      convertCache.value[cacheKey] = list.pngs
      previewFolder.value = pdfDiskName.replace(/\.pdf$/i, '')
      previewPngs.value = list.pngs
      progressVisible.value = false
      previewVisible.value = true

      // 更新状态：转图已完成
      updateStepStatus(pdfDiskName, 'convert', 'done')

      // 显示成功消息
      ElMessage.success({
        message: `转图完成！已生成 ${list.pngs?.length || 0} 张图片`,
        duration: 3000
      })
    } else {
      ElMessage.error('转图失败：' + progressMsg.value)
      // 失败时清除转图状态
      updateStepStatus(pdfDiskName, 'convert', 'failed')
    }
  } catch (e) {
    console.error('❌ 转图请求失败:', e)
    ElMessage.error('转图请求失败：' + (e.response?.data?.error || e.message))
    // 失败时清除转图状态
    updateStepStatus(pdfDiskName, 'convert', 'failed')
  } finally {
    convertingObj.value[pdfDiskName] = false
    delete convertingObj.value[pdfDiskName]
  }
}

// 新增：更新步骤状态的辅助函数
function updateStepStatus(pdfDiskName, step, status) {
  console.log(`🔄 更新步骤状态: ${pdfDiskName} - ${step} -> ${status}`)

  // 这里可以根据需要存储步骤状态
  // 例如：可以维护一个步骤状态对象
  if (!stepStatuses.value[pdfDiskName]) {
    stepStatuses.value[pdfDiskName] = {}
  }
  stepStatuses.value[pdfDiskName][step] = status
  stepStatuses.value = { ...stepStatuses.value }


}




// 5. 修改 handleBatchCrop 函数，更新操作时间
async function handleBatchCrop(pdfDiskName) {
  console.log('开始批量裁切:', pdfDiskName)

  // 更新当前PDF和操作时间
  updateCurrentPdf(pdfDiskName)

  // ... 原有的批量裁切逻辑保持不变 ...
  const cacheKey = pdfDiskName.replace('.pdf', '')
  if (joinedResults.value[pdfDiskName] && joinedResults.value[pdfDiskName].length > 0) {
    console.log('使用现有结果，跳过处理')
    ElMessage.info('已使用缓存的裁切结果')
    return
  }

  try {
    progressVisible.value = true
    progressPercent.value = 0
    progressStatus.value = ''
    progressMsg.value = '正在检查缓存...'

    const result = await cutTablesForPDF(pdfDiskName, convertCache.value)
    console.log('批量裁切完成，结果:', result)

    if (result && result.success) {
      let imageUrls = []

      if (result.data && result.data.joined) {
        imageUrls = result.data.joined
      } else if (result.joined) {
        imageUrls = result.joined
      } else if (result.images) {
        imageUrls = result.images
      } else if (Array.isArray(result)) {
        imageUrls = result
      }

      const fullImageUrls = imageUrls.map(imgPath => {
        if (imgPath.startsWith('http')) {
          return imgPath
        } else if (imgPath.startsWith('joined_tables/')) {
          return getBackendUrl(`/${imgPath}`)
        } else if (imgPath.startsWith('static/')) {
          return getBackendUrl(`/${imgPath.replace('static/', '')}`)
        } else {
          return getStaticUrl(imgPath)
        }
      })

      joinedResults.value[pdfDiskName] = fullImageUrls
      console.log('📦 已写进缓存：', pdfDiskName, result.images.length, result.images[0])
      console.log('📦 已写进缓存：', pdfDiskName, result.images.length, result.images.slice(0, 3))

      ElMessage.success(`批量裁切完成，共生成 ${fullImageUrls.length} 个表格`)
    } else {
      ElMessage.error('批量裁切失败: ' + (result?.message || result?.error || '未知错误'))
    }
  } catch (error) {
    console.error('批量裁切出错:', error)
    ElMessage.error('批量裁切失败: ' + error.message)
  } finally {
    progressVisible.value = false
  }
}


// 6. 修改 handleScreenImagesCompleted 函数，更新操作时间
const handleScreenImagesCompleted = (data) => {
  console.log('🎯 TwoColumnPage handleScreenImagesCompleted 被调用:', data)

  // 添加数据检查
  if (!data) {
    console.error('handleScreenImagesCompleted: data 参数为空')
    return
  }

  const { pdfDiskName, hasScreened, screeningResult } = data

  // 更新当前PDF和操作时间
  updateCurrentPdf(pdfDiskName)

  // 记录筛选步骤完成时间
  recordStepCompletion(pdfDiskName, 'screen', {
    result: screeningResult,
    timestamp: Date.now()
  })

  // 更新筛选状态 - 使用深拷贝确保响应式更新
  const newHasScreenedImages = { ...hasScreenedImages.value }
  newHasScreenedImages[pdfDiskName] = hasScreened || true
  hasScreenedImages.value = newHasScreenedImages

  // 更新筛选结果
  if (screeningResult) {
    const newScreeningResultMap = { ...screeningResultMap.value }
    newScreeningResultMap[pdfDiskName] = screeningResult
    screeningResultMap.value = newScreeningResultMap
  }

  console.log('✅ 筛选状态已更新:', {
    pdfDiskName,
    hasScreened: hasScreenedImages.value[pdfDiskName],
    screeningResult,
    completionTime: stepCompletionTime.value[pdfDiskName]?.screen,
    currentHasScreenedImages: JSON.parse(JSON.stringify(hasScreenedImages.value))
  })

  // 显示成功消息
  if (screeningResult) {
    ElMessage.success({
      message: `图片筛选完成！发现 ${screeningResult.has_table_count || 0} 张有表格图片，${screeningResult.no_table_count || 0} 张无表格图片`,
      duration: 3000
    })
  } else {
    ElMessage.success('图片筛选完成！')
  }

  // 添加延迟检查，确认状态是否真的更新了
  setTimeout(() => {
    console.log('⏰ 延迟检查状态:', {
      pdfDiskName,
      hasScreened: hasScreenedImages.value[pdfDiskName],
      'hasScreenedImages[pdfDiskName] 类型': typeof hasScreenedImages.value[pdfDiskName],
      'hasScreenedImages[pdfDiskName] 值': hasScreenedImages.value[pdfDiskName],
      'hasScreenedImages 对象': JSON.parse(JSON.stringify(hasScreenedImages.value)),
      'stepCompletionTime': stepCompletionTime.value[pdfDiskName]
    })
  }, 100)
}

// 新增：记录步骤完成时间的通用函数
const recordStepCompletion = (pdfDiskName, step, data = {}) => {
  console.log(`📝 记录步骤完成时间: ${pdfDiskName} - ${step}`, data)

  // 确保时间记录对象存在
  if (!stepCompletionTime.value[pdfDiskName]) {
    stepCompletionTime.value[pdfDiskName] = {}
  }

  // 记录完成时间
  stepCompletionTime.value[pdfDiskName][step] = data.timestamp || Date.now()

  // 如果需要，记录额外数据
  if (data.result) {
    if (!stepCompletionTime.value[pdfDiskName].data) {
      stepCompletionTime.value[pdfDiskName].data = {}
    }
    stepCompletionTime.value[pdfDiskName].data[step] = data.result
  }

  // 强制响应式更新
  stepCompletionTime.value = { ...stepCompletionTime.value }

  console.log(`✅ ${step}步骤完成时间已记录:`, {
    pdfDiskName,
    step,
    time: new Date(stepCompletionTime.value[pdfDiskName][step]).toLocaleTimeString(),
    hasResult: !!data.result
  })

  // 同时更新步骤状态
  updateStepStatus(pdfDiskName, step, 'done')

  // 触发事件通知子组件
  emitStepCompletionEvent(pdfDiskName, step, 'done')
}


// 新增：触发步骤完成事件
const emitStepCompletionEvent = (pdfDiskName, step, status) => {
  // 这里可以触发自定义事件，通知其他组件
  console.log(`📢 触发步骤完成事件: ${pdfDiskName} - ${step} - ${status}`)

  // 示例：如果需要传递给布局组件
  // emit('step-completed', { pdfDiskName, step, status })
}


// 7. 添加表格解析完成的处理函数
const handleParseTablesCompleted = (data) => {
  console.log('🎯 TwoColumnPage handleParseTablesCompleted 被调用:', data)

  // 添加数据检查
  if (!data) {
    console.error('handleParseTablesCompleted: data 参数为空')
    return
  }

  const { pdfDiskName, parsingResult, progress } = data

  // 更新当前PDF
  updateCurrentPdf(pdfDiskName)

  // 记录解析步骤完成时间
  if (progress?.percentage === 100 || parsingResult?.success) {
    recordStepCompletion(pdfDiskName, 'parse', {
      result: parsingResult,
      progress: progress,
      timestamp: Date.now()
    })

    // 更新解析进度
    const newParsingProgressMap = { ...parsingProgressMap.value }
    newParsingProgressMap[pdfDiskName] = {
      percentage: 100,
      status: 'success',
      message: '表格解析完成'
    }
    parsingProgressMap.value = newParsingProgressMap

    // 显示成功消息
    ElMessage.success({
      message: '表格解析完成！',
      duration: 3000
    })
  }

  console.log('✅ 解析状态已更新:', {
    pdfDiskName,
    completionTime: stepCompletionTime.value[pdfDiskName]?.parse,
    progress: progress,
    result: parsingResult
  })
}

// 8. 修改现有的 handleParseTables 函数，调用完成回调
const handleParseTables = async (pdfDiskName) => {
  console.log('🔄 开始表格解析:', pdfDiskName)

  // 更新当前PDF
  updateCurrentPdf(pdfDiskName)

  // 设置解析中状态
  isParsing.value = true

  try {
    // 模拟解析过程 - 实际应该调用API
    console.log(`📊 开始解析 ${pdfDiskName} 的表格...`)

    // 这里应该是实际的API调用
    // const result = await parseTablesApi(pdfDiskName)

    // 模拟解析成功
    setTimeout(() => {
      handleParseTablesCompleted({
        pdfDiskName,
        parsingResult: { success: true, tables: 5 },
        progress: { percentage: 100, status: 'success' }
      })
      isParsing.value = false
    }, 2000)

  } catch (error) {
    console.error('❌ 表格解析失败:', error)

    // 记录失败状态
    updateStepStatus(pdfDiskName, 'parse', 'failed')

    ElMessage.error('表格解析失败: ' + error.message)
    isParsing.value = false
  }
}




// 在 setup 中添加处理函数
const handleUpdateScreeningStatus = (data) => {
  console.log('🎯 收到筛选状态更新:', data)
  const { pdfDiskName, hasScreened } = data

  // 更新状态
  hasScreenedImages.value[pdfDiskName] = hasScreened

  console.log('✅ 筛选状态已更新:', {
    pdfDiskName,
    hasScreened: hasScreenedImages.value[pdfDiskName],
    allStatus: hasScreenedImages.value
  })
}




async function cutTable(filename) {
  const { zones } = await useCrop(filename, cropLoading, cutResults)
  if (zones) ElMessage.success(`已裁切 ${zones} 个表格`)
}



function openLLMConfig() {
  llmConfigRef.value?.open()
}

function onLLMConfigured(success = true) {
  console.log('🎯 TwoColumnPage: LLM配置完成', success)
  if (success) {
    ElMessage.success('LLM配置已更新，现在可以识别表格了！')
  }
}

async function handleImageSelected(imageInfo) {
  try {
    console.log('图片选中:', imageInfo)
    const excelData = await fetchExcelDataForImage(imageInfo)
    currentExcelData.value = excelData
    ElMessage.success(`已加载表格数据: ${excelData.tableName}`)
  } catch (error) {
    console.error('加载Excel数据失败:', error)
    ElMessage.error('加载表格数据失败')
  }
}

async function fetchExcelDataForImage(imageInfo) {
  const response = await fetch(`/api/excel-data?imagePath=${encodeURIComponent(imageInfo.imagePath)}`)
  if (!response.ok) {
    throw new Error('获取Excel数据失败')
  }

  const data = await response.json()
  return {
    tableName: imageInfo.tableName || '未命名表格',
    imagePath: imageInfo.imagePath,
    excelPath: data.excelPath,
    data: data.tableData,
    headers: data.headers,
    lastUpdated: data.lastUpdated
  }
}

async function handleRecognizeTable(tableData) {
  try {
    console.log('🔄 开始识别表格:', tableData)

    const result = await llmApi.recognizeTable({
      image_data: tableData.image,
      table_type: tableData.type || 'non_financial',
      use_local_cache: true
    })

    console.log('✅ 表格识别结果:', result)
    return result
  } catch (error) {
    console.error('❌ 表格识别失败:', error)
    return {
      success: false,
      error: '表格识别失败',
      message: error.message
    }
  }
}


async function handleExcelDataReceived(excelInfo) {
  try {
    console.log('🎯 TwoColumnPage 收到 excel-data-received 事件:', excelInfo)

    if (!excelInfo.excelUrl) {
      console.error('❌ 没有收到excelUrl')
      return
    }

    console.log('🔄 强制清除当前数据')
    currentExcelData.value = null
    excelViewerKey.value++

    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    let finalExcelUrl = excelInfo.excelUrl

    // ⭐⭐⭐ 修复：确保URL格式正确 ⭐⭐⭐
    if (finalExcelUrl.startsWith('/static/excel_output/')) {
      // 已经是正确的静态文件路径，不需要转换
      console.log('✅ 使用原始静态文件路径:', finalExcelUrl)
    } else if (finalExcelUrl.includes('excel_output')) {
      // 提取相对路径，转换为静态文件路径
      const fileName = finalExcelUrl.split('excel_output/').pop()
      finalExcelUrl = `/static/excel_output/${fileName}`
      console.log('🔄 转换为静态文件路径:', finalExcelUrl)
    } else {
      // 其他情况，直接使用
      console.log('🔍 使用原始路径:', finalExcelUrl)
    }

    // 清理URL参数（如果有）
    if (finalExcelUrl.includes('?')) {
      finalExcelUrl = finalExcelUrl.split('?')[0]
    }

    console.log('🔄 调用getExcelContent:', finalExcelUrl)

    // 使用llmApi获取Excel内容
    const response = await llmApi.getExcelContent(finalExcelUrl)
    console.log('🔍 getExcelContent 完整响应:', response)

    if (response.success === false) {
      console.error('❌ API调用失败:', response.error)
      // 尝试直接构建Excel数据对象
      await createExcelDataFromUrl(finalExcelUrl, excelInfo)
      return
    }

    let excelData = null
    if (response.data && response.data.sheets) {
      excelData = response.data
    } else if (response.sheets) {
      excelData = response
    } else {
      console.error('❌ 无法识别的数据格式，尝试直接构建数据')
      await createExcelDataFromUrl(finalExcelUrl, excelInfo)
      return
    }

    // 构建Excel数据对象
    const newExcelData = {
      tableName: excelInfo.tableName || '百度OCR识别结果',
      excelUrl: finalExcelUrl,
      tableType: excelInfo.tableType || 'baidu_ocr',
      lastUpdated: new Date().toISOString(),
      sheets: excelData.sheets || [],
      data: excelData.data || [],
      headers: excelData.headers || [],
      filePath: excelData.filePath || finalExcelUrl,
      totalSheets: excelData.totalSheets || (excelData.sheets ? excelData.sheets.length : 0),
      // 添加百度OCR特有的信息
      source: 'baidu_ocr',
      originalFilename: excelInfo.originalFilename,
      tablesCount: excelInfo.tablesCount
    }

    console.log('🎉 新Excel数据对象:', newExcelData)

    // 强制更新视图
    currentExcelData.value = null
    await nextTick()

    currentExcelData.value = newExcelData
    excelViewerKey.value++

    console.log('✅ Excel数据更新完成，当前数据:', currentExcelData.value)
    ElMessage.success(`表格数据加载成功，共 ${currentExcelData.value.sheets?.length || 0} 个工作表`)

  } catch (error) {
    console.error('💥 处理Excel数据失败:', error)
    ElMessage.error('加载Excel数据失败: ' + error.message)
  }
}



// 新增：直接从URL构建Excel数据的备用方法
async function createExcelDataFromUrl(excelUrl, excelInfo) {
  try {
    console.log('🔄 尝试直接构建Excel数据:', excelUrl)

    const newExcelData = {
      tableName: excelInfo.tableName || '百度OCR识别结果',
      excelUrl: excelUrl,
      tableType: excelInfo.tableType || 'baidu_ocr',
      lastUpdated: new Date().toISOString(),
      sheets: [
        {
          name: 'Sheet1',
          data: [], // 空数据，等待后续加载
          headers: []
        }
      ],
      data: [], // 空数据
      headers: [], // 空表头
      filePath: excelUrl,
      totalSheets: 1,
      source: 'baidu_ocr',
      originalFilename: excelInfo.originalFilename,
      tablesCount: excelInfo.tablesCount,
      // 添加下载链接
      downloadUrl: excelUrl,
      status: 'pending' // 标记为待加载状态
    }

    // 强制更新视图
    currentExcelData.value = null
    await nextTick()

    currentExcelData.value = newExcelData
    excelViewerKey.value++

    console.log('✅ 基础Excel数据已创建:', currentExcelData.value)
    ElMessage.success('Excel文件已生成，正在加载数据...')

    // 尝试异步加载Excel内容
    setTimeout(() => {
      loadExcelContentAsync(excelUrl)
    }, 100)

  } catch (error) {
    console.error('❌ 构建Excel数据失败:', error)
    throw error
  }
}

// 新增：异步加载Excel内容
async function loadExcelContentAsync(excelUrl) {
  try {
    console.log('🔄 异步加载Excel内容:', excelUrl)

    const response = await llmApi.getExcelContent(excelUrl)

    if (response.success && currentExcelData.value) {
      let excelData = null
      if (response.data && response.data.sheets) {
        excelData = response.data
      } else if (response.sheets) {
        excelData = response
      }

      if (excelData) {
        // 更新现有数据
        currentExcelData.value.sheets = excelData.sheets || []
        currentExcelData.value.data = excelData.data || []
        currentExcelData.value.headers = excelData.headers || []
        currentExcelData.value.totalSheets = excelData.totalSheets || (excelData.sheets ? excelData.sheets.length : 0)
        currentExcelData.value.status = 'loaded'

        console.log('✅ Excel内容加载完成:', currentExcelData.value)
        ElMessage.success('Excel数据加载完成')
      }
    }
  } catch (error) {
    console.error('❌ 异步加载Excel内容失败:', error)
    if (currentExcelData.value) {
      currentExcelData.value.status = 'error'
      currentExcelData.value.error = error.message
    }
  }
}



// 处理移动图片 - 增强版本
const handleMoveImage = async ({ imageName, fromType, toType, pdfDiskName }) => {
  try {
    const targetPdf = pdfDiskName || currentScreeningPdf.value
    if (!targetPdf) {
      throw new Error('未指定PDF')
    }

    const pdfFolder = targetPdf.replace('.pdf', '')

    console.log(`🔄 移动图片: ${imageName} from ${fromType} to ${toType}`)

    // 乐观更新：先更新UI
    const currentData = screeningData.value[targetPdf]
    if (currentData) {
      // 从原分类移除
      const fromArray = currentData[fromType] || []
      const toArray = currentData[toType] || []

      const imageIndex = fromArray.findIndex(img => img.name === imageName)
      if (imageIndex !== -1) {
        const [movedImage] = fromArray.splice(imageIndex, 1)

        // 更新图片类型
        movedImage.type = toType
        movedImage.moved_at = new Date().toISOString()


        // ⭐ 新增：更新图片的URL和路径
        const baseUrl = window.location.origin
        const pdfFolder = targetPdf.replace('.pdf', '')
        movedImage.url = `${baseUrl}/api/filtered-tables-image/${pdfFolder}/${toType}/${imageName}`
        movedImage.relative_path = `filtered_tables/${pdfFolder}/${toType}/${imageName}`

        // 添加到目标分类
        toArray.push(movedImage)

        // 强制响应式更新
        screeningData.value = { ...screeningData.value }

        // 更新统计
        if (screeningStats.value[targetPdf]) {
          screeningStats.value[targetPdf][`${fromType}_count`] = Math.max(0, (screeningStats.value[targetPdf][`${fromType}_count`] || 0) - 1)
          screeningStats.value[targetPdf][`${toType}_count`] = (screeningStats.value[targetPdf][`${toType}_count`] || 0) + 1
          screeningStats.value = { ...screeningStats.value }
        }
      }
    }

    // 调用API进行实际移动
    try {
      const response = await screeningApi.moveImage(pdfFolder, {
        imageName,
        fromType,
        toType,
        movePhysically: true
      })

      if (response.success) {
        console.log('✅ 图片移动成功:', response.message)


        // 无论是否重命名，都要更新本地数据
        const toArray = screeningData.value[targetPdf][toType] || []
        const movedImageIndex = toArray.findIndex(img => img.name === imageName)
        if (movedImageIndex !== -1) {
          // 更新图片对象的路径信息
          const actualName = response.data?.actual_name || imageName
          const toPath = response.data?.to_path || response.data?.file_info?.new_path
          const newUrl = response.data?.new_url || response.data?.file_info?.new_url

          toArray[movedImageIndex].name = actualName
          toArray[movedImageIndex].type = toType  // 更新分类类型
          if (toPath) toArray[movedImageIndex].path = toPath
          if (newUrl) toArray[movedImageIndex].url = newUrl

          // ⭐ 新增：如果API没有返回URL，则根据新分类和文件名构建URL
          if (!toArray[movedImageIndex].url) {
            const baseUrl = window.location.origin
            const pdfFolder = targetPdf.replace('.pdf', '')

            // 构建正确的分类图片URL
            toArray[movedImageIndex].url = `${baseUrl}/api/filtered-tables-image/${pdfFolder}/${toType}/${actualName}`

            // 同时更新relative_path
            toArray[movedImageIndex].relative_path = `filtered_tables/${pdfFolder}/${toType}/${actualName}`
          }

          // 如果当前选中的就是这张图片，更新选中状态
          if (selectedImageInManager?.value?.name === imageName) {
            selectedImageInManager.value = { ...toArray[movedImageIndex] }
          }

          screeningData.value = { ...screeningData.value }
        }





        // 显示简短的成功提示
        ElMessage.success({
          message: `已移动到${toType === 'tables' ? '有表格' : '无表格'}`,
          duration: 1500
        })

      } else {
        throw new Error(response.error || '移动失败')
      }

    } catch (apiError) {
      console.warn('⚠️ API移动失败（可能是后端未实现），但UI已更新', apiError)
      // 保持乐观更新，显示模拟成功消息
      ElMessage.success({
        message: `已移动到${toType === 'tables' ? '有表格' : '无表格'}（模拟）`,
        duration: 1500
      })
    }

  } catch (error) {
    console.error('💥 移动图片失败:', error)
    ElMessage.error(`移动图片失败: ${error.message}`)

    // 尝试恢复UI状态
    try {
      const targetPdf = pdfDiskName || currentScreeningPdf.value
      if (targetPdf && screeningData.value[targetPdf]) {
        // 重新获取数据
        const pdfFolder = targetPdf.replace('.pdf', '')
        const response = await screeningApi.getClassifiedImages(pdfFolder)
        if (response.success) {
          screeningData.value[targetPdf] = response.data
          screeningData.value = { ...screeningData.value }
        }
      }
    } catch (recoveryError) {
      console.error('恢复UI状态失败:', recoveryError)
    }
  }
}

// 处理刷新分类数据 - 增强版本
const handleRefreshClassification = async (pdfDiskName) => {
  try {
    console.log('🔄 刷新分类数据:', pdfDiskName)
    const pdfFolder = pdfDiskName.replace('.pdf', '')

    // 显示加载状态
    const loadingMessage = ElMessage.info('正在刷新数据...', { duration: 0 })

    // 重新获取分类数据
    const response = await screeningApi.getClassifiedImages(pdfFolder)

    if (response.success) {
      screeningData.value[pdfDiskName] = response.data

      // 更新统计
      if (response.stats) {
        screeningStats.value[pdfDiskName] = response.stats
      }

      // 关闭加载消息
      loadingMessage.close()

      ElMessage.success('数据已刷新')

      console.log('✅ 数据刷新完成:', {
        tables: response.data.tables?.length || 0,
        no_tables: response.data.no_tables?.length || 0,
        total: response.stats?.total || 0
      })

    } else {
      loadingMessage.close()
      throw new Error(response.error || '刷新失败')
    }

  } catch (error) {
    console.error('刷新分类数据失败:', error)
    ElMessage.error(`刷新失败: ${error.message}`)
  }
}

// 处理重新检测图片 - 增强版本
const handleRedetectImage = async ({ imageName, currentType, pdfDiskName }) => {
  try {
    console.log('🔄 重新检测图片:', { imageName, currentType, pdfDiskName })
    const pdfFolder = pdfDiskName.replace('.pdf', '')

    // 显示加载状态
    const loadingMessage = ElMessage.info('正在重新检测...', { duration: 0 })

    // 调用重新检测API
    const response = await screeningApi.redetectImage(pdfFolder, {
      imageName,
      currentType,
      use_llm: true
    })

    loadingMessage.close()

    if (response.success) {
      const newType = response.data.detected_type
      const confidence = response.data.confidence || 0.8

      ElMessage.success(`重新检测完成: ${newType === 'tables' ? '有表格' : '无表格'} (${(confidence * 100).toFixed(1)}%置信度)`)

      // 如果分类发生变化，自动移动图片
      if (newType !== currentType) {
        // 延迟一点时间，让用户看到重新检测结果
        setTimeout(() => {
          handleMoveImage({
            imageName,
            fromType: currentType,
            toType: newType,
            pdfDiskName
          })
        }, 500)
      } else {
        ElMessage.info('分类未变化，无需移动')
      }

    } else {
      throw new Error(response.error || '重新检测失败')
    }

  } catch (error) {
    console.error('重新检测失败:', error)
    ElMessage.error(`重新检测失败: ${error.message}`)
  }
}

// 处理完成分类管理
const handleFinishClassification = () => {
  console.log('✅ 完成分类管理')

  // 如果有数据变化，可以在这里保存或同步
  if (currentScreeningPdf.value && screeningData.value[currentScreeningPdf.value]) {
    const data = screeningData.value[currentScreeningPdf.value]
    const stats = screeningStats.value[currentScreeningPdf.value]

    console.log('最终分类结果:', {
      tables: data.tables?.length || 0,
      no_tables: data.no_tables?.length || 0,
      total: stats?.total || 0
    })
  }

  ElMessage.success('分类管理完成')
  closeImageClassification()
}



// 在模板中暴露这些函数给ImageScreeningManager
// 添加一个响应式变量来跟踪选中的图片（在分类管理器中）
const selectedImageInManager = ref(null)

//  --------------------------------



// 新增函数：关闭图片分类管理器
const closeImageClassification = () => {
  screeningVisible.value = false
  currentScreeningPdf.value = ''
  console.log('已关闭图片分类管理器')
}




function manuallyTriggerExcelUpdate() {
  console.log('🔄 手动触发Excel更新')
}

async function forceRefreshExcel() {
  if (currentExcelData.value) {
    try {
      ElMessage.info('正在强制刷新Excel数据...')

      const excelInfo = {
        excelUrl: currentExcelData.value.originalExcelPath || currentExcelData.value.excelUrl,
        tableName: currentExcelData.value.tableName,
        tableType: currentExcelData.value.tableType || 'unknown'
      }

      console.log('🔄 强制刷新Excel数据:', excelInfo)
      await handleExcelDataReceived(excelInfo)

    } catch (error) {
      console.error('强制刷新失败:', error)
      ElMessage.error('强制刷新失败: ' + error.message)
    }
  } else {
    ElMessage.warning('没有可刷新的Excel数据')
  }
}

function openVisualization() {
  if (!currentExcelData.value) {
    ElMessage.warning('请先加载表格数据')
    return
  }

  visualizationKey.value++
  visualizationVisible.value = true
  console.log('📊 打开可视化分析:', currentExcelData.value)
}

async function saveExcelData() {
  if (!currentExcelData.value) return

  try {
    const response = await fetch('/api/save-excel-data', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(currentExcelData.value)
    })

    if (response.ok) {
      ElMessage.success('Excel数据保存成功')
    } else {
      throw new Error('保存失败')
    }
  } catch (error) {
    console.error('保存Excel数据失败:', error)
    ElMessage.error('保存Excel数据失败')
  }
}

async function exportAllData() {
  if (!currentExcelData.value) return
  ElMessage.info('导出功能开发中...')
}

function updateExcelContent(newData) {
  if (currentExcelData.value) {
    currentExcelData.value.data = newData
  }
}

// ---------------- 辅助函数 ----------------
async function pollProgress(jobId) {
  return new Promise((resolve) => {
    const timer = setInterval(async () => {
      try {
        const { data } = await axios.get(getBackendUrl(`/api/progress/${jobId}`))

        progressPercent.value = data.percent
        if (data.percent === 100) {
          progressStatus.value = 'success'
          progressMsg.value = '转图完成，正在加载预览...'
          clearInterval(timer)
          resolve()
        } else if (data.percent < 0) {
          progressStatus.value = 'exception'
          progressMsg.value = data.error || '未知错误'
          clearInterval(timer)
          resolve()
        } else {
          progressMsg.value = `正在转换第 ${data.finished} / ${data.total} 页...`
        }
      } catch {
        progressStatus.value = 'exception'
        progressMsg.value = '获取进度失败'
        clearInterval(timer)
        resolve()
      }
    }, 500)
  })
}




</script>


<style scoped>
.two-column-page {
  height: 100vh;
  position: relative;
}

/* 图片分类管理器对话框样式 */
.screening-manager-dialog {
  .el-dialog__body {
    padding: 0;
    height: 80vh;
    overflow: hidden;
    display: flex;
  flex-direction: column;
  }
}

.loading-container {
  padding: 40px;
  height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>