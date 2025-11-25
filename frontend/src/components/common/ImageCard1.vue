<template>
  <div class="image-card">
    <div class="card-header">
      <!-- 修改表格名称显示 -->
      <span class="table-name">表格{{ index + 1 }}：{{ displayName }}</span>

      <el-button
        v-if="llmConfigured"
        type="primary"
        size="small"
        :loading="llmLoading"
        @click="$emit('llm-process', image)"
        class="process-btn"
      >
        {{ llmLoading ? '识别中' : '识别' }}
      </el-button>
    </div>

    <div class="image-container" @click="$emit('preview', image)">
      <el-image
        :src="image"
        :preview-src-list="[image]"
        fit="contain"
        class="table-image"
        :title="`表格${index + 1}：${displayName}`"
      >
        <template #error>
          <div class="image-error">
            <el-icon><Picture /></el-icon>
            <span>加载失败</span>
          </div>
        </template>
      </el-image>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Picture } from '@element-plus/icons-vue'

const props = defineProps({
  image: {
    type: String,
    required: true
  },
  index: {
    type: Number,
    required: true
  },
  imageName: {  // 新增：接收图片名称
    type: String,
    default: ''
  },
  llmConfigured: {
    type: Boolean,
    default: false
  },
  llmLoading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['preview', 'llm-process'])

// 计算属性：生成显示名称
const displayName = computed(() => {
  // 如果传入了 imageName，直接使用
  if (props.imageName) {
    return props.imageName
  }

  // 否则从图片URL中提取
  try {
    const fileName = props.image.split('/').pop()
    const nameWithoutExt = fileName.replace(/\.(png|jpg|jpeg)$/i, '')
    const parts = nameWithoutExt.split('_')

    if (parts.length > 1) {
      return parts.slice(1).join('_')
    }

    return nameWithoutExt
  } catch (error) {
    return '未知表格'
  }
})
</script>

<style scoped>
.image-card {
  width: 200px;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 12px;
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.image-card:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
  min-height: 40px;
}

.table-name {
  font-size: 12px;
  font-weight: 500;
  color: #333;
  line-height: 1.4;
  word-break: break-all;
  flex: 1;
  margin-right: 8px;
}

.process-btn {
  flex-shrink: 0;
}

.image-container {
  cursor: pointer;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid #f0f0f0;
}

.table-image {
  width: 100%;
  height: 150px;
  display: block;
}

.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 150px;
  color: #999;
  background: #f5f5f5;
}

.image-error .el-icon {
  font-size: 24px;
  margin-bottom: 8px;
}
</style>