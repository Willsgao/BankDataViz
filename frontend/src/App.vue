<!-- App.vue -->
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

    <!-- 右侧：Excel数据展示区域 -->
    <div class="right-panel">
      <div class="panel-header">
        <div class="header-title">
          <span v-if="currentExcelData">
            <i class="el-icon-document"></i>
            表格数据 - {{ currentExcelData.tableName }}
          </span>
          <span v-else>
            <i class="el-icon-document"></i>
            表格数据查看器
          </span>
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
            type="info"
            @click="exportAllData"
            icon="el-icon-download"
            size="small"
            :disabled="!currentExcelData"
          >
            导出数据
          </el-button>
        </div>
      </div>

      <!-- Excel数据展示区域 -->
      <div class="excel-content" v-if="currentExcelData">
        <ExcelDataViewer
          :excel-data="currentExcelData"
          @update:content="updateExcelContent"
          @close="currentExcelData = null"
        />
      </div>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <el-empty description="暂无表格数据">
          <div class="empty-tips">
            <p>请从左侧选择图片并点击"识别"按钮</p>
            <p>或对PDF文件进行批量裁切后识别表格</p>
          </div>
        </el-empty>
      </div>
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

import { getBackendUrl, getStaticUrl } from '@/utils/config'

// 组件导入
import FileUpload from '@/components/FileUpload.vue'
import FileList from '@/components/FileList.vue'
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

const exportAllData = async () => {
  if (!currentExcelData.value) return
  ElMessage.info('导出功能开发中...')
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
    const { data } = await axios.post(getBackendUrl(`/api/convert-pdf-async/${pdfDiskName}`))
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
          return getBackendUrl(`/${imgPath}`)
        } else if (imgPath.startsWith('static/')) {
          return getBackendUrl(`/${imgPath.replace('static/', '')}`)

        } else {
          return getStaticUrl(imgPath)
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

// ---------------- Excel数据处理 ----------------
import { llmApi } from '@/api/llm'

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
    console.log('🔍 getExcelContent 完整响应:', response)

    // 详细分析响应结构
    console.log('🔍 response 类型:', typeof response)
    console.log('🔍 response 键:', Object.keys(response || {}))
    console.log('🔍 response.success:', response?.success)
    console.log('🔍 response.data:', response?.data)
    console.log('🔍 response.data 类型:', typeof response?.data)
    console.log('🔍 response.data 键:', response?.data ? Object.keys(response.data) : 'null')

    // 根据调试信息调整逻辑
    let excelData = null

    if (response?.success && response.data) {
      console.log('✅ 使用新格式数据')
      excelData = response.data
    } else if (response?.data?.success && response.data.data) {
      console.log('✅ 使用旧格式数据')
      excelData = response.data.data
    } else if (response?.sheets) {
      console.log('✅ 直接使用response作为数据')
      excelData = response
    } else {
      console.error('❌ 无法识别的数据格式')
      ElMessage.error('数据格式错误')
      return
    }

    console.log('📊 最终Excel数据:', excelData)

    // 设置完整的Excel数据
    currentExcelData.value = {
      ...excelData,
      tableName: excelInfo.tableName || '未命名表格',
      excelUrl: excelInfo.excelUrl,
      lastUpdated: new Date().toISOString()
    }

    console.log('🎉 设置后的currentExcelData:', currentExcelData.value)
    ElMessage.success(`表格数据加载成功，共 ${currentExcelData.value.sheets?.length || 0} 个工作表`)

  } catch (error) {
    console.error('💥 处理Excel数据失败:', error)
    ElMessage.error('加载Excel数据失败: ' + error.message)
  }
}

</script>

<style scoped>
.app-layout {
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

.panel-header {
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
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.excel-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
}

.empty-tips {
  text-align: center;
  color: #909399;
  font-size: 14px;
  line-height: 1.6;
}

.empty-tips p {
  margin: 4px 0;
}
</style>