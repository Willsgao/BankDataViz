<template>
  <div class="file-upload">
    <el-upload
      class="upload-area"
      :action="uploadActionUrl"
      :show-file-list="false"
      :before-upload="beforeUpload"
      :on-success="handleSuccess"
      :on-error="handleError"
      multiple
      :limit="20"
      drag
    >
      <div class="upload-content">
        <el-icon class="upload-icon">
          <upload-filled />
        </el-icon>
        <div class="upload-text">
          <div>将文件拖到此处，或<em>点击上传</em></div>
          <div class="upload-tip">
            支持 PDF、图片 (PNG/JPG) 格式
          </div>
        </div>
      </div>
    </el-upload>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled, Loading } from '@element-plus/icons-vue'
import { getBackendUrl } from '@/utils/config'

const uploadActionUrl = ref('')

onMounted(() => {
  console.log('🔥 FileUpload 已挂载')
  uploadActionUrl.value = getBackendUrl('/api/upload')
  console.log('📌 uploadActionUrl:', uploadActionUrl.value)
})

// 上传前验证 - 待处理文件：只接受 PDF 和图片
const beforeUpload = (file) => {
  const isPDF = file.type === 'application/pdf'
  const isImage = file.type.startsWith('image/')
  const isValidType = isPDF || isImage

  if (!isValidType) {
    ElMessage.error('待处理文件只能上传 PDF 或图片文件!')
    return false
  }

  const isLt50M = file.size / 1024 / 1024 < 50
  if (!isLt50M) {
    ElMessage.error('文件大小不能超过 50MB!')
    return false
  }

  return true
}

// 上传成功
const handleSuccess = (response, file) => {
  console.log('📤 上传响应:', response)

  if (!response.success) {
    ElMessage.error(response.error || '上传失败')
    return
  }

  // 检查是否为 Excel 文件
  const isExcel = file.name.endsWith('.xlsx') || file.name.endsWith('.xls')
  if (isExcel) {
    // Excel 文件上传成功
    ElMessage.success(`Excel 文件 "${file.name}" 上传成功`)
    emit('uploaded')
    return
  }

  // 检查是否为重复文件（仅 PDF/图片）
  if (response.duplicate) {
    // 显示重复文件处理对话框
    showDuplicateDialog(file.name, response)
  } else {
    // 新文件上传成功
    ElMessage.success('文件上传成功')
    emit('uploaded')
  }
}

// 显示重复文件对话框
const showDuplicateDialog = (fileName, response) => {
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
      center: false,
      distinguishCancelAndClose: true,
      showClose: true
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
        console.log('用户关闭了对话框')
      }
    })
}

// 上传失败
const handleError = (error, file) => {
  console.error('上传失败:', error)
  ElMessage.error('文件上传失败')
}

const emit = defineEmits(['uploaded'])
</script>

<style scoped>
.file-upload {
  width: 100%;
}

.upload-area {
  width: 100%;
}

/* 调整上传区域高度 */
.upload-content {
  padding: 20px 10px !important; /* 减小内边距 */
  text-align: center;
}

/* 调整图标大小 */
.upload-icon {
  font-size: 32px !important; /* 减小图标 */
  color: #c0c4cc;
  margin-bottom: 8px !important; /* 减小间距 */
}

/* 调整文字 */
.upload-text {
  color: #606266;
  font-size: 14px; /* 可以稍微调整字体大小 */
}

.upload-text em {
  color: #409eff;
  font-style: normal;
}

/* 调整提示文字 */
.upload-tip {
  font-size: 11px !important; /* 减小提示文字 */
  color: #909399;
  margin-top: 4px !important; /* 减小间距 */
}

/* 调整整个上传区域的最小高度 */
:deep(.el-upload-dragger) {
  min-height: 120px !important; /* 设置最小高度 */
  height: 120px !important; /* 固定高度 */
  padding: 0 !important; /* 移除默认内边距 */
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}

/* 鼠标悬停效果 */
:deep(.el-upload-dragger:hover) {
  border-color: #409eff;
  background-color: #f5f7fa;
}

/* 禁用加载状态（如果需要） */
.upload-loading {
  padding: 20px 10px !important; /* 减小内边距 */
  text-align: center;
  color: #909399;
}

.loading-icon {
  font-size: 32px !important; /* 减小加载图标 */
  color: #c0c4cc;
  margin-bottom: 8px !important;
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
</style>