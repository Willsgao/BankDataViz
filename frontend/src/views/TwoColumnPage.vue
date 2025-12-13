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
    @load-files="loadFiles"
    @delete-file="deleteFile"
    @cut-table="cutTable"
    @convert-and-preview="convertAndPreview"
    @handle-batch-crop="handleBatchCrop"
    @open-llm-config="openLLMConfig"
    @handle-image-selected="handleImageSelected"
    @handle-ocr-completed="handleOcrCompleted"
    @handle-recognize-table="handleRecognizeTable"
    @handle-excel-data-received="handleExcelDataReceived"
    @manually-trigger-excel-update="manuallyTriggerExcelUpdate"
    @force-refresh-excel="forceRefreshExcel"
    @open-visualization="openVisualization"
    @save-excel-data="saveExcelData"
    @export-all-data="exportAllData"
    @update-excel-content="updateExcelContent"
  />

  <!-- 其他全局组件 -->
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

</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

// 组件导入
import TwoColumnLayout from '@/layouts/TwoColumnLayout.vue'

import LLMConfig from '@/components/common/LLMConfig.vue'
import PdfPagePreview from '@/components/pdf/PdfPagePreview.vue'
import ExcelDataViewer from '@/components/table/ExcelViewer.vue'
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

// ---------------- 初始化 composables ----------------
const { cutTablesForPDF, batchCropLoading } = useBatchTableCrop(joinedResults)




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



// ---------------- 业务函数实现 ----------------
async function loadFiles() {
  try {
    files.value = await getFiles()
    console.log('📁 加载的文件列表:', files.value)

    if (files.value.length > 0) {
      const firstFile = files.value[0]

      // 构建正确的 URL（使用当前页面的协议和主机名）
      const baseUrl = window.location.origin // 'http://localhost:8080'
      const testUrl = `${baseUrl}/api/file-info/${firstFile.disk_name}`

      console.log('🔗 测试URL:', testUrl)

      try {
        const testResponse = await fetch(testUrl)
        console.log('✅ 文件访问测试:', testResponse.ok)
      } catch (error) {
        console.error('❌ 文件访问测试失败:', error)
      }
    }
  } catch (error) {
    console.error('加载文件失败:', error)
    ElMessage.error('加载文件失败')
  }
}


async function deleteFile(file) {
  try {
    console.log('🔍 删除文件函数被调用，参数:', file)

    // 检查参数类型并获取正确的文件名
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
    await loadFiles()
  } catch (err) {
    if (err !== 'cancel') {
      console.error('❌ 删除失败:', err)
      ElMessage.error('删除失败：' + (err.response?.data?.error || err.message))
    }
  }
}


async function cutTable(filename) {
  const { zones } = await useCrop(filename, cropLoading, cutResults)
  if (zones) ElMessage.success(`已裁切 ${zones} 个表格`)
}



async function convertAndPreview(pdfDiskName) {
  console.log('🔄 开始转图预览，文件名:', pdfDiskName)

  const cacheKey = pdfDiskName.replace('.pdf', '')
  convertingObj.value[pdfDiskName] = true
  progressVisible.value = true
  progressPercent.value = 0
  progressStatus.value = ''
  progressMsg.value = '正在检查缓存...'

  if (convertCache.value[cacheKey]) {
    previewFolder.value = pdfDiskName.replace(/\.pdf$/i, '')
    previewPngs.value = convertCache.value[cacheKey]
    progressVisible.value = false
    previewVisible.value = true
    convertingObj.value[pdfDiskName] = false
    delete convertingObj.value[pdfDiskName]
    return
  }

  try {
    progressMsg.value = '正在提交任务...'

    // 使用相对路径，让代理处理
    console.log('🔗 调用转图API:', `/api/convert-pdf-async/${pdfDiskName}`)

    const { data } = await axios.post(`/api/convert-pdf-async/${pdfDiskName}`)

    if (data.hitCache) {
      convertCache.value[cacheKey] = data.pngs
      previewFolder.value = pdfDiskName.replace(/\.pdf$/i, '')
      previewPngs.value = data.pngs
      progressVisible.value = false
      previewVisible.value = true
      convertingObj.value[pdfDiskName] = false
      delete convertingObj.value[pdfDiskName]
      return
    }

    progressMsg.value = '任务已提交，正在转图...'
    await pollProgress(data.jobId)

    if (progressStatus.value === 'success') {
      const list = await getPngList(pdfDiskName.replace(/\.pdf$/i, ''))
      convertCache.value[cacheKey] = list.pngs
      previewFolder.value = pdfDiskName.replace(/\.pdf$/i, '')
      previewPngs.value = list.pngs
      progressVisible.value = false
      previewVisible.value = true
    } else {
      ElMessage.error('转图失败：' + progressMsg.value)
    }
  } catch (e) {
    console.error('❌ 转图请求失败:', e)
    ElMessage.error('转图请求失败：' + (e.response?.data?.error || e.message))
  } finally {
    convertingObj.value[pdfDiskName] = false
    delete convertingObj.value[pdfDiskName]
  }
}



async function handleBatchCrop(pdfDiskName) {
  console.log('开始批量裁切:', pdfDiskName)

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
</style>