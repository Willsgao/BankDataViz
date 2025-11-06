<template>
  <div class="pdf-controls" v-if="pdf">
    <div class="file-info">
      <div class="file-name">{{ pdf.filename }}</div>
      <div class="file-date">上传于: {{ formatDate(pdf.created_at) }}</div>
    </div>

    <div class="pdf-actions">
      <el-button type="danger" size="small" icon="el-icon-delete"
                 @click="$emit('delete', pdf.filename)">删除</el-button>

      <el-button type="primary" size="small" icon="el-icon-crop"
                 @click="$emit('crop', pdf.filename)"
                 :loading="!!cropLoading[pdf.filename]">图表切割</el-button>

      <el-button type="success" size="small" icon="el-icon-picture"
                 @click="$emit('convert', pdf.disk_name)"
                 :loading="!!converting[pdf.filename]">转图并预览</el-button>

      <el-button
        type="warning"
        size="small"
        icon="el-icon-crop"
        @click="$emit('batch-crop', pdf.disk_name)"
        v-if="convertCache[pdf.disk_name.replace('.pdf', '')]"
        :loading="batchCropLoading[pdf.disk_name]"
        :disabled="batchCropLoading[pdf.disk_name]">
        {{ hasBatchResults ? '重新切表格' : '批量切表格' }}
      </el-button>

      <el-button
        v-if="hasBatchResults"
        type="info"
        size="small"
        icon="el-icon-delete"
        @click="$emit('clear-cache', pdf.disk_name)"
        title="清除裁切缓存">
        清除缓存
      </el-button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  pdf: {
    type: Object,
    required: true
  },
  cropLoading: {
    type: Object,
    default: () => ({})
  },
  converting: {
    type: Object,
    default: () => ({})
  },
  convertCache: {
    type: Object,
    default: () => ({})
  },
  batchCropLoading: {
    type: Object,
    default: () => ({})
  },
  hasBatchResults: {
    type: Boolean,
    default: false
  }
})

defineEmits(['delete', 'crop', 'convert', 'batch-crop', 'clear-cache'])

const formatDate = (ts) => {
  if (!ts) return '未知时间'
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
</script>

<style scoped>
.pdf-controls {
  padding: 16px;
  background: #fafafa;
  border-top: 1px solid #eee;
  flex-shrink: 0;
}

.file-info {
  text-align: center;
  margin-bottom: 12px;
}

.file-name {
  color: #333;
  font-weight: bold;
  font-size: 16px;
  margin-bottom: 4px;
}

.file-date {
  color: #666;
  font-size: 12px;
}

.pdf-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}
</style>