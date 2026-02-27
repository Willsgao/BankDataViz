<!-- frontend/src/views/TwoColumnPage.vue -->
<template>
  <TwoColumnLayout
      :files="files"
      :current-pdf-index="currentPdfIndex"
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
      :persistent-file-status="persistentFileStatus"
      @load-files="loadFiles"
      @delete-file="deleteFile"
      @cut-table="cutTable"
      @convert-and-preview="convertAndPreview"
      @handle-screen-images="handleScreenImages"
      @handle-open-classification="handleOpenClassification"
      @switch-pdf="switchToPdf"
      @clear-cache="handleClearCache"
      @parse-tables="handleParseTables"
      @table-type-change="handleTableTypeChange"
      @screen-images-completed="handleScreenImagesCompleted"
      @parse-tables-completed="handleParseTablesCompleted"
      @show-progress-dialog="showProgressDialog"
    />

  <!-- 确保全局组件在正确的位置 -->
    <ProgressDialog v-model="progressVisible" :percent="progressPercent" :status="progressStatus" :msg="progressMsg"/>
    <PdfPagePreview
      v-model:visible="previewVisible"
      :folder="previewFolder"
      :pngs="previewPngs"
    />
    <LLMConfig ref="llmConfigRef" @configured="onLLMConfigured" />


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

    <!-- 表格解析进度监控弹窗 -->
    <el-dialog
      v-model="progressDialogVisible"
      title="PDF解析进度监控"
      width="90%"
      top="2vh"
      destroy-on-close
      :close-on-click-modal="false"
      class="progress-monitor-dialog"
    >
      <ProgressMonitorDialog
        v-if="progressDialogVisible"
        :tasks="allParsingTasks"
        :summary="tasksSummary"
        :loading="false"
        @refresh="refreshTasks"
        @cancel="cancelTask"
        @view-result="handleViewResult"
        @retry="handleRetryTask"
        @view-detail="handleViewTaskDetail"
        @clear-completed="handleClearCompletedTasks"
        @close="closeProgressDialog"
      />
    </el-dialog>


</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed, watch, reactive } from 'vue'  // 添加了 watch 导入
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


// API导入
import { getFiles, deleteFile as delApi } from '@/api/file'
import { getPngList } from '@/api/convert'

// Composables导入
import { useCrop } from '@/composables/useCrop'
import { useBatchTableCrop } from '@/composables/useBatchTableCrop'
import { baiduOcrApi } from '@/api/baiduOcr'

// 工具函数导入
import { getBackendUrl, getStaticUrl, getSmartUrl  } from '@/utils/config'

// 在现有的 import 语句中添加
import ProgressMonitorDialog from '@/components/progress/ProgressMonitorDialog.vue'

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
const cutTable = ref(null)

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

const finalResultsMap = ref({})
const persistentFileStatus = ref({})

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
  'update-step-status',
  'smart-process-pdf',
  'show-progress-dialog'
])


// ---------------- 生命周期 ----------------
onMounted(async () => {
  await loadFiles()
  await loadPersistentFileStatus()

})

// 监听智能处理事件
const handleSmartProcessPdf = (pdfDiskName) => {
  console.log('🎯 TwoColumnPage 收到智能处理事件:', pdfDiskName)
  // 调用之前创建的智能处理函数
  smartProcessPdf(pdfDiskName)
}

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

    if (!ocrResult.success) {
      ElMessage.error(`OCR识别失败: ${ocrResult.error}`)
      return
    }



  } catch (error) {
    console.error('💥 处理OCR结果失败:', error)
    ElMessage.error('处理识别结果失败: ' + error.message)
  }
}




// 处理清除缓存
const handleClearCache = (pdfDiskName) => {
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
  tableType.value = newType
  ElMessage.info(`表格类型已切换为: ${newType === 'financial' ? '财务报表' : '非财务报表'}`)
}

// 处理图片筛选
const handleScreenImages = async (pdfDiskName) => {

  // 更新当前PDF
  updateCurrentPdf(pdfDiskName)

  // 设置筛选中状态
  isScreening.value = true

  // 显示进度对话框
  progressVisible.value = true
  progressPercent.value = 0
  progressStatus.value = ''
  progressMsg.value = '正在筛选图片...'

  try {
    // 1. 获取该PDF的所有PNG图片
    const cacheKey = pdfDiskName.replace(/\.pdf$/i, '')
    const pngList = convertCache.value[cacheKey]

    if (!pngList || pngList.length === 0) {
      ElMessage.warning('请先完成转图操作')
      return
    }

    // 2. 调用后端API进行图片筛选
    const response = await axios.post(getSmartUrl(`/api/screen-table-images/${cacheKey}`), {
      png_names: pngList,
      filter_only: false
    })

    if (response.data.success) {
      // 调用完成回调
      handleScreenImagesCompleted({
        pdfDiskName: pdfDiskName,
        hasScreened: true,
        screeningResult: {
          success: true,
          pdfDiskName: pdfDiskName,
          total_count: response.data.total_images || pngList.length,
          has_table_count: response.data.has_table_count || 0,
          no_table_count: response.data.no_table_count || 0
        }
      })

      ElMessage.success('图片筛选完成')
    } else {
      ElMessage.error('图片筛选失败: ' + response.data.error)
    }

  } catch (error) {
    console.error('❌ 图片筛选失败:', error)
    ElMessage.error('图片筛选失败: ' + error.message)
  } finally {
    // 关闭进度对话框
    progressVisible.value = false
    isScreening.value = false
  }
}



// 修改：加载分类数据的函数 - 移除 ElMessage.info
const loadClassificationData = async (pdfDiskName) => {
  try {
    console.log('🔄 加载分类数据:', pdfDiskName)
    const pdfFolder = pdfDiskName.replace('.pdf', '')

    // 调用真实的API获取分类数据
    const response = await screeningApi.getClassifiedImages(pdfFolder)

    if (response.success) {

    // 处理图片数据，使用原有的 getImageUrl 函数
    const processImages = (images, type) => {
      return (images || [])
        .map(img => {
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
        .sort((a, b) => {
          // 提取页码进行排序
          const getPageNumber = (filename) => {
            const match = (filename || '').match(/(\d+)\.(png|jpg|jpeg)$/i)
            return match ? parseInt(match[1]) : 0
          }
          return getPageNumber(a.name) - getPageNumber(b.name)
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
    await loadClassificationData(currentScreeningPdf.value)
  }
})



// ============ 新增：任务操作方法 ============
// 1. 查看任务结果
const handleViewResult = (jobId) => {

  // 查找任务对应的PDF
  const task = allParsingTasks.value.find(t => t.job_id === jobId)
  if (task) {
    const pdfDiskName = task.pdfDiskName || extractPdfFromJobId(jobId)
    if (pdfDiskName) {
      // 切换到该PDF
      switchToPdfByDiskName(pdfDiskName)

      // 关闭进度弹窗
      closeProgressDialog()

      ElMessage.success(`已切换到任务 ${pdfDiskName}`)
    } else {
      ElMessage.warning('未找到对应的PDF文件')
    }
  } else {
    ElMessage.error('任务不存在')
  }
}

// 2. 重试失败任务
const handleRetryTask = async (jobId) => {
  try {
    console.log('🔄 重试任务:', jobId)

    const task = allParsingTasks.value.find(t => t.job_id === jobId)
    if (!task) {
      ElMessage.error('任务不存在')
      return
    }

    const pdfDiskName = task.pdfDiskName || extractPdfFromJobId(jobId)
    if (!pdfDiskName) {
      ElMessage.error('无法获取PDF信息')
      return
    }

    // 重新提交解析
    handleParseTables(pdfDiskName)

    // 从列表中移除旧任务
    allParsingTasks.value = allParsingTasks.value.filter(t => t.job_id !== jobId)

    ElMessage.success('已重新提交解析任务')

  } catch (error) {
    console.error('❌ 重试任务失败:', error)
    ElMessage.error(`重试失败: ${error.message}`)
  }
}

// 3. 查看任务详情
const handleViewTaskDetail = (task) => {

  // 打开任务详情弹窗
  ElMessageBox.alert(
    `
    <div style="font-family: 'Monaco', 'Menlo', 'Consolas', monospace; font-size: 12px;">
      <p><strong>任务ID:</strong> ${task.job_id || 'N/A'}</p>
      <p><strong>PDF文件:</strong> ${getPdfFilename(task)}</p>
      <p><strong>状态:</strong> ${task.status || task.original_status || 'unknown'}</p>
      <p><strong>进度:</strong> ${task.progress || task.percentage || 0}%</p>
      <p><strong>已处理图片:</strong> ${task.processed || task.processed_images || 0}/${task.total || task.total_images || 0}</p>
      <p><strong>开始时间:</strong> ${new Date(task.timestamp || task.start_time).toLocaleString()}</p>
      <p><strong>最后消息:</strong> ${task.message || '无'}</p>
    </div>
    `,
    '任务详情',
    {
      dangerouslyUseHTMLString: true,
      customClass: 'task-detail-dialog',
      confirmButtonText: '关闭',
      showClose: false
    }
  )
}

// 4. 清除已完成任务
const handleClearCompletedTasks = () => {
  try {
    const completedTasks = allParsingTasks.value.filter(task =>
      task.status === 'completed' ||
      task.original_status === 'completed' ||
      task.status === 'success'
    )

    if (completedTasks.length === 0) {
      ElMessage.info('没有已完成的任务')
      return
    }

    ElMessageBox.confirm(
      `确定要清除 ${completedTasks.length} 个已完成的任务吗？`,
      '清除确认',
      {
        confirmButtonText: '确认清除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    ).then(() => {
      // 只保留未完成的任务
      allParsingTasks.value = allParsingTasks.value.filter(task =>
        task.status !== 'completed' &&
        task.original_status !== 'completed' &&
        task.status !== 'success'
      )

      // 更新统计
      updateTasksSummary(allParsingTasks.value)

      ElMessage.success(`已清除 ${completedTasks.length} 个已完成任务`)
    })

  } catch (error) {
    if (error !== 'cancel') {
      console.error('❌ 清除任务失败:', error)
    }
  }
}

// 5. 工具函数：从jobId提取PDF信息
const extractPdfFromJobId = (jobId) => {
  if (!jobId) return null

  // 查找对应的PDF
  for (const pdf of files.value) {
    if (pdf.disk_name && jobId.includes(pdf.disk_name.replace('.pdf', ''))) {
      return pdf.disk_name
    }
  }

  return null
}

// 6. 工具函数：获取PDF文件名
const getPdfFilename = (task) => {
  if (task.filename) return task.filename

  if (task.pdfDiskName) {
    // 在文件列表中查找
    const pdf = files.value.find(f => f.disk_name === task.pdfDiskName)
    if (pdf) return pdf.filename
    return task.pdfDiskName
  }

  return '未知文件'
}

// 7. 切换到指定PDF
const switchToPdfByDiskName = (pdfDiskName) => {
  const pdf = files.value.find(f => f.disk_name === pdfDiskName)
  if (pdf) {
    switchToPdf(pdf)
  } else {
    console.warn('⚠️ 未找到PDF:', pdfDiskName)
  }
}


const getImageUrl = (imageData, pdfFolder) => {
  try {
    console.log('🖼️ 生成图片URL - 输入:', { imageData, pdfFolder })

    // 优先使用后端返回的URL
    if (imageData.url && typeof imageData.url === 'string') {

      const baseUrl = window.location.origin
      let finalUrl = imageData.url

      // 确保URL是完整的
      if (imageData.url.startsWith('/')) {
        finalUrl = baseUrl + imageData.url
      } else if (!imageData.url.startsWith('http')) {
        finalUrl = baseUrl + '/api' + (imageData.url.startsWith('/') ? imageData.url : '/' + imageData.url)
      }

      return finalUrl
    }

    // 备用方案
    const baseUrl = window.location.origin
    const type = imageData.type || 'tables'
    const imageName = imageData.name || imageData.filename || ''

    const finalUrl = `${baseUrl}/filtered-tables-image/${pdfFolder}/${type}/${imageName}`
    console.log('🔧 构建的图片URL:', finalUrl)

    return finalUrl

  } catch (error) {
    console.error('❌❌ 生成图片URL时出错:', error)
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

}

// ---------------- 计算属性：获取当前PDF对象 ----------------

const otherPdfs = computed(() => {
  if (!currentPdfDiskName.value) return files.value

  return files.value.filter(f => f.disk_name !== currentPdfDiskName.value)
})






// 提取测试函数
async function testFileAccess(file) {
  try {
    const baseUrl = window.location.origin
    const testUrl = `${baseUrl}/api/file-info/${file.disk_name}`

    const testResponse = await fetch(testUrl)

    if (!testResponse.ok) {
      console.warn('⚠️ 文件访问测试失败，状态码:', testResponse.status)
    }
  } catch (error) {
    console.error('❌ 文件访问测试失败:', error)
  }
}


// 1. 修改 loadFiles 函数，设置默认当前PDF
async function loadFiles() {
  try {
    console.log('🔍🔍 第一步：检查 loadFiles() 执行')

    // 🔴 修复：不要清空 currentPdfDiskName，保留当前选择状态
    const previousCurrentPdf = currentPdfDiskName.value // 保存当前选择
    files.value = []
    // currentPdfDiskName.value = '' // ← 删除这行，不要清空

    // 调用 API
    const apiResult = await getFiles()

    // 🔴 修复：检查API响应是否成功
    if (!apiResult.success) {
      console.error('❌❌ API返回失败:', apiResult.error)
      ElMessage.error('获取文件列表失败: ' + (apiResult.error || '未知错误'))
      return
    }

    // 获取文件数组
    const fileList = apiResult.files || []

    files.value = fileList

    // 如果没有文件，清空状态
    if (files.value.length === 0) {
      console.log('📭📭 没有PDF文件，清空当前PDF')
      currentPdfDiskName.value = '' // 只有确实没有文件时才清空
      ElMessage.info('没有找到PDF文件')
      return
    }

    // 🔴 修复：优先使用之前选择的PDF（如果还存在）
    let defaultPdf = null
    if (previousCurrentPdf) {
      defaultPdf = files.value.find(f => f.disk_name === previousCurrentPdf)
    }

    // 如果之前的选择不存在，使用最近操作的文件
    if (!defaultPdf && Object.keys(lastOperationTime.value).length > 0) {
      const sorted = Object.entries(lastOperationTime.value)
        .sort((a, b) => b[1] - a[1])
      const latestPdfDiskName = sorted[0][0]
      defaultPdf = files.value.find(f => f.disk_name === latestPdfDiskName)
    }

    // 如果还没有找到，使用第一个文件
    if (!defaultPdf) {
      defaultPdf = files.value[0]
      console.log('📌📌 使用第一个文件作为默认PDF:', defaultPdf.filename)
    }

    // 更新当前PDF状态
    updateCurrentPdf(defaultPdf.disk_name)

  } catch (error) {
    console.error('💥💥 加载文件失败:', error)
    ElMessage.error('加载文件失败: ' + (error.message || '未知错误'))
    files.value = []
    currentPdfDiskName.value = ''
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
  console.log('🚀🚀🚀🚀 开始智能处理流程:', pdfDiskName)

  // 更新当前PDF
  updateCurrentPdf(pdfDiskName)

  const cacheKey = pdfDiskName.replace('.pdf', '')

  try {
    // 步骤1：调用智能处理接口（替代原有的转图和筛选步骤）
    const smartResult = await smartProcessPdf(pdfDiskName)

    // 步骤2：使用智能处理的结果，不再调用老的接口
    if (smartResult && smartResult.success) {

      // 直接从智能处理结果获取数据，不再调用 getPngList
      if (smartResult.pngs) {
        convertCache.value[cacheKey] = smartResult.pngs
      } else if (smartResult.conversion && smartResult.conversion.png_count > 0) {
        // 如果智能处理没有直接返回pngs，但显示已转图，可以安全地设置为空数组
        // 因为智能处理已经将图片复制到 no_tables 目录
        convertCache.value[cacheKey] = [] // 或者设置为模拟数据
      }

      // 更新筛选状态
      hasScreenedImages.value[pdfDiskName] = true

      // 记录完成时间
      recordStepCompletion(pdfDiskName, 'convert', { timestamp: Date.now() })
      recordStepCompletion(pdfDiskName, 'screen', { timestamp: Date.now() })

      console.log('🎯🎯 智能处理完成，更新UI状态')
      updateUIAfterAutoProcess(pdfDiskName)

    } else {
      throw new Error('智能处理失败')
    }

  } catch (error) {
    console.error('❌❌❌❌ 智能处理失败:', error)
    ElMessage.error('智能处理失败: ' + error.message)

    // 失败时也可以尝试调用智能处理的状态检查接口
    try {
      const statusResponse = await axios.get(`/api/pdf-process-status/${pdfDiskName}`)
      if (statusResponse.data.success) {
        const status = statusResponse.data
        if (status.conversion.converted) {
          // 即使智能处理失败，但如果转图已完成，可以手动设置状态
          convertCache.value[cacheKey] = [] // 设置为空，因为图片在文件系统中
          hasScreenedImages.value[pdfDiskName] = status.classification.classified
        }
      }
    } catch (statusError) {
      console.error('状态检查也失败:', statusError)
    }
  }
}


// 添加一个函数来检查后端图片是否真的存在
async function checkPdfImagesExist(pdfDiskName) {
  const cacheKey = pdfDiskName.replace('.pdf', '')

  try {
    // 直接调用后端API检查图片
    const pngList = await getPngList(cacheKey)

    if (pngList && pngList.pngs && pngList.pngs.length > 0) {
      console.log('✅ 后端图片存在:', pngList.pngs.length, '张')

      // 更新前端缓存
      convertCache.value[cacheKey] = pngList.pngs

      return {
        exists: true,
        count: pngList.pngs.length,
        pngs: pngList.pngs
      }
    } else {
      console.log('❌ 后端没有图片')
      return { exists: false }
    }
  } catch (error) {
    console.error('检查图片失败:', error)
    return { exists: false, error: error.message }
  }
}



// 执行转图操作
async function executeConvertPdf(pdfDiskName, cacheKey) {
  convertingObj.value[pdfDiskName] = true
  progressVisible.value = true
  progressPercent.value = 0
  progressStatus.value = ''
  progressMsg.value = '正在转图...'

  try {
    // 检查缓存
    progressMsg.value = '正在检查缓存...'

    // 调用转图API
    const { data } = await axios.post(getSmartUrl(`/api/convert-pdf-async/${pdfDiskName}`))

    if (data.hitCache) {
      // 缓存命中
      convertCache.value[cacheKey] = data.pngs
      progressVisible.value = false
      ElMessage.success(`转图完成！已有 ${data.pngs?.length || 0} 张图片`)
    } else {
      // 需要实际转图
      progressMsg.value = '任务已提交，正在转图...'
      await pollProgress(data.jobId)

      if (progressStatus.value === 'success') {
        const list = await getPngList(pdfDiskName.replace(/\.pdf$/i, ''))
        convertCache.value[cacheKey] = list.pngs
        ElMessage.success(`转图完成！已生成 ${list.pngs?.length || 0} 张图片`)
      } else {
        throw new Error('转图失败：' + progressMsg.value)
      }
    }

    // 记录转图完成
    recordStepCompletion(pdfDiskName, 'convert', { timestamp: Date.now() })
    updateStepStatus(pdfDiskName, 'convert', 'done')

  } catch (error) {
    console.error('❌ 转图失败:', error)
    ElMessage.error('转图失败: ' + error.message)
    throw error // 抛出错误，停止后续流程
  } finally {
    convertingObj.value[pdfDiskName] = false
    progressVisible.value = false
  }
}

// 执行图片筛选操作
async function executeScreenImages(pdfDiskName, cacheKey) {
  isScreening.value = true
  progressVisible.value = true
  progressPercent.value = 50
  progressStatus.value = ''
  progressMsg.value = '正在筛选图片...'

  try {
    // 获取该PDF的PNG图片
    const pngList = convertCache.value[cacheKey]

    if (!pngList || pngList.length === 0) {
      throw new Error('请先完成转图操作')
    }

    // 调用后端API进行图片筛选
    const response = await axios.post(getSmartUrl(`/api/screen-table-images/${cacheKey}`), {
      png_names: pngList,
      filter_only: false
    })

    if (response.data.success) {
      // 更新筛选状态
      const newHasScreenedImages = { ...hasScreenedImages.value }
      newHasScreenedImages[pdfDiskName] = true
      hasScreenedImages.value = newHasScreenedImages

      // 更新筛选结果
      const newScreeningResultMap = { ...screeningResultMap.value }
      newScreeningResultMap[pdfDiskName] = {
        success: true,
        pdfDiskName: pdfDiskName,
        total_count: response.data.total_images || pngList.length,
        has_table_count: response.data.has_table_count || 0,
        no_table_count: response.data.no_table_count || 0
      }
      screeningResultMap.value = newScreeningResultMap

      // 记录筛选完成
      recordStepCompletion(pdfDiskName, 'screen', {
        timestamp: Date.now(),
        result: newScreeningResultMap[pdfDiskName]
      })

      ElMessage.success('图片筛选完成！')
    } else {
      throw new Error('图片筛选失败: ' + response.data.error)
    }

  } catch (error) {
    console.error('❌ 图片筛选失败:', error)
    ElMessage.error('图片筛选失败: ' + error.message)
    throw error // 抛出错误，停止后续流程
  } finally {
    isScreening.value = false
    progressVisible.value = false
  }
}

// 更新UI状态
function updateUIAfterAutoProcess(pdfDiskName) {
  console.log('🔄 更新UI状态，确保按钮显示:', pdfDiskName)

  // 强制更新响应式数据，确保组件重新渲染
  const updatedHasScreenedImages = { ...hasScreenedImages.value }
  hasScreenedImages.value = updatedHasScreenedImages

  const updatedConvertCache = { ...convertCache.value }
  convertCache.value = updatedConvertCache

  // 触发组件重新计算
  nextTick(() => {
    console.log('✅ UI状态更新完成，应该显示分类管理和表格分析按钮了')
  })
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


async function smartProcessPdf(pdfDiskName) {
  console.log('🚀🚀🚀🚀🚀🚀🚀🚀 开始智能处理PDF:', pdfDiskName)

  // 更新当前PDF
  updateCurrentPdf(pdfDiskName)

  const cacheKey = pdfDiskName.replace('.pdf', '')
  convertingObj.value[pdfDiskName] = true
  progressVisible.value = true
  progressPercent.value = 0
  progressStatus.value = ''
  progressMsg.value = '开始智能处理PDF...'

  try {
    // 步骤1: 检查状态
    progressPercent.value = 10
    progressMsg.value = '检查PDF处理状态...'

    const statusResponse = await axios.get(`/api/pdf-process-status/${pdfDiskName}`)

    if (statusResponse.data.success && statusResponse.data.ready_for_parsing) {
      // 如果已经处理完成，直接返回成功结果
      progressMsg.value = 'PDF已预处理完成，可直接进行表格解析'
      progressPercent.value = 100

      setTimeout(() => {
        progressVisible.value = false
      }, 1000)

      // ✅ 返回处理结果，供父函数使用
      return {
        success: true,
        ready: true,
        conversion: statusResponse.data.conversion,
        classification: statusResponse.data.classification
      }
    }

    // 步骤2: 执行智能处理
    progressPercent.value = 30
    progressMsg.value = '执行智能预处理...'

    const processResponse = await axios.post(`/api/smart-process-pdf/${pdfDiskName}`)

    if (!processResponse.data.success) {
      throw new Error(processResponse.data.error || '智能处理失败')
    }

    // 完成
    progressPercent.value = 100
    progressStatus.value = 'success'
    progressMsg.value = '智能处理完成！'

    setTimeout(() => {
      progressVisible.value = false
    }, 1000)

    // ✅ 返回处理结果，供父函数使用
    return {
      success: true,
      ready: false,
      data: processResponse.data
    }

  } catch (error) {
    console.error('❌❌❌❌❌❌❌❌ 智能处理失败:', error)
    progressPercent.value = 100
    progressStatus.value = 'exception'
    progressMsg.value = '处理失败: ' + error.message

    setTimeout(() => {
      progressVisible.value = false
    }, 2000)

    // ✅ 返回错误结果
    return {
      success: false,
      error: error.message
    }
  } finally {
    convertingObj.value[pdfDiskName] = false
    delete convertingObj.value[pdfDiskName]
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

    // ✅ 必须调用保存！传递完整的后端数据
    saveFinalFileStatus(pdfDiskName, {
      ...parsingResult,  // 包含 processed_images, skipped_images, total_images
      ...progress,       // 包含 progress, message, status
      status: 'completed',
      message: '表格解析完成',
      progress: 100,
      lastUpdated: new Date().toISOString()
    })

    // 显示成功消息
    ElMessage.success({
      message: '表格解析完成！',
      duration: 3000
    })
  }

}


// ✅ 修复版本：保存完整的进度显示信息
const saveFinalFileStatus = (pdfDiskName, statusData) => {
  if (!pdfDiskName) return

  // 构建完整的进度显示数据
  const processed = statusData.processed_images || statusData.processed || 0
  const skipped = statusData.skipped_images || statusData.skipped || 0
  const totalImages = statusData.total_images || statusData.total || 0
  const actualTotal = totalImages > 0 ? totalImages : (processed + skipped)

  const fullStatusData = {
    ...statusData,
    diskName: pdfDiskName,
    // ✅ 添加进度显示字段
    progress_display: `${processed}+${skipped}/${actualTotal}`,
    // ✅ 确保有基本字段
    processed_images: processed,
    skipped_images: skipped,
    total_images: actualTotal,
    // ✅ 添加时间戳
    saved_at: new Date().toISOString()
  }

  console.log('💾 保存文件状态:', { pdfDiskName, fullStatusData })

  // 1. 保存到内存 - 强制响应式更新
  persistentFileStatus.value = {
    ...persistentFileStatus.value,
    [pdfDiskName]: fullStatusData
  }

  // 2. 保存到 localStorage
  if (typeof localStorage !== 'undefined') {
    try {
      localStorage.setItem(`file_status_${pdfDiskName}`, JSON.stringify(fullStatusData))
      console.log('✅ 文件状态已保存到 localStorage:', pdfDiskName)
    } catch (error) {
      console.warn('⚠️ 保存到 localStorage 失败:', error)
    }
  }

  // 3. 更新到 parsingProgressMap
  if (parsingProgressMap.value[pdfDiskName]) {
    parsingProgressMap.value[pdfDiskName] = {
      ...parsingProgressMap.value[pdfDiskName],
      ...fullStatusData
    }
  }

  // ✅ 同时记录到 stepCompletionTime
  if (!stepCompletionTime.value[pdfDiskName]) {
    stepCompletionTime.value[pdfDiskName] = {}
  }
  stepCompletionTime.value[pdfDiskName].parse = Date.now()
  stepCompletionTime.value = { ...stepCompletionTime.value }
}


// ✅ 修复版本：确保响应式更新
const loadPersistentFileStatus = async () => {
  try {
    if (typeof localStorage !== 'undefined') {
      const allKeys = Object.keys(localStorage)
      const statusKeys = allKeys.filter(key => key.startsWith('file_status_'))

      if (statusKeys.length === 0) {
        console.log('📭 localStorage中没有找到持久化状态')
        return
      }

      const loadedData = {}

      for (const key of statusKeys) {
        const statusData = localStorage.getItem(key)
        if (statusData) {
          try {
            const parsedData = JSON.parse(statusData)
            const pdfDiskName = key.replace('file_status_', '')
            loadedData[pdfDiskName] = parsedData
            console.log('📥 加载状态:', pdfDiskName, parsedData)
          } catch (e) {
            console.warn('❌ 解析状态数据失败:', e, key)
          }
        }
      }

      // ✅ 关键修复：使用扩展运算符触发响应式更新
      persistentFileStatus.value = {
        ...persistentFileStatus.value,
        ...loadedData
      }

    }
  } catch (error) {
    console.error('❌ 加载持久化状态失败:', error)
  }
}




// ✅ 新增：获取文件的持久化状态
const getPersistentFileStatus = (diskName) => {
  return persistentFileStatus.value[diskName] || null
}


// 添加一个辅助函数来生成进度显示文本
function formatProgressDisplay(progressData) {
  if (!progressData) return '';

  const processed = progressData.processed_images || 0;
  const skipped = progressData.skipped_images || 0;
  const total = progressData.total_images || 0;

  // 处理中状态
  if (progressData.status === 'processing') {
    if (progressData.progress === 85) {
      return '正在生成Excel文件...';
    }
    return `处理中 ${processed}+${skipped}/${total}`;
  }

  // 完成状态
  if (progressData.status === 'completed' || progressData.status === 'success') {
    if (total > 0 || (processed + skipped) > 0) {
      const actualTotal = total > 0 ? total : processed + skipped;
      return `${processed}+${skipped}/${actualTotal}`;
    }
  }

  // 失败状态
  if (progressData.status === 'failed' || progressData.status === 'exception') {
    return '处理失败';
  }

  // 默认返回原有消息
  return progressData.message || '';
}


function subscribeTableProgressSSE(jobId, pdfDiskName) {
  return new Promise((resolve, reject) => {
    console.log(`🔌 开始SSE订阅: jobId=${jobId}, pdf=${pdfDiskName}`)

    // 创建EventSource连接
    const eventSource = new EventSource(`/api/table-progress-sse/${jobId}`)

    // 监听消息
    // 监听消息
    eventSource.onmessage = (event) => {
      try {
        const progressData = JSON.parse(event.data)
        console.log('📥 收到SSE消息:', progressData)

        if (progressData.job_id === jobId) {
          // ✅ 计算正确的图片数量
          const processed = parseInt(progressData.processed_images) || 0
          const skipped = parseInt(progressData.skipped_images) || 0
          const total = parseInt(progressData.total_images) || (processed + skipped)
          const actualTotal = total > 0 ? total : processed + skipped

          // ✅ 计算正确的进度
          let progress = parseInt(progressData.progress) || 0

          // ✅ 关键修复：任务完成时进度强制为100%
          if (progressData.status === 'completed' || progressData.status === 'success') {
            progress = 100
          } else if (actualTotal > 0) {
            // 计算已处理总数
            const totalProcessed = processed + skipped
            progress = Math.round((totalProcessed / actualTotal) * 100)
          }

          // ✅ 状态映射
          const elementStatus = mapStatusToElementStatus(progressData.status)

          // ✅ 增强进度数据
          const enhancedData = {
            ...progressData,
            original_filename: progressData.original_filename || pdfDiskName,
            pdf_folder: progressData.pdf_folder || pdfDiskName?.replace('.pdf', ''),

            // ✅ 关键修复：使用计算后的进度
            progress: progress,
            percentage: progress,

            // ✅ 关键修复：包含所有图片数量字段
            processed_images: processed,
            skipped_images: skipped,
            total_images: actualTotal,

            // 计算显示格式
            processed: processed + skipped,  // 总处理数
            total: actualTotal,  // 总数
            progress_display: `${processed + skipped}/${actualTotal}`,

            // 状态字段
            element_status: elementStatus,
            original_status: progressData.status,
            status: progressData.status,
            display_status: elementStatus === 'success' ? 'completed' :
                          elementStatus === 'exception' ? 'failed' :
                          progressData.status
          }

          // ✅ 存储到 parsingProgressMap
          parsingProgressMap.value = {
            ...parsingProgressMap.value,
            [jobId]: enhancedData
          }

          if (pdfDiskName && pdfDiskName !== jobId) {
            parsingProgressMap.value[pdfDiskName] = {
              job_id: jobId,
              is_reference: true,
              referenced_to: jobId,
              original_filename: enhancedData.original_filename,
              pdf_folder: enhancedData.pdf_folder,
              pdfDiskName: pdfDiskName,
              status: enhancedData.status,
              progress: enhancedData.progress,  // ✅ 包含进度
              message: enhancedData.message,
              started_at: enhancedData.started_at,
              processed_images: enhancedData.processed_images,
              total_images: enhancedData.total_images,
              skipped_images: enhancedData.skipped_images
            }
          }

          console.log('📊 更新任务进度:', enhancedData)

          // 强制刷新
          refreshTasks()

          // 如果任务完成
          if (progressData.status === 'completed' || progressData.status === 'failed') {
            eventSource.close()

            // 保存最终结果
            if (pdfDiskName) {
              saveFinalFileStatus(pdfDiskName, enhancedData)
            }

            resolve(progressData)
          }
        }
      } catch (error) {
        console.error('❌ 解析SSE数据失败:', error, '原始数据:', event.data)
      }
    }




    // 错误处理
    eventSource.onerror = (error) => {
      console.error('❌ SSE连接错误:', error)
      eventSource.close()
      reject(new Error('进度连接失败'))
    }

    // 设置超时（5分钟）
    setTimeout(() => {
      if (eventSource.readyState !== EventSource.CLOSED) {
        console.warn('⏰ SSE连接超时，强制关闭')
        eventSource.close()
        reject(new Error('进度查询超时'))
      }
    }, 300000)
  })
}


// 辅助函数：保存最终结果
function saveFinalResult(pdfDiskName, enhancedData) {
  try {
    console.log('💾 开始保存最终结果:', { pdfDiskName, progressData: enhancedData })

    // 这里可以调用您的保存逻辑
    // 例如：localStorage、API调用等
    const resultData = {
      pdfDiskName: pdfDiskName,
      jobId: enhancedData.job_id,
      status: enhancedData.status,
      originalFilename: enhancedData.original_filename,
      pdfFolder: enhancedData.pdf_folder,
      startedAt: enhancedData.started_at,
      completedAt: new Date().toISOString(),
      totalImages: enhancedData.total_images,
      processedImages: enhancedData.processed_images,
      skippedImages: enhancedData.skipped_images,
      message: enhancedData.message
    }

    localStorage.setItem(`final_result_${pdfDiskName}`, JSON.stringify(resultData))

  } catch (error) {
    console.error('❌ 保存最终结果失败:', error)
  }
}


// ✅ 状态映射函数
function mapStatusToElementStatus(originalStatus) {
  const statusMap = {
    'queued': 'warning',      // 排队中 -> 警告（黄色）
    'processing': 'warning',  // 处理中 -> 警告（黄色）
    'completed': 'success',   // 已完成 -> 成功（绿色）
    'success': 'success',     // 成功 -> 成功（绿色）
    'failed': 'exception',    // 失败 -> 异常（红色）
    'exception': 'exception', // 异常 -> 异常（红色）
    '': '',                   // 空状态
    'unknown': 'warning'      // 未知 -> 警告
  }
  return statusMap[originalStatus] || 'warning'
}



// 8. 在 handleParseTables 函数中，替换模拟代码为真实的API调用
const handleParseTables = async (pdfDiskName) => {
  console.log('🔄 开始表格解析:', pdfDiskName)

  updateCurrentPdf(pdfDiskName)
  isParsing.value = true

  try {
    // 检查筛选状态
    const hasScreened = hasScreenedImages.value[pdfDiskName]
    if (!hasScreened) {
      ElMessage.warning('请先完成图片筛选再进行表格解析')
      isParsing.value = false
      return
    }

    const pdfFolder = pdfDiskName.replace(/\.pdf$/i, '')


    // 简化请求：后端会自动获取png_names
    const response = await axios.post(getSmartUrl(`/api/process-tables/${pdfFolder}`), {
      table_type: tableType.value,
      use_ocr: true,
      force_refresh: false
    }, {
      headers: {
        'Content-Type': 'application/json'
      }
    })

    console.log('✅ 收到响应:', response.data)

    if (response.data.success) {
      const jobId = response.data.job_id
      const totalImages = response.data.total_images || 0

      // 🔴 添加参数校验
      if (!jobId || jobId === 'undefined') {
        console.error('❌ 后端返回的jobId无效:', jobId)

        // 如果没有job_id，说明是即时完成的处理
        ElMessage.success('表格处理已完成（即时处理）')
        isParsing.value = false
        return
      }

      ElMessage.success(`表格解析任务已提交，发现 ${totalImages} 张表格图片`)

      // 轮询进度
      //await pollTableProgress(jobId, pdfDiskName)
    await subscribeTableProgressSSE(jobId, pdfDiskName).then((result) => {
      console.log('✅ SSE进度订阅完成:', result);
    }).catch((error) => {
      console.error('❌ SSE进度订阅失败:', error);
      isParsing.value = false;
    });

    } else {
      ElMessage.error('提交表格解析任务失败: ' + response.data.error)
      isParsing.value = false
    }

  } catch (error) {
    console.error('❌ 表格解析失败:', error)

    updateStepStatus(pdfDiskName, 'parse', 'failed')

    if (error.response?.data?.error) {
      ElMessage.error('表格解析失败: ' + error.response.data.error)
    } else {
      ElMessage.error('表格解析失败: ' + error.message)
    }

    isParsing.value = false
  }
}


// 监听文件处理事件
const handleFileProcessed = (event) => {
  console.log('🎯 文件处理事件:', event)

  const { type, fileId, fileName, response } = event

  if (type === 'duplicate') {

    // 可以在这里添加特殊处理，比如高亮显示已存在的文件
    highlightExistingFile(fileId)

  } else if (type === 'new') {

    // 可以选择性地立即设置为新文件的当前PDF
    if (response.file_id) {
      const newFile = files.value.find(f =>
        f.disk_name.includes(response.file_id) ||
        f.filename === fileName
      )

      if (newFile) {
        switchToPdf(newFile)
      }
    }
  }
}

// 高亮显示已存在的文件
const highlightExistingFile = (fileId) => {
  // 可以在这里添加视觉效果

  // 例如，找到对应的文件并添加临时高亮类
  setTimeout(() => {
    const existingFile = files.value.find(f =>
      f.disk_name.includes(fileId)
    )


  }, 500)
}



// 新增：轮询表格解析进度
async function pollTableProgress(jobId, pdfDiskName) {
  // 🔴 添加参数校验
  if (!jobId || jobId === 'undefined') {
    console.error('❌ 无效的jobId:', jobId)
    ElMessage.error('任务ID无效，无法查询进度')
    isParsing.value = false
    return Promise.resolve() // 直接返回已解决的Promise
  }

  return new Promise((resolve) => {
    const timer = setInterval(async () => {
      try {
        // const { data } = await axios.get(`/api/table-progress/${jobId}`)
        // 5. 表格进度查询
        const { data } = await axios.get(getSmartUrl(`/api/table-progress/${jobId}`))

        // 更新解析进度
        const newParsingProgressMap = { ...parsingProgressMap.value }
        newParsingProgressMap[pdfDiskName] = {
          percentage: data.percent || data.progress || 0,
          status: data.status || 'primary',
          message: data.message || `正在解析表格...`,
          jobId: jobId
        }
        parsingProgressMap.value = newParsingProgressMap

        if (data.percent === 100 || data.status === 'completed' || data.status === 'success') {
          // 解析完成
          clearInterval(timer)

          handleParseTablesCompleted({
            pdfDiskName,
            parsingResult: data.result || { success: true },
            progress: { percentage: 100, status: 'success' }
          })

          isParsing.value = false
          resolve()

        } else if (data.status === 'failed' || data.status === 'error') {
          // 解析失败
          clearInterval(timer)

          updateStepStatus(pdfDiskName, 'parse', 'failed')
          ElMessage.error('表格解析失败: ' + (data.error || data.message))

          isParsing.value = false
          resolve()
        }

      } catch (error) {
        console.error('❌ 获取表格解析进度失败:', error)
        clearInterval(timer)

        // 失败时清除解析状态
        updateStepStatus(pdfDiskName, 'parse', 'failed')
        ElMessage.error('获取解析进度失败')

        isParsing.value = false
        resolve()
      }
    }, 1000) // 每秒轮询一次
  })
}



// ----------------------------------------------

// 在现有的数据声明部分添加以下内容
// ============ 新增：进度监控相关状态 ============
const progressDialogVisible = ref(false)  // 控制弹窗显示
const allParsingTasks = ref([])           // 存储所有任务数据
const tasksSSE = ref(null)                // 用于存储SSE连接实例
const tasksSummary = ref({                // 任务统计摘要
  total: 0,
  processing: 0,
  completed: 0,
  failed: 0,
  queued: 0
})


// ============ 新增：方法 ============
// 1. 显示进度弹窗
const showProgressDialog = () => {
  console.log('📊 显示进度弹窗')
  progressDialogVisible.value = true

  // 弹窗打开时立即获取一次任务列表
  fetchAllParsingTasks()

  // 建立SSE连接用于实时更新
  connectToTasksSSE()
}



// 修改现有的 fetchAllParsingTasks 方法
const fetchAllParsingTasks = async () => {
  try {
    // ========== 第一步：诊断 parsingProgressMap 数据 ==========
    console.log('🔍=== 第一步：诊断 parsingProgressMap 数据 ===')

    // 1. 获取所有任务ID
    const allKeys = Object.keys(parsingProgressMap.value)

    // 2. 查找所有任务中最新的任务
    let latestJobId = null
    let latestTimestamp = 0

    allKeys.forEach(key => {
      const task = parsingProgressMap.value[key]
      if (task) {
        // ✅ 跳过引用条目
        if (task.is_reference === true) {
          return
        }

        // 尝试从多个字段获取时间
        const taskTime = task.timestamp || task.started_at || task.start_time
        if (taskTime) {
          const timeValue = new Date(taskTime).getTime()
          if (timeValue > latestTimestamp) {
            latestTimestamp = timeValue
            latestJobId = key
          }
        }
      }
    })

    if (latestJobId) {
      const latestTask = parsingProgressMap.value[latestJobId]
    } else {
      console.log('🔍 未找到最新任务')
    }

    // 3. 列出所有任务及其关键字段
    console.log('📋 当前所有任务列表:')
    allKeys.forEach((key, index) => {
      const task = parsingProgressMap.value[key]
    })
    console.log('🔍=== 诊断结束 ===\n')
    // ========== 诊断结束 ==========

    const tasks = []
    const processedJobIds = new Set()  // 用于去重

    // 从现有的 parsingProgressMap 中提取任务
    Object.entries(parsingProgressMap.value).forEach(([key, taskData]) => {
      if (!taskData) return

      console.log(`  🔍 处理key: "${key}"`)

      // ✅ 方案2核心：跳过引用条目
      if (taskData.is_reference === true) {
        console.log(`  ⏭️ 跳过引用条目: ${key} -> ${taskData.referenced_to || '未知'}`)

        // ✅ 关键修复：引用条目有文件名，但我们不处理它
        // 主数据会通过jobId被处理
        return
      }

      // 处理主数据
      processTaskData(key, taskData, tasks, processedJobIds)
    })

    // 按时间排序（最新的在前）
    tasks.sort((a, b) => {
      const timeA = a.timestamp || a.started_at || a.start_time || 0
      const timeB = b.timestamp || b.started_at || b.start_time || 0

      // 处理时间字符串
      const dateA = timeA ? new Date(timeA).getTime() : 0
      const dateB = timeB ? new Date(timeB).getTime() : 0

      return dateB - dateA
    })

    allParsingTasks.value = tasks

    // 更新统计摘要
    updateTasksSummary(tasks)

    // 打印任务统计
    const activeCount = tasks.filter(t => t.is_active).length
    const completedCount = tasks.filter(t => t.status === 'completed' || t.status === 'success').length
    const failedCount = tasks.filter(t => t.status === 'failed' || t.status === 'exception').length

  } catch (error) {
    console.error('❌ 获取任务列表失败:', error)
    // 不显示错误消息，避免干扰用户
  }
}


// 新增辅助函数：处理单个任务数据
function processTaskData(key, taskData, tasks, processedJobIds) {
  // ✅ 内联定义安全日期转换函数 - 修复：返回当前时间而不是1970年
  const safeToISOString = (dateValue) => {
    // ✅ 修复：如果是无效值，返回当前时间
    if (!dateValue ||
        dateValue === "None" ||
        dateValue === "null" ||
        dateValue === "undefined" ||
        dateValue === "") {
      return new Date().toISOString();  // ✅ 返回当前时间
    }

    try {
      // 尝试解析日期
      let date;

      // 如果是数字时间戳（字符串形式）
      if (typeof dateValue === 'string' && /^\d+$/.test(dateValue)) {
        const timestamp = parseInt(dateValue);
        // 判断是秒还是毫秒（通常后端返回的是秒）
        date = new Date(timestamp * 1000); // 假设是秒，转换为毫秒
      }
      // 如果是数字时间戳（数字形式）
      else if (typeof dateValue === 'number') {
        // 判断是秒还是毫秒
        if (dateValue < 10000000000) { // 小于 10000000000 秒，认为是秒
          date = new Date(dateValue * 1000);
        } else {
          date = new Date(dateValue);
        }
      }
      // 如果是ISO字符串
      else if (typeof dateValue === 'string') {
        // ✅ 新增：检查是否为1970年时间，如果是也返回当前时间
        if (dateValue.includes("1970-01-01")) {
          return new Date().toISOString();  // ✅ 返回当前时间
        }
        date = new Date(dateValue);
      }
      // 其他情况
      else {
        date = new Date(dateValue);
      }

      // 验证日期是否有效
      if (isNaN(date.getTime())) {
        return new Date().toISOString();  // ✅ 返回当前时间
      }

      // 检查是否是1970年
      if (date.getFullYear() === 1970) {
        return new Date().toISOString();  // ✅ 返回当前时间
      }

      return date.toISOString();
    } catch (e) {
      console.error("日期转换错误:", e, "原始值:", dateValue);
      return new Date().toISOString();  // ✅ 返回当前时间
    }
  };

  const task = { ...taskData }

  // 获取真实的job_id
  const realJobId = task.job_id || (key.includes('table_') ? key : null)

  if (!realJobId) {
    console.log(`  ⏭️ 跳过没有job_id的条目: ${key}`)
    return
  }

  // 去重检查
  if (processedJobIds.has(realJobId)) {
    return
  }

  // 标记为已处理
  processedJobIds.add(realJobId)

  // 确定任务标识符
  if (key.includes('table_') && key.startsWith('table_')) {
    // 这是以job_id为键的任务
    task.job_id = key
    task.task_key = 'job_id'
  } else {
    // 这是以PDF为键的任务
    task.pdfDiskName = key
    task.job_id = realJobId
    task.task_key = 'pdf_disk_name'
  }

  // 确保有必要的字段
  if (!task.status && task.original_status) {
    task.status = task.original_status
  }

  if (!task.original_filename) {
    console.log(`  ⚠️ 任务 ${task.job_id} 缺少original_filename字段`)

    // 优先级1：从pdfDiskName推断
    if (task.pdfDiskName) {
      task.original_filename = task.pdfDiskName
    }
    // 优先级2：从pdf_folder推断
    else if (task.pdf_folder) {
      task.original_filename = `${task.pdf_folder}.pdf`
    }
    // 优先级3：从key推断
    else if (key.endsWith('.pdf')) {
      task.original_filename = key
    }
    // 优先级4：从job_id推断
    else if (task.job_id && task.job_id.startsWith('table_')) {
      const jobIdParts = task.job_id.split('_')
      if (jobIdParts.length > 1) {
        task.original_filename = `table_${jobIdParts[1]}.pdf`
      } else {
        task.original_filename = task.job_id
      }
    }
    // 优先级5：默认值
    else {
      task.original_filename = task.job_id || '未知文件'
    }
  } else {
    console.log(`  ✅ 任务 ${task.job_id} 已有original_filename: ${task.original_filename}`)
  }

  // ✅ 修复：统一时间字段，使用安全的日期转换
  if (!task.started_at || task.started_at === "1970-01-01T00:00:00.000Z") {
    if (task.timestamp) {
      const startedAt = safeToISOString(task.timestamp);
      // 如果是有效时间，使用它
      if (startedAt && !startedAt.includes("1970-01-01")) {
        task.started_at = startedAt;
      } else {
        // 否则使用当前时间
        task.started_at = new Date().toISOString();
      }
    } else {
      // 直接使用当前时间
      task.started_at = new Date().toISOString();
    }
  } else {
    // 如果已经有时间但可能是1970年，检查并修复
    const existingTime = safeToISOString(task.started_at);
    if (existingTime.includes("1970-01-01")) {
      task.started_at = new Date().toISOString();
    }
  }

  // ✅ 修复：确保其他时间字段也是安全的
  ['completed_at', 'last_updated', 'task_start_time', 'created_at'].forEach(field => {
    if (task[field]) {
      const safeTime = safeToISOString(task[field]);
      // 如果返回的是1970年，使用当前时间
      if (safeTime && !safeTime.includes("1970-01-01")) {
        task[field] = safeTime;
      } else {
        // 对于 completed_at，只有已完成的任务才需要设置
        if (field === 'completed_at' && (task.status === 'completed' || task.status === 'success')) {
          task[field] = new Date().toISOString();
        } else if (field !== 'completed_at') {
          task[field] = new Date().toISOString();
        }
      }
    } else {
      // 如果字段不存在，根据情况设置
      if (field === 'created_at') {
        task[field] = new Date().toISOString(); // 创建时间总是需要的
      } else if (field === 'last_updated') {
        task[field] = new Date().toISOString(); // 最后更新时间总是需要的
      }
    }
  });

  // ✅ 确保所有任务都有创建时间
  if (!task.created_at) {
    task.created_at = new Date().toISOString();
  }

  // ✅ 修复：计算正确的图片处理数量
  const processed = parseInt(task.processed_images) || 0;
  const skipped = parseInt(task.skipped_images) || 0;
  const total = parseInt(task.total_images) || (processed + skipped);

  // 计算已处理总数
  const totalProcessed = processed + skipped;

  // ✅ 修复：任务完成时强制设置进度为100%
  if (task.status === 'completed' || task.status === 'success') {
    task.progress = 100;
    task.percentage = 100;
  } else if (total > 0) {
    // 计算实时进度
    const progress = Math.round((totalProcessed / total) * 100);
    task.progress = progress;
    task.percentage = progress;
  } else {
    task.progress = task.progress || 0;
    task.percentage = task.percentage || 0;
  }

  // ✅ 添加图片处理显示格式
  task.progress_display = `${totalProcessed}/${total}`;

  // ✅ 为任务添加文件信息
  if (task.pdf_folder || task.pdfDiskName) {
    const diskName = task.pdf_folder || task.pdfDiskName
    const pdfFile = files.value.find(f =>
      f.disk_name === diskName ||
      f.disk_name === `${diskName}.pdf` ||
      f.disk_name === diskName.replace('.pdf', '')
    )

    if (pdfFile) {
      task.file_info = {
        disk_name: pdfFile.disk_name,
        filename: pdfFile.filename,
        raw_filename: pdfFile.raw_filename || pdfFile.filename,
        created_at: pdfFile.created_at,
        file_size: pdfFile.file_size
      }

      if (!task.original_filename && pdfFile.raw_filename) {
        task.original_filename = pdfFile.raw_filename
      }
    }
  }

  // ✅ 计算显示名称
  task.display_name = task.original_filename || task.job_id || '未知任务'

  if (task.display_name.length > 30) {
    task.display_name_short = task.display_name.substring(0, 27) + '...'
  } else {
    task.display_name_short = task.display_name
  }

  // ✅ 计算进度状态
  if (task.status === 'queued' || task.status === 'processing') {
    task.is_active = true
    task.progress_status = 'processing'
  } else if (task.status === 'completed' || task.status === 'success') {
    task.is_active = false
    task.progress_status = 'success'
  } else if (task.status === 'failed' || task.status === 'exception') {
    task.is_active = false
    task.progress_status = 'exception'
  } else {
    task.is_active = false
    task.progress_status = ''
  }

  tasks.push(task)
}


// 3. 更新任务统计摘要
const updateTasksSummary = (tasks) => {
  const summary = {
    total: tasks.length,
    processing: 0,
    completed: 0,
    failed: 0,
    queued: 0
  }

  tasks.forEach(task => {
    const status = task.status || task.original_status || 'unknown'
    switch (status) {
      case 'processing':
        summary.processing++
        break
      case 'completed':
      case 'success':
        summary.completed++
        break
      case 'failed':
      case 'exception':
        summary.failed++
        break
      case 'queued':
        summary.queued++
        break
    }
  })

  tasksSummary.value = summary
}

// 4. 连接SSE获取实时更新
const connectToTasksSSE = () => {
  // 先关闭现有的连接
  if (tasksSSE.value) {
    tasksSSE.value.close()
  }

  try {
    // 建立新的SSE连接
    tasksSSE.value = new EventSource('/api/all-tasks-progress')

    tasksSSE.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        // 更新任务列表
        updateTaskInList(data)

      } catch (error) {
        console.error('❌ 解析任务更新数据失败:', error)
      }
    }

    tasksSSE.value.onerror = (error) => {
      console.error('❌ 任务进度SSE连接错误:', error)
      // 可以在这里实现重连逻辑
    }

    tasksSSE.value.onopen = () => {
    }

  } catch (error) {
    console.error('❌ 建立任务进度SSE连接失败:', error)
  }
}

// 5. 更新单个任务在列表中的状态
const updateTaskInList = (taskData) => {
  const jobId = taskData.job_id
  const pdfDiskName = taskData.pdfDiskName

  if (!jobId && !pdfDiskName) {
    console.warn('⚠️ 更新任务数据缺少标识符:', taskData)
    return
  }

  // 查找现有任务
  const taskIndex = allParsingTasks.value.findIndex(task =>
    task.job_id === jobId ||
    task.pdfDiskName === pdfDiskName ||
    task.job_id === pdfDiskName
  )

  if (taskIndex >= 0) {
    // 更新现有任务
    allParsingTasks.value[taskIndex] = {
      ...allParsingTasks.value[taskIndex],
      ...taskData
    }
  } else {
    // 添加新任务
    allParsingTasks.value.push(taskData)
  }

  // 触发响应式更新
  allParsingTasks.value = [...allParsingTasks.value]

  // 更新统计
  updateTasksSummary(allParsingTasks.value)
}

// 6. 手动刷新任务列表
const refreshTasks = () => {
  fetchAllParsingTasks()
}

// 7. 取消任务
const cancelTask = async (jobId) => {
  try {

    await ElMessageBox.confirm(
      '确定要取消此任务吗？',
      '取消确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // 调用后端API取消任务
    const response = await axios.post(`/api/cancel-task/${jobId}`)

    if (response.data.success) {
      ElMessage.success('任务已取消')

      // 从列表中移除已取消的任务
      allParsingTasks.value = allParsingTasks.value.filter(task => task.job_id !== jobId)

      // 更新统计
      updateTasksSummary(allParsingTasks.value)

    } else {
      throw new Error(response.data.error || '取消任务失败')
    }

  } catch (error) {
    if (error !== 'cancel') {
      console.error('❌ 取消任务失败:', error)
      ElMessage.error(`取消任务失败: ${error.message}`)
    }
  }
}

// 8. 关闭弹窗时清理
const closeProgressDialog = () => {
  progressDialogVisible.value = false

  // 关闭SSE连接
  if (tasksSSE.value) {
    tasksSSE.value.close()
    tasksSSE.value = null
  }
}

// ============ 新增：生命周期钩子 ============
// 页面卸载时清理SSE连接
onUnmounted(() => {
  if (tasksSSE.value) {
    tasksSSE.value.close()
    tasksSSE.value = null
  }
})

// 监听弹窗状态变化
watch(progressDialogVisible, (newVal) => {
  if (newVal) {
    // 弹窗打开时的处理
    console.log('📊 进度弹窗已打开')
  } else {
    // 弹窗关闭时的处理
    console.log('📊 进度弹窗已关闭')
  }
})


// 现有的 currentPdf 计算属性
const currentPdf = computed(() => {
  if (!currentPdfDiskName.value || files.value.length === 0) return null
  return files.value.find(f => f.disk_name === currentPdfDiskName.value) || null
})

// 新增：currentPdfIndex 计算属性
const currentPdfIndex = computed(() => {
  if (!currentPdfDiskName.value || files.value.length === 0) return 0
  const index = files.value.findIndex(f => f.disk_name === currentPdfDiskName.value)
  return index >= 0 ? index : 0
})


// 在 setup 中添加处理函数
const handleUpdateScreeningStatus = (data) => {
  console.log('🎯 收到筛选状态更新:', data)
  const { pdfDiskName, hasScreened } = data

  // 更新状态
  hasScreenedImages.value[pdfDiskName] = hasScreened
}




function openLLMConfig() {
  llmConfigRef.value?.open()
}

function onLLMConfigured(success = true) {
  if (success) {
    ElMessage.success('LLM配置已更新，现在可以识别表格了！')
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

  // 如果有数据变化，可以在这里保存或同步
  if (currentScreeningPdf.value && screeningData.value[currentScreeningPdf.value]) {
    const data = screeningData.value[currentScreeningPdf.value]
    const stats = screeningStats.value[currentScreeningPdf.value]

  }

  ElMessage.success('分类管理完成')
  closeImageClassification()
}



// 在模板中暴露这些函数给ImageScreeningManager
// 添加一个响应式变量来跟踪选中的图片（在分类管理器中）
const selectedImageInManager = ref(null)


// 新增函数：关闭图片分类管理器
const closeImageClassification = () => {
  screeningVisible.value = false
  currentScreeningPdf.value = ''
  console.log('已关闭图片分类管理器')
}




// ---------------- 辅助函数 ----------------
async function pollProgress(jobId) {
  return new Promise((resolve) => {
    const timer = setInterval(async () => {
      try {
        const { data } = await axios.get(getSmartUrl(`/api/progress/${jobId}`))

        progressPercent.value = data.percent
        if (data.percent === 100) {
          progressStatus.value = 'success'
          progressMsg.value = '转图完成！'  // 移除预览相关文字
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

/* 文件项高亮动画 */
@keyframes highlightPulse {
  0% { background-color: rgba(64, 158, 255, 0.1); }
  50% { background-color: rgba(64, 158, 255, 0.3); }
  100% { background-color: rgba(64, 158, 255, 0.1); }
}

.pdf-file-item.highlighted {
  animation: highlightPulse 2s ease-in-out 3;
  border-left: 3px solid #409eff;
}

/* 重复文件特殊标记 */
.pdf-file-item.duplicate-file::before {
  content: "🔄";
  margin-right: 8px;
  font-size: 12px;
}

/* 新文件特殊标记 */
.pdf-file-item.new-file::before {
  content: "🆕";
  margin-right: 8px;
  font-size: 12px;
}


/* 在现有的 <style> 部分添加 */
/* 进度监控弹窗样式 */
.progress-monitor-dialog .el-dialog {
  height: 85vh;
  display: flex;
  flex-direction: column;
}

.progress-monitor-dialog .el-dialog__body {
  flex: 1;
  padding: 16px 20px;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.progress-monitor-dialog .el-dialog__header {
  padding: 16px 20px 12px;
  border-bottom: 1px solid #ebeef5;
}

.progress-monitor-dialog .el-dialog__title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.progress-monitor-dialog .el-dialog__headerbtn {
  top: 18px;
  right: 20px;
}

/* 任务详情弹窗样式 */
.task-detail-dialog .el-message-box {
  width: 500px;
  max-width: 90vw;
}

.task-detail-dialog .el-message-box__header {
  padding-bottom: 12px;
  border-bottom: 1px solid #e4e7ed;
}

.task-detail-dialog .el-message-box__content {
  padding: 20px;
  font-size: 13px;
  line-height: 1.6;
}

.task-detail-dialog .el-message-box__content p {
  margin: 8px 0;
  display: flex;
  align-items: baseline;
}

.task-detail-dialog .el-message-box__content strong {
  display: inline-block;
  width: 100px;
  color: #606266;
  flex-shrink: 0;
}

.task-detail-dialog .el-message-box__btns {
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
}


</style>