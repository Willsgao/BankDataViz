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
import { ref, watch } from 'vue'

const props = defineProps({ file: Object })
const emit = defineEmits(['close'])

// 直接使用 ref 和 watch
const pdfUrl = ref('')

watch(() => props.file, (newFile) => {
  if (newFile) {
    const baseUrl = window.location.origin
    const fileId = newFile.disk_name || newFile.filename
    pdfUrl.value = `${baseUrl}/api/file/${fileId}`
    console.log('📄 PDF文件切换:', newFile.filename)
  }
}, { immediate: true, deep: true })
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