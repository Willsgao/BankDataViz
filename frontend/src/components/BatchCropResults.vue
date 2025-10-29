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

      <el-button
        type="success"
        size="small"
        icon="el-icon-cpu"
        @click="handleBatchLLMProcess"
        :loading="batchLlmLoading"
        :disabled="!llmConfigured || batchLlmLoading"
      >
        大模型表格识别
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
      <!-- 在 BatchCropResults.vue 的 images-scroll 部分 -->
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

<script setup>
import { ref, onMounted, nextTick } from 'vue'
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
  }
})

const emit = defineEmits(['open-config', 'preview-image', 'llm-process', 'single-llm-process', 'clear-cache'])

// LLM相关状态
const batchLlmLoading = ref(false)
const singleLlmLoading = ref({})

// 临时修复：直接设为 true，跳过 API 检查
const llmConfigured = ref(true)

// 新增：跳转相关状态
const jumpIndex = ref('')
const scrollContainer = ref(null)
const imageCards = ref([])

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

// 修改 checkLLMStatus 函数
const checkLLMStatus = async () => {
  try {
    console.log('跳过 LLM 状态检查，直接启用按钮')
    llmConfigured.value = true
  } catch (error) {
    console.error('LLM状态检查失败:', error)
    llmConfigured.value = true
  }
}

// 批量LLM处理
const handleBatchLLMProcess = async () => {
  try {
    batchLlmLoading.value = true

    // 先检查LLM配置状态
    const isConfigured = await checkAndConfigureLLM()
    if (!isConfigured) {
      return
    }

    // 获取裁切的图片路径
    const imagePaths = props.images.map(url => {
      if (url.startsWith('http')) {
        const urlObj = new URL(url)
        return urlObj.pathname.replace('/static/', 'static/')
      }
      return url
    }).filter(path => path)

    console.log('准备处理的图片路径:', imagePaths)

    if (imagePaths.length === 0) {
      ElMessage.warning('没有可用的裁切图片进行识别')
      return
    }

    // 构建输出目录
    const pdfStem = props.pdf.disk_name.replace('.pdf', '')
    const outputDir = `./output/llm_results/${pdfStem}`

    console.log('开始批量LLM处理:', {
      imageCount: imagePaths.length,
      outputDir,
      pdfName: props.pdf.disk_name
    })

    const response = await llmApi.batchProcess({
      image_paths: imagePaths,
      output_dir: outputDir,
      bank_name: '未知银行'
    })

    console.log('LLM批量处理响应:', response)

    if (response.data && response.data.success) {
      const resultData = response.data.data || response.data
      ElMessage.success(`表格识别完成！成功处理 ${resultData.success || 0} 个文件`)

      emit('llm-process', {
        pdfDiskName: props.pdf.disk_name,
        result: resultData,
        success: true
      })
    } else {
      const errorMsg = response.data?.error || response.error || '未知错误'
      ElMessage.error(`表格识别失败: ${errorMsg}`)

      emit('llm-process', {
        pdfDiskName: props.pdf.disk_name,
        error: errorMsg,
        success: false
      })
    }

  } catch (error) {
    console.error('LLM处理失败:', error)

    if (error !== 'cancel') {
      let errorMsg = 'LLM处理异常'

      if (error.response) {
        errorMsg = `服务器错误: ${error.response.status} - ${error.response.data?.error || error.response.statusText}`
      } else if (error.request) {
        errorMsg = '网络连接错误，请检查网络连接'
      } else {
        errorMsg = `处理异常: ${error.message}`
      }

      ElMessage.error(errorMsg)

      emit('llm-process', {
        pdfDiskName: props.pdf.disk_name,
        error: errorMsg,
        success: false
      })
    }
  } finally {
    batchLlmLoading.value = false
  }
}

// 检查和配置LLM的函数
const checkAndConfigureLLM = async () => {
  try {
    const statusResponse = await llmApi.getStatus()
    if (statusResponse.data && statusResponse.data.success) {
      const status = statusResponse.data.data

      if (status.client_configured) {
        console.log('LLM已配置，可以开始处理')
        return true
      }
    }

    const result = await ElMessageBox.confirm(
      'LLM未配置，请先配置大模型参数后才能进行表格识别',
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
    return false

  } catch (error) {
    console.error('检查LLM状态失败:', error)
    ElMessage.error('检查LLM配置失败')
    return false
  }
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
      const message = response.from_cache ?
        `已加载表格${index + 1}的现有数据` :
        `表格${index + 1}识别完成！`
      ElMessage.success(message)

      if (response.excel_url) {
        console.log('📤 发射 single-llm-process 事件:', {
          excelUrl: response.excel_url,
          index: index
        })

        emit('single-llm-process', {
          excelUrl: response.excel_url,
          index: index
        })
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
        const message = financialResponse.from_cache ?
          `已加载表格${index + 1}的现有数据` :
          `表格${index + 1}识别完成！`
        ElMessage.success(message)

        if (financialResponse.excel_url) {
          emit('single-llm-process', {
            excelUrl: financialResponse.excel_url,
            index: index
          })
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


onMounted(() => {
  checkLLMStatus()
})
</script>

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

/* 新增：跳转控制区域样式 */
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

/* 新增：高亮卡片样式 */
:deep(.highlight-card) {
  box-shadow: 0 0 0 2px #1890ff !important;
  transition: box-shadow 0.3s ease;
}
</style>