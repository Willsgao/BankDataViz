<template>
  <el-dialog
    v-model="dialogVisible"
    title="图片预览"
    width="80%"
    top="5vh"
    :before-close="handleClose"
    :close-on-click-modal="true"
    :close-on-press-escape="true"
    custom-class="image-preview-dialog"
  >
    <div class="preview-content">
      <!-- 图片显示 -->
      <div class="image-container">
        <img :src="image" :alt="`预览图片 ${index + 1}`" class="preview-image" />
      </div>

      <!-- 导航控制 -->
      <div class="navigation-controls">
        <el-button
          :disabled="index <= 0"
          @click="handlePrev"
          icon="el-icon-arrow-left"
        >
          上一张
        </el-button>

        <span class="page-info">
          {{ index + 1 }} / {{ total }}
        </span>

        <el-button
          :disabled="index >= total - 1"
          @click="handleNext"
          icon="el-icon-arrow-right"
        >
          下一张
        </el-button>
      </div>
    </div>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  image: {
    type: String,
    default: ''
  },
  index: {
    type: Number,
    default: 0
  },
  total: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['update:visible', 'prev', 'next'])

// 使用本地状态同步
const dialogVisible = ref(false)

// 监听父组件的visible变化
watch(() => props.visible, (newVal) => {
  console.log('🖼️ ImagePreviewDialog - visible变化:', newVal)
  dialogVisible.value = newVal
})

// 监听本地状态变化，同步到父组件
watch(dialogVisible, (newVal) => {
  console.log('🖼️ ImagePreviewDialog - dialogVisible变化:', newVal)
  emit('update:visible', newVal)
})

const handleClose = () => {
  console.log('🖼️ ImagePreviewDialog - 关闭对话框')
  dialogVisible.value = false
}

const handlePrev = () => {
  console.log('🖼️ ImagePreviewDialog - 上一张')
  emit('prev')
}

const handleNext = () => {
  console.log('🖼️ ImagePreviewDialog - 下一张')
  emit('next')
}

// 键盘事件
const handleKeydown = (event) => {
  if (!dialogVisible.value) return

  switch(event.key) {
    case 'ArrowLeft':
      handlePrev()
      break
    case 'ArrowRight':
      handleNext()
      break
    case 'Escape':
      handleClose()
      break
  }
}

// 添加键盘事件监听
if (typeof window !== 'undefined') {
  window.addEventListener('keydown', handleKeydown)
}
</script>

<style scoped>
.preview-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.image-container {
  max-height: 70vh;
  display: flex;
  justify-content: center;
  align-items: center;
}

.preview-image {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
}

.navigation-controls {
  display: flex;
  align-items: center;
  gap: 16px;
  justify-content: center;
}

.page-info {
  font-size: 14px;
  color: #606266;
  min-width: 80px;
  text-align: center;
}

:deep(.image-preview-dialog) {
  .el-dialog__body {
    padding: 20px;
  }
}
</style>