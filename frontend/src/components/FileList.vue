<template>
  <div class="file-list">
    <div v-for="f in files" :key="f.id" class="file-item">
      <!-- 预览 -->
      <pdf-viewer v-if="isPDF(f.filename)" :file="f" @close="emit('close', f)" />
      <image-viewer v-else :file="f" />

      <!-- 信息 & 按钮 -->
      <div class="file-meta">
        <div class="file-name">{{ f.filename }}</div>
        <div class="file-date">上传于：{{ formatDate(f.created_at) }}</div>

        <div class="actions">
          <el-button
              type="danger"
              size="small"
              icon="el-icon-delete"
              @click="() => {
                console.log('删除按钮触发，文件名：', f.filename);  // 新增日志
                emit('delete', f.filename)
              }"
            >删除</el-button>

          <el-button type="primary" size="small" icon="el-icon-crop"
                     @click="emit('crop', f.filename)"
                     :loading="!!cropLoading[f.filename]">图表切割</el-button>

          <!-- PDF 额外按钮 -->
            <el-button type="success" size="small" icon="el-icon-picture"
                       @click="emit('convert', f.disk_name)"
                       :loading="!!converting[f.filename]">转图并预览</el-button>


            <el-button
              type="warning"
              size="small"
              icon="el-icon-crop"
              @click="emit('batchCrop', f.disk_name)"
              v-if="convertCache[f.disk_name.replace('.pdf', '')]"
              :loading="batchCropLoading[f.disk_name]"
              :disabled="batchCropLoading[f.disk_name]"
            >
              批量切表格
            </el-button>



        </div>

        <!-- 切图结果 -->
        <crop-result v-if="cropResults[f.filename]" :images="cropResults[f.filename]" />
      </div>
    </div>
  </div>
</template>

<script setup>
import PdfViewer from './PdfViewer.vue'
import ImageViewer from './ImageViewer.vue'
import CropResult from './CropResult.vue'

defineProps({
  files: {
    type: Array,
    default: () => [] // 补充默认值
  },
  cropLoading: {
    type: Object,
    default: () => ({}) // 补充默认值
  },
  cropResults: {
    type: Object,
    default: () => ({}) // 补充默认值
  },
  converting: {
    type: Object,
    default: () => ({}) // 补充默认值
  },
  convertCache: {
    type: Object,
    default: () => ({}) // 补充默认值
  },
  // 新增：批量裁切加载状态
  batchCropLoading: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits([
  'delete', 'crop', 'convert', 'batchCrop', 'close'
])

const isPDF = n => n.toLowerCase().endsWith('.pdf')

const formatDate = ts => {
  if (!ts) return '未知时间'
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
</script>

<style scoped>
.file-list {
  flex: 1;
  overflow-y: auto;
  padding-right: 10px;
  max-height: calc(100vh - 170px);
}
.file-item {
  margin-bottom: 20px;
  border: 1px solid #eee;
  padding: 10px;
  border-radius: 4px;
  background: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
.file-meta {
  margin-top: 10px;
  text-align: center;
}
.file-name {
  color: #333;
  font-weight: bold;
  font-size: 14px;
}
.file-date {
  color: #888;
  font-size: 12px;
}
.actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  justify-content: center;
}
</style>