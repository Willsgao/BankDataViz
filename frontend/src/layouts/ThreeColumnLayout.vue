<!-- frontend/src/layouts/ThreeColumnLayout.vue -->
<template>
  <div class="three-column-layout" :class="{ 'middle-collapsed': isMiddleCollapsed, 'resizing': isResizing }">
    <!-- 左侧：PDF预览滚动区域 -->
    <div class="left-panel" ref="leftPanel" :style="{ flex: `0 0 ${currentWidths.left}px` }">
      <!-- 修改后的 panel-header -->
      <div class="panel-header">
        <div class="header-left">
          <h3>PDF预览</h3>
          <!-- 添加展开按钮 - 当中间栏折叠时显示 -->
          <el-button
            v-if="isMiddleCollapsed"
            size="small"
            circle
            @click="$emit('toggle-middle')"
            class="expand-btn"
            title="展开中间栏"
          >
            <el-icon><Right /></el-icon>
          </el-button>
        </div>
      </div>

      <div class="scroll-content">
        <slot name="left"></slot>
      </div>

      <!-- 左侧拖拽条 - 中间栏展开时显示在右侧 -->
      <div
        v-if="!isMiddleCollapsed"
        class="resize-handle resize-handle-right"
        @mousedown="startResize('left', $event)"
        :title="'调整左侧宽度 (当前: ' + currentWidths.left + 'px)'"
      ></div>

      <!-- 中间栏折叠时，显示一个更明显的拖拽条 -->
      <div
        v-else
        class="resize-handle resize-handle-right collapsed-handle"
        @mousedown="startResize('left-right', $event)"
        title="调整左右面板宽度"
      >
        <div class="handle-indicator"></div>
      </div>
    </div>

    <!-- 中间：表格信息区域 -->
    <div
      class="middle-panel"
      v-if="!isMiddleCollapsed"
      ref="middlePanel"
      :style="{ flex: `0 0 ${currentWidths.middle}px` }"
    >
      <!-- 左侧拖拽条 -->
      <div
        class="resize-handle resize-handle-left"
        @mousedown="startResize('middle-left', $event)"
        :title="'调整左侧和中间宽度'"
      ></div>

      <!-- 上部分：筛选出的PDF名称 -->
      <div class="middle-top" :class="{ 'collapsed': isTopSectionCollapsed }">
        <div class="section-header" @click="toggleTopSection">
          <span class="section-title">筛选的PDF文件</span>
          <div class="header-right">
            <el-tag type="info" size="small">{{ filteredPdfCount }} 个文件</el-tag>
            <el-icon :class="{'rotate-icon': !isTopSectionCollapsed}">
              <ArrowDown />
            </el-icon>
          </div>
        </div>
        <div v-show="!isTopSectionCollapsed" class="scroll-content">
          <slot name="middle-top"></slot>
        </div>
      </div>

      <!-- 下部分：表格名称列表 -->
      <div class="middle-bottom" :class="{ 'expanded': isTopSectionCollapsed }">
        <div class="section-header">
          <span class="section-title">表格名称列表</span>
          <el-tag type="info">{{ tableCount }} 个表格</el-tag>
        </div>
        <div class="scroll-content">
          <slot name="middle-bottom"></slot>
        </div>
      </div>

      <!-- 右侧拖拽条 -->
      <div
        class="resize-handle resize-handle-right"
        @mousedown="startResize('middle-right', $event)"
        :title="'调整中间宽度 (当前: ' + currentWidths.middle + 'px)'"
      ></div>
    </div>

    <!-- 右侧：Excel内容滚动区域 -->
    <div class="right-panel" ref="rightPanel" :style="{ flex: '1 1 auto' }">


      <div class="panel-header">
        <h3>Excel表格内容</h3>
        <!-- 已移除展开按钮 -->
      </div>
      <div class="scroll-content">
        <slot name="right"></slot>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, defineProps, defineEmits, onMounted, watch, nextTick } from 'vue'
import { ArrowDown, Right } from '@element-plus/icons-vue'

const props = defineProps({
  filteredPdfCount: {
    type: Number,
    default: 0
  },
  tableCount: {
    type: Number,
    default: 0
  },
  isMiddleCollapsed: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['toggle-middle'])

const isTopSectionCollapsed = ref(false)

// 拖拽相关状态
const leftPanel = ref(null)
const middlePanel = ref(null)
const rightPanel = ref(null)
const isResizing = ref(false)
const currentResizeType = ref('')

// 默认宽度
const defaultWidths = {
  left: 400,
  middle: 320,
  right: 500
}

// 当前宽度
const currentWidths = ref({
  left: defaultWidths.left,
  middle: defaultWidths.middle,
  right: defaultWidths.right
})

const toggleTopSection = () => {
  isTopSectionCollapsed.value = !isTopSectionCollapsed.value
}

// 开始拖拽调整大小
const startResize = (type, e) => {
  console.log(`开始拖拽: ${type}`, e)
  e.preventDefault()
  e.stopPropagation()

  isResizing.value = true
  currentResizeType.value = type

  const startX = e.clientX
  const startLeftWidth = currentWidths.value.left
  const startMiddleWidth = currentWidths.value.middle

  const handleMouseMove = (moveEvent) => {
    if (!isResizing.value) return

    const deltaX = moveEvent.clientX - startX
    console.log(`拖拽移动: deltaX = ${deltaX}, type = ${type}`)

    switch (type) {
      case 'left':
        // 调整左侧面板宽度
        currentWidths.value.left = Math.max(300, Math.min(600, startLeftWidth + deltaX))
        console.log(`调整左侧宽度: ${currentWidths.value.left}px`)
        break
      case 'middle-left':
        // 同时调整左侧和中间面板
        currentWidths.value.left = Math.max(300, Math.min(600, startLeftWidth + deltaX))
        currentWidths.value.middle = Math.max(250, Math.min(500, startMiddleWidth - deltaX))
        console.log(`调整左侧: ${currentWidths.value.left}px, 中间: ${currentWidths.value.middle}px`)
        break
      case 'middle-right':
        // 调整中间面板宽度，右侧自动适应
        currentWidths.value.middle = Math.max(250, Math.min(500, startMiddleWidth + deltaX))
        console.log(`调整中间宽度: ${currentWidths.value.middle}px`)
        break
      case 'right':
        // 调整右侧面板最小宽度
        currentWidths.value.middle = Math.max(250, Math.min(500, startMiddleWidth - deltaX))
        console.log(`调整中间宽度: ${currentWidths.value.middle}px`)
        break


      case 'left-right':
          // 中间栏折叠时，调整左侧面板宽度，右侧自动适应
          const newWidth = Math.max(300, Math.min(800, startLeftWidth + deltaX))
          currentWidths.value.left = newWidth
          console.log(`折叠状态调整左侧宽度: ${newWidth}px`)

          // 强制更新视图
          forceUpdateView()
          break

    }
  }


  const forceUpdateView = async () => {
      await nextTick()
      // 可以尝试触发一些DOM操作来强制更新
      if (leftPanel.value) {
        leftPanel.value.style.flex = `0 0 ${currentWidths.value.left}px`
      }
    }

  const handleMouseUp = () => {
    console.log('结束拖拽')
    isResizing.value = false
    currentResizeType.value = ''
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
    document.body.style.cursor = ''
  }

  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
  document.body.style.cursor = 'col-resize'
}

// 监听中间面板折叠状态变化
watch(() => props.isMiddleCollapsed, (newVal) => {
  if (newVal) {
    // 中间面板折叠时，左侧固定宽度，右侧自动填充
    currentWidths.value.left = defaultWidths.left
  } else {
    // 中间面板展开时，恢复默认宽度
    currentWidths.value.left = defaultWidths.left
    currentWidths.value.middle = defaultWidths.middle
  }
})

onMounted(() => {
  // 初始化宽度
  currentWidths.value.left = defaultWidths.left
  currentWidths.value.middle = defaultWidths.middle
})
</script>

<style scoped>
.three-column-layout {
  display: flex;
  height: 100%;
  gap: 0;
  padding: 16px;
  background: #f5f5f5;
  overflow: hidden;
  width: 100%;
}

.three-column-layout.middle-collapsed {
  gap: 0;
}

.three-column-layout.middle-collapsed .left-panel {
  /* flex: 0 0 400px !important; */  /* 删除这行 */
  margin-right: 0;
  border-radius: 8px 0 0 8px;
}


.three-column-layout.middle-collapsed .right-panel {
  flex: 1 1 auto !important;
  margin-left: 0;
  border-radius: 0 8px 8px 0;
}

.three-column-layout.resizing {
  user-select: none;
  cursor: col-resize;
}

.three-column-layout.resizing * {
  pointer-events: none;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rotate-icon {
  transform: rotate(180deg);
  transition: transform 0.2s;
}

.expand-btn {
  transform: rotate(0deg);
  transition: transform 0.3s ease;
}

.expand-btn:hover {
  transform: rotate(0deg) scale(1.1);
}

/* 面板基础样式 - 使用flex布局 */
.left-panel,
.middle-panel,
.right-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  height: 100%;
  min-width: 0; /* 重要：防止内容溢出 */
}

/* 右侧面板自动填充剩余空间 */
.right-panel {
  flex: 1 1 auto;
  min-width: 350px; /* 最小宽度 */
}

/* 面板头部 */
.panel-header {
  flex-shrink: 0;
  padding: 12px 16px;
  background: #fafafa;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

/* 可滚动内容区域 */
.scroll-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

/* 分区头部 */
.section-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e4e7ed;
  cursor: pointer;
  user-select: none;
}

.section-title {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

/* 中间面板上下分区 */
.middle-top {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-bottom: 1px solid #e4e7ed;
  min-height: 0;
  transition: flex 0.3s ease;
}

.middle-bottom {
  flex: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  transition: flex 0.3s ease;
}

/* 折叠状态：下方占满 */
.middle-top.collapsed {
  flex: 0;
}

.middle-bottom.expanded {
  flex: 1;
}

/* 基础拖拽条样式 */
.resize-handle {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 12px; /* 增加宽度 */
  background: rgba(64, 158, 255, 0.1); /* 轻微背景色使其可见 */
  cursor: col-resize;
  z-index: 20; /* 提高层级 */
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.resize-handle:hover {
  background: rgba(64, 158, 255, 0.3);
  width: 16px; /* 悬停时更宽 */
}

.resize-handle:active {
  background: rgba(64, 158, 255, 0.5);
}

.resize-handle-left {
  left: -6px; /* 调整位置，因为宽度增加了 */
}

.resize-handle-right {
  right: -6px; /* 调整位置，因为宽度增加了 */
}

/* 折叠状态下的拖拽条样式 */
.collapsed-handle {
  width: 16px; /* 折叠时更宽 */
  background: linear-gradient(90deg,
    rgba(64, 158, 255, 0.2),
    rgba(64, 158, 255, 0.1),
    rgba(64, 158, 255, 0.2));
}

.collapsed-handle:hover {
  width: 20px;
  background: linear-gradient(90deg,
    rgba(64, 158, 255, 0.4),
    rgba(64, 158, 255, 0.3),
    rgba(64, 158, 255, 0.4));
  box-shadow: 0 0 10px rgba(64, 158, 255, 0.3);
}

/* 拖拽条指示器 */
.handle-indicator {
  width: 4px;
  height: 40px;
  background: rgba(64, 158, 255, 0.6);
  border-radius: 2px;
  transition: all 0.2s;
}

.collapsed-handle:hover .handle-indicator {
  background: rgba(64, 158, 255, 0.9);
  height: 60px;
  width: 6px;
}

/* 确保内容不会溢出 */
.three-column-layout > * {
  min-width: 0;
}
</style>