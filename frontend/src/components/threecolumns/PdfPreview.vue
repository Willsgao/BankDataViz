<template>
  <div class="pdf-preview-container">
    <div
      v-if="selectedPdf"
      class="pdf-viewer"
    >
      <div class="pdf-header">
        <h3>{{ selectedPdf.name }}</h3>
        <div class="header-actions">
          <el-button
            type="primary"
            size="small"
            :loading="downloadLoading"
            @click="$emit('download-pdf', selectedPdf)"
          >
            <el-icon><Download /></el-icon>
            下载PDF
          </el-button>
        </div>
      </div>
      <div class="pdf-content">
        <iframe
          v-if="pdfUrl"
          ref="pdfIframe"
          :key="pdfUrl + currentPage"
          :src="pdfUrl + '#page=' + currentPage"
          width="100%"
          height="100%"
          frameborder="0"
          @load="$emit('pdf-loaded')"
        />
        <div
          v-else
          class="no-preview"
        >
          <el-icon><Document /></el-icon>
          <p>无法加载PDF预览</p>
        </div>
      </div>
    </div>
    <div
      v-else
      class="pdf-placeholder"
    >
      <el-icon><Document /></el-icon>
      <p>请从右侧选择PDF文件进行预览</p>
    </div>
  </div>
</template>

<script setup>
import { Download, Document } from '@element-plus/icons-vue'
import { ref, defineProps, defineEmits } from 'vue'

const props = defineProps({
  selectedPdf: Object,
  pdfUrl: String,
  currentPage: {
    type: Number,
    default: 1
  },
  downloadLoading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['download-pdf', 'pdf-loaded'])

const pdfIframe = ref(null)

</script>

<style scoped>
.pdf-preview-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.pdf-viewer {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.pdf-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #fafafa;
  border-bottom: 1px solid #e4e7ed;
}

.pdf-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pdf-content {
  flex: 1;
  min-height: 0;
  background: #f8f9fa;
}

.pdf-content iframe {
  display: block;
  width: 100%;
  height: 100%;
}

.no-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}

.no-preview .el-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.pdf-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
  text-align: center;
  padding: 20px;
}

.pdf-placeholder .el-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}
</style>