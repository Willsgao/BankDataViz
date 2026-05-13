<template>
  <div class="llm-analysis">
    <div class="analysis-prompt">
      <el-input
        v-model="customPrompt"
        type="textarea"
        :placeholder="defaultPlaceholder"
        :rows="3"
      />
      <el-button
        type="primary"
        :loading="loading"
        class="analyze-btn"
        @click="performLLMAnalysis"
      >
        开始分析
      </el-button>
    </div>
    <div
      v-if="analysisResult"
      class="llm-result"
    >
      <h4>AI分析结果</h4>
      <div
        class="result-content"
        v-html="analysisResult"
      />
    </div>
    <div
      v-else-if="!loading"
      class="analysis-tips"
    >
      <el-alert
        title="分析提示"
        type="info"
        description="您可以询问关于班级整体表现、学生优势不足、教学建议等问题"
        show-icon
        :closable="false"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { calculateScoreRange, calculateDimensionAverages, formatLLMResult } from './utils/analysisUtils'

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  sheetName: {
    type: String,
    default: ''
  }
})

const customPrompt = ref('')
const loading = ref(false)
const analysisResult = ref('')

const defaultPlaceholder = computed(() => {
  return `请输入您想要分析的问题，例如：分析${props.sheetName}班级的作文优势和不足，给出具体的教学建议...`
})

const performLLMAnalysis = async () => {
  if (!customPrompt.value.trim()) {
    ElMessage.warning('请输入分析问题')
    return
  }

  if (!props.data.length) {
    ElMessage.warning('没有数据可分析')
    return
  }

  loading.value = true
  analysisResult.value = ''

  try {
    // 构建分析数据摘要
    const analysisData = {
      summary: {
        total_students: props.data.length,
        sheet_name: props.sheetName,
        score_range: calculateScoreRange(props.data),
        dimension_avg: calculateDimensionAverages(props.data)
      },
      sample_data: props.data.slice(0, 5) // 取前5条作为样本
    }

    const response = await fetch('/api/llm-analysis', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        data: analysisData,
        prompt: customPrompt.value,
        sheet_name: props.sheetName
      })
    })

    if (response.ok) {
      const result = await response.json()
      analysisResult.value = formatLLMResult(result.analysis || '暂无分析结果')
      ElMessage.success('分析完成')
    } else {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.error || '分析请求失败')
    }
  } catch (error) {
    console.error('LLM分析失败:', error)
    // 模拟返回结果（在实际环境中应该删除）
    analysisResult.value = generateMockAnalysis()
    ElMessage.warning('使用模拟分析结果（请配置真实LLM服务）')
  } finally {
    loading.value = false
  }
}

const generateMockAnalysis = () => {
  const scoreRange = calculateScoreRange(props.data)
  const dimensionAvg = calculateDimensionAverages(props.data)

  return `
    <h4>📊 ${props.sheetName} 班级作文分析报告</h4>
    <p><strong>基于您的问题：</strong>"${customPrompt.value}"</p>

    <p><strong>📈 数据概览：</strong></p>
    <ul>
      <li>班级人数: ${props.data.length}人</li>
      <li>总分范围: ${scoreRange.min}-${scoreRange.max}分</li>
      <li>平均分: ${scoreRange.avg}分</li>
    </ul>

    <p><strong>🎯 各维度表现：</strong></p>
    <ul>
      ${Object.entries(dimensionAvg).map(([dim, score]) =>
        `<li>${dim}: ${score}分</li>`
      ).join('')}
    </ul>

    <p><strong>💡 教学建议：</strong></p>
    <ul>
      <li>重点关注得分较低的维度，进行针对性训练</li>
      <li>对高分学生进行拔高培养，低分学生进行基础巩固</li>
      <li>加强书写规范训练，提升卷面分数</li>
      <li>组织优秀作文展示，促进学生互相学习</li>
    </ul>

    <p><em>注: 这是模拟分析结果，实际使用时请连接真实的LLM服务</em></p>
  `
}
</script>

<style scoped>
.llm-analysis {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 500px;
}

.analysis-prompt {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.analyze-btn {
  align-self: flex-end;
  width: 120px;
}

.llm-result {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  border-left: 4px solid #409eff;
}

.llm-result h4 {
  margin: 0 0 16px 0;
  color: #303133;
  border-bottom: 1px solid #e4e7ed;
  padding-bottom: 8px;
}

.result-content {
  line-height: 1.8;
  color: #606266;
}

.result-content ul {
  margin: 8px 0;
  padding-left: 20px;
}

.result-content li {
  margin: 4px 0;
}

.analysis-tips {
  margin-top: 20px;
}
</style>