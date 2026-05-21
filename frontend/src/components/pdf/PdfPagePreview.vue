<script setup>
import { computed } from 'vue'
import { getBackendUrl } from '@/utils/config'

const props = defineProps({
  visible: Boolean,
  folder: String,
  pngs: Array
})

const emit = defineEmits(['update:visible'])

// 使用计算属性解决只读问题
const localVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

// 处理 PDF 名称
const pdfName = computed(() => {
  if (!props.folder) return ''
  return props.folder.replace ? props.folder.replace(/\.pdf$/i, '') : props.folder
})

// 构建图片 URL - 使用 /api/png/ 端点
const imageUrls = computed(() => {
  if (!props.pngs || !Array.isArray(props.pngs)) return []

  const folder = (props.folder || '').replace(/\.pdf$/i, '')

  return props.pngs.map(png => {
    if (!png) return ''
    if (png.startsWith('http')) return png
    // 转图产生的 PNG 通过 /api/png/ 端点访问
    const name = png.startsWith('/') ? png.split('/').pop() : png
    return getBackendUrl(`/api/png/${folder}/${name}`)
  })
})

// 图片加载错误处理
const handleImageError = (index) => {
  console.error(`图片加载失败: ${props.pngs?.[index]}`)
  console.error(`构建的URL: ${imageUrls.value[index]}`)
}

// 关闭对话框
const handleClose = () => {
  localVisible.value = false
}
</script>

<template>
  <el-dialog
    v-model="localVisible"
    title="PDF页面预览"
    width="90%"
    top="5vh"
    @close="handleClose"
  >
    <div class="pdf-preview-container">
      <div
        v-for="(url, index) in imageUrls"
        :key="index"
        class="page-item"
      >
        <div class="page-number">
          第 {{ index + 1 }} 页
        </div>
        <img
          v-if="url"
          :src="url"
          :alt="`Page ${index + 1}`"
          class="page-image"
          @error="handleImageError(index)"
        >
        <div
          v-else
          class="image-error"
        >
          图片加载失败
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="handleClose">
        关闭
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.pdf-preview-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  max-height: 70vh;
  overflow-y: auto;
}

.page-item {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 8px;
  background: #fafafa;
}

.page-number {
  text-align: center;
  font-weight: bold;
  margin-bottom: 8px;
  color: #606266;
}

.page-image {
  width: 100%;
  height: auto;
  display: block;
}

.image-error {
  text-align: center;
  color: #f56c6c;
  padding: 20px;
}
</style>