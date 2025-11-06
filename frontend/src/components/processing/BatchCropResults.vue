<script setup>
import { ref, onMounted, nextTick, computed, watch } from 'vue'  // ⭐⭐⭐ 添加 watch 导入 ⭐⭐⭐
import { ElMessage, ElMessageBox } from 'element-plus'
import { llmApi } from '@/api/llm'
import ImageCard from './ImageCard.vue'

const props = defineProps({
  pdf: {
    type: Object,
    required: true
  },
  images: {
    type: Array,
    default: () => []
  },
  tableType: {
    type: String,
    default: 'financial'
  },
  llmLoading: {  // ⭐⭐⭐ 添加 llmLoading prop ⭐⭐⭐
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['open-config', 'preview-image', 'llm-process', 'single-llm-process', 'clear-cache', 'force-reset-loading', 'task-completed'])

// LLM相关状态
const batchLlmLoading = ref(false)
const singleLlmLoading = ref({})

// 临时修复：直接设为 true，跳过 API 检查
const llmConfigured = ref(true)

// 新增：跳转相关状态
const jumpIndex = ref('')
const scrollContainer = ref(null)
const imageCards = ref([])



// 监听父组件传递的 llmLoading 状态
watch(() => props.llmLoading, (newVal) => {
  console.log('🔄 BatchCropResults 收到 llmLoading 状态变化:', {
    newVal,
    pdfName: props.pdf.disk_name,
    currentState: batchLlmLoading.value
  })

  // ⭐⭐⭐ 关键：同步父组件的 loading 状态 ⭐⭐⭐
  if (props.pdf?.disk_name && newVal[props.pdf.disk_name] !== undefined) {
    batchLlmLoading.value = newVal[props.pdf.disk_name]
    console.log('✅ BatchCropResults 同步 loading 状态:', batchLlmLoading.value)
  }
}, { immediate: true, deep: true })

// 修改 resetLoadingState 函数（如果存在的话）
const resetLocalLoading = () => {
  console.log('🔄 BatchCropResults 本地重置 loading')
  batchLlmLoading.value = false
}




// 监听任务完成事件
const handleTaskCompleted = (data) => {
  console.log('🎯 BatchCropResults 收到任务完成事件:', data)
  if (data.pdfName === props.pdf.disk_name) {
    batchLlmLoading.value = false
    console.log('✅ BatchCropResults 重置loading状态')
  }
}




// 跳转到指定图片
const jumpToImage = async () => {
  if (!jumpIndex.value || jumpIndex.value < 1 || jumpIndex.value > props.images.length) {
    ElMessage.warning(`请输入 1-${props.images.length} 之间的有效序号`)
    return
  }

  const targetIndex = parseInt(jumpIndex.value) - 1 // 转换为0-based索引

  try {
    // 等待DOM更新
    await nextTick()

    if (scrollContainer.value && imageCards.value[targetIndex]) {
      // 获取目标图片卡片元素
      const targetCard = imageCards.value[targetIndex].$el

      if (targetCard) {
        // 滚动到目标卡片
        targetCard.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
          inline: 'center'
        })

        // 添加高亮效果
        targetCard.classList.add('highlight-card')
        setTimeout(() => {
          targetCard.classList.remove('highlight-card')
        }, 2000)

        ElMessage.success(`已跳转到第 ${jumpIndex.value} 个表格`)
      }
    }
  } catch (error) {
    console.error('跳转失败:', error)
    ElMessage.error('跳转失败，请重试')
  }
}

// 添加打开配置的方法
const openConfig = () => {
  emit('open-config')
}

// 新增：从图片URL中提取表格名称
const extractImageName = (imgUrl) => {
  try {
    // 从URL中获取文件名（去掉路径）
    const fileName = imgUrl.split('/').pop()

    // 去掉扩展名
    const nameWithoutExt = fileName.replace(/\.(png|jpg|jpeg)$/i, '')

    // 提取 '_' 后面的部分
    const parts = nameWithoutExt.split('_')
    if (parts.length > 1) {
      // 返回从第二个部分开始的所有部分
      return parts.slice(1).join('_')
    }

    return nameWithoutExt // 如果没有 '_'，返回原名称
  } catch (error) {
    console.error('提取图片名称失败:', error)
    return '未知表格'
  }
}

// LLM配置状态检查函数
const checkLLMStatus = async () => {
  try {
    console.log('🔄 BatchCropResults 检查LLM配置状态...')
    const response = await llmApi.getStatus()
    console.log('🔍 BatchCropResults LLM状态响应:', response)

    if (response.success) {
      llmConfigured.value = response.data.client_configured
      console.log(`✅ BatchCropResults LLM配置状态: ${llmConfigured.value ? '已配置' : '未配置'}`)
    } else {
      console.error('❌ BatchCropResults 获取LLM状态失败:', response.error)
      llmConfigured.value = false
    }
  } catch (error) {
    console.error('💥 BatchCropResults 检查LLM状态失败:', error)
    llmConfigured.value = false
  }
}

// 在 BatchCropResults.vue 中
const handleBatchLLMProcess = async () => {
  try {

    console.log('🔄 BatchCropResults - 开始批量LLM处理')

    // ⭐⭐⭐ 立即设置本地 loading 状态 ⭐⭐⭐
    batchLlmLoading.value = true
    console.log('🔄 设置 batchLlmLoading = true')

    // 检查LLM配置状态
    await checkLLMStatus()
    console.log('🔍 BatchCropResults LLM配置状态:', llmConfigured.value)

    if (!llmConfigured.value) {
      console.log('❌ BatchCropResults - LLM未配置，弹出配置对话框')
      const result = await ElMessageBox.confirm(
        'LLM未配置，请先配置大模型参数后才能进行批量表格识别',
        '提示',
        {
          confirmButtonText: '去配置',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )

      if (result) {
        emit('open-config')
      }
      // ⭐⭐⭐ 配置取消时重置 loading ⭐⭐⭐
      batchLlmLoading.value = false
      return
    }

    console.log('🔄 BatchCropResults - 准备处理的图片数量:', props.images.length)

    // 传递表格类型信息
    const batchParams = {
      imageCount: props.images.length,
      outputDir: `static/excel_data/${props.pdf.disk_name.replace('.pdf', '')}`,
      pdfName: props.pdf.disk_name,
      tableType: props.tableType
    }

    console.log('🔄 BatchCropResults - 开始批量LLM处理:', batchParams)

    // 调用父组件的批量处理
    emit('llm-process', batchParams)

  } catch (error) {
    console.error('💥 BatchCropResults - 批量LLM处理失败:', error)
    ElMessage.error('批量表格识别异常: ' + (error.response?.data?.error || error.message))
    // ⭐⭐⭐ 出错时重置 loading ⭐⭐⭐
    batchLlmLoading.value = false
  }
}


// 添加手动重置按钮用于调试
const forceReset = () => {
  console.log('🔄 手动强制重置 loading 状态')
  batchLlmLoading.value = false
  // 同时通知父组件
  emit('force-reset-loading', { pdfName: props.pdf.disk_name })
}

const handleSingleLLMProcess = async (imgUrl, index) => {
  try {
    console.log('🔍 BatchCropResults - 收到参数:', { imgUrl, index })
    singleLlmLoading.value[index] = true

    if (!llmConfigured.value) {
      await ElMessageBox.confirm(
        'LLM未配置，请先配置大模型参数后再进行表格识别',
        '提示',
        {
          confirmButtonText: '去配置',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
      return
    }

    const urlObj = new URL(imgUrl)
    const imagePath = urlObj.pathname.replace('/static/', 'static/')
    const outputPath = `./output/llm_results/single_${index + 1}.xlsx`

    console.log('🔄 调用processImage API，参数:', {
      image_path: imagePath,
      output_path: outputPath,
      sheet_name: `表格${index + 1}`,
      bank_name: '未知银行'
    })

    // 先尝试普通表格识别
    const response = await llmApi.processNonFinancialTable({
      image_path: imagePath,
      output_path: outputPath,
      sheet_name: `表格${index + 1}`,
      bank_name: '未知银行'
    })

    console.log('✅ processNonFinancialTable完整响应:', response)

    if (response.success) {
      // ⭐⭐⭐ 修复：正确处理新的返回格式 ⭐⭐⭐
      let excelUrl = ''

      // 检查新的批量处理格式
      if (response.data && response.data.excel_url) {
        excelUrl = response.data.excel_url
        console.log('📄 从data.excel_url获取Excel URL:', excelUrl)
      }
      // 检查旧的单个处理格式
      else if (response.excel_url) {
        excelUrl = response.excel_url
        console.log('📄 从excel_url获取Excel URL:', excelUrl)
      }
      // 检查results数组中的URL
      else if (response.data && response.data.results && response.data.results[0] && response.data.results[0].excel_url) {
        excelUrl = response.data.results[0].excel_url
        console.log('📄 从results数组获取Excel URL:', excelUrl)
      }

      const message = response.from_cache ?
        `已加载表格${index + 1}的现有数据` :
        `表格${index + 1}识别完成！`
      ElMessage.success(message)

      if (excelUrl) {
        console.log('📤 发射 single-llm-process 事件:', {
          excelUrl: excelUrl,
          index: index
        })

        emit('single-llm-process', {
          excelUrl: excelUrl,
          index: index
        })
      } else {
        console.warn('⚠️ 无法找到Excel URL，响应结构:', response)
        ElMessage.warning('处理完成但无法获取Excel文件路径')
      }
    } else {
      // 如果普通表格识别失败，尝试财务表格识别
      console.log('🔄 普通表格识别失败，尝试财务表格识别')
      const financialResponse = await llmApi.processImage({
        image_path: imagePath,
        output_path: outputPath,
        sheet_name: `表格${index + 1}`,
        bank_name: '未知银行'
      })

      console.log('✅ 财务表格识别响应:', financialResponse)

      if (financialResponse.success) {
        // ⭐⭐⭐ 同样修复财务表格的URL获取逻辑 ⭐⭐⭐
        let excelUrl = ''

        if (financialResponse.data && financialResponse.data.excel_url) {
          excelUrl = financialResponse.data.excel_url
        } else if (financialResponse.excel_url) {
          excelUrl = financialResponse.excel_url
        } else if (financialResponse.data && financialResponse.data.results && financialResponse.data.results[0] && financialResponse.data.results[0].excel_url) {
          excelUrl = financialResponse.data.results[0].excel_url
        }

        const message = financialResponse.from_cache ?
          `已加载表格${index + 1}的现有数据` :
          `表格${index + 1}识别完成！`
        ElMessage.success(message)

        if (excelUrl) {
          emit('single-llm-process', {
            excelUrl: excelUrl,
            index: index
          })
        } else {
          console.warn('⚠️ 财务表格无法找到Excel URL，响应结构:', financialResponse)
          ElMessage.warning('处理完成但无法获取Excel文件路径')
        }
      } else {
        // 显示详细的错误信息
        const errorMsg = response.error || response.message || financialResponse.error || '未知错误'
        console.error('❌ 所有识别方法都失败:', {
          普通表格错误: response.error,
          财务表格错误: financialResponse.error
        })
        ElMessage.error(`表格${index + 1}识别失败: ${errorMsg}`)
      }
    }

  } catch (error) {
    console.error('💥 单张LLM处理失败:', error)
    const errorDetail = error.response?.data?.error || error.message || '未知错误'
    ElMessage.error('单张表格识别异常: ' + errorDetail)
  } finally {
    singleLlmLoading.value[index] = false
  }
}


// 添加 mounted 调试
onMounted(() => {
  console.log('🔍 BatchCropResults 初始化状态:', {
    llmLoadingProp: props.llmLoading,
    pdfName: props.pdf.disk_name
  })
  checkLLMStatus()
})


</script>

<template>
  <div class="batch-crop-result">
    <div class="batch-header">
      <span class="batch-title">批量裁切结果</span>
      <span class="batch-count">共 {{ images.length }} 个表格</span>
    </div>

    <!-- 新增：跳转输入框 -->
    <div class="jump-control" v-if="images.length > 0">
      <el-input
        v-model="jumpIndex"
        type="number"
        placeholder="输入表格序号"
        :min="1"
        :max="images.length"
        size="small"
        style="width: 120px; margin-right: 8px;"
        @keyup.enter="jumpToImage"
      />
      <el-button
        type="primary"
        size="small"
        @click="jumpToImage"
        :disabled="!jumpIndex || jumpIndex < 1 || jumpIndex > images.length"
      >
        跳转
      </el-button>
      <span class="jump-hint">可输入 1-{{ images.length }} 之间的数字</span>
    </div>

    <div class="batch-actions">
      <!-- 配置按钮 -->
      <el-button
        v-if="!llmConfigured"
        type="warning"
        size="small"
        icon="el-icon-setting"
        @click="openConfig"
      >
        配置LLM
      </el-button>

      <!-- 大模型表格识别按钮 -->
      <el-button
        type="success"
        size="small"
        icon="el-icon-cpu"
        @click="handleBatchLLMProcess"
        :loading="batchLlmLoading"
        :disabled="!llmConfigured || batchLlmLoading"
      >
        {{ batchLlmLoading ? '处理中...' : '大模型表格识别' }}
      </el-button>


      <!-- 调试信息显示 -->
      <div v-if="batchLlmLoading" class="debug-info">
        <span>状态: {{ batchLlmLoading ? '处理中' : '就绪' }}</span>
        <span>PDF: {{ pdf?.disk_name }}</span>
      </div>

      <!-- 调试用重置按钮 -->
      <el-button
        v-if="batchLlmLoading"
        type="warning"
        size="small"
        icon="el-icon-refresh"
        @click="forceReset"
      >
        强制重置
      </el-button>

      <el-button
        type="info"
        size="small"
        icon="el-icon-delete"
        @click="$emit('clear-cache', pdf.disk_name)"
        title="清除裁切缓存"
        :disabled="batchLlmLoading"
      >
        清除缓存
      </el-button>
    </div>

    <div class="scroll-container">
      <div class="images-scroll" ref="scrollContainer">
        <ImageCard
          v-for="(imgUrl, index) in images"
          :key="index"
          :image="imgUrl"
          :index="index"
          :image-name="extractImageName(imgUrl)"
          :llm-configured="llmConfigured"
          :llm-loading="singleLlmLoading[index]"
          :ref="el => { if (el) imageCards[index] = el }"
          @preview="$emit('preview-image', $event, index)"
          @llm-process="handleSingleLLMProcess($event, index)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.batch-crop-result {
  margin: 16px;
  padding: 16px;
  border: 1px solid #e8f4fd;
  border-radius: 8px;
  background: #f7fbff;
  flex-shrink: 0;
}

.batch-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.batch-title {
  font-weight: bold;
  color: #1890ff;
  font-size: 14px;
}

.batch-count {
  color: #52c41a;
  font-size: 12px;
}

.jump-control {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #f0f7ff;
  border-radius: 4px;
  border: 1px solid #d1e9ff;
}

.jump-hint {
  margin-left: 12px;
  color: #666;
  font-size: 12px;
}

.batch-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.scroll-container {
  overflow-x: auto;
  padding: 8px 0;
}

.images-scroll {
  display: flex;
  gap: 16px;
  padding: 4px;
}

:deep(.highlight-card) {
  box-shadow: 0 0 0 2px #1890ff !important;
  transition: box-shadow 0.3s ease;
}
</style>