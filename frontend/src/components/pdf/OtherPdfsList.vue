<template>
  <div class="other-pdfs">
    <div class="other-pdfs-title">其他PDF文件</div>
    <div v-for="pdf in pdfs" :key="pdf.id" class="other-pdf-item">
      <div class="other-pdf-name">{{ pdf.filename }}</div>
      <div class="other-pdf-actions">
        <el-button size="mini" type="primary" @click="$emit('switch-pdf', pdf)">切换到该PDF</el-button>
        <el-button size="mini" type="danger" @click="$emit('delete', pdf.filename)">删除</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  pdfs: {
    type: Array,
    default: () => []
  }
})

defineEmits(['switch-pdf', 'delete'])
</script>

<style scoped>
.other-pdfs {
  margin-top: 16px;
  padding: 16px;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  background: #f9f9f9;
  flex-shrink: 0;
}

.other-pdfs-title {
  font-weight: bold;
  margin-bottom: 12px;
  color: #666;
  font-size: 14px;
}

.other-pdf-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid #eee;
}

.other-pdf-item:last-child {
  border-bottom: none;
}

.other-pdf-name {
  font-size: 14px;
  color: #333;
  flex: 1;
}

.other-pdf-actions {
  display: flex;
  gap: 8px;
}
</style>