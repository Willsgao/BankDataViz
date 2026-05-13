<template>
  <div class="deepseek-panel">
    <!-- 配置区 -->
    <div class="config-section">
      <div class="section-title">
        DeepSeek 配置
      </div>
      <div class="config-row">
        <span class="config-label">Chrome Profile</span>
        <el-input
          v-model="chromeUserDataDir"
          size="small"
          placeholder="留空使用当前浏览器"
          style="flex:1"
        />
      </div>
      <div class="config-row">
        <span class="config-label">提示词</span>
        <el-input
          v-model="prompt"
          size="small"
          type="textarea"
          :rows="2"
          placeholder="发送给 DeepSeek 的提示词"
          style="flex:1"
        />
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="action-bar">
      <el-button
        type="primary"
        :loading="status === 'running'"
        :disabled="!canStart"
        @click="onStart"
      >
        <el-icon v-if="status !== 'running'">
          <MagicStick />
        </el-icon>
        {{ status === 'running' ? `正在识别 (${currentIndex}/${totalRegions})` : '发送到 DeepSeek' }}
      </el-button>
      <el-button
        v-if="status === 'running'"
        type="danger"
        size="small"
        @click="onCancel"
      >
        取消
      </el-button>
      <el-button
        v-if="status === 'done'"
        size="small"
        @click="onReset"
      >
        重置
      </el-button>
    </div>

    <!-- 进度指示 -->
    <div
      v-if="status === 'running'"
      class="progress-section"
    >
      <el-progress
        :percentage="progressPercent"
        :format="progressFormat"
        :stroke-width="10"
      />
      <div class="current-task">
        <span class="task-label">当前处理：</span>
        <span class="task-name">{{ currentRegionName }}</span>
      </div>
    </div>

    <!-- 汇总统计 -->
    <div
      v-if="results.length > 0"
      class="stats-bar"
    >
      <el-tag
        type="success"
        effect="plain"
      >
        成功 {{ successCount }} 个
      </el-tag>
      <el-tag
        v-if="failedCount > 0"
        type="danger"
        effect="plain"
      >
        失败 {{ failedCount }} 个
      </el-tag>
      <el-tag
        type="info"
        effect="plain"
      >
        共 {{ results.length }} 个
      </el-tag>
    </div>

    <!-- 结果列表 -->
    <div class="results-area">
      <div
        v-if="results.length === 0 && status === 'idle'"
        class="results-empty"
      >
        <el-icon
          :size="40"
          color="#c0c4cc"
        >
          <Document />
        </el-icon>
        <p>暂无识别结果</p>
        <p class="empty-hint">
          上传文件并确认选区后，点击「发送到 DeepSeek」
        </p>
      </div>

      <div
        v-else
        class="results-list"
      >
        <div
          v-for="item in results"
          :key="item.id"
          class="result-card"
          :class="{
            'result-success': item.success,
            'result-error': !item.success,
          }"
        >
          <div class="result-header">
            <span class="result-label">{{ item.label }}</span>
            <el-tag
              :type="item.success ? 'success' : 'danger'"
              size="small"
              effect="plain"
            >
              {{ item.success ? '成功' : '失败' }}
            </el-tag>
          </div>

          <!-- 缩略图 -->
          <img
            v-if="item.thumbnail"
            :src="item.thumbnail"
            class="result-thumb"
          >

          <!-- 结果内容 -->
          <div
            v-if="item.success && item.result"
            class="result-content"
          >
            <pre class="result-text">{{ item.result }}</pre>
          </div>
          <div
            v-else-if="!item.success && item.error"
            class="result-error-msg"
          >
            {{ item.error }}
          </div>
          <div
            v-else-if="status === 'running' && item.id === currentRegionId"
            class="result-loading"
          >
            <el-icon class="is-loading">
              <Loading />
            </el-icon>
            识别中...
          </div>
        </div>
      </div>
    </div>

    <!-- 确认保存 -->
    <div
      v-if="status === 'done' && successCount > 0"
      class="confirm-section"
    >
      <el-divider />
      <div class="confirm-tip">
        确认以上结果无误后，点击「保存 Excel」保存全部结果
      </div>
      <el-button
        type="success"
        @click="onConfirm"
      >
        <el-icon><DocumentChecked /></el-icon>
        确认结果 → 保存 Excel
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import {
  MagicStick, Document, Loading, DocumentChecked, CircleCheckFilled
} from '@element-plus/icons-vue'

const props = defineProps({
  status: {
    type: String,
    default: 'idle', // 'idle' | 'running' | 'done' | 'error'
  },
  regions: {
    type: Array,
    default: () => [], // [{ id, label, image_base64, thumbnail }]
  },
  results: {
    type: Array,
    default: () => [], // [{ id, label, success, result, error, thumbnail }]
  },
  currentRegionId: { type: String, default: '' },
  currentRegionName: { type: String, default: '' },
  totalRegions: { type: Number, default: 0 },
})

const emit = defineEmits(['start', 'cancel', 'reset', 'confirm'])

// ---- 配置 ----
const chromeUserDataDir = ref('')
const prompt = ref(`请仔细分析这张图片，识别其中包含的所有表格。

**如果图片中包含表格：**
- 将所有表格内容转换为Markdown格式输出
- 严格保持原表格的行列结构
- **多级表头处理规则（非常重要）：**
  - 如果表头包含多个层级（如"年份→季度"、"大分类→小分类"），必须为每一层单独建立表头行
  - 上层合并单元格的类别名需要跨列标记，下层保持独立列名
  - 示例正确格式：
    |  | 2024年 | 2024年 | 2024年 | 2024年 | 2023年 | 2023年 | 2023年 | 2023年 |
    |  | 第一季度 | 第二季度 | 第三季度 | 第四季度 | 第一季度 | 第二季度 | 第三季度 | 第四季度 |
- 遇到合并单元格时，在对应位置保留原内容，相邻单元格留空
- 空值单元格用"-"占位，不要遗漏任何数据
- 每个表格独立输出，并用序号标注（如"表格1"、"表格2"）
- 最后统计并输出："该图片共包含 X 个表格，总计 Y 行数据"

**如果图片中不包含任何表格：**
- 直接描述图片的完整内容，不强行构造表格
- 开头明确标注："该图片不包含表格，内容描述如下："

请开始识别。`)

// ---- 计算属性 ----
const currentIndex = computed(() => {
  if (!props.currentRegionId) return 0
  const idx = props.regions.findIndex(r => r.id === props.currentRegionId)
  return idx >= 0 ? idx + 1 : 0
})

const progressPercent = computed(() => {
  if (props.totalRegions === 0) return 0
  return Math.round((currentIndex.value / props.totalRegions) * 100)
})

const progressFormat = computed(() => {
  return () => `${currentIndex.value} / ${props.totalRegions}`
})

const canStart = computed(() => {
  return props.regions.length > 0 && props.status !== 'running'
})

const successCount = computed(() => props.results.filter(r => r.success).length)
const failedCount = computed(() => props.results.filter(r => !r.success).length)

// ---- 事件 ----
function onStart() {
  emit('start', {
    prompt: prompt.value,
    user_data_dir: chromeUserDataDir.value,
  })
}

function onCancel() {
  emit('cancel')
}

function onReset() {
  emit('reset')
}

function onConfirm() {
  emit('confirm', props.results.filter(r => r.success))
}

// ---- 暴露配置供父组件使用 ----
defineExpose({
  prompt,
  chromeUserDataDir,
})
</script>

<style scoped>
.deepseek-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
  overflow: hidden;
}

/* 配置区 */
.config-section {
  flex-shrink: 0;
  background: #f0f2f5;
  border-radius: 6px;
  padding: 10px 12px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.config-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 6px;
}

.config-row:last-child {
  margin-bottom: 0;
}

.config-label {
  font-size: 12px;
  color: #606266;
  flex-shrink: 0;
  width: 60px;
  padding-top: 4px;
}

/* 操作按钮 */
.action-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* 进度 */
.progress-section {
  flex-shrink: 0;
}

.current-task {
  display: flex;
  gap: 6px;
  font-size: 12px;
  margin-top: 4px;
}

.task-label {
  color: #909399;
}

.task-name {
  color: #303133;
  font-weight: 500;
}

/* 统计 */
.stats-bar {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* 结果区 */
.results-area {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.results-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 8px;
  color: #909399;
  text-align: center;
  padding: 40px;
}

.empty-hint {
  font-size: 12px;
  color: #c0c4cc;
  margin: 0;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 结果卡片 */
.result-card {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
  background: white;
}

.result-card.result-success {
  border-left: 3px solid #67c23a;
}

.result-card.result-error {
  border-left: 3px solid #f56c6c;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
}

.result-label {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
}

.result-thumb {
  width: 100%;
  max-height: 80px;
  object-fit: cover;
  display: block;
  border-bottom: 1px solid #f0f0f0;
}

.result-content {
  padding: 8px 10px;
  max-height: 200px;
  overflow-y: auto;
}

.result-text {
  margin: 0;
  font-size: 12px;
  color: #303133;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  line-height: 1.6;
}

.result-error-msg {
  padding: 8px 10px;
  font-size: 12px;
  color: #f56c6c;
}

.result-loading {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px;
  font-size: 12px;
  color: #909399;
}

/* 确认保存 */
.confirm-section {
  flex-shrink: 0;
}

.confirm-tip {
  font-size: 12px;
  color: #909399;
  text-align: center;
  margin-bottom: 8px;
}
</style>
