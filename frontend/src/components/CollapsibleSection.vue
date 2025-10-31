<template>
  <div class="collapsible-section" :class="{ collapsed: collapsed }">
    <div class="section-header" @click="handleToggle">
      <div class="header-left">
        <el-icon class="collapse-icon" :class="{ rotated: collapsed }">
          <ArrowRight />
        </el-icon>
        <span class="section-title">{{ title }}</span>
      </div>
      <div class="header-actions">
        <el-tag v-if="collapsed" type="info" size="small">已折叠</el-tag>
        <el-button
          v-else
          type="text"
          size="small"
          :icon="Collapse"
          @click.stop="handleToggle"
          title="折叠"
        />
      </div>
    </div>

    <div class="section-content" v-if="!collapsed">
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ArrowRight, Collapse } from '@element-plus/icons-vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  collapsed: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['toggle'])

const handleToggle = () => {
  emit('toggle')
}
</script>

<style scoped>
.collapsible-section {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: white;
  transition: all 0.3s ease;
  overflow: hidden;
}

.collapsible-section.collapsed {
  background: #f8f9fa;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s ease;
}

.collapsed .section-header {
  border-bottom: none;
  background: #f0f2f5;
}

.section-header:hover {
  background: #ebedf0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.collapse-icon {
  transition: transform 0.3s ease;
  font-size: 12px;
  color: #909399;
}

.collapse-icon.rotated {
  transform: rotate(90deg);
}

.section-title {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-content {
  padding: 0;
  max-height: 400px; /* 默认最大高度 */
  overflow: auto;
  transition: max-height 0.3s ease;
}

/* 当PDF预览区域展开时，自动调整高度 */
.collapsible-section:first-child .section-content {
  max-height: none;
  flex: 1;
}

/* 当其他区域都折叠时，PDF预览区域占据更多空间 */
.pdf-sections-container .collapsible-section:first-child:not(.collapsed) .section-content {
  min-height: 500px;
  flex: 1;
}
</style>