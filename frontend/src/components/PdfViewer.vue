<template>
  <div class="pdf-container">
    <iframe :src="pdfUrl" width="100%" height="700px" frameborder="0"></iframe>
    <el-button size="mini" circle icon="el-icon-close" class="close"
               @click="$emit('close')" title="关闭预览"/>
  </div>
</template>

<script setup>
const props = defineProps({ file: Object })
const pdfUrl = `http://127.0.0.1:5000/file/${props.file.filename}`
defineEmits(['close'])
</script>

<style scoped>
.pdf-container{ position:relative; }
.close{ position:absolute; top:8px; right:8px; z-index:10; }
</style>