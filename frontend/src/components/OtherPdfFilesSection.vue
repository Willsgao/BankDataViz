<template>
  <div class="other-pdf-files-section">
    <div class="files-list">
      <div
        v-for="(pdf, index) in files"
        :key="pdf.id"
        class="pdf-item"
        :class="{ active: index === currentPdfIndex }"
        @click="handleSwitchPdf(pdf)"
      >
        <div class="pdf-info">
          <i class="el-icon-document pdf-icon"></i>
          <span class="pdf-name">{{ pdf.filename }}</span>
        </div>
        <div class="pdf-actions">
          <el-button
            type="primary"
            text
            size="small"
            @click.stop="handleConvert(pdf.disk_name)"
            :loading="converting[pdf.disk_name]"
          >
            预览
          </el-button>
          <el-button
            type="danger"
            text
            size="small"
            @click.stop="handleDelete(pdf.filename)"
          >
            删除
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  files: {
    type: Array,
    default: () => []
  },
  currentPdfIndex: {
    type: Number,
    default: -1
  },
  converting: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['switch-pdf', 'delete', 'convert'])

const handleSwitchPdf = (pdf) => {
  emit('switch-pdf', pdf)
}

const handleDelete = (filename) => {
  emit('delete', filename)
}

const handleConvert = (diskName) => {
  emit('convert', diskName)
}
</script>

<style scoped>
.other-pdf-files-section {
  padding: 12px;
}

.files-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pdf-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  transition: all 0.2s ease;
}

.pdf-item:hover {
  border-color: #409eff;
  background: #f0f7ff;
}

.pdf-item.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.pdf-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.pdf-icon {
  color: #f56c6c;
  font-size: 16px;
}

.pdf-name {
  font-size: 14px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pdf-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
</style>