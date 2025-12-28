<template>
  <div class="pdf-list">
    <div class="collapse-control">
      <el-tooltip content="折叠中间区域" placement="top">
        <el-button
          size="small"
          circle
          @click.stop="$emit('toggle-middle')"
          class="collapse-btn"
        >
          <el-icon><Close /></el-icon>
        </el-button>
      </el-tooltip>
    </div>
    <div v-if="isSearching" class="loading-state">
      <el-icon class="is-loading"><Loading /></el-icon>
      搜索中...
    </div>
    <div v-else-if="filteredPdfCount === 0" class="empty-state">
      <p>暂无搜索结果</p>
      <p class="tip">在右上角搜索框输入PDF名称关键字</p>
    </div>
    <div v-else class="pdf-items">
      <div
        v-for="pdf in searchResults"
        :key="pdf.id || pdf.name"
        class="pdf-item"
        :class="{ 'active': selectedPdf && selectedPdf.id === pdf.id }"
        @click="$emit('select-pdf', pdf)"
      >
        <el-icon><Document /></el-icon>
        <span class="pdf-name">{{ pdf.name }}</span>
        <el-tag v-if="pdf.matchType" size="small" type="success">
          {{ pdf.matchType }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Close, Loading, Document } from '@element-plus/icons-vue'

defineProps({
  searchResults: {
    type: Array,
    default: () => []
  },
  isSearching: {
    type: Boolean,
    default: false
  },
  filteredPdfCount: {
    type: Number,
    default: 0
  },
  selectedPdf: Object
})

defineEmits(['toggle-middle', 'select-pdf'])
</script>

<style scoped>
.pdf-list {
  padding: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.collapse-control {
  padding: 8px 12px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: flex-end;
}

.collapse-btn {
  transform: rotate(45deg);
  transition: transform 0.3s ease;
}

.collapse-btn:hover {
  transform: rotate(45deg) scale(1.1);
}

.loading-state {
  padding: 20px;
  text-align: center;
  color: #909399;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: #909399;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}

.tip {
  font-size: 12px;
  margin-top: 8px;
}

.pdf-items {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.pdf-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  gap: 8px;
  transition: background-color 0.2s;
}

.pdf-item:hover {
  background: #f5f7fa;
}

.pdf-item.active {
  background: #ecf5ff;
  border-left: 3px solid #409eff;
}

.pdf-item:last-child {
  border-bottom: none;
}

.pdf-name {
  flex: 1;
  font-size: 14px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>