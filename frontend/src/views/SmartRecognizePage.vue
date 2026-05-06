<template>
  <div class="smart-recognize-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>智能识别</h2>
      <p class="page-desc">
        上传文件 → 自动检测表格区域 → 拖拽调整 → 确认后批量发给 DeepSeek → 保存 Excel
      </p>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧：文件预览 + 框选 -->
      <div class="left-panel">
        <FilePreview
          ref="filePreviewRef"
          @file-loaded="onFileLoaded"
          @boxes-confirmed="onBoxesConfirmed"
        />
      </div>

      <!-- 右侧：DeepSeek 操作面板 -->
      <div class="right-panel">
        <DeepseekPanel
          ref="deepseekPanelRef"
          :status="processStatus"
          :regions="pendingRegions"
          :results="results"
          :current-region-id="currentRegionId"
          :current-region-name="currentRegionName"
          :total-regions="pendingRegions.length"
          @start="onStartBatch"
          @cancel="onCancelBatch"
          @reset="onReset"
          @confirm="onConfirmResults"
        />
      </div>
    </div>

    <!-- 保存对话框 -->
    <el-dialog v-model="saveDialogVisible" title="保存 Excel" width="450px">
      <el-form label-width="80px">
        <el-form-item label="文件名">
          <el-input
            v-model="saveFilename"
            placeholder="默认自动生成时间戳文件名"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="saveDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingExcel" @click="doSaveExcel">
          确认保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import FilePreview from '@/components/smartRecognize/FilePreview.vue'
import DeepseekPanel from '@/components/smartRecognize/DeepseekPanel.vue'
import { batchRecognize, batchSaveExcel } from '@/api/smartRecognize'

// ---- Refs ----
const filePreviewRef = ref(null)
const deepseekPanelRef = ref(null)

// ---- 状态 ----
const processStatus = ref('idle') // 'idle' | 'running' | 'done'
const pendingRegions = ref([])     // [{ id, label, image_base64, thumbnail }]
const results = ref([])           // [{ id, label, success, result, error, thumbnail }]
const currentRegionId = ref('')
const currentRegionName = ref('')

// ---- 保存 ----
const saveDialogVisible = ref(false)
const saveFilename = ref('')
const savingExcel = ref(false)

// ---- 文件加载完成 ----
function onFileLoaded(payload) {
  console.log('文件加载完成:', payload)
  // 检测到表格时会自动显示在 AreaSelector 中
  // 用户可以在此基础上调整
}

// ---- 框选确认：从 AreaSelector 获取截图列表 ----
function onBoxesConfirmed(confirmedItems) {
  if (!confirmedItems || confirmedItems.length === 0) {
    ElMessage.warning('没有确认的选区')
    return
  }
  pendingRegions.value = confirmedItems
  results.value = []
  processStatus.value = 'idle'
  ElMessage.success(`已确认 ${confirmedItems.length} 个选区，点击「发送到 DeepSeek」开始识别`)
}

// ---- 开始批量识别 ----
async function onStartBatch({ prompt, user_data_dir }) {
  // 直接从当前页取已确认的截图（不依赖 pendingRegions）
  const confirmedItems = filePreviewRef.value?.getCurrentPageConfirmedItems()
  if (!confirmedItems || confirmedItems.length === 0) {
    ElMessage.warning('当前页没有已确认的选区截图')
    return
  }
  pendingRegions.value = confirmedItems

  processStatus.value = 'running'
  results.value = []

  // 依次处理每个区域
  for (const region of pendingRegions.value) {
    currentRegionId.value = region.id
    currentRegionName.value = region.label

    // 添加 pending 状态的占位
    if (!results.value.find(r => r.id === region.id)) {
      results.value.push({
        id: region.id,
        label: region.label,
        success: false,
        result: '',
        error: '',
        thumbnail: region.thumbnail || '',
      })
    }

    try {
      const res = await batchRecognize({
        regions: [{
          id: region.id,
          image_base64: region.image_base64,
          label: region.label,
        }],
        prompt,
        user_data_dir,
      })

      if (res.success && res.results?.[0]) {
        const r = res.results[0]
        const idx = results.value.findIndex(x => x.id === region.id)
        if (idx >= 0) {
          results.value[idx] = {
            ...results.value[idx],
            success: r.success,
            result: r.result || '',
            error: r.error || '',
          }
        }
      } else {
        const idx = results.value.findIndex(x => x.id === region.id)
        if (idx >= 0) {
          results.value[idx].error = res.error || '识别失败'
        }
      }
    } catch (err) {
      console.error(`区域 ${region.label} 识别失败:`, err)
      const idx = results.value.findIndex(x => x.id === region.id)
      if (idx >= 0) {
        results.value[idx].error = err.message || '网络请求失败'
      }
    }
  }

  currentRegionId.value = ''
  currentRegionName.value = ''
  processStatus.value = 'done'

  const successCount = results.value.filter(r => r.success).length
  ElMessage.success(`识别完成：${successCount}/${results.value.length} 个成功`)
}

// ---- 取消批量识别 ----
function onCancelBatch() {
  // 由于是同步循环，取消只能在下一次开始时生效
  ElMessage.info('已取消后续识别')
  processStatus.value = 'done'
}

// ---- 重置 ----
function onReset() {
  pendingRegions.value = []
  results.value = []
  processStatus.value = 'idle'
  currentRegionId.value = ''
  currentRegionName.value = ''
  filePreviewRef.value?.reset()
}

// ---- 确认结果 -> 保存 Excel ----
function onConfirmResults(successResults) {
  const now = new Date()
  saveFilename.value = `智能识别_${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}_${String(now.getHours()).padStart(2,'0')}${String(now.getMinutes()).padStart(2,'0')}`
  saveDialogVisible.value = true
  // 暂存以供保存时使用
  window._pendingSaveResults = successResults
}

async function doSaveExcel() {
  const successResults = window._pendingSaveResults || results.value.filter(r => r.success)
  if (successResults.length === 0) {
    ElMessage.warning('没有成功的结果可保存')
    return
  }

  savingExcel.value = true
  try {
    const res = await batchSaveExcel({
      results: successResults.map(r => ({
        id: r.id,
        label: r.label,
        result: r.result,
      })),
      filename: saveFilename.value,
    })

    if (res.success) {
      ElMessage.success('Excel 保存成功！正在下载...')
      saveDialogVisible.value = false
      // 触发文件下载
      const baseUrl = process.env.VUE_APP_API_BASE_URL || 'http://localhost:5000'
      const downloadUrl = res.url.startsWith('http')
        ? res.url
        : `${baseUrl}${res.url}`
      window.open(downloadUrl, '_blank')
    } else {
      ElMessage.error('保存失败: ' + (res.error || ''))
    }
  } catch (err) {
    ElMessage.error('保存失败: ' + (err.message || ''))
  } finally {
    savingExcel.value = false
  }
}
</script>

<style scoped>
.smart-recognize-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 60px);
  padding: 16px;
  gap: 12px;
  overflow: hidden;
}

.page-header {
  flex-shrink: 0;
}

.page-header h2 {
  margin: 0 0 4px 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.page-desc {
  margin: 0;
  font-size: 13px;
  color: #909399;
}

.main-content {
  display: flex;
  flex: 1;
  gap: 16px;
  min-height: 0;
}

.left-panel {
  flex: 0 0 60%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  background: white;
  padding: 12px;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  background: white;
  padding: 12px;
}
</style>
