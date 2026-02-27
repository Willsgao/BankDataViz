<template>
  <div class="progress-monitor-dialog">
    <!-- 统计摘要栏 -->
    <div class="summary-section">
      <div class="summary-title">
        <i class="el-icon-s-data"></i>
        <span>任务统计摘要</span>
        <el-button
          size="small"
          type="text"
          icon="el-icon-refresh"
          @click="$emit('refresh')"
          title="刷新"
        />
      </div>

      <div class="summary-cards">
        <el-card class="summary-card total">
          <div class="card-content">
            <div class="card-icon">
              <i class="el-icon-s-order"></i>
            </div>
            <div class="card-info">
              <div class="card-value">{{ summary.total }}</div>
              <div class="card-label">总任务数</div>
            </div>
          </div>
        </el-card>

        <el-card class="summary-card processing">
          <div class="card-content">
            <div class="card-icon">
              <i class="el-icon-loading"></i>
            </div>
            <div class="card-info">
              <div class="card-value">{{ summary.processing }}</div>
              <div class="card-label">处理中</div>
            </div>
          </div>
        </el-card>

        <el-card class="summary-card completed">
          <div class="card-content">
            <div class="card-icon">
              <i class="el-icon-success"></i>
            </div>
            <div class="card-info">
              <div class="card-value">{{ summary.completed }}</div>
              <div class="card-label">已完成</div>
            </div>
          </div>
        </el-card>

        <el-card class="summary-card queued">
          <div class="card-content">
            <div class="card-icon">
              <i class="el-icon-time"></i>
            </div>
            <div class="card-info">
              <div class="card-value">{{ summary.queued }}</div>
              <div class="card-label">排队中</div>
            </div>
          </div>
        </el-card>

        <el-card class="summary-card failed">
          <div class="card-content">
            <div class="card-icon">
              <i class="el-icon-error"></i>
            </div>
            <div class="card-info">
              <div class="card-value">{{ summary.failed }}</div>
              <div class="card-label">失败</div>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="task-list-section">
      <div class="section-header">
        <span class="section-title">解析任务列表</span>
        <div class="section-actions">
          <el-button
            size="small"
            @click="handleAutoRefreshToggle"
            :type="autoRefresh ? 'primary' : ''"
          >
            <i class="el-icon-refresh"></i>
            {{ autoRefresh ? '停止刷新' : '自动刷新' }}
          </el-button>
          <el-button
            size="small"
            icon="el-icon-refresh-right"
            @click="$emit('refresh')"
          >
            立即刷新
          </el-button>
        </div>
      </div>

      <div class="task-table-container">
        <el-table
          :data="filteredTasks"
          style="width: 100%"
          height="400"
          v-loading="loading"
          empty-text="暂无进行中的解析任务"
        >
          <!-- 文件列 -->
          <el-table-column label="PDF文件" width="250">
              <template #default="{ row }">
                <div class="pdf-info-cell">
                  <i class="el-icon-document"></i>
                  <div class="pdf-details">
                    <!-- 显示原始文件名 -->
                    <div class="pdf-filename" :title="row.original_filename">
                      {{ truncateText(row.original_filename, 25) }}
                    </div>
                    <!-- 显示数据库ID（用于调试） -->
                    <div v-if="row.from_database" class="pdf-db-id">
                      <small>ID: {{ truncateText(row.pdf_folder, 15) }}</small>
                    </div>
                  </div>
                </div>
              </template>
            </el-table-column>


          <!-- 状态列 -->
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag
                :type="getStatusTagType(row)"
                size="small"
                effect="light"
                class="status-tag"
              >
                <i v-if="row.status === 'processing'" class="el-icon-loading"></i>
                {{ getStatusText(row) }}
              </el-tag>
            </template>
          </el-table-column>

          <!-- 进度列 -->
          <el-table-column label="进度" width="200">
            <template #default="{ row }">
              <div class="progress-cell">
                <el-progress
                  :percentage="getProgressPercentage(row)"
                  :status="getProgressStatus(row)"
                  :stroke-width="6"
                  :text-inside="true"
                  :show-text="true"
                  class="task-progress"
                >
                  <span>{{ getProgressText(row) }}</span>
                </el-progress>
                <div v-if="row.status === 'processing'" class="progress-time">
                  {{ getElapsedTime(row) }}
                </div>
              </div>
            </template>
          </el-table-column>

          <!-- 图片处理统计 -->
          <el-table-column label="图片处理" width="140">
            <template #default="{ row }">
              <div class="image-stats">
                <div v-if="row.processed !== undefined || row.processed_images !== undefined">
                  <span class="processed">{{ row.processed || row.processed_images || 0 }}</span>
                  <span class="separator">/</span>
                  <span class="total">{{ row.total || row.total_images || 0 }}</span>
                </div>
                <div v-else class="no-stats">-</div>
              </div>
            </template>
          </el-table-column>

          <!-- 开始时间 -->
          <el-table-column label="开始时间" width="150">
              <template #default="{ row }">
                <div class="time-cell">
                  {{ formatDateTime(row.started_at) }}
                </div>
              </template>
            </el-table-column>

          <!-- 操作列 -->
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <div class="action-buttons">
                <!-- 取消按钮（仅处理中状态显示） -->
                <el-button
                  v-if="row.status === 'processing' || row.original_status === 'processing'"
                  size="small"
                  type="danger"
                  @click="$emit('cancel', row.job_id)"
                  class="action-btn"
                >
                  取消
                </el-button>

                <!-- 查看按钮 -->
                <el-button
                  v-if="row.status === 'completed' || row.original_status === 'completed'"
                  size="small"
                  type="success"
                  @click="$emit('view-result', row.job_id)"
                  class="action-btn"
                >
                  查看结果
                </el-button>

                <!-- 重新提交按钮（失败状态） -->
                <el-button
                  v-if="row.status === 'failed' || row.original_status === 'failed'"
                  size="small"
                  type="warning"
                  @click="$emit('retry', row.job_id)"
                  class="action-btn"
                >
                  重试
                </el-button>

                <!-- 详情按钮 -->
                <el-button
                  size="small"
                  type="text"
                  @click="$emit('view-detail', row)"
                  class="action-btn"
                >
                  详情
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 筛选和排序 -->
      <div class="task-filters">
        <el-select
          v-model="statusFilter"
          size="small"
          placeholder="筛选状态"
          clearable
          style="width: 120px; margin-right: 8px;"
        >
          <el-option label="全部状态" value="" />
          <el-option label="排队中" value="queued" />
          <el-option label="处理中" value="processing" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
        </el-select>

        <el-input
          v-model="searchKeyword"
          size="small"
          placeholder="搜索PDF文件名"
          prefix-icon="el-icon-search"
          clearable
          style="width: 200px;"
        />
      </div>
    </div>

    <!-- 底部操作栏 -->
    <div class="dialog-footer">
      <div class="footer-left">
        <el-button
          v-if="hasCompletedTasks"
          type="text"
          size="small"
          @click="clearCompletedTasks"
        >
          清空已完成任务
        </el-button>
      </div>
      <div class="footer-right">
        <el-button @click="$emit('close')">关闭</el-button>
        <el-button type="primary" @click="$emit('refresh')">刷新</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, onUnmounted } from 'vue'

const props = defineProps({
  tasks: {
    type: Array,
    default: () => []
  },
  summary: {
    type: Object,
    default: () => ({
      total: 0,
      processing: 0,
      completed: 0,
      failed: 0,
      queued: 0
    })
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'refresh',
  'cancel',
  'view-result',
  'retry',
  'view-detail',
  'clear-completed',
  'close'
])

// 本地状态
const statusFilter = ref('')
const searchKeyword = ref('')
const autoRefresh = ref(true)
let autoRefreshTimer = null

// 计算属性
const filteredTasks = computed(() => {
  let result = [...props.tasks]

  // 状态筛选
  if (statusFilter.value) {
    result = result.filter(task => {
      const status = task.status || task.original_status
      return status === statusFilter.value
    })
  }

  // 关键词搜索
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(task => {
      const filename = getPdfFilename(task).toLowerCase()
      return filename.includes(keyword) ||
             (task.job_id && task.job_id.toLowerCase().includes(keyword))
    })
  }

  return result
})

const hasCompletedTasks = computed(() => {
  return props.tasks.some(task =>
    task.status === 'completed' || task.original_status === 'completed'
  )
})

// 工具函数
const getPdfFilename = (task) => {
  if (task.filename) return task.filename
  if (task.pdfDiskName) {
    // 从pdfDiskName中提取文件名
    const parts = task.pdfDiskName.split('_')
    if (parts.length > 1) {
      return parts.slice(1).join('_') + '.pdf'
    }
    return task.pdfDiskName
  }
  return task.job_id || '未知文件'
}

const getStatusTagType = (task) => {
  const status = task.status || task.original_status
  switch (status) {
    case 'queued': return 'info'
    case 'processing': return 'warning'
    case 'completed':
    case 'success': return 'success'
    case 'failed':
    case 'exception': return 'danger'
    default: return 'info'
  }
}

const getStatusText = (task) => {
  const status = task.status || task.original_status
  const statusMap = {
    'queued': '排队中',
    'processing': '处理中',
    'completed': '已完成',
    'success': '已完成',
    'failed': '失败',
    'exception': '异常',
    'unknown': '未知'
  }
  return statusMap[status] || status
}

// 修改 getProgressPercentage 函数
const getProgressPercentage = (task) => {
  if (task.progress !== undefined) return task.progress
  if (task.percentage !== undefined) return task.percentage

  // ✅ 修复：从图片处理数量计算，包括跳过的图片
  if (task.processed_images !== undefined || task.skipped_images !== undefined || task.total_images !== undefined) {
    const processed = parseInt(task.processed_images) || 0
    const skipped = parseInt(task.skipped_images) || 0
    const total = parseInt(task.total_images) || (processed + skipped)

    if (total > 0) {
      // ✅ 已处理总数 = 新处理 + 跳过
      const totalProcessed = processed + skipped
      return Math.round((totalProcessed / total) * 100)
    }
  }

  return 0
}

// 修改图片处理统计显示逻辑
const imageStats = computed(() => {
  return (task) => {
    const processed = parseInt(task.processed_images) || 0
    const skipped = parseInt(task.skipped_images) || 0
    const total = parseInt(task.total_images) || (processed + skipped)

    // ✅ 正确显示：总处理数/总数
    if (total > 0) {
      return `${processed + skipped}/${total}`
    }
    return '-'
  }
})


const getProgressPercentage0000 = (task) => {
  if (task.progress !== undefined) return task.progress
  if (task.percentage !== undefined) return task.percentage

  // 从图片处理数量计算
  if (task.processed_images !== undefined && task.total_images !== undefined) {
    if (task.total_images > 0) {
      return Math.round((task.processed_images / task.total_images) * 100)
    }
  }

  return 0
}

const getProgressStatus = (task) => {
  const status = task.status || task.original_status
  if (status === 'processing') return ''
  if (status === 'completed' || status === 'success') return 'success'
  if (status === 'failed' || status === 'exception') return 'exception'
  return ''
}

const getProgressText = (task) => {
  const percent = getProgressPercentage(task)
  if (percent === 100) return '完成'
  return `${percent}%`
}

const getElapsedTime = (task) => {
  const startTime = task.timestamp || task.start_time
  if (!startTime) return ''

  const now = Date.now()
  const start = new Date(startTime).getTime()
  const elapsedMs = now - start

  if (elapsedMs < 60000) {
    return `${Math.floor(elapsedMs / 1000)}秒`
  } else if (elapsedMs < 3600000) {
    return `${Math.floor(elapsedMs / 60000)}分钟`
  } else {
    return `${Math.floor(elapsedMs / 3600000)}小时`
  }
}


// 智能格式化：根据时间远近决定显示格式
const formatDateTime = (timestamp) => {
  if (!timestamp) return '-'

  try {
    const date = new Date(timestamp)

    if (isNaN(date.getTime())) {
      return '无效时间'
    }

    if (date.getFullYear() === 1970 && date.getMonth() === 0 && date.getDate() === 1) {
      return '未记录'
    }

    const now = new Date()
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24))

    if (diffDays === 0) {
      // 今天：只显示时间
      return `今天 ${date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })}`
    } else if (diffDays === 1) {
      // 昨天
      return `昨天 ${date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })}`
    } else if (diffDays < 7) {
      // 一周内：显示星期几
      const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
      const weekday = weekdays[date.getDay()]
      return `${weekday} ${date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })}`
    } else if (date.getFullYear() === now.getFullYear()) {
      // 今年：显示月-日 时:分:秒
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    } else {
      // 跨年：显示完整的年月日
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    }
  } catch (e) {
    console.error('时间格式化错误:', e, timestamp)
    return '时间错误'
  }
}


// 截断文本函数
const truncateText = (text, length) => {
  if (!text) return ''
  if (text.length <= length) return text
  return text.substring(0, length) + '...'
}


// 自动刷新逻辑
const handleAutoRefreshToggle = () => {
  autoRefresh.value = !autoRefresh.value

  if (autoRefresh.value) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
}

const startAutoRefresh = () => {
  if (autoRefreshTimer) clearInterval(autoRefreshTimer)
  autoRefreshTimer = setInterval(() => {
    emit('refresh')
  }, 5000) // 5秒刷新一次
}

const stopAutoRefresh = () => {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
}

const clearCompletedTasks = () => {
  emit('clear-completed')
}

// 生命周期
onUnmounted(() => {
  stopAutoRefresh()
})

// 监听任务数据变化
watch(() => props.tasks, () => {
  if (autoRefresh.value && !autoRefreshTimer) {
    startAutoRefresh()
  }
}, { immediate: true })
</script>

<style scoped>
.progress-monitor-dialog {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 600px;
}

/* 统计摘要区域 */
.summary-section {
  margin-bottom: 20px;
}

.summary-title {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.summary-title i {
  margin-right: 8px;
  color: #409eff;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.summary-card {
  transition: all 0.2s;
  cursor: pointer;
}

.summary-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-content {
  display: flex;
  align-items: center;
  padding: 12px;
}

.card-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  font-size: 20px;
}

.card-info {
  flex: 1;
}

.card-value {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: 4px;
}

.card-label {
  font-size: 12px;
  color: #606266;
  white-space: nowrap;
}

/* 不同统计卡片的样式 */
.summary-card.total .card-icon {
  background: #f0f9ff;
  color: #409eff;
}

.summary-card.processing .card-icon {
  background: #fdf6ec;
  color: #e6a23c;
  animation: spin 2s linear infinite;
}

.summary-card.completed .card-icon {
  background: #f0f9eb;
  color: #67c23a;
}

.summary-card.queued .card-icon {
  background: #f4f4f5;
  color: #909399;
}

.summary-card.failed .card-icon {
  background: #fef0f0;
  color: #f56c6c;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 任务列表区域 */
.task-list-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.task-table-container {
  flex: 1;
  min-height: 0;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  overflow: hidden;
}

/* PDF信息单元格 */
.pdf-info-cell {
  display: flex;
  align-items: center;
}

.pdf-info-cell i {
  font-size: 20px;
  color: #409eff;
  margin-right: 8px;
  flex-shrink: 0;
}

.pdf-details {
  flex: 1;
  min-width: 0;
}

.pdf-filename {
  font-weight: 500;
  color: #303133;
  margin-bottom: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pdf-job-id {
  font-size: 11px;
  color: #909399;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
}

/* 状态标签 */
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.status-tag i {
  font-size: 12px;
  animation: spin 1.5s linear infinite;
}

/* 进度单元格 */
.progress-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-progress {
  flex: 1;
}

.progress-time {
  font-size: 11px;
  color: #909399;
  text-align: right;
}

/* 图片统计 */
.image-stats {
  text-align: center;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
}

.processed {
  color: #67c23a;
  font-weight: 600;
}

.separator {
  margin: 0 2px;
  color: #c0c4cc;
}

.total {
  color: #606266;
}

.no-stats {
  color: #c0c4cc;
  font-style: italic;
}

/* 时间单元格 */
.time-cell {
  font-size: 12px;
  color: #606266;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.action-btn {
  padding: 4px 8px;
  min-height: 24px;
}

/* 筛选区域 */
.task-filters {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}

/* 底部操作栏 */
.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

.footer-left {
  flex: 1;
}

.footer-right {
  display: flex;
  gap: 8px;
}

/* 响应式调整 */
@media (max-width: 1200px) {
  .summary-cards {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .summary-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
