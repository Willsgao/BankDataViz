<template>
  <div class="non-pdf-files">
    <div
      v-if="hasPDF"
      class="non-pdf-title"
    >
      图片文件
    </div>
    <div
      v-for="file in files"
      :key="file.id"
      class="file-item"
    >
      <ImageViewer :file="file" />

      <div class="file-meta">
        <div class="file-name">
          {{ file.filename }}
        </div>
        <div class="file-date">
          上传于: {{ formatDate(file.created_at) }}
        </div>

        <div class="actions">
          <!-- 修改这里：传递完整的文件对象 -->
          <el-button
            type="danger"
            size="small"
            icon="el-icon-delete"
            @click="$emit('delete', file)"
          >
            删除
          </el-button>

          <el-button
            type="primary"
            size="small"
            icon="el-icon-crop"
            :loading="!!cropLoading[file.filename]"
            @click="$emit('crop', file.filename)"
          >
            图表切割
          </el-button>
        </div>

        <CropResult
          v-if="cropResults[file.filename]"
          :images="cropResults[file.filename]"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

import ImageViewer from '@/components/common/ImageViewer.vue'
import CropResult from '@/components/processing/CropResult.vue'

const props = defineProps({
  files: {
    type: Array,
    default: () => []
  },
  cropLoading: {
    type: Object,
    default: () => ({})
  },
  cropResults: {
    type: Object,
    default: () => ({})
  },
  hasPDF: {
    type: Boolean,
    default: false
  }
})

defineEmits([
  'switch-pdf', 'delete', 'crop', 'convert', 'batch-crop',
  'clear-cache', 'close-pdf', 'preview-image', 'llm-process', 'single-llm-process'
])

const formatDate = (ts) => {
  if (!ts) return '未知时间'
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
</script>

<style scoped>
.non-pdf-files {
  margin-top: 16px;
  flex-shrink: 0;
}

.non-pdf-title {
  font-weight: bold;
  margin-bottom: 12px;
  color: #666;
  font-size: 16px;
}

.file-item {
  margin-bottom: 20px;
  border: 1px solid #eee;
  padding: 10px;
  border-radius: 4px;
  background: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  max-width: 500px;
  margin-left: auto;
  margin-right: auto;
}

.file-meta {
  margin-top: 10px;
  text-align: center;
}

.actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}
</style>