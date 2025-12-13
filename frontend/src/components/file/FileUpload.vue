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
import { ElMessage } from 'element-plus'
import { UploadFilled, Loading } from '@element-plus/icons-vue'
import { getBackendUrl } from '@/utils/config'

const configReady = ref(false)
const uploadActionUrl = ref('')

// uploadActionUrl.value = '/api/upload'
onMounted(() => {
  console.log('🔥 FileUpload 已挂载')
  uploadActionUrl.value = 'http://101.43.35.52:5000/upload'
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

// 上传成功
const handleSuccess = (response, file) => {
  ElMessage.success('文件上传成功')
  emit('uploaded')
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
</style>