<template>
  <div class="app-container">
    <file-upload @uploaded="loadFiles"/>
    <file-list
      :files="files"
      :crop-loading="cropLoading"
      :crop-results="cutResults"
      :converting="convertingObj"
      :convert-cache="convertCache"
      :batch-crop-loading="batchCropLoading"
      @delete="deleteFile"
      @crop="cutTable"
      @convert="convertAndPreview"
      @batch-crop="handleBatchCrop"
    />
    <editor-panel v-model="content" @save="saveText"/>
    <progress-dialog v-model="progressVisible" :percent="progressPercent" :status="progressStatus" :msg="progressMsg"/>
    <pdf-page-preview
      v-model:visible="previewVisible"
      :folder="previewFolder"
      :pngs="previewPngs"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import FileUpload from '@/components/FileUpload.vue'
import FileList from '@/components/FileList.vue'
import EditorPanel from '@/components/EditorPanel.vue'
import ProgressDialog from '@/components/ProgressDialog.vue'
import PdfPagePreview from '@/components/PdfPagePreview.vue'
import { getFiles, deleteFile as delApi } from '@/api/file'
import { getText, saveText as saveApi } from '@/api/text'
import { getPngList } from '@/api/convert'
import { useCrop } from '@/composables/useCrop'
import { useBatchTableCrop } from '@/composables/useBatchTableCrop'
import { useConvert } from '@/composables/useConvert'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRotate } from '@/composables/useRotate'


// 先声明
/* ---------------- 数据 ---------------- */
const files           = ref([])
const content         = ref('')
const cropLoading     = ref({})
const cutResults      = ref({})
const convertCache    = ref({})
const convertingObj   = ref({})
const progressVisible = ref(false)
const progressPercent = ref(0)
const progressStatus  = ref('')
const progressMsg     = ref('')
const previewVisible  = ref(false)
const previewFolder   = ref('')
const previewPngs     = ref([])

/* ---------------- 初始化 composables ---------------- */
// 提前初始化批量裁切工具，获取 cutTablesForPDF 函数
const { cutTablesForPDF, batchCropLoading } = useBatchTableCrop(cutResults)


/* ---------------- 生命周期 ---------------- */
onMounted(async () => {
  await loadFiles()
  content.value = await getText()
})

/* ---------------- 业务入口 ---------------- */
async function loadFiles() {
  try { files.value = await getFiles() }
  catch { ElMessage.error('加载文件失败') }
}

// App.vue 中的 deleteFile 方法
async function deleteFile(filename) {
  try {
    // 使用 ElMessageBox.confirm 替代 ElMessage.confirm
    await ElMessageBox.confirm(
      '确定删除该文件吗？',
      '删除确认',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    // 用户点击确认后执行删除
    await delApi(filename)
    ElMessage.success('已删除')
    await loadFiles()
  } catch (err) {
    // 捕获用户取消操作（ElMessageBox 取消时会抛出错误）
    if (err !== 'cancel') {  // 仅在非用户取消的情况下提示错误
      ElMessage.error('删除失败：' + (err.response?.data?.error || err.message))
    }
  }
}


async function saveText() {
  try { await saveApi(content.value); ElMessage.success('保存成功') }
  catch { ElMessage.error('保存失败') }
}

async function cutTable(filename) {
  const { zones } = await useCrop(filename, cropLoading, cutResults)
  if (zones) ElMessage.success(`已裁切 ${zones} 个表格`)
}

/* 关键：直接把 convertAndPreview 放在父级，内部直接改值 */
async function convertAndPreview(pdfDiskName) {
  const cacheKey = pdfDiskName.replace('.pdf', ''); // 去掉 .pdf 后缀
  // convertCache.value[cacheKey] = list.pngs; // 键为 "test"

  convertingObj.value[pdfDiskName] = true
  progressVisible.value = true
  progressPercent.value = 0
  progressStatus.value = ''
  progressMsg.value = '正在检查缓存...'

  /* 1. 本地缓存命中 */
  if (convertCache.value[cacheKey]) {
    previewFolder.value = pdfDiskName.replace(/\.pdf$/i, '')
    previewPngs.value   = convertCache.value[cacheKey]
    progressVisible.value = false
    previewVisible.value  = true
    convertingObj.value[pdfDiskName] = false
    delete convertingObj.value[pdfDiskName]
    return
  }

  /* 2. 后端返回已缓存 / 3. 真正转图 */
  try {
    progressMsg.value = '正在提交任务...'
    const { data } = await axios.post(`http://127.0.0.1:5000/api/convert-pdf-async/${pdfDiskName}`)
    if (data.hitCache) {
      convertCache.value[cacheKey] = data.pngs
      previewFolder.value = pdfDiskName.replace(/\.pdf$/i, '')
      previewPngs.value   = data.pngs
      progressVisible.value = false
      previewVisible.value  = true
      convertingObj.value[pdfDiskName] = false
      delete convertingObj.value[pdfDiskName]
      return
    }
    /* 3. 轮询进度 */
    progressMsg.value = '任务已提交，正在转图...'
    await pollProgress(data.jobId)
    if (progressStatus.value === 'success') {
      const list = await getPngList(pdfDiskName.replace(/\.pdf$/i, ''))
      convertCache.value[cacheKey] = list.pngs
      previewFolder.value = pdfDiskName.replace(/\.pdf$/i, '')
      previewPngs.value   = list.pngs
      progressVisible.value = false
      previewVisible.value  = true
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


// 批量裁切时直接使用
async function handleBatchCrop(pdfDiskName) {
  const folderKey = pdfDiskName.replace(/\.pdf$/i, '')   // 和缓存保持一致
  await cutTablesForPDF(folderKey, convertCache.value)
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
</script>