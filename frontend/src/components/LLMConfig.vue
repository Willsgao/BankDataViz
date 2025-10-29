<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'
import { llmApi } from '@/api/llm'

const visible = ref(false)
const testing = ref(false)
const saving = ref(false)
const formRef = ref()
const testResult = ref(null)
const configMode = ref('default') // 'default' 或 'custom'
const activeCollapse = ref([])

// 默认配置值
const defaultConfig = reactive({
  base_url: 'https://ark.cn-beijing.volces.com/api/v3',
  model_id: 'doubao-1-5-vision-pro-250328',
  // 注意：API密钥不能设置真实的默认值，但可以提供示例格式
  api_key_example: 'your-api-key-here'
})

// 当前配置状态
const currentConfig = reactive({
  base_url: '',
  model_id: '',
  prompts_configured: {}
})

// 可用模型列表
const availableModels = ref([
  {
    id: 'doubao-1-5-vision-pro-250328',
    name: '豆包视觉专业版',
    description: '支持视觉识别的专业模型（推荐）'
  },
  {
    id: 'doubao-seed-1-6-vision-250815',
    name: '豆包视觉种子版',
    description: '视觉识别基础模型'
  }
])

// 在 data 部分添加
const tableType = ref('financial') // 默认金融表格

// 在表单数据中添加表格类型
const form = reactive({
  base_url: '',
  api_key: '',
  model_id: '',
  table_type: 'financial', // 新增：表格类型
  prompts: {
    assessment: '',
    simple: '',
    standard: '',
    complex: ''
  }
})


// 计算属性
const canTestConnection = computed(() => {
  if (configMode.value === 'default') {
    return defaultConfig.base_url && form.api_key && defaultConfig.model_id
  } else {
    return form.base_url && form.api_key && form.model_id
  }
})

// 表单验证规则
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

// 打开配置对话框
const open = () => {
  visible.value = true
  loadCurrentConfig()
}

// 配置模式改变
const onConfigModeChange = (mode) => {
  if (mode === 'default') {
    // 使用默认配置时，自动填充默认值但不允许编辑
    form.base_url = defaultConfig.base_url
    form.model_id = defaultConfig.model_id
    // API密钥不自动填充，但显示示例
    resetToDefaultPrompts()
  } else {
    // 自定义配置时，清空表单让用户输入
    if (!form.base_url) form.base_url = ''
    if (!form.model_id) form.model_id = ''
  }
}

// 加载当前配置状态
const loadCurrentConfig = async () => {
  try {
    const response = await llmApi.getStatus()
    if (response.data && response.data.success) {
      const data = response.data.data

      // 更新当前配置显示
      currentConfig.base_url = data.base_url || ''
      currentConfig.model_id = data.model_id || ''
      currentConfig.prompts_configured = data.prompts_configured || {}

      // 如果已有配置，判断是默认配置还是自定义配置
      if (data.client_configured) {
        const isUsingDefaultConfig =
          data.base_url === defaultConfig.base_url &&
          data.model_id === defaultConfig.model_id

        configMode.value = isUsingDefaultConfig ? 'default' : 'custom'

        if (isUsingDefaultConfig) {
          form.base_url = defaultConfig.base_url
          form.model_id = defaultConfig.model_id
        } else {
          form.base_url = data.base_url || ''
          form.model_id = data.model_id || ''
        }
      } else {
        // 没有配置时，默认使用默认配置模式
        configMode.value = 'default'
        form.base_url = defaultConfig.base_url
        form.model_id = defaultConfig.model_id
      }
    }
  } catch (error) {
    console.error('加载配置状态失败:', error)
  }
}

// 填充示例API密钥（仅用于演示）
const fillExampleApiKey = () => {
  if (configMode.value === 'default') {
    ElMessage.info('请填写您真实的API密钥')
  } else {
    // 在自定义模式下，可以填充示例格式
    form.api_key = defaultConfig.api_key_example
    ElMessage.info('已填充示例格式，请替换为您的真实API密钥')
  }
}

// 重置提示词为空（使用后端默认）
const resetToDefaultPrompts = () => {
  form.prompts = {
    assessment: '',
    simple: '',
    standard: '',
    complex: ''
  }
}


// 修改网络检查方法，避免401错误
const checkNetworkStatus = async () => {
  try {
    const testUrl = form.base_url || defaultConfig.base_url
    console.log('🌐 测试网络连接到:', testUrl)

    // 使用更简单的网络检查，避免API验证
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 5000) // 5秒超时

    try {
      // 尝试连接，但不验证响应状态
      await fetch(testUrl, {
        method: 'HEAD',
        mode: 'no-cors',
        signal: controller.signal
      })
      clearTimeout(timeoutId)
      return true
    } catch (error) {
      clearTimeout(timeoutId)
      // 即使是401错误也说明网络是通的
      if (error.name === 'AbortError') {
        console.log('🌐 网络连接超时')
        return false
      }
      // 其他错误（包括401）都认为网络是通的
      console.log('🌐 网络连接测试完成（可能有认证错误，但网络通畅）')
      return true
    }
  } catch (error) {
    console.log('🌐 网络连接测试异常:', error)
    return false
  }
}



// 修改测试连接方法
const testConnection = async () => {
  try {
    testing.value = true
    testResult.value = null

    const testData = {
      api_key: form.api_key,
      model_id: configMode.value === 'default' ? defaultConfig.model_id : form.model_id,
      base_url: configMode.value === 'default' ? defaultConfig.base_url : form.base_url
    }

    console.log('🔧 测试连接详细参数:', testData)

    // 基础验证
    if (!testData.api_key || testData.api_key === defaultConfig.api_key_example) {
      ElMessage.warning('请填写有效的API密钥')
      testing.value = false
      return
    }

    if (!testData.base_url) {
      ElMessage.warning('请填写基础URL')
      testing.value = false
      return
    }

    // 检查网络连接
    ElMessage.info('正在测试网络连接...')
    const networkOk = await checkNetworkStatus()
    if (!networkOk) {
      ElMessage.warning('网络连接异常，请检查网络设置')
    }

    // 进行API测试
    ElMessage.info('正在测试API连接...')
    const response = await llmApi.testConnection(testData)

    if (response.success) {
      testResult.value = {
        success: true,
        message: '连接测试成功！'
      }
      ElMessage.success('🎉 连接测试成功！')
    } else {
      testResult.value = {
        success: false,
        message: response.error || '连接测试失败'
      }
      ElMessage.error(`❌ 连接测试失败: ${response.error}`)
    }
  } catch (error) {
    console.error('❌ 测试连接异常:', error)
    testResult.value = {
      success: false,
      message: `测试异常: ${error.message}`
    }
    ElMessage.error(`💥 连接测试异常: ${error.message}`)
  } finally {
    testing.value = false
  }
}

// 修复保存配置方法
const saveConfig = async () => {
  try {
    // 如果是自定义模式，需要验证表单
    if (configMode.value === 'custom') {
      try {
        await formRef.value.validate()
      } catch (validationError) {
        console.log('❌ 表单验证失败:', validationError)
        ElMessage.warning('请完善配置信息')
        return
      }
    }

    // 检查API密钥是否是示例值
    if (form.api_key === defaultConfig.api_key_example || !form.api_key) {
      ElMessage.warning('请使用真实的API密钥，不要使用示例值')
      return
    }

    saving.value = true

    // 构建配置数据
    const configData = {
      api_key: form.api_key,
      base_url: configMode.value === 'default' ? defaultConfig.base_url : form.base_url,
      model_id: configMode.value === 'default' ? defaultConfig.model_id : form.model_id,
      table_type: form.table_type || 'financial'
    }

    console.log('💾 保存配置数据:', {
      ...configData,
      api_key: '***' // 不打印真实的API密钥
    })

    // 只有在自定义模式下且用户输入了提示词时才发送提示词
    if (configMode.value === 'custom') {
      const nonEmptyPrompts = {}
      Object.keys(form.prompts).forEach(key => {
        if (form.prompts[key] && form.prompts[key].trim() !== '') {
          nonEmptyPrompts[key] = form.prompts[key].trim()
        }
      })

      if (Object.keys(nonEmptyPrompts).length > 0) {
        configData.prompts = nonEmptyPrompts
      }
    }

    // 调用配置API
    const response = await llmApi.configure(configData)
    console.log('🔧 配置API响应:', response)

    if (response && response.success) {
      ElMessage.success(`🎉 配置保存成功！（${configMode.value === 'default' ? '默认配置' : '自定义配置'}）`)
      visible.value = false
      emit('configured')

      // 重新加载状态
      await loadCurrentConfig()
    } else {
      const errorMsg = response?.error || response?.message || '未知错误'
      console.error('❌ 配置保存失败:', errorMsg)
      ElMessage.error(`配置保存失败: ${errorMsg}`)
    }

  } catch (error) {
    console.error('💥 配置保存异常:', error)
    if (error.errors) {
      ElMessage.warning('请完善配置信息')
    } else {
      ElMessage.error(`配置保存异常: ${error.message}`)
    }
  } finally {
    saving.value = false
  }
}



// 关闭对话框
const handleClose = () => {
  visible.value = false
  resetForm()
  testResult.value = null
  configMode.value = 'default'
}

// 重置表单
const resetForm = () => {
  form.base_url = ''
  form.api_key = ''
  form.model_id = ''
  resetToDefaultPrompts()
}

// 暴露方法给父组件
defineExpose({ open })

const emit = defineEmits(['configured'])
</script>

<template>
  <div class="llm-config">
    <el-dialog
      v-model="visible"
      title="LLM 大模型配置"
      width="700px"
      :before-close="handleClose"
    >
      <!-- 配置模式选择 -->
      <div class="config-mode">
        <el-radio-group v-model="configMode" @change="onConfigModeChange">
          <el-radio-button label="default">使用默认配置</el-radio-button>
          <el-radio-button label="custom">自定义配置</el-radio-button>
        </el-radio-group>
      </div>

      <el-form :model="form" label-width="120px" :rules="rules" ref="formRef" :disabled="configMode === 'default'">
        <el-form-item label="基础URL" prop="base_url">
          <el-input
            v-model="form.base_url"
            placeholder="请输入LLM API基础URL"
          />
          <div class="config-hint" v-if="configMode === 'default'">
            <el-icon><InfoFilled /></el-icon>
            使用默认配置: {{ defaultConfig.base_url }}
          </div>
        </el-form-item>

        <el-form-item label="API密钥" prop="api_key">
          <div class="api-key-input">
            <el-input
              v-model="form.api_key"
              type="password"
              placeholder="请输入API密钥"
              show-password
            />
            <el-button
              type="text"
              @click="fillExampleApiKey"
              class="example-btn"
              v-if="configMode === 'custom' && !form.api_key"
            >
              示例格式
            </el-button>
          </div>
          <div class="config-hint">
            <el-icon><InfoFilled /></el-icon>
            <span v-if="configMode === 'default'">使用默认配置（需要您填写API密钥）</span>
            <span v-else>请填写您的真实API密钥</span>
            <span class="example-format" v-if="configMode === 'custom'">示例: {{ defaultConfig.api_key_example }}</span>
          </div>
        </el-form-item>

        <el-form-item label="模型ID" prop="model_id">
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
              <span style="float: left">{{ model.name }}</span>
              <span style="float: right; color: #8492a6; font-size: 13px">
                {{ model.description }}
              </span>
            </el-option>
          </el-select>
          <div class="config-hint" v-if="configMode === 'default'">
            <el-icon><InfoFilled /></el-icon>
            使用默认配置: {{ defaultConfig.model_id }}
          </div>
        </el-form-item>

        <!-- 测试连接区域 -->
        <el-form-item>
          <el-button
            type="primary"
            @click="testConnection"
            :loading="testing"
            :disabled="!canTestConnection"
          >
            测试连接
          </el-button>
          <span v-if="testResult" :class="testResult.success ? 'success-text' : 'error-text'">
            {{ testResult.message }}
          </span>
        </el-form-item>

        <!-- 提示词配置 -->
        <el-collapse v-model="activeCollapse">
          <el-collapse-item title="高级配置（提示词）" name="prompts">
            <div class="prompts-header">
              <span>提示词配置</span>
              <el-button type="text" @click="resetToDefaultPrompts" size="small" :disabled="configMode === 'default'">
                重置为默认提示词
              </el-button>
            </div>

            <el-form-item label="评估提示词">
              <el-input
                v-model="form.prompts.assessment"
                type="textarea"
                :rows="3"
                placeholder="留空使用默认提示词"
                show-word-limit
                maxlength="2000"
                :disabled="configMode === 'default'"
              />
            </el-form-item>
            <el-form-item label="简单表格提示词">
              <el-input
                v-model="form.prompts.simple"
                type="textarea"
                :rows="3"
                placeholder="留空使用默认提示词"
                show-word-limit
                maxlength="2000"
                :disabled="configMode === 'default'"
              />
            </el-form-item>
            <el-form-item label="标准表格提示词">
              <el-input
                v-model="form.prompts.standard"
                type="textarea"
                :rows="3"
                placeholder="留空使用默认提示词"
                show-word-limit
                maxlength="2000"
                :disabled="configMode === 'default'"
              />
            </el-form-item>
            <el-form-item label="复杂表格提示词">
              <el-input
                v-model="form.prompts.complex"
                type="textarea"
                :rows="3"
                placeholder="留空使用默认提示词"
                show-word-limit
                maxlength="2000"
                :disabled="configMode === 'default'"
              />
            </el-form-item>
          </el-collapse-item>
        </el-collapse>
      </el-form>

      <template #footer>
        <div class="footer-actions">
          <div class="config-summary">
            <span v-if="configMode === 'default'">当前模式：使用默认配置</span>
            <span v-else>当前模式：自定义配置</span>
          </div>
          <div>
            <el-button @click="handleClose">取消</el-button>
            <el-button type="primary" @click="saveConfig" :loading="saving">
              {{ configMode === 'default' ? '保存默认配置' : '保存自定义配置' }}
            </el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.config-mode {
  margin-bottom: 20px;
  text-align: center;
}

.config-hint {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.example-format {
  margin-left: 8px;
  color: #e6a23c;
  font-style: italic;
}

.api-key-input {
  display: flex;
  gap: 8px;
  align-items: center;
}

.example-btn {
  flex-shrink: 0;
}

.success-text {
  color: #67c23a;
  margin-left: 10px;
}

.error-text {
  color: #f56c6c;
  margin-left: 10px;
}

.footer-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.config-summary {
  color: #606266;
  font-size: 14px;
}

.prompts-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 0 8px;
}

.prompts-header span {
  font-weight: 500;
  color: #303133;
}
</style>