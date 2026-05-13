<!-- 在现有的"图片筛选"按钮旁边添加"分类管理"按钮 -->
<template>
  <div
    v-if="pdf"
    class="pdf-controls"
  >
    <div class="file-info">
      <div class="file-name">
        {{ pdf.filename }}
      </div>
      <div class="file-date">
        上传于: {{ formatDate(pdf.created_at) }}
      </div>
    </div>

    <div class="pdf-actions">
      <el-button
        type="success"
        size="small"
        icon="el-icon-picture"
        :loading="!!converting[pdf.filename]"
        @click="$emit('convert', pdf.disk_name)"
      >
        开始转图
      </el-button>


      <!-- 分类管理按钮：仅在已筛选图片后显示 -->
      <el-button
        v-if="hasScreenedImages"
        type="warning"
        size="small"
        icon="el-icon-folder-checked"
        :title="'管理分类图片（有表格: ' + (screeningResult?.has_table_count || 0) + '张, 无表格: ' + (screeningResult?.no_table_count || 0) + '张）'"
        @click="$emit('open-classification', pdf.disk_name)"
      >
        分类管理
        <el-badge
          v-if="screeningResult"
          :value="(screeningResult.has_table_count || 0) + (screeningResult.no_table_count || 0)"
          :max="99"
          class="classification-badge"
        />
      </el-button>

      <!-- 表格解析按钮：只要已转图就显示 -->
      <el-button
        v-if="shouldShowParseButton"
        type="primary"
        size="small"
        icon="el-icon-document"
        :loading="isParsing"
        :title="hasScreenedImages ? '基于筛选结果解析表格' : '解析所有图片中的表格'"
        @click="$emit('parse-tables', pdf.disk_name)"
      >
        {{ hasResults ? '重新解析' : '表格解析' }}
      </el-button>

      <!-- 筛选结果信息 -->
      <div
        v-if="screeningResult"
        class="screening-info"
      >
        <el-tag
          v-if="screeningResult.has_table_count > 0"
          size="small"
          type="success"
        >
          有表格: {{ screeningResult.has_table_count }}张
        </el-tag>
        <el-tag
          v-if="screeningResult.no_table_count > 0"
          size="small"
          type="info"
        >
          无表格: {{ screeningResult.no_table_count }}张
        </el-tag>
      </div>

      <!-- 解析进度显示 -->
      <div
        v-if="parsingProgress"
        class="parsing-progress"
      >
        <div class="progress-text">
          表格解析中...
        </div>
        <el-progress
          :percentage="parsingProgress.percentage"
          :status="parsingProgress.status"
          :stroke-width="8"
          :show-text="false"
          style="width: 120px; margin: 0 8px;"
        />
        <span class="progress-detail">{{ parsingProgress.message }}</span>
      </div>

      <el-button
        v-if="hasBatchResults"
        type="info"
        size="small"
        icon="el-icon-delete"
        title="清除裁切缓存"
        @click="$emit('clear-cache', pdf.disk_name)"
      >
        清除缓存
      </el-button>
    </div>
  </div>
</template>

<script setup>
// <el-button type="danger" size="small" icon="el-icon-delete"
//                 @click="$emit('delete', pdf.filename)">删除</el-button>

import { computed } from 'vue'

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
  },
  parsingProgress: {
    type: Object,
    default: null
  },
  // 新增：筛选相关状态
  hasScreenedImages: {
    type: Boolean,
    default: false
  },
  isScreening: {  // 筛选loading状态
    type: Boolean,
    default: false
  },
  screeningResult: {  // 筛选结果
    type: Object,
    default: null
  }
})

const emit = defineEmits(['delete', 'screen-images', 'convert', 'batch-crop', 'clear-cache', 'parse-tables', 'open-classification'])

// 计算是否已转图
const hasConvertCache = computed(() => {
  const cacheKey = props.pdf.disk_name.replace(/\.pdf$/i, '')
  const cacheData = props.convertCache[cacheKey]
  return cacheData && Array.isArray(cacheData) && cacheData.length > 0
})



const formatDate = (ts) => {
  if (!ts) return '未知时间'
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}


// 计算是否显示分类管理按钮
const shouldShowClassificationButton = computed(() => {
  const diskName = props.pdf.disk_name
  const hasScreened = props.hasScreenedImages

  console.log('🔍 分类管理按钮显示条件检查:', {
    diskName,
    hasScreened,
    shouldShow: hasScreened
  })

  return hasScreened
})

// 计算是否显示表格解析按钮 - 分阶段显示
const shouldShowParseButton = computed(() => {
  const diskName = props.pdf.disk_name
  const hasScreened = props.hasScreenedImages
  const hasConverted = hasConvertCache.value

  const showButton = hasScreened // 主要看筛选状态

  console.log('🔍 表格解析按钮显示状态:', {
    diskName,
    转图状态: hasConverted ? '已完成' : '未完成',
    筛选状态: hasScreened ? '已完成' : '未完成',
    显示按钮: showButton ? '是' : '否'
  })

  return showButton
})


</script>

<style scoped>
/* 保持原有样式不变，添加新的样式 */

.screening-info {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 0 8px;
}

.parsing-progress {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  background: #f0f9ff;
  border-radius: 4px;
  border: 1px solid #bae6fd;
}

.progress-text {
  font-size: 12px;
  color: #0284c7;
  margin-right: 8px;
}

.progress-detail {
  font-size: 11px;
  color: #64748b;
  margin-left: 8px;
}

/* 分类管理按钮的徽章样式 */
:deep(.classification-badge) {
  margin-left: 4px;

  .el-badge__content {
    font-size: 10px;
    height: 16px;
    line-height: 16px;
    padding: 0 4px;
    background-color: #f56c6c;
  }
}

</style>