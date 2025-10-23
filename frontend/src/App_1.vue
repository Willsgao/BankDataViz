<template>
  <div class="app-container">
    <file-upload @uploaded="loadFiles" />

    <file-list
      :files="files"
      :crop-loading="cropLoading"
      :crop-results="cutResults"
      :converting="convertingObj"
      :convert-cache="convertCache"
      @delete="deleteFile"
      @crop="cutTable"
      @convert="handleConvert"
      @batch-crop="handleBatchCrop"
    />

    <editor-panel v-model="content" @save="saveText" />

    <progress-dialog
      v-model="progressVisible"
      :percent="progressPercent"
      :status="progressStatus"
      :msg="progressMsg"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import FileUpload from '@/components/FileUpload.vue'
import FileList from '@/components/FileList.vue'
import EditorPanel from '@/components/EditorPanel.vue'
import ProgressDialog from '@/components/ProgressDialog.vue'
import { getFiles, deleteFile as delApi } from '@/api/file'
import { getText, saveText as saveApi } from '@/api/text'
import { useConvert } from '@/composables/useConvert'
import { useCrop } from '@/composables/useCrop'
import { useBatchTableCrop } from '@/composables/useBatchTableCrop'

/* ---------- 数据 ---------- */
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

/* ✅ 新增预览相关 */
const previewPngs        = ref([])
const previewFolder      = ref('')
const previewVisible     = ref(false)

/* ---------- 生命周期 ---------- */
onMounted(async () => {
  await loadFiles()
  content.value = await getText()
})

/* ---------- 业务函数 ---------- */
async function loadFiles() {
  try { files.value = await getFiles() }
  catch { ElMessage.error('加载文件失败') }
}

async function deleteFile(filename) {
  try {
    await ElMessage.confirm('确定删除？', '提示', { type: 'warning' })
    await delApi(filename)
    ElMessage.success('已删除')
    await loadFiles()
  } catch { /* 取消 */ }
}

async function saveText() {
  try { await saveApi(content.value); ElMessage.success('保存成功') }
  catch { ElMessage.error('保存失败') }
}

async function cutTable(filename) {
  const { zones } = await useCrop(filename, cropLoading, cutResults)
  if (zones) ElMessage.success(`已裁切 ${zones} 个表格`)
}

const converting = ref(false)   // ← 新增一个局部 loading 标志
const progress   = ref({ percent:0, status:'', msg:'' })

async function handleConvert(pdfDiskName) {
  const { convert } = useConvert(pdfDiskName, converting, progress)
  const { ok, pngs, folder } = await convert()
  if (ok) {
    // 把结果塞给全局弹窗/预览
    previewPngs.value   = pngs
    previewFolder.value = folder
    previewVisible.value = true
  }
}

async function handleBatchCrop(pdfDiskName) {
  const { cutTablesForPDF } = useBatchTableCrop(cutResults)
  await cutTablesForPDF(pdfDiskName, convertCache.value)
}
</script>

<style scoped>
.app-container {
  display: flex;
  height: 100vh;
  width: 100%;
}
.file-panel {
  flex: 1;
  padding: 20px;
  border-right: 1px solid #e6e6e6;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.editor-panel {
  flex: 1;
  padding: 20px;
  display: flex;
  flex-direction: column;
}
@media (max-width: 1200px) {
  .app-container {
    flex-direction: column;
  }
  .file-panel,
  .editor-panel {
    flex: none;
    height: 50vh;
  }
}
</style>