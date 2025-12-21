<template>
  <div class="pdf-controls" v-if="pdf">
    <div class="file-info">
      <div class="file-name">{{ pdf.filename }}</div>
      <div class="file-date">上传于: {{ formatDate(pdf.created_at) }}</div>
    </div>

    <div class="pdf-actions">
      <el-button type="danger" size="small" icon="el-icon-delete"
                 @click="$emit('delete', pdf.filename)">删除</el-button>

      <el-button type="primary" size="small" icon="el-icon-crop"
                 @click="$emit('crop', pdf.filename)"
                 :loading="!!cropLoading[pdf.filename]">图表切割</el-button>

      <el-button type="success" size="small" icon="el-icon-picture"
                 @click="$emit('convert', pdf.disk_name)"
                 :loading="!!converting[pdf.filename]">转图并预览</el-button>

      <!-- 表格解析按钮：仅在已转图或已有解析结果时显示 -->
      <el-button
        v-if="shouldShowParseButton"
        type="primary"
        size="small"
        icon="el-icon-document"
        @click="$emit('parse-tables', pdf.disk_name)"
        :loading="isParsing">
        {{ hasResults ? '重新解析' : '表格解析' }}
      </el-button>

      <el-button
        v-if="hasBatchResults"
        type="info"
        size="small"
        icon="el-icon-delete"
        @click="$emit('clear-cache', pdf.disk_name)"
        title="清除裁切缓存">
        清除缓存
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted } from 'vue'

const props = defineProps({
  pdf: {
    type: Object,
    required: true
  },
  cropLoading: {
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
  hasBatchResults: {
    type: Boolean,
    default: false
  },
  isParsing: {
    type: Boolean,
    default: false
  },
  hasResults: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['delete', 'crop', 'convert', 'batch-crop', 'clear-cache', 'parse-tables'])

// 调试函数：输出当前状态
const debugStatus = () => {
  console.log('📊 PdfControls 状态调试:')
  console.log('pdf.disk_name:', props.pdf.disk_name)
  console.log('convertCache:', props.convertCache)
  console.log('convertCache[disk_name]:', props.convertCache[props.pdf.disk_name])
  console.log('hasResults:', props.hasResults)
  console.log('shouldShowParseButton:', shouldShowParseButton.value)
}

// 计算是否显示表格解析按钮
// 计算是否显示表格解析按钮
const shouldShowParseButton = computed(() => {
  const diskName = props.pdf.disk_name

  // 移除 .pdf 后缀进行匹配（因为 convertCache 使用不带后缀的键）
  const cacheKey = diskName.replace(/\.pdf$/i, '')

  // 检查 convertCache 中是否有该文件的数据
  const hasConvertCache = !!props.convertCache[cacheKey]

  // 如果已经有解析结果，也显示按钮
  const shouldShow = hasConvertCache || props.hasResults

  // 调试输出
  if (shouldShow) {
    console.log(`✅ 应该显示表格解析按钮: ${diskName}`)
    console.log(`   - 缓存键: ${cacheKey}`)
    console.log(`   - hasConvertCache: ${hasConvertCache}`)
    console.log(`   - hasResults: ${props.hasResults}`)
    console.log(`   - convertCache[${cacheKey}]:`, props.convertCache[cacheKey])
  }

  return shouldShow
})

// 监听 convertCache 的变化
watch(() => props.convertCache, (newCache) => {
  console.log('🔄 convertCache 发生变化:', newCache)
  console.log(`检查 ${props.pdf.disk_name} 是否在新缓存中:`, newCache[props.pdf.disk_name])
}, { deep: true })

// 监听该文件是否在转图中
watch(() => props.converting[props.pdf.filename], (isConverting, wasConverting) => {
  // 如果之前正在转图，但现在不是了（转图完成）
  if (wasConverting && !isConverting) {
    console.log(`🔄 转图完成: ${props.pdf.filename}`)
    console.log(`检查缓存:`, props.convertCache[props.pdf.disk_name])
  }
}, { immediate: true })

const formatDate = (ts) => {
  if (!ts) return '未知时间'
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// 组件挂载时调试
onMounted(() => {
  console.log('📄 PdfControls 挂载:', props.pdf.filename)
  debugStatus()
})
</script>

<style scoped>
.pdf-controls {
  padding: 16px;
  background: #fafafa;
  border-top: 1px solid #eee;
  flex-shrink: 0;
}

.file-info {
  text-align: center;
  margin-bottom: 12px;
}

.file-name {
  color: #333;
  font-weight: bold;
  font-size: 16px;
  margin-bottom: 4px;
}

.file-date {
  color: #666;
  font-size: 12px;
}

.pdf-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}
</style>