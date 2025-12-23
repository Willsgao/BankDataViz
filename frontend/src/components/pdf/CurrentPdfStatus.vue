<template>
  <div class="current-pdf-status">
    <!-- 头部：当前PDF基本信息 -->
    <div class="status-header">
      <div class="pdf-info">
        <div class="pdf-name">
          <i class="el-icon-document"></i>
          <span class="name-text" :title="currentPdf?.filename">
            {{ currentPdf?.filename || '未选择PDF' }}
          </span>
        </div>
        <div class="pdf-date" v-if="currentPdf?.created_at">
          上传于: {{ formatDate(currentPdf.created_at) }}
        </div>
      </div>

      <div class="status-badges">
        <!-- 转图状态 -->
        <el-tag
          v-if="convertingObj[currentPdf?.disk_name]"
          size="small"
          type="warning"
          class="status-tag"
        >
          <i class="el-icon-loading"></i>
          转图中...
        </el-tag>

        <!-- 已转图状态 -->
        <el-tag
          v-else-if="hasConvertCache"
          size="small"
          type="success"
          class="status-tag"
          :title="`已转图 ${convertCacheCount} 张`"
        >
          <i class="el-icon-picture"></i>
          已转图
          <span class="count-badge">{{ convertCacheCount }}</span>
        </el-tag>

        <!-- 未转图状态 -->
        <el-tag
          v-else
          size="small"
          type="info"
          class="status-tag"
        >
          <i class="el-icon-picture-outline"></i>
          未转图
        </el-tag>

        <!-- 筛选状态 -->
        <el-tag
          v-if="hasScreened"
          size="small"
          :type="screeningComplete ? 'success' : 'primary'"
          class="status-tag"
        >
          <i class="el-icon-filter"></i>
          已筛选
          <span class="count-badge">{{ screeningResult?.has_table_count || 0 }}</span>
          /
          <span class="count-badge">{{ screeningResult?.no_table_count || 0 }}</span>
        </el-tag>
      </div>
    </div>

    <!-- 新增：PDF处理流水线卡片 -->
    <PdfPipelineCard
      v-if="currentPdf"
      :current-pdf="currentPdf"
      :converting-obj="convertingObj"
      :convert-cache="convertCache"
      :has-screened-images="hasScreenedImages"
      :screening-result-map="screeningResultMap"
      :parsing-progress-map="parsingProgressMap"
      :is-screening="isScreening"
      :is-parsing="isParsing"
    />

    <!-- 操作快捷按钮 -->
    <div class="quick-actions" v-if="currentPdf">
      <div class="actions-row">
        <!-- 转图按钮 -->
        <el-button
          size="mini"
          :type="hasConvertCache ? 'success' : 'primary'"
          :icon="hasConvertCache ? 'el-icon-picture' : 'el-icon-picture-outline'"
          :loading="!!convertingObj[currentPdf.disk_name]"
          @click="handleConvert"
          title="转图并预览"
        >
          {{ hasConvertCache ? '重新转图' : '转图' }}
        </el-button>

        <!-- 图片筛选按钮 -->
        <el-button
          v-if="hasConvertCache"
          size="mini"
          type="primary"
          icon="el-icon-filter"
          :loading="isScreening"
          @click="handleScreenImages"
          :title="hasScreened ? '重新筛选表格图片' : '筛选出含表格的图片'"
        >
          {{ hasScreened ? '重新筛选' : '图片筛选' }}
        </el-button>

        <!-- 分类管理按钮 -->
        <el-button
          v-if="hasScreened"
          size="mini"
          type="warning"
          icon="el-icon-folder-checked"
          @click="handleOpenClassification"
          :title="'管理分类图片'"
        >
          分类管理
          <el-badge
            v-if="screeningResult"
            :value="(screeningResult.has_table_count || 0) + (screeningResult.no_table_count || 0)"
            :max="99"
            class="mini-badge"
          />
        </el-button>
      </div>

      <div class="actions-row" v-if="hasScreened">
        <!-- 表格解析按钮 -->
        <el-button
          size="mini"
          type="primary"
          icon="el-icon-document"
          :loading="isParsing"
          @click="handleParseTables"
          :title="hasScreened ? '基于筛选结果解析表格' : '解析所有图片中的表格'"
        >
          {{ hasResults ? '重新解析' : '表格解析' }}
        </el-button>

        <!-- 清除缓存按钮 -->
        <el-button
          v-if="hasBatchResults"
          size="mini"
          type="info"
          icon="el-icon-delete"
          @click="handleClearCache"
          title="清除裁切缓存"
        >
          清除缓存
        </el-button>
      </div>
    </div>

    <!-- 空状态提示 -->
    <div v-else class="empty-status">
      <el-empty description="请选择一个PDF文件开始处理" :image-size="60">
        <p class="empty-tip">点击左侧PDF列表中的文件进行操作</p>
      </el-empty>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
// 导入新增的组件
import PdfPipelineCard from './PdfPipelineCard.vue'

const props = defineProps({
  // 当前PDF对象
  currentPdf: {
    type: Object,
    default: null
  },

  // 转图相关状态
  convertingObj: {
    type: Object,
    default: () => ({})
  },
  convertCache: {
    type: Object,
    default: () => ({})
  },

  // 筛选相关状态
  hasScreenedImages: {
    type: Object,
    default: () => ({})
  },
  isScreening: {
    type: Boolean,
    default: false
  },
  screeningResultMap: {
    type: Object,
    default: () => ({})
  },

  // 表格解析相关状态
  isParsing: {
    type: Boolean,
    default: false
  },
  hasResults: {
    type: Boolean,
    default: false
  },
  parsingProgressMap: {
    type: Object,
    default: () => ({})
  },

  // 批量裁切结果
  hasBatchResults: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'convert',
  'screen-images',
  'open-classification',
  'parse-tables',
  'clear-cache'
])

// 计算属性
const hasConvertCache = computed(() => {
  if (!props.currentPdf?.disk_name) return false
  const cacheKey = props.currentPdf.disk_name.replace(/\.pdf$/i, '')
  const cacheData = props.convertCache[cacheKey]
  return cacheData && Array.isArray(cacheData) && cacheData.length > 0
})

const convertCacheCount = computed(() => {
  if (!props.currentPdf?.disk_name) return 0
  const cacheKey = props.currentPdf.disk_name.replace(/\.pdf$/i, '')
  const cacheData = props.convertCache[cacheKey]
  return cacheData?.length || 0
})

const hasScreened = computed(() => {
  if (!props.currentPdf?.disk_name) return false
  return !!props.hasScreenedImages[props.currentPdf.disk_name]
})

const screeningResult = computed(() => {
  if (!props.currentPdf?.disk_name) return null
  return props.screeningResultMap[props.currentPdf.disk_name]
})

const screeningComplete = computed(() => {
  if (!screeningResult.value) return false
  return screeningResult.value.has_table_count > 0 || screeningResult.value.no_table_count > 0
})

// 事件处理函数
const handleConvert = () => {
  if (props.currentPdf?.disk_name) {
    emit('convert', props.currentPdf.disk_name)
  }
}

const handleScreenImages = () => {
  if (props.currentPdf?.disk_name) {
    emit('screen-images', props.currentPdf.disk_name)
  }
}

const handleOpenClassification = () => {
  if (props.currentPdf?.disk_name) {
    emit('open-classification', props.currentPdf.disk_name)
  }
}

const handleParseTables = () => {
  if (props.currentPdf?.disk_name) {
    emit('parse-tables', props.currentPdf.disk_name)
  }
}

const handleClearCache = () => {
  if (props.currentPdf?.disk_name) {
    emit('clear-cache', props.currentPdf.disk_name)
  }
}

const formatDate = (ts) => {
  if (!ts) return '未知时间'
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
</script>

<style scoped>
.current-pdf-status {
  border-bottom: 1px solid #e4e7ed;
  padding: 12px 16px;
  background: #fafafa;
  min-height: 140px;
  display: flex;
  flex-direction: column;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.pdf-info {
  flex: 1;
  min-width: 0;
  margin-right: 12px;
}

.pdf-name {
  display: flex;
  align-items: center;
  margin-bottom: 4px;
}

.pdf-name .el-icon-document {
  margin-right: 6px;
  color: #409eff;
}

.name-text {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pdf-date {
  font-size: 12px;
  color: #909399;
}

.status-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: default;
}

.status-tag .count-badge {
  font-weight: bold;
  margin-left: 2px;
}

.quick-actions {
  margin-top: 12px;
}

.actions-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.actions-row:last-child {
  margin-bottom: 0;
}

.actions-row .el-button {
  flex: 1;
  min-width: 80px;
  max-width: 120px;
}

.mini-badge {
  margin-left: 4px;
}

.mini-badge :deep(.el-badge__content) {
  font-size: 10px;
  height: 14px;
  line-height: 14px;
  padding: 0 3px;
}

.empty-status {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.empty-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}
</style>