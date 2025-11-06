<template>
  <div class="batch-processor">
    <a-alert
      v-if="!llmConfigured"
      message="LLM未配置"
      description="请先配置LLM参数后再进行批量处理"
      type="warning"
      show-icon
      class="alert-warning"
    />

    <a-form :model="form" layout="vertical">
      <a-form-item label="图片路径列表">
        <a-textarea
          v-model:value="form.image_paths_text"
          placeholder="每行输入一个图片文件路径"
          :rows="6"
          :disabled="processing"
        />
        <div class="tip-text">提示：每行输入一个完整的图片文件路径</div>
      </a-form-item>

      <a-form-item label="输出目录">
        <a-input
          v-model:value="form.output_dir"
          placeholder="请输入输出目录路径"
          :disabled="processing"
        />
      </a-form-item>

      <a-form-item label="银行名称">
        <a-input
          v-model:value="form.bank_name"
          placeholder="未知银行"
          :disabled="processing"
        />
      </a-form-item>

      <a-form-item>
        <a-button
          type="primary"
          @click="handleBatchProcess"
          :loading="processing"
          :disabled="!llmConfigured"
        >
          开始批量处理
        </a-button>

        <a-button @click="handleReset" style="margin-left: 8px;">
          重置
        </a-button>
      </a-form-item>
    </a-form>

    <!-- 批量处理结果 -->
    <a-card v-if="processing || batchResult" title="批量处理结果" class="result-card">
      <a-progress
        v-if="processing"
        :percent="progressPercent"
        status="active"
      />

      <div v-if="batchResult" class="batch-result">
        <a-alert
          :message="batchResultMessage"
          :type="batchResultType"
          show-icon
        />

        <a-descriptions v-if="batchResult.success" bordered size="small">
          <a-descriptions-item label="总处理数">
            {{ batchResult.data.total }}
          </a-descriptions-item>
          <a-descriptions-item label="成功数">
            <span style="color: #52c41a">{{ batchResult.data.success }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="跳过数">
            <span style="color: #faad14">{{ batchResult.data.skipped }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="失败数">
            <span style="color: #ff4d4f">{{ batchResult.data.failed }}</span>
          </a-descriptions-item>
        </a-descriptions>

        <!-- 详细结果表格 -->
        <a-table
          v-if="batchResult.data.details"
          :dataSource="batchResult.data.details"
          :columns="detailColumns"
          size="small"
          class="detail-table"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'">
              <a-tag :color="getStatusColor(record.status)">
                {{ getStatusText(record.status) }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'complexity'">
              {{ record.complexity || '-' }}
            </template>
          </template>
        </a-table>
      </div>
    </a-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { llmApi } from '@/api/llm'

const processing = ref(false)
const progressPercent = ref(0)
const llmConfigured = ref(false)
const batchResult = ref(null)

// 表单数据
const form = reactive({
  image_paths_text: '',
  output_dir: '',
  bank_name: '未知银行'
})

// 表格列定义
const detailColumns = [
  {
    title: '图片路径',
    dataIndex: 'image_path',
    key: 'image_path',
    ellipsis: true
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    width: 100
  },
  {
    title: '复杂度',
    dataIndex: 'complexity',
    key: 'complexity',
    width: 120
  },
  {
    title: '输出路径',
    dataIndex: 'output_path',
    key: 'output_path',
    ellipsis: true
  }
]

// 计算结果消息
const batchResultMessage = computed(() => {
  if (!batchResult.value) return ''
  return batchResult.value.success ? '批量处理完成！' : `批量处理失败: ${batchResult.value.error}`
})

const batchResultType = computed(() => {
  if (!batchResult.value) return 'info'
  return batchResult.value.success ? 'success' : 'error'
})

// 检查LLM配置状态
const checkLLMStatus = async () => {
  try {
    const response = await llmApi.getStatus()
    if (response.success) {
      llmConfigured.value = response.data.client_configured
    }
  } catch (error) {
    console.error('检查LLM状态失败:', error)
  }
}

// 批量处理
const handleBatchProcess = async () => {
  try {
    processing.value = true
    progressPercent.value = 10
    batchResult.value = null

    // 转换图片路径文本为数组
    const image_paths = form.image_paths_text
      .split('\n')
      .map(path => path.trim())
      .filter(path => path.length > 0)

    if (image_paths.length === 0) {
      message.error('请至少输入一个图片路径')
      return
    }

    const params = {
      image_paths,
      output_dir: form.output_dir,
      bank_name: form.bank_name
    }

    const response = await llmApi.batchProcess(params)

    if (response.success) {
      batchResult.value = response
      progressPercent.value = 100
      message.success('批量处理完成！')
    } else {
      batchResult.value = response
      message.error(`批量处理失败: ${response.error}`)
    }
  } catch (error) {
    message.error('批量处理异常')
  } finally {
    processing.value = false
  }
}

// 重置表单
const handleReset = () => {
  form.image_paths_text = ''
  form.output_dir = ''
  form.bank_name = '未知银行'
  batchResult.value = null
  progressPercent.value = 0
}

// 获取状态颜色
const getStatusColor = (status) => {
  const colors = {
    success: 'green',
    error: 'red',
    skip: 'orange'
  }
  return colors[status] || 'default'
}

// 获取状态文本
const getStatusText = (status) => {
  const texts = {
    success: '成功',
    error: '失败',
    skip: '跳过'
  }
  return texts[status] || status
}

onMounted(() => {
  checkLLMStatus()
})
</script>

<style scoped>
.batch-processor {
  max-width: 1200px;
}

.alert-warning {
  margin-bottom: 20px;
}

.tip-text {
  color: #999;
  font-size: 12px;
  margin-top: 4px;
}

.result-card {
  margin-top: 20px;
}

.batch-result {
  margin-top: 16px;
}

.detail-table {
  margin-top: 16px;
}
</style>