<template>
  <div class="app-layout">
    <!-- 左侧：PDF预览和文件操作区域 -->
    <div class="left-panel">
      <file-upload @uploaded="loadFiles"/>
      <file-list
        :files="files"
        :crop-loading="cropLoading"
        :crop-results="cutResults"
        :converting="convertingObj"
        :convert-cache="convertCache"
        :batch-crop-loading="batchCropLoading"
        :joined-results="joinedResults"
        @delete="deleteFile"
        @crop="cutTable"
        @convert="convertAndPreview"
        @batch-crop="handleBatchCrop"
        @open-llm-config="openLLMConfig"
        @image-selected="handleImageSelected"
        @recognize-table="handleRecognizeTable"
        @excel-data-received="handleExcelDataReceived"
      />
    </div>

    <!-- 右侧：富文本编辑器 -->
    <div class="right-panel">
      <div class="editor-header">
        <div class="header-title">
          {{ currentExcelData ? `表格数据 - ${currentExcelData.tableName}` : '文本编辑器' }}
        </div>
        <div class="header-actions">
          <el-button
            type="primary"
            @click="openLLMConfig"
            icon="el-icon-cpu"
            size="small"
          >
            LLM配置
          </el-button>
          <el-button
            type="success"
            @click="saveExcelData"
            icon="el-icon-document"
            size="small"
            :disabled="!currentExcelData"
          >
            保存Excel
          </el-button>
          <el-button
            type="success"
            @click="saveText"
            icon="el-icon-check"
            size="small"
          >
            保存文本
          </el-button>
        </div>
      </div>

      <!-- Excel数据展示区域 -->
      <div v-if="currentExcelData" class="excel-preview-section">
        <ExcelDataViewer
          :excel-data="currentExcelData"
          @update:content="updateExcelContent"
        />
      </div>

      <!-- 原有的富文本编辑器 -->
      <editor-panel
        v-model="content"
        @save="saveText"
        :class="{ 'half-height': currentExcelData }"
      />
    </div>

    <!-- 其他组件 -->
    <progress-dialog v-model="progressVisible" :percent="progressPercent" :status="progressStatus" :msg="progressMsg"/>
    <pdf-page-preview
      v-model:visible="previewVisible"
      :folder="previewFolder"
      :pngs="previewPngs"
    />
    <LLMConfig ref="llmConfigRef" @configured="onLLMConfigured" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

// 组件导入
import FileUpload from '@/components/FileUpload.vue'
import FileList from '@/components/FileList.vue'
import EditorPanel from '@/components/EditorPanel.vue'
import ProgressDialog from '@/components/ProgressDialog.vue'
import PdfPagePreview from '@/components/PdfPagePreview.vue'
import ExcelDataViewer from '@/components/ExcelDataViewer.vue'
import LLMConfig from '@/components/LLMConfig.vue'

// API导入
import { getFiles, deleteFile as delApi } from '@/api/file'
import { getText, saveText as saveApi } from '@/api/text'
import { getPngList } from '@/api/convert'

// Composables导入
import { useCrop } from '@/composables/useCrop'
import { useBatchTableCrop } from '@/composables/useBatchTableCrop'
import { useConvert } from '@/composables/useConvert'

// ---------------- 数据声明 ----------------
const files = ref([])
const content = ref('')
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

// ---------------- 初始化 composables ----------------
const { cutTablesForPDF, batchCropLoading } = useBatchTableCrop(joinedResults)

// ---------------- 生命周期 ----------------
onMounted(async () => {
  await loadFiles()
  content.value = await getText()
})

// ---------------- 业务函数 ----------------
async function loadFiles() {
  try {
    files.value = await getFiles()
  } catch {
    ElMessage.error('加载文件失败')
  }
}

async function deleteFile(filename) {
  try {
    await ElMessageBox.confirm(
      '确定删除该文件吗？',
      '删除确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await delApi(filename)
    ElMessage.success('已删除')
    await loadFiles()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('删除失败：' + (err.response?.data?.error || err.message))
    }
  }
}

async function saveText() {
  try {
    await saveApi(content.value);
    ElMessage.success('保存成功')
  } catch {
    ElMessage.error('保存失败')
  }
}

async function cutTable(filename) {
  const { zones } = await useCrop(filename, cropLoading, cutResults)
  if (zones) ElMessage.success(`已裁切 ${zones} 个表格`)
}

// ---------------- Excel相关功能 ----------------
const handleImageSelected = async (imageInfo) => {
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

const fetchExcelDataForImage = async (imageInfo) => {
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

const saveExcelData = async () => {
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

const updateExcelContent = (newData) => {
  if (currentExcelData.value) {
    currentExcelData.value.data = newData
  }
}

const openLLMConfig = () => {
  llmConfigRef.value?.open()
}

const onLLMConfigured = () => {
  ElMessage.success('LLM配置已更新，现在可以识别表格了！')
}

// ---------------- 其他函数 ----------------
async function convertAndPreview(pdfDiskName) {
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
    const { data } = await axios.post(`http://127.0.0.1:5000/api/convert-pdf-async/${pdfDiskName}`)
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
    ElMessage.error('请求失败：' + (e.response?.data?.error || e.message))
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
          return `http://127.0.0.1:5000/${imgPath}`
        } else if (imgPath.startsWith('static/')) {
          return `http://127.0.0.1:5000/${imgPath.replace('static/', '')}`
        } else {
          return `http://127.0.0.1:5000/static/${imgPath}`
        }
      })

      joinedResults.value[pdfDiskName] = fullImageUrls
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

function clearBatchCropCache(pdfDiskName) {
  const cacheKey = pdfDiskName.replace('.pdf', '')

  if (joinedResults.value[pdfDiskName]) {
    delete joinedResults.value[pdfDiskName]
  }

  const storageKey = `batch_crop_${cacheKey}`
  localStorage.removeItem(storageKey)

  ElMessage.success('已清除裁切缓存')
}

async function pollProgress(jobId) {
  return new Promise((resolve) => {
    const timer = setInterval(async () => {
      try {
        const { data } = await axios.get(`http://127.0.0.1:5000/api/progress/${jobId}`)
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


// 在 App.vue 的 script 部分修改识别函数
import { llmApi } from '@/api/llm'  // 确保导入llmApi

// 构建Excel文件路径
const buildExcelPath = async (tableInfo) => {
  // 从图片URL提取哈希目录名（如 d0586abf1323dbfd80a926ce1e2d5676）
  const imageUrl = tableInfo.imageUrl
  console.log('原始图片URL:', imageUrl)

  const hashMatch = imageUrl.match(/static\/joined_tables\/([a-f0-9]+)/)
  const hashDir = hashMatch ? hashMatch[1] : 'default'

  console.log('提取的哈希目录:', hashDir)
  console.log('表格索引:', tableInfo.index)

  // 构建Excel路径：static/excel_data/{hash}/single_{index}.xlsx
  const excelPath = `static/excel_data/${hashDir}/single_${tableInfo.index + 1}.xlsx`
  console.log('构建的Excel路径:', excelPath)

  return excelPath
}



// 在 App.vue 中
const handleExcelDataReceived = async (excelInfo) => {
  try {
    console.log('🎯 App.vue 收到 excel-data-received 事件:', excelInfo)

    if (!excelInfo.excelUrl) {
      console.error('❌ 没有收到excelUrl')
      ElMessage.error('缺少Excel文件路径')
      return
    }

    console.log('📝 开始调用getExcelContent API，URL:', excelInfo.excelUrl)

    // 调用API读取Excel内容
    const response = await llmApi.getExcelContent(excelInfo.excelUrl)
    console.log('✅ getExcelContent响应:', response)

    if (response.success) {
      console.log('📊 Excel数据成功加载:', response.data)
      // 显示在富文本编辑器中
      displayTableInEditor(response.data, excelInfo.tableName)
      ElMessage.success('表格数据加载成功')
    } else {
      console.error('❌ getExcelContent失败:', response.error)
      ElMessage.error('加载表格数据失败: ' + response.error)
    }

  } catch (error) {
    console.error('💥 处理Excel数据失败:', error)
    ElMessage.error('加载Excel数据失败: ' + error.message)
  }
}


// 确保 displayTableInEditor 函数存在
const displayTableInEditor = (tableData, tableName) => {
  console.log('🖊️ 显示表格数据:', tableData)

  if (!tableData || !tableData.headers || !tableData.data) {
    console.error('❌ 表格数据格式错误')
    return
  }

  // 将表格数据转换为Markdown格式
  const markdownTable = convertToMarkdown(tableData, tableName)
  console.log('📄 生成的Markdown:', markdownTable)

  // 在现有内容后追加表格
  const separator = '\n\n---\n\n'
  content.value += separator + markdownTable

  // 滚动到编辑器底部
  setTimeout(() => {
    const editor = document.querySelector('.editor-panel')
    if (editor) {
      editor.scrollTop = editor.scrollHeight
    }
  }, 100)
}


// 表格数据转Markdown
const convertToMarkdown = (tableData, tableName) => {
  const { headers, data } = tableData

  let markdown = `## ${tableName}\n\n`

  // 表头
  markdown += '| ' + headers.join(' | ') + ' |\n'

  // 分隔线
  markdown += '|' + headers.map(() => '---').join('|') + '|\n'

  // 数据行
  data.forEach(row => {
    const rowData = headers.map(header => row[header] || '')
    markdown += '| ' + rowData.join(' | ') + ' |\n'
  })

  return markdown
}


// 处理Excel URL接收
const handleExcelUrlReceived = async (excelInfo) => {
  try {
    console.log('收到Excel信息:', excelInfo)

    // 调用API读取Excel内容
    const response = await llmApi.getExcelContent(excelInfo.excelUrl)

    if (response.success) {
      // 显示在富文本编辑器中
      displayTableInEditor(response.data, excelInfo.tableName)
      ElMessage.success('表格数据加载成功')
    } else {
      ElMessage.error('加载表格数据失败: ' + response.error)
    }

  } catch (error) {
    console.error('处理Excel数据失败:', error)
    ElMessage.error('加载Excel数据失败: ' + error.message)
  }
}

// 从Excel URL获取数据的函数
const fetchExcelData = async (excelUrl) => {
  try {
    // 调用后端API读取Excel内容
    const response = await llmApi.getExcelData(excelUrl)

    if (response.success) {
      return response.data
    } else {
      throw new Error(response.error || '读取Excel失败')
    }
  } catch (error) {
    console.error('获取Excel数据失败:', error)
    throw error
  }
}


// 在 App.vue 的 script 部分修改识别函数
const handleRecognizeTable = async (tableInfo) => {
  const loadingKey = `${tableInfo.pdfName}_${tableInfo.index}`

  // 添加加载状态管理（需要在data中定义）
  if (!recognizeLoading.value) {
    recognizeLoading.value = {}
  }
  recognizeLoading.value[loadingKey] = true

  try {
    console.log('开始识别流程，tableInfo:', tableInfo)

    // 1. 构建预期的Excel文件路径
    const excelPath = await buildExcelPath(tableInfo)
    console.log('构建的Excel路径:', excelPath)

    // 2. 检查Excel文件是否存在
    console.log('开始检查Excel数据...')
    const existingData = await checkExcelData(excelPath)
    console.log('检查结果:', existingData ? '存在' : '不存在')

    if (existingData) {
      // 3. 如果存在，直接显示在富文本编辑器中
      console.log('使用现有数据:', existingData)
      displayTableInEditor(existingData, tableInfo.tableName)
      ElMessage.success('已加载现有表格数据')
    } else {
      // 4. 如果不存在，调用大模型识别
      console.log('调用大模型识别...')
      const recognizedData = await recognizeWithLLM(tableInfo, excelPath)
      console.log('识别完成:', recognizedData)
      displayTableInEditor(recognizedData, tableInfo.tableName)
      ElMessage.success('表格识别完成')
    }
  } catch (error) {
    console.error('表格识别失败:', error)
    ElMessage.error('表格识别失败: ' + error.message)
  } finally {
    recognizeLoading.value[loadingKey] = false
  }
}

// 检查Excel数据是否存在
const checkExcelData = async (excelPath) => {
  try {
    console.log('调用检查Excel接口，路径:', excelPath)
    const response = await llmApi.checkExcel(excelPath)
    console.log('检查Excel响应:', response.data)

    if (response.data.success) {
      return response.data.exists ? response.data.excelData : null
    } else {
      console.error('检查Excel接口返回失败:', response.data.error)
      return null
    }
  } catch (error) {
    console.error('检查Excel数据失败:', error)
    // 如果检查失败，也返回null，让流程继续走识别
    return null
  }
}

// 调用大模型识别
const recognizeWithLLM = async (tableInfo, excelPath) => {
  try {
    const response = await llmApi.recognizeTable({
      imageUrl: tableInfo.imageUrl,
      excelPath: excelPath,
      tableName: tableInfo.tableName,
      index: tableInfo.index
    })

    if (response.data.success) {
      return response.data.recognizedData
    } else {
      throw new Error(response.data.error || '识别失败')
    }
  } catch (error) {
    console.error('大模型识别失败:', error)
    throw error
  }
}





</script>

<style scoped>
/* 样式保持不变 */
.app-layout {
  display: flex;
  height: 100vh;
  gap: 16px;
  padding: 16px;
  background: #f5f5f5;
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

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
  flex-shrink: 0;
}

.header-title {
  font-weight: 600;
  color: #303133;
  font-size: 16px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.excel-preview-section {
  border-bottom: 1px solid #e4e7ed;
  background: #f8f9fa;
  max-height: 40%;
  overflow: auto;
}

:deep(.half-height) {
  max-height: 60%;
  min-height: 200px;
}
</style>