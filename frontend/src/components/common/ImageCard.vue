<template>
  <div class="image-card">
    <div class="card-header">
      <span class="table-name">表格{{ index + 1 }}：{{ displayName }}</span>

      <el-button
        type="primary"
        size="small"
        :loading="ocrLoading"
        class="process-btn"
        @click="handleOcrRecognize"
      >
        {{ ocrLoading ? '识别中' : '识别' }}
      </el-button>
    </div>

    <div
      class="image-container"
      @click="$emit('preview', image)"
    >
      <el-image
        :src="image"
        :preview-src-list="[image]"
        fit="contain"
        class="table-image"
        :title="`表格${index + 1}：${displayName}`"
      >
        <template #error>
          <div class="image-error">
            <el-icon><Picture /></el-icon>
            <span>加载失败</span>
          </div>
        </template>
      </el-image>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Picture } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { baiduOcrApi } from '@/api/baiduOcr'  // 导入百度OCR API

import { onMounted } from 'vue'


const props = defineProps({
  image: {
    type: String,
    required: true
  },
  index: {
    type: Number,
    required: true
  },
  imageName: {
    type: String,
    default: ''
  },
  // 移除 llmConfigured 和 llmLoading，因为百度OCR不需要配置
})

const emit = defineEmits(['preview', 'ocr-completed'])  // 修改事件名

const ocrLoading = ref(false)

// 计算属性：生成显示名称
const displayName = computed(() => {
  if (props.imageName) {
    return props.imageName
  }

  try {
    const fileName = props.image.split('/').pop()
    const nameWithoutExt = fileName.replace(/\.(png|jpg|jpeg)$/i, '')
    const parts = nameWithoutExt.split('_')

    if (parts.length > 1) {
      return parts.slice(1).join('_')
    }

    return nameWithoutExt
  } catch (error) {
    return '未知表格'
  }
})

// 在 ImageCard.vue 的 handleOcrRecognize 函数中
async function handleOcrRecognize() {
  try {
    ocrLoading.value = true
    console.log('🔄 开始百度OCR识别:', props.image)

    // 从图片URL获取图片文件
    const imageFile = await urlToFile(props.image, `table-${props.index + 1}.png`)

    // 调用百度OCR接口
    const result = await baiduOcrApi.recognizeTable(imageFile)

    if (result.success) {
      console.log('✅ 百度OCR识别成功:', result)

      // 构建完整的Excel URL
      const excelUrl = `/static/excel_output/${result.data.excel_filename}`

      // 构建完整的识别结果数据
      const ocrResult = {
        success: true,
        image: props.image,
        tableName: displayName.value,
        excelUrl: excelUrl, // 使用完整的URL
        excelFilename: result.data.excel_filename,
        originalFilename: result.data.original_filename,
        tablesCount: result.data.tables_count,
        wordsCount: result.data.words_count,
        source: 'baidu_ocr'
      }

      // 触发OCR完成事件
      emit('ocr-completed', ocrResult)

      ElMessage.success('表格识别成功')
    } else {
      throw new Error(result.error || 'OCR识别失败')
    }

  } catch (error) {
    console.error('❌ 百度OCR识别失败:', error)
    ElMessage.error(`识别失败: ${error.message}`)

    // 发送失败结果
    emit('ocr-completed', {
      success: false,
      image: props.image,
      tableName: displayName.value,
      error: error.message,
      source: 'baidu_ocr'
    })
  } finally {
    ocrLoading.value = false
  }
}


// 辅助函数：将图片URL转换为File对象
async function urlToFile(url, filename) {
  try {
    const response = await fetch(url)
    const blob = await response.blob()
    return new File([blob], filename, { type: blob.type })
  } catch (error) {
    console.error('转换图片URL失败:', error)
    throw new Error('无法获取图片文件')
  }
}


onMounted(() => {
  console.log('🔍 ImageCard 实际收到 src：', props.image)
})


</script>

<!-- 样式部分保持不变 -->
<style scoped>
.image-card {
  width: 200px;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 12px;
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.image-card:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
  min-height: 40px;
}

.table-name {
  font-size: 12px;
  font-weight: 500;
  color: #333;
  line-height: 1.4;
  word-break: break-all;
  flex: 1;
  margin-right: 8px;
}

.process-btn {
  flex-shrink: 0;
}

.image-container {
  cursor: pointer;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid #f0f0f0;
}

.table-image {
  width: 100%;
  height: 150px;
  display: block;
}

.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 150px;
  color: #999;
  background: #f5f5f5;
}

.image-error .el-icon {
  font-size: 24px;
  margin-bottom: 8px;
}
</style>