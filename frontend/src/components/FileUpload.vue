<template>
  <el-upload
    class="upload-area"
    action="http://127.0.0.1:5000/upload"
    :show-file-list="false"
    :before-upload="beforeUpload"
    :on-success="handleSuccess"
    drag
  >
    <i class="el-icon-upload"></i>
    <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
    <template #tip>
      <div class="el-upload__tip">只能上传PDF/图片文件</div>
    </template>
  </el-upload>
</template>

<script setup>
import { ElMessage } from 'element-plus'

const emit = defineEmits(['uploaded'])

const beforeUpload = (file) => {
  const allow = ['pdf','png','jpg','jpeg','gif']
  const ok = allow.some(ext=> file.name.toLowerCase().endsWith(`.${ext}`))
  if (!ok) ElMessage.error('只能上传PDF或图片文件!')
  return ok
}

const handleSuccess = () => emit('uploaded')
</script>

<style scoped>
.upload-area { margin-bottom: 20px; }
</style>