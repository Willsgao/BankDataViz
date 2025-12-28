<template>
  <div v-if="selectedSheet" class="save-status-bar">
    <div class="save-info">
      <el-tag :type="status.type" size="small">
        <el-icon><Timer /></el-icon>
        {{ status.text }}
      </el-tag>

      <span class="change-count" v-if="modifiedCellsCount > 0">
        已修改 {{ modifiedCellsCount }} 个单元格
      </span>

      <span class="last-save">
        最后保存: {{ formatTime(lastSaveTime) }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { Timer } from '@element-plus/icons-vue'
import { defineProps } from 'vue'

const props = defineProps({
  selectedSheet: Object,
  status: {
    type: Object,
    default: () => ({ type: 'info', text: '' })
  },
  modifiedCellsCount: {
    type: Number,
    default: 0
  },
  lastSaveTime: Number
})

const formatTime = (timestamp) => {
  if (!timestamp) return '从未保存'
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}
</script>

<style scoped>
.save-status-bar {
  padding: 8px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
}

.save-info {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
}

.change-count {
  color: #e6a23c;
  font-weight: 500;
}

.last-save {
  color: #909399;
  margin-left: auto;
}
</style>