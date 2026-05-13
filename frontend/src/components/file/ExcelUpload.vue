<template>
  <div class="excel-upload">
    <!-- 上传提示 -->
    <div
      v-if="!hasFile"
      class="upload-hint"
    >
      <el-icon class="hint-icon">
        <Document />
      </el-icon>
      <div class="hint-text">
        <div class="hint-title">
          将成品文件拖到此处，或<em>点击上传</em>
        </div>
        <div class="hint-tip">
          支持 Excel (.xlsx/.xls)、Word (.docx)、PDF 格式，文件大小不超过 50MB
        </div>
      </div>
    </div>

    <!-- 文件选择区域 -->
    <el-upload
      ref="uploadRef"
      class="excel-upload-drag"
      :class="{ 'has-file': hasFile }"
      :action="uploadUrl"
      :headers="headers"
      :data="{ description: description }"
      :before-upload="beforeUpload"
      :on-success="handleSuccess"
      :on-error="handleError"
      :on-remove="handleRemove"
      :on-change="handleChange"
      :file-list="fileList"
      :auto-upload="false"
      :multiple="false"
      accept=".xlsx,.xls,.docx,.doc,.pdf"
      drag
    >
      <template v-if="!hasFile">
        <el-icon class="el-icon--upload">
          <upload-filled />
        </el-icon>
        <div class="el-upload__text">
          拖拽文件或<em>点击上传</em>
        </div>
      </template>
      <template v-else>
        <el-icon class="file-icon">
          <Document />
        </el-icon>
        <div class="file-info">
          <span class="file-name">{{ currentFile?.name }}</span>
          <span class="file-size">{{ formatFileSize(currentFile?.size) }}</span>
        </div>
      </template>
    </el-upload>

    <!-- 文件描述输入 -->
    <div
      v-if="hasFile"
      class="description-input"
    >
      <el-input
        v-model="description"
        placeholder="添加文件描述（可选）"
        size="small"
        clearable
      />
    </div>

    <!-- 上传按钮 -->
    <div class="upload-actions">
      <el-button
        v-if="hasFile && !uploading"
        type="primary"
        size="small"
        @click="submitUpload"
      >
        <el-icon><Upload /></el-icon>
        上传
      </el-button>
      <el-button
        v-if="uploading"
        type="primary"
        size="small"
        :loading="true"
      >
        上传中...
      </el-button>
      <el-button
        v-if="hasFile && !uploading"
        size="small"
        @click="clearFile"
      >
        取消
      </el-button>
    </div>

    <!-- 上传进度 -->
    <el-progress
      v-if="uploading"
      :percentage="uploadProgress"
      :stroke-width="6"
      class="upload-progress"
    />

    <!-- 上传历史列表 -->
    <div
      v-if="uploadHistory.length > 0"
      class="upload-history"
    >
      <div class="history-header">
        <span class="history-title">上传历史</span>
        <el-button
          type="text"
          size="small"
          @click="clearHistory"
        >
          清空
        </el-button>
      </div>
      <div class="history-list">
        <div
          v-for="item in uploadHistory"
          :key="item.id"
          class="history-item"
        >
          <div class="history-info">
            <el-icon><Document /></el-icon>
            <span class="history-name">{{ item.filename }}</span>
            <el-tag
              size="small"
              type="success"
            >
              成功
            </el-tag>
          </div>
          <div class="history-meta">
            {{ item.file_size_display }} · {{ item.created_at }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled, Document, Upload } from '@element-plus/icons-vue'
import { uploadExcel } from '@/api/excel'

// 定义 emit
const emit = defineEmits(['uploaded', 'upload-success'])

// 上传组件引用
const uploadRef = ref(null)
const fileList = ref([])
const uploading = ref(false)
const uploadProgress = ref(0)
const description = ref('')
const uploadHistory = ref([])

// 上传 URL（实际使用手动上传，不依赖 el-upload 的自动上传）
const uploadUrl = '/api/excel/upload'
const headers = {}

// 判断是否有文件
const hasFile = computed(() => fileList.value.length > 0)

// 当前文件
const currentFile = computed(() => fileList.value[0] || null)

// 上传前验证 - 成品文件：支持 Excel、Word、PDF
const beforeUpload = (file) => {
  // 检查文件类型：Excel (.xlsx/.xls)、Word (.docx/.doc)、PDF (.pdf)
  const fileName = file.name.toLowerCase()
  const isExcel = fileName.endsWith('.xlsx') || fileName.endsWith('.xls')
  const isWord = fileName.endsWith('.docx') || fileName.endsWith('.doc')
  const isPDF = fileName.endsWith('.pdf')
  
  if (!isExcel && !isWord && !isPDF) {
    ElMessage.error('成品文件只能上传 Excel、Word 或 PDF 格式!')
    return false
  }

  // 检查文件大小 (50MB)
  const isLt50M = file.size / 1024 / 1024 < 50
  if (!isLt50M) {
    ElMessage.error('文件大小不能超过 50MB!')
    return false
  }

  return true
}

// 文件变化
const handleChange = (file, files) => {
  fileList.value = files.slice(-1) // 只保留最新选择的一个文件
}

// 提交上传
const submitUpload = async () => {
  if (!currentFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  uploading.value = true
  uploadProgress.value = 0

  try {
    // 使用手动上传
    const file = currentFile.value.raw
    const response = await uploadExcel(file, description.value)

    // 注意：响应拦截器返回的是 response.data，所以 response 本身就是后端数据
    if (response.success) {
      ElMessage.success('文件上传成功')

      // 添加到上传历史
      uploadHistory.value.unshift(response.data)

      // 触发事件
      emit('uploaded')
      emit('upload-success', response.data)

      // 清空当前文件
      clearFile()
    } else if (response.duplicate) {
      // 文件名重复，显示确认对话框
      uploading.value = false
      await handleDuplicateFilename(response.existing_file)
    } else {
      ElMessage.error(response.error || '上传失败')
    }
  } catch (error) {
    console.log('🔍 捕获错误:', error)
    console.log('🔍 error.response:', error.response)
    console.log('🔍 error.response?.data:', error.response?.data)
    
    // 如果是文件名重复（检查 duplicate 标志）
    if (error.response?.data?.duplicate) {
      console.log('🔍 进入 duplicate 分支')
      console.log('🔍 existing_file:', error.response.data.existing_file)
      uploading.value = false
      await handleDuplicateFilename(error.response.data.existing_file)
    } else {
      console.error('上传失败:', error)
      ElMessage.error(error.response?.data?.error || '上传失败，请重试')
    }
  } finally {
    uploading.value = false
    uploadProgress.value = 0
  }
}

// 上传成功
const handleSuccess = (response, file) => {
  console.log('Excel 上传成功:', response)

  if (response.success) {
    ElMessage.success(response.message || '文件上传成功')

    // 添加到上传历史
    uploadHistory.value.unshift(response.data)

    // 触发事件
    emit('uploaded')
    emit('upload-success', response.data)
  } else {
    ElMessage.error(response.error || '上传失败')
  }

  uploading.value = false
}

// 处理文件名重复
const handleDuplicateFilename = async (existingFile) => {
  console.log('🔍 handleDuplicateFilename 被调用, existingFile:', existingFile)
  try {
    console.log('🔍 准备显示确认对话框...')
    await ElMessageBox.confirm(
      `文件名 "${existingFile.filename}" 已存在！\n\n` +
      `已有上传时间: ${existingFile.created_at}\n` +
      `上传者: ${existingFile.uploader_name}\n\n` +
      `是否继续上传并创建新版本？`,
      '发现同名文件',
      {
        confirmButtonText: '继续上传',
        cancelButtonText: '取消',
        type: 'warning',
        distinguishCancelAndClose: true
      }
    )
    console.log('🔍 用户点击了确认')

    // 用户确认，继续上传
    const file = currentFile.value.raw
    const response = await uploadExcel(file, description.value, true)

    if (response.success) {
      ElMessage.success('文件上传成功')
      uploadHistory.value.unshift(response.data)
      emit('uploaded')
      emit('upload-success', response.data)
      clearFile()
    } else {
      ElMessage.error(response.error || '上传失败')
    }
  } catch (action) {
    if (action === 'cancel' || action === 'close') {
      ElMessage.info('已取消上传')
      clearFile()
    }
  }
}

// 上传失败
const handleError = (error) => {
  console.error('Excel 上传失败:', error)
  ElMessage.error('上传失败，请重试')
  uploading.value = false
}

// 删除文件
const handleRemove = () => {
  fileList.value = []
  description.value = ''
}

// 清空当前文件
const clearFile = () => {
  fileList.value = []
  description.value = ''
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

// 清空上传历史
const clearHistory = () => {
  uploadHistory.value = []
}

// 格式化文件大小
const formatFileSize = (size) => {
  if (!size) return '0 B'
  if (size < 1024) return size + ' B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB'
  return (size / (1024 * 1024)).toFixed(2) + ' MB'
}
</script>

<style scoped>
.excel-upload {
  padding: 16px;
}

.upload-hint {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;
}

.hint-icon {
  font-size: 32px;
  color: #409eff;
}

.hint-text {
  flex: 1;
}

.hint-title {
  font-size: 14px;
  color: #303133;
  margin-bottom: 4px;
}

.hint-title em {
  color: #409eff;
  font-style: normal;
}

.hint-tip {
  font-size: 12px;
  color: #909399;
}

.excel-upload-drag {
  width: 100%;
}

.excel-upload-drag :deep(.el-upload) {
  width: 100%;
}

.excel-upload-drag :deep(.el-upload-dragger) {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  height: auto;
  min-height: 120px;
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  background: #fafafa;
  transition: all 0.3s;
}

.excel-upload-drag :deep(.el-upload-dragger:hover) {
  border-color: #409eff;
  background: #f0f9ff;
}

.excel-upload-drag.has-file :deep(.el-upload-dragger) {
  border-color: #67c23a;
  background: #f0f9eb;
  padding: 20px 16px;
}

.excel-upload-drag :deep(.el-icon--upload) {
  font-size: 48px;
  color: #c0c4cc;
  margin-bottom: 12px;
}

.file-icon {
  font-size: 48px;
  color: #67c23a;
  margin-bottom: 8px;
}

.file-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.file-name {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: 12px;
  color: #909399;
}

.description-input {
  margin-top: 12px;
}

.upload-actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
  justify-content: center;
}

.upload-progress {
  margin-top: 16px;
}

.upload-history {
  margin-top: 24px;
  border-top: 1px solid #ebeef5;
  padding-top: 16px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.history-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  padding: 10px 12px;
  background: #f5f7fa;
  border-radius: 6px;
}

.history-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.history-info .el-icon {
  color: #409eff;
}

.history-name {
  flex: 1;
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-meta {
  font-size: 12px;
  color: #909399;
  padding-left: 24px;
}
</style>
