<template>
  <div class="llm-settings">
    <div class="settings-header">
      <h1>大模型配置</h1>
      <p>配置表格识别所需的大模型参数</p>
    </div>

    <div class="settings-content">
      <el-card class="config-card">
        <template #header>
          <div class="card-header">
            <span>基础配置</span>
            <el-button
              type="primary"
              :loading="testing"
              @click="testConnection"
            >
              测试连接
            </el-button>
          </div>
        </template>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="120px"
        >
          <el-form-item
            label="基础URL"
            prop="base_url"
          >
            <el-input
              v-model="form.base_url"
              placeholder="例如: https://ark.cn-beijing.volces.com/api/v3"
            />
          </el-form-item>

          <el-form-item
            label="API密钥"
            prop="api_key"
          >
            <el-input
              v-model="form.api_key"
              type="password"
              placeholder="请输入API密钥"
              show-password
            />
          </el-form-item>

          <el-form-item
            label="模型"
            prop="model_id"
          >
            <el-select
              v-model="form.model_id"
              placeholder="请选择模型"
              style="width: 100%"
            >
              <el-option
                v-for="model in availableModels"
                :key="model.id"
                :label="model.name"
                :value="model.id"
              >
                <div class="model-option">
                  <div class="model-name">
                    {{ model.name }}
                  </div>
                  <div class="model-desc">
                    {{ model.description }}
                  </div>
                </div>
              </el-option>
            </el-select>
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              :loading="saving"
              size="large"
              @click="saveConfig"
            >
              保存配置
            </el-button>
            <el-button @click="goBack">
              返回
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 状态显示 -->
      <el-card
        v-if="currentStatus"
        class="status-card"
      >
        <template #header>
          <span>当前状态</span>
        </template>
        <div class="status-info">
          <div class="status-item">
            <span class="label">配置状态:</span>
            <el-tag :type="currentStatus.client_configured ? 'success' : 'danger'">
              {{ currentStatus.client_configured ? '已配置' : '未配置' }}
            </el-tag>
          </div>
          <div
            v-if="currentStatus.model_id"
            class="status-item"
          >
            <span class="label">当前模型:</span>
            <span>{{ currentStatus.model_id }}</span>
          </div>
          <div
            v-if="currentStatus.base_url"
            class="status-item"
          >
            <span class="label">服务地址:</span>
            <span>{{ currentStatus.base_url }}</span>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { llmApi } from '@/api/llm'

const router = useRouter()
const formRef = ref()
const testing = ref(false)
const saving = ref(false)
const currentStatus = ref(null)

// 表单数据
const form = reactive({
  base_url: '',
  api_key: '',
  model_id: ''
})

// 验证规则
const rules = {
  base_url: [
    { required: true, message: '请输入基础URL', trigger: 'blur' }
  ],
  api_key: [
    { required: true, message: '请输入API密钥', trigger: 'blur' }
  ],
  model_id: [
    { required: true, message: '请选择模型', trigger: 'change' }
  ]
}

// 可用模型
const availableModels = ref([
  {
    id: 'doubao-1-5-vision-pro-250328',
    name: '豆包视觉专业版',
    description: '支持视觉识别的专业模型'
  },
  {
    id: 'doubao-seed-1-6-vision-250815',
    name: '豆包视觉种子版',
    description: '视觉识别基础模型'
  },
  {
    id: 'gpt-4-vision-preview',
    name: 'GPT-4 Vision',
    description: 'OpenAI视觉模型'
  },
  {
    id: 'qwen-vl-plus',
    name: '通义千问VL',
    description: '阿里云视觉语言模型'
  }
])

// 加载当前状态
const loadCurrentStatus = async () => {
  try {
    const response = await llmApi.getStatus()
    if (response.success) {
      currentStatus.value = response.data
      // 如果已配置，填充表单
      if (response.data.client_configured) {
        form.base_url = response.data.base_url || ''
        form.model_id = response.data.model_id || ''
      }
    }
  } catch (error) {
    console.error('加载状态失败:', error)
  }
}

// 测试连接
const testConnection = async () => {
  if (!form.base_url || !form.api_key || !form.model_id) {
    ElMessage.warning('请先填写完整的配置信息')
    return
  }

  try {
    testing.value = true
    const response = await llmApi.testConnection({
      base_url: form.base_url,
      api_key: form.api_key,
      model_id: form.model_id
    })

    if (response.success) {
      ElMessage.success('连接测试成功！')
    } else {
      ElMessage.error(`连接测试失败: ${response.error}`)
    }
  } catch (error) {
    ElMessage.error(`测试异常: ${error.message}`)
  } finally {
    testing.value = false
  }
}

// 保存配置
const saveConfig = async () => {
  try {
    await formRef.value.validate()
    saving.value = true

    const response = await llmApi.configure({
      base_url: form.base_url,
      api_key: form.api_key,
      model_id: form.model_id
    })

    if (response.success) {
      ElMessage.success('配置保存成功！')
      await loadCurrentStatus() // 重新加载状态
    } else {
      ElMessage.error(`保存失败: ${response.error}`)
    }
  } catch (error) {
    if (error.errors) {
      ElMessage.warning('请完善配置信息')
    } else {
      ElMessage.error(`保存异常: ${error.message}`)
    }
  } finally {
    saving.value = false
  }
}

// 返回
const goBack = () => {
  router.back()
}

onMounted(() => {
  loadCurrentStatus()
})
</script>

<style scoped>
.llm-settings {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.settings-header {
  text-align: center;
  margin-bottom: 30px;
}

.settings-header h1 {
  color: #303133;
  margin-bottom: 10px;
}

.settings-header p {
  color: #606266;
}

.config-card, .status-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.model-option {
  line-height: 1.4;
}

.model-name {
  font-weight: 500;
}

.model-desc {
  font-size: 12px;
  color: #909399;
}

.status-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-item .label {
  font-weight: 500;
  min-width: 80px;
}
</style>