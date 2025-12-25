<template>
  <div class="file-upload">
    <el-upload
      class="upload-area"
      :action="uploadActionUrl"
      :show-file-list="false"
      :before-upload="beforeUpload"
      :on-success="handleSuccess"
      :on-error="handleError"
      drag
      v-if="true"
    >
      <div class="upload-content">
        <el-icon class="upload-icon"><upload-filled /></el-icon>
        <div class="upload-text">
          <div>将文件拖到此处，或<em>点击上传</em></div>
          <div class="upload-tip">支持 PDF、PNG、JPG 格式文件</div>
        </div>
      </div>
    </el-upload>

    <!-- 加载状态 -->
    <div v-else class="upload-loading">
      <el-icon class="loading-icon"><loading /></el-icon>
      <div>初始化上传组件...</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getBackendUrl } from '@/utils/config'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled, Loading } from '@element-plus/icons-vue'

const configReady = ref(false)
const uploadActionUrl = ref('')

// uploadActionUrl.value = 'http://101.43.35.52:5000/upload'
onMounted(() => {
  console.log('🔥 FileUpload 已挂载')
  uploadActionUrl.value = '/api/upload'
  console.log('📌 uploadActionUrl:', uploadActionUrl.value)
})


// 上传前验证
const beforeUpload = (file) => {
  const isPDF = file.type === 'application/pdf'
  const isImage = file.type.startsWith('image/')
  const isValidType = isPDF || isImage

  if (!isValidType) {
    ElMessage.error('只能上传 PDF 或图片文件!')
    return false
  }

  const isLt50M = file.size / 1024 / 1024 < 50
  if (!isLt50M) {
    ElMessage.error('文件大小不能超过 50MB!')
    return false
  }

  return true
}


// 上传成功 - 修正版本
const handleSuccess = (response, file) => {
  console.log('📤 上传响应:', response)

  if (!response.success) {
    ElMessage.error(response.error || '上传失败')
    return
  }

  // 检查是否为重复文件
  if (response.duplicate) {
    // 显示重复文件处理对话框
    showDuplicateDialog(file.name, response)
  } else {
    // 新文件上传成功
    ElMessage.success('文件上传成功')
    emit('uploaded')
  }
}


// 显示重复文件处理对话框 - 修复版本
// 显示重复文件对话框 - 确保有取消按钮
const showDuplicateDialog = (fileName, response) => {
  // 方法1：使用 confirm 方法（应该自动显示取消按钮）
  ElMessageBox.confirm(
    `文件 "${fileName}" 已存在！\n\n` +
    `文件ID: ${response.file_id?.slice(0, 12)}...\n` +
    `已有 ${response.upload_count || 1} 次上传记录\n\n` +
    `是否使用现有文件？`,
    '发现重复文件',
    {
      confirmButtonText: '使用现有文件',
      cancelButtonText: '取消上传',
      type: 'warning',
      center: false, // 不居中，这样按钮在右侧
      distinguishCancelAndClose: true, // 区分取消和关闭
      showClose: true // 显示关闭按钮
    }
  )
    .then(() => {
      // 用户点击"使用现有文件"
      ElMessage.success('已关联到现有文件')
      emit('uploaded')
    })
    .catch((action) => {
      if (action === 'cancel') {
        // 用户点击"取消"
        ElMessage.info('已取消重复文件上传')
      } else if (action === 'close') {
        // 用户点击关闭按钮
        console.log('用户关闭了对话框')
      }
    })
}


// 辅助函数：格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 上传失败 - 修复错误处理
const handleError = (error, file, fileList) => {
  console.error('上传失败详情:', {
    error: error,
    file: file,
    fileList: fileList
  })

  let errorMsg = '文件上传失败'

  // 处理不同的错误情况
  if (typeof error === 'string') {
    errorMsg = error
  } else if (error && error.message) {
    errorMsg = error.message
  } else if (error && error.status) {
    errorMsg = `上传失败 (状态码: ${error.status})`
  } else if (error && error.response) {
    // 尝试从响应中获取错误信息
    try {
      const responseData = error.response.data
      if (responseData && responseData.error) {
        errorMsg = responseData.error
      }
    } catch (e) {
      console.warn('解析错误响应失败:', e)
    }
  }

  ElMessage.error(errorMsg)
  emit('upload-error', { file, error: errorMsg })
}

const emit = defineEmits(['uploaded', 'file-processed', 'upload-error'])


</script>

<style scoped>
.file-upload {
  width: 100%;
}

.upload-area {
  width: 100%;
}

.upload-content {
  padding: 40px 20px;
  text-align: center;
}

.upload-icon {
  font-size: 48px;
  color: #c0c4cc;
  margin-bottom: 16px;
}

.upload-text {
  color: #606266;
}

.upload-text em {
  color: #409eff;
  font-style: normal;
}

.upload-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

.upload-loading {
  padding: 40px 20px;
  text-align: center;
  color: #909399;
}

.loading-icon {
  font-size: 48px;
  color: #c0c4cc;
  margin-bottom: 16px;
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 新增对话框样式 */
:deep(.duplicate-dialog) {
  .el-message-box__content {
    max-height: 400px;
    overflow-y: auto;
  }

  .el-message-box__header {
    background: #fff8e6;
    border-bottom: 1px solid #ffeaa7;
  }

  .el-message-box__title {
    color: #e6a23c;
    font-weight: 600;
  }

  .el-message-box__btns {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding-top: 15px;
    border-top: 1px solid #f0f0f0;
  }

  .el-message-box__btns .el-button {
    min-width: 100px;
  }
}

</style>