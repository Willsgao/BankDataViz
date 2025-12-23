<template>
  <div class="pipeline-card" v-if="currentPdf">
    <div class="card-header">
      <span class="title">处理进度</span>
      <el-tag v-if="currentStage" size="mini" :type="getStageTagType(currentStage)">
        {{ getStageText(currentStage) }}
      </el-tag>
    </div>

    <div class="pipeline-steps">
      <!-- 1. PDF上传 - 总是已完成 -->
      <div class="step done">
        <div class="step-icon">
          <i class="el-icon-upload"></i>
        </div>
        <div class="step-content">
          <div class="step-title">PDF上传</div>
          <div class="step-status">已完成</div>
        </div>
        <div class="step-time">
          {{ formatDate(currentPdf.created_at) }}
        </div>
      </div>

      <!-- 2. PDF转图 - 动态状态 -->
      <div :class="['step', getConvertStepClass()]">
        <div class="step-icon">
          <i :class="getConvertIcon()"></i>
        </div>
        <div class="step-content">
          <div class="step-title">PDF转图</div>
          <div class="step-status">{{ getConvertText() }}</div>
          <div v-if="getConvertStepClass() === 'processing'" class="step-progress">
            <el-progress
              :percentage="convertProgress"
              :show-text="false"
              :stroke-width="4"
              style="width: 80px;"
            />
          </div>
          <div v-if="getConvertStepClass() === 'done' && convertDone" class="step-time">
            {{ convertDoneTime }}
          </div>
        </div>
      </div>

      <!-- 3. 图片筛选 - 动态状态 -->
      <div :class="['step', getScreeningStepClass()]">
        <div class="step-icon">
          <i :class="getScreeningIcon()"></i>
        </div>
        <div class="step-content">
          <div class="step-title">图片筛选</div>
          <div class="step-status">{{ getScreeningText() }}</div>
          <div v-if="screeningResult" class="step-stats">
            <span class="stat-item tables">{{ screeningResult.has_table_count || 0 }} 有表格</span>
            <span class="stat-item no-tables">{{ screeningResult.no_table_count || 0 }} 无表格</span>
          </div>
          <div v-if="getScreeningStepClass() === 'done' && screeningDone" class="step-time">
            {{ screeningDoneTime }}
          </div>
        </div>
      </div>

      <!-- 4. 表格解析 - 动态状态 -->
      <div :class="['step', getParsingStepClass()]">
        <div class="step-icon">
          <i :class="getParsingIcon()"></i>
        </div>
        <div class="step-content">
          <div class="step-title">表格解析</div>
          <div class="step-status">{{ getParsingText() }}</div>
          <div v-if="getParsingStepClass() === 'processing' && parsingProgress" class="step-progress">
            <el-progress
              :percentage="parsingProgress.percentage || 0"
              :show-text="false"
              :stroke-width="4"
              :status="parsingProgress.status || 'primary'"
              style="width: 80px;"
            />
            <span class="progress-text">{{ parsingProgress.message || '' }}</span>
          </div>
          <div v-if="getParsingStepClass() === 'done' && parsingDone" class="step-time">
            {{ parsingDoneTime }}
          </div>
        </div>
      </div>

      <!-- 当前操作提示 -->
      <div v-if="nextActionHint" class="action-hint">
        <i class="el-icon-info"></i>
        <span>{{ nextActionHint }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  // 当前PDF对象
  currentPdf: {
    type: Object,
    default: null
  },
  // 转图状态
  convertingObj: {
    type: Object,
    default: () => ({})
  },
  // 转图缓存
  convertCache: {
    type: Object,
    default: () => ({})
  },
  // 筛选状态
  hasScreenedImages: {
    type: Object,
    default: () => ({})
  },
  // 筛选结果
  screeningResultMap: {
    type: Object,
    default: () => ({})
  },
  // 解析进度
  parsingProgressMap: {
    type: Object,
    default: () => ({})
  },
  // 是否在筛选中
  isScreening: {
    type: Boolean,
    default: false
  },
  // 是否在解析中
  isParsing: {
    type: Boolean,
    default: false
  },
  // 步骤完成时间记录（从父组件传递）
  stepCompletionTime: {
    type: Object,
    default: () => ({})
  }
})

// 1. 获取当前PDF的disk_name
const pdfDiskName = computed(() => {
  return props.currentPdf?.disk_name || ''
})

// 2. PDF转图状态
const hasConvertCache = computed(() => {
  if (!pdfDiskName.value) return false
  const cacheKey = pdfDiskName.value.replace(/\.pdf$/i, '')
  const cacheData = props.convertCache[cacheKey]
  return cacheData && Array.isArray(cacheData) && cacheData.length > 0
})

// 转图完成状态
const convertDone = computed(() => {
  if (!pdfDiskName.value) return false
  return hasConvertCache.value || !!props.stepCompletionTime[pdfDiskName.value]?.convert
})

const convertDoneTime = computed(() => {
  if (!pdfDiskName.value) return ''
  const time = props.stepCompletionTime[pdfDiskName.value]?.convert
  return time ? `完成于: ${formatTime(time)}` : '已完成'
})

// 转图步骤状态判断
const getConvertStepClass = () => {
  if (!pdfDiskName.value) return 'pending'
  
  // 如果正在进行转图
  if (props.convertingObj[pdfDiskName.value]) return 'processing'
  
  // 如果已经完成转图
  if (convertDone.value) return 'done'
  
  // 否则等待转图
  return 'pending'
}

const getConvertIcon = () => {
  const status = getConvertStepClass()
  return {
    pending: 'el-icon-picture-outline',
    processing: 'el-icon-loading',
    done: 'el-icon-picture'
  }[status]
}

const getConvertText = () => {
  const status = getConvertStepClass()
  const texts = {
    pending: '等待转图',
    processing: '转图中...',
    done: '已完成'
  }
  return texts[status]
}

const convertProgress = computed(() => {
  return props.convertingObj[pdfDiskName.value] ? 50 : 0
})

// 3. 图片筛选状态
const hasScreened = computed(() => {
  return pdfDiskName.value ? !!props.hasScreenedImages[pdfDiskName.value] : false
})

const screeningResult = computed(() => {
  return pdfDiskName.value ? props.screeningResultMap[pdfDiskName.value] : null
})

// 筛选完成状态
const screeningDone = computed(() => {
  if (!pdfDiskName.value) return false
  return hasScreened.value || !!props.stepCompletionTime[pdfDiskName.value]?.screen
})

const screeningDoneTime = computed(() => {
  if (!pdfDiskName.value) return ''
  const time = props.stepCompletionTime[pdfDiskName.value]?.screen
  return time ? `完成于: ${formatTime(time)}` : '已完成'
})

// 筛选步骤状态判断
const getScreeningStepClass = () => {
  if (!pdfDiskName.value) return 'pending'
  
  // 如果正在进行筛选
  if (props.isScreening) return 'processing'
  
  // 如果已经完成筛选
  if (screeningDone.value) return 'done'
  
  // 如果转图已完成，可以开始筛选
  if (convertDone.value) return 'pending'
  
  // 否则等待转图完成
  return 'skipped'
}

const getScreeningIcon = () => {
  const status = getScreeningStepClass()
  return {
    pending: 'el-icon-folder-opened',
    processing: 'el-icon-loading',
    done: 'el-icon-folder-checked',
    skipped: 'el-icon-folder-opened'
  }[status]
}

const getScreeningText = () => {
  const status = getScreeningStepClass()
  if (status === 'skipped') {
    return '等待转图完成'
  }
  const texts = {
    pending: '准备筛选',
    processing: '筛选中...',
    done: '已完成'
  }
  return texts[status]
}

// 4. 表格解析状态
const parsingProgress = computed(() => {
  return pdfDiskName.value ? props.parsingProgressMap[pdfDiskName.value] : null
})

// 解析完成状态
const parsingDone = computed(() => {
  if (!pdfDiskName.value) return false
  const progress = parsingProgress.value
  const hasProgressDone = progress && progress.percentage === 100
  const hasTime = !!props.stepCompletionTime[pdfDiskName.value]?.parse
  return hasProgressDone || hasTime
})

const parsingDoneTime = computed(() => {
  if (!pdfDiskName.value) return ''
  const time = props.stepCompletionTime[pdfDiskName.value]?.parse
  return time ? `完成于: ${formatTime(time)}` : '已完成'
})

// 解析步骤状态判断
const getParsingStepClass = () => {
  if (!pdfDiskName.value) return 'pending'
  
  // 如果正在进行解析
  if (props.isParsing) return 'processing'
  
  // 如果已经完成解析
  if (parsingDone.value) return 'done'
  
  // 如果筛选已完成，可以开始解析
  if (screeningDone.value) return 'pending'
  
  // 否则等待筛选完成
  return 'skipped'
}

const getParsingIcon = () => {
  const status = getParsingStepClass()
  return {
    pending: 'el-icon-document',
    processing: 'el-icon-loading',
    done: 'el-icon-document-checked',
    skipped: 'el-icon-document'
  }[status]
}

const getParsingText = () => {
  const status = getParsingStepClass()
  if (status === 'processing' && parsingProgress.value) {
    return `解析中 ${parsingProgress.value.percentage || 0}%`
  }
  
  if (status === 'skipped') {
    return '等待筛选完成'
  }
  
  return {
    pending: '准备解析',
    done: '已完成'
  }[status]
}

// 5. 当前整体阶段
const currentStage = computed(() => {
  if (!pdfDiskName.value) return 'idle'
  
  // 如果有进行中的步骤
  if (props.convertingObj[pdfDiskName.value]) return 'converting'
  if (props.isScreening) return 'screening'
  if (props.isParsing) return 'parsing'
  
  // 检查当前应处于哪个阶段
  if (!convertDone.value) return 'ready_for_convert'
  if (!screeningDone.value) return 'ready_for_screening'
  if (!parsingDone.value) return 'ready_for_parsing'
  
  // 所有步骤都已完成
  return 'completed'
})

const getStageTagType = (stage) => {
  const types = {
    idle: 'info',
    ready_for_convert: 'info',
    converting: 'warning',
    ready_for_screening: 'primary',
    screening: 'primary',
    ready_for_parsing: 'success',
    parsing: 'success',
    completed: 'success'
  }
  return types[stage] || 'info'
}

const getStageText = (stage) => {
  const texts = {
    idle: '未开始',
    ready_for_convert: '准备转图',
    converting: '转图中',
    ready_for_screening: '准备筛选',
    screening: '筛选中',
    ready_for_parsing: '准备解析',
    parsing: '解析中',
    completed: '已完成'
  }
  return texts[stage] || '未知状态'
}

// 6. 下一步操作提示
const nextActionHint = computed(() => {
  if (!pdfDiskName.value) return ''
  
  if (props.convertingObj[pdfDiskName.value]) return '正在转图，请稍候...'
  if (props.isScreening) return '正在筛选图片，请稍候...'
  if (props.isParsing) return '正在解析表格，请稍候...'
  
  if (!convertDone.value) return '点击"转图"按钮开始处理'
  if (!screeningDone.value) return '转图完成！点击"图片筛选"继续'
  if (!parsingDone.value) return '筛选完成！点击"表格解析"继续'
  
  return '所有处理已完成！'
})

// 工具函数
const formatDate = (ts) => {
  if (!ts) return '--'
  const d = new Date(ts)
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hour = String(d.getHours()).padStart(2, '0')
  const minute = String(d.getMinutes()).padStart(2, '0')
  return `${month}-${day} ${hour}:${minute}`
}

const formatTime = (ts) => {
  if (!ts) return ''
  const d = new Date(ts)
  const hour = String(d.getHours()).padStart(2, '0')
  const minute = String(d.getMinutes()).padStart(2, '0')
  return `${hour}:${minute}`
}
</script>

<style scoped>
.pipeline-card {
  background: white;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 12px;
  border: 1px solid #ebeef5;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f2f5;
}

.card-header .title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.pipeline-steps {
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: relative;
}

.step {
  display: flex;
  align-items: flex-start;
  padding: 8px;
  border-radius: 6px;
  transition: all 0.2s;
}

.step:hover {
  background: #fafafa;
}

.step-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  flex-shrink: 0;
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-title {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 2px;
}

.step-status {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.step-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.progress-text {
  font-size: 11px;
  color: #409eff;
}

.step-time {
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
}

.step-stats {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.stat-item {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
  background: #f0f2f5;
}

.stat-item.tables {
  background: #f0f9eb;
  color: #67c23a;
}

.stat-item.no-tables {
  background: #f5f7fa;
  color: #909399;
}

/* 步骤状态样式 */
.step.done .step-icon {
  background: #f0f9eb;
  color: #67c23a;
  border: 1px solid #e1f5d8;
}

.step.processing .step-icon {
  background: #f0f9ff;
  color: #409eff;
  border: 1px solid #b3e0ff;
  animation: spin 1.5s linear infinite;
}

.step.pending .step-icon {
  background: #f5f7fa;
  color: #409eff;
  border: 1px solid #dcdfe6;
}

.step.skipped .step-icon {
  background: #f5f7fa;
  color: #c0c4cc;
  border: 1px solid #ebeef5;
  opacity: 0.6;
}

.step.skipped .step-title,
.step.skipped .step-status {
  color: #c0c4cc;
  opacity: 0.6;
}

/* 连接线 */
.step:not(:last-child) {
  position: relative;
}

.step:not(:last-child)::after {
  content: '';
  position: absolute;
  left: 16px;
  bottom: -13px;
  width: 1px;
  height: 12px;
  background: #ebeef5;
}

/* 已完成步骤后的连接线 */
.step.done:not(:last-child)::after {
  background: #67c23a;
}

/* 跳过的步骤后的连接线 */
.step.skipped:not(:last-child)::after {
  background: #ebeef5;
  opacity: 0.6;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 操作提示 */
.action-hint {
  margin-top: 12px;
  padding: 8px 12px;
  background: #f0f9ff;
  border-radius: 6px;
  border: 1px solid #b3e0ff;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #409eff;
}

.action-hint i {
  font-size: 14px;
}
</style>