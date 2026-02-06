<template>
  <div class="pdf-container">
    <iframe
      :src="pdfUrl"
      class="pdf-iframe"
      frameborder="0"
    ></iframe>
    <el-button
      size="mini"
      circle
      icon="el-icon-close"
      class="close"
      @click="$emit('close')"
      title="关闭预览"
    />
  </div>
</template>

<script setup>
const props = defineProps({ file: Object })
import { getBackendUrl } from '@/utils/config'

// const pdfUrl = getBackendUrl(`/api/file/${props.file.disk_name || props.file.filename}`)

const pdfUrl = computed(() => {
  if (!props.file) return ''

  // 保持原有的URL生成逻辑
  const baseUrl = getBackendUrl(`/api/file/${props.file.disk_name || props.file.filename}`)

  // 只有当文件发生变化时才添加时间戳强制刷新
  if (props.file.disk_name !== previousFile.value) {
    previousFile.value = props.file.disk_name
    return `${baseUrl}?t=${Date.now()}` // 强制刷新
  }

  return baseUrl // 使用缓存
})

const previousFile = ref('')

defineEmits(['close'])

</script>

<style scoped>
.pdf-container {
  position: relative;
  width: 100%;
  height: 100%;
  background: #f8f9fa;
  display: flex;
}

.pdf-iframe {
  width: 100%;
  height: 100%;
  border: none;
  flex: 1;
}

.close {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 10;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #dcdfe6;
}
</style>