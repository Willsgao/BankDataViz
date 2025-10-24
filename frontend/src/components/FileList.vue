<template>
  <div class="file-list">
    <div v-for="f in files" :key="f.id" class="file-item">
      <!-- 原始的PDF预览 - 保持不变 -->
      <pdf-viewer v-if="isPDF(f.filename)" :file="f" @close="emit('close', f)" />
      <image-viewer v-else :file="f" />

      <!-- 信息 & 按钮 -->
      <div class="file-meta">
        <div class="file-name">{{ f.filename }}</div>
        <div class="file-date">上传于: {{ formatDate(f.created_at) }}</div>

        <div class="actions">
          <el-button type="danger" size="small" icon="el-icon-delete"
                     @click="emit('delete', f.filename)">删除</el-button>

          <el-button type="primary" size="small" icon="el-icon-crop"
                     @click="emit('crop', f.filename)"
                     :loading="!!cropLoading[f.filename]">图表切割</el-button>

          <el-button type="success" size="small" icon="el-icon-picture"
                     @click="emit('convert', f.disk_name)"
                     :loading="!!converting[f.filename]">转图并预览</el-button>

          <el-button type="warning" size="small" icon="el-icon-crop"
                     @click="emit('batchCrop', f.disk_name)"
                     v-if="convertCache[f.disk_name.replace('.pdf', '')]"
                     :loading="batchCropLoading[f.disk_name]"
                     :disabled="batchCropLoading[f.disk_name]">
            批量切表格
          </el-button>
        </div>

        <!-- 切图结果 -->
        <crop-result v-if="cropResults[f.filename]" :images="cropResults[f.filename]" />

        <!-- 新增：批量裁切结果 - 可滚动预览的小图 -->
        <div v-if="joinedResults[f.disk_name] && joinedResults[f.disk_name].length" class="batch-crop-result">
          <div class="batch-header">
            <span class="batch-title">批量裁切结果</span>
            <span class="batch-count">共 {{ joinedResults[f.disk_name].length }} 个表格</span>
          </div>

          <div class="scroll-container">
            <div class="images-scroll">
              <div v-for="(imgUrl, index) in joinedResults[f.disk_name]" :key="index" class="image-card">
                <div class="image-wrapper">
                  <img :src="imgUrl"
                       :alt="`表格${index + 1}`"
                       class="thumbnail"
                       @click="previewImage(imgUrl, index)"
                       @load="onImageLoad"
                       @error="onImageError" />
                  <div class="image-overlay">
                    <el-button size="mini" type="primary" @click="previewImage(imgUrl, index)">查看</el-button>
                  </div>
                </div>
                <div class="image-info">
                  <div class="image-name">{{ getFileName(imgUrl) }}</div>
                  <div class="image-index">表格 {{ index + 1 }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 图片预览对话框 -->
        <el-dialog v-model="previewDialogVisible" :title="`表格预览 (${currentPreviewIndex + 1}/${currentPreviewTotal})`" width="80%">
          <div class="preview-content">
            <img :src="currentPreviewImage" class="preview-image" />
            <div class="preview-nav">
              <el-button @click="prevImage" :disabled="currentPreviewIndex === 0">上一张</el-button>
              <span class="preview-position">{{ currentPreviewIndex + 1 }} / {{ currentPreviewTotal }}</span>
              <el-button @click="nextImage" :disabled="currentPreviewIndex === currentPreviewTotal - 1">下一张</el-button>
            </div>
          </div>
        </el-dialog>

        <!-- 调试信息 -->
        <div v-if="joinedResults[f.disk_name]" class="debug-info">
          <div>调试信息: {{ joinedResults[f.disk_name].length }} 个文件</div>
          <div v-for="(url, idx) in joinedResults[f.disk_name]" :key="idx" style="font-size:10px;color:#666;">
            {{ url }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import PdfViewer from './PdfViewer.vue'
import ImageViewer from './ImageViewer.vue'
import CropResult from './CropResult.vue'

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
  joinedResults: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits([
  'delete', 'crop', 'convert', 'batchCrop', 'close'
])

// 图片预览相关状态
const previewDialogVisible = ref(false)
const currentPreviewImage = ref('')
const currentPreviewIndex = ref(0)
const currentPreviewTotal = ref(0)
const currentPreviewList = ref([])

const isPDF = n => n.toLowerCase().endsWith('.pdf')

const formatDate = ts => {
  if (!ts) return '未知时间'
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// 从路径中提取文件名
const getFileName = (path) => {
  return path.split('/').pop() || path
}

// 图片加载成功
const onImageLoad = (event) => {
  console.log('图片加载成功:', event.target.src)
}

// 图片加载失败
const onImageError = (event) => {
  console.log('图片加载失败:', event.target.src)
  event.target.style.display = 'none'
}

// 图片预览功能
const previewImage = (imgUrl, index) => {
  // 找到当前文件的所有图片
  const fileKey = Object.keys(props.joinedResults).find(key =>
    props.joinedResults[key].includes(imgUrl)
  )

  if (fileKey) {
    currentPreviewList.value = props.joinedResults[fileKey]
    currentPreviewImage.value = imgUrl
    currentPreviewIndex.value = index
    currentPreviewTotal.value = currentPreviewList.value.length
    previewDialogVisible.value = true
  }
}

const prevImage = () => {
  if (currentPreviewIndex.value > 0) {
    currentPreviewIndex.value--
    currentPreviewImage.value = currentPreviewList.value[currentPreviewIndex.value]
  }
}

const nextImage = () => {
  if (currentPreviewIndex.value < currentPreviewTotal.value - 1) {
    currentPreviewIndex.value++
    currentPreviewImage.value = currentPreviewList.value[currentPreviewIndex.value]
  }
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
  flex-wrap: wrap;
}

/* 新增：批量裁切结果样式 */
.batch-crop-result {
  margin-top: 16px;
  padding: 16px;
  border: 1px solid #e8f4fd;
  border-radius: 8px;
  background: #f7fbff;
}

.batch-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.batch-title {
  font-weight: bold;
  color: #1890ff;
  font-size: 14px;
}

.batch-count {
  color: #52c41a;
  font-size: 12px;
}

.scroll-container {
  overflow-x: auto;
  padding: 8px 0;
}

.images-scroll {
  display: flex;
  gap: 16px;
  padding: 4px;
}

.image-card {
  flex: 0 0 auto;
  width: 180px;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  overflow: hidden;
  background: white;
  transition: all 0.3s ease;
}

.image-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.image-wrapper {
  position: relative;
  width: 100%;
  height: 120px;
  overflow: hidden;
  background: #f5f5f5;
}

.thumbnail {
  width: 100%;
  height: 100%;
  object-fit: contain;
  cursor: pointer;
  transition: transform 0.3s ease;
}

.thumbnail:hover {
  transform: scale(1.05);
}

.image-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.image-wrapper:hover .image-overlay {
  opacity: 1;
}

.image-info {
  padding: 8px;
  text-align: center;
}

.image-name {
  font-size: 11px;
  color: #666;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.image-index {
  font-size: 12px;
  color: #1890ff;
  font-weight: 500;
}

/* 图片预览对话框样式 */
.preview-content {
  text-align: center;
}

.preview-image {
  max-width: 100%;
  max-height: 60vh;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
}

.preview-nav {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
}

.preview-position {
  color: #666;
  font-size: 14px;
}

.debug-info {
  margin-top: 8px;
  padding: 8px;
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 4px;
  font-size: 12px;
  color: #856404;
}

/* 滚动条样式 */
.scroll-container::-webkit-scrollbar {
  height: 6px;
}

.scroll-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.scroll-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.scroll-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .actions {
    flex-direction: column;
    align-items: center;
  }
}
</style>