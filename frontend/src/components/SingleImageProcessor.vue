<template>
  <div class="single-processor">
    <a-alert
      v-if="!llmConfigured"
      message="LLM未配置"
      description="请先配置LLM参数后再进行表格识别"
      type="warning"
      show-icon
      class="alert-warning"
    />

    <a-form :model="form" layout="vertical">
      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item label="图片路径">
            <a-input
              v-model:value="form.image_path"
              placeholder="请输入图片文件路径"
              :disabled="processing"
            >
              <template #addonAfter>
                <a-button type="link" @click="handleSelectImage">
                  选择文件
                </a-button>
              </template>
            </a-input>
          </a-form-item>
        </a-col>

        <a-col :span="12">
          <a-form-item label="输出路径">
            <a-input
              v-model:value="form.output_path"
              placeholder="请输入输出Excel文件路径"
              :disabled="processing"
            />
          </a-form-item>
        </a-col>
      </a-row>

      <a-row :gutter="16">
        <a-col :span="8">
          <a-form-item label="工作表名称">
            <a-input
              v-model:value="form.sheet_name"
              placeholder="识别结果"
              :disabled="processing"
            />
          </a-form-item>
        </a-col>

        <a-col :span="8">
          <a-form-item label="银行名称">
            <a-input
              v-model:value="form.bank_name"
              placeholder="未知银行"
              :disabled="processing"
            />
          </a-form-item>
        </a-col>

        <a-col :span="8">
          <a-form-item label="自定义提示词">
            <a-button type="link" @click="showCustomPrompt = true">
              设置自定义提示词
            </a-button>
          </a-form-item>
        </a-col>
      </a-row>

      <a-form-item>
        <a-button
          type="primary"
          @click="handleProcess"
          :loading="processing"
          :disabled="!llmConfigured"
        >
          开始识别
        </a-button>

        <a-button @click="handleReset" style="margin-left: 8px;">
          重置
        </a-button>
      </a-form-item>
    </a-form>

    <!-- 进度显示 -->
    <a-card v-if="processing || result" title="处理结果" class="result-card">
      <a-progress
        v-if="processing"
        :percent="progressPercent"
        :status="progressStatus"
      />

      <div v-if="result" class="result-content">
        <a-alert
          :message="resultMessage"
          :type="resultType"
          show-icon
        />

        <a-descriptions v-if="result.success" bordered size="small">
          <a-descriptions-item label="处理状态">成功</a-descriptions-item>
          <a-descriptions-item label="表格复杂度">
            {{ result.data.complexity }}
          </a-descriptions-item>
          <a-descriptions-item label="处理模式">
            {{ result.data.mode }}
          </a-descriptions-item>
          <a-descriptions-item label="表格名称">
            {{ result.data.table_name }}
          </a-descriptions-item>
          <a-descriptions-item label="数据行数">
            {{ result.data.data_rows }}
          </a-descriptions-item>
          <a-descriptions-item label="输出路径">
            <a :href="`file:///${result.data.output_path}`" target="_blank">
              {{ result.data.output_path }}
            </a>
          </a-descriptions-item>
        </a-descriptions>
      </div>
    </a-card>

    <!-- 自定义提示词模态框 -->
    <a-modal
      v-model:visible="showCustomPrompt"
      title="自定义提示词"
      @ok="handleCustomPromptOk"
      @cancel="showCustomPrompt = false"
    >
      <a-textarea
        v-model:value="form.custom_prompt"
        placeholder="请输入自定义处理提示词（可选）"
        :rows="6"
      />
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { llmApi } from '@/api/llm'

const processing = ref(false)
const progressPercent = ref(0)
const progressStatus = ref('active')
const showCustomPrompt = ref(false)
const llmConfigured = ref(false)
const result = ref(null)

// 表单数据
const form = reactive({
  image_path: '',
  output_path: '',
  sheet_name: '识别结果',
  bank_name: '未知银行',
  custom_prompt: ''
})

// 计算结果消息
const resultMessage = computed(() => {
  if (!result.value) return ''
  return result.value.success ? '表格识别成功！' : `识别失败: ${result.value.error}`
})

const resultType = computed(() => {
  if (!result.value) return 'info'
  return result.value.success ? 'success' : 'error'
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

// 处理图片
const handleProcess = async () => {
  try {
    processing.value = true
    progressPercent.value = 10
    result.value = null

    const response = await llmApi.processImage(form)

    if (response.success) {
      result.value = response
      progressPercent.value = 100
      progressStatus.value = 'success'
      message.success('表格识别完成！')
    } else {
      result.value = response
      progressStatus.value = 'exception'
      message.error(`识别失败: ${response.error}`)
    }
  } catch (error) {
    message.error('处理异常')
    progressStatus.value = 'exception'
  } finally {
    processing.value = false
  }
}

// 重置表单
const handleReset = () => {
  Object.keys(form).forEach(key => {
    if (key !== 'sheet_name' && key !== 'bank_name') {
      form[key] = ''
    }
  })
  result.value = null
  progressPercent.value = 0
  progressStatus.value = 'active'
}

// 选择图片文件
const handleSelectImage = () => {
  // 这里可以实现文件选择对话框
  message.info('文件选择功能待实现')
}

// 自定义提示词确认
const handleCustomPromptOk = () => {
  showCustomPrompt.value = false
  message.success('自定义提示词已设置')
}

onMounted(() => {
  checkLLMStatus()
})
</script>

<style scoped>
.single-processor {
  max-width: 1000px;
}

.alert-warning {
  margin-bottom: 20px;
}

.result-card {
  margin-top: 20px;
}

.result-content {
  margin-top: 16px;
}
</style>