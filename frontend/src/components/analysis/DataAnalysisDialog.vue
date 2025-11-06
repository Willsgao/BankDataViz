<template>
  <el-dialog
    v-model="visible"
    :title="analysisTitle"
    width="90%"
    top="5vh"
    class="analysis-dialog"
    @closed="handleClose"
  >
    <div class="analysis-container">
      <!-- 分析类型选择 -->
      <div class="analysis-type-selector">
        <el-radio-group v-model="selectedAnalysisType" @change="handleAnalysisTypeChange">
          <el-radio-button label="score-distribution">分数分布分析</el-radio-button>
          <el-radio-button label="dimension-analysis">维度对比分析</el-radio-button>
          <el-radio-button label="class-comparison">班级对比分析</el-radio-button>
          <el-radio-button label="teacher-comment">教师评语分析</el-radio-button>
          <el-radio-button label="llm-analysis">AI智能分析</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 班级选择器（仅在多班级分析时显示） -->
      <div v-if="isMultiClassAnalysis && selectedAnalysisType !== 'class-comparison'" class="class-selector">
        <el-alert
          title="多班级数据分析"
          type="info"
          :description="`当前分析 ${allClassData.length} 个班级的数据`"
          show-icon
          :closable="false"
        />
        <div class="class-checkboxes">
          <el-checkbox-group v-model="selectedClasses">
            <el-checkbox
              v-for="classData in allClassData"
              :key="classData.className"
              :label="classData.className"
            >
              {{ classData.className }} ({{ classData.tableName }})
            </el-checkbox>
          </el-checkbox-group>
        </div>
      </div>

      <!-- 可视化内容 -->
      <div class="analysis-content">
        <ScoreDistributionChart
          v-if="selectedAnalysisType === 'score-distribution' && analysisData.length"
          :data="analysisData"
          :is-multi-class="isMultiClassAnalysis"
          :selected-classes="selectedClasses"
        />

        <DimensionAnalysisChart
          v-else-if="selectedAnalysisType === 'dimension-analysis' && analysisData.length"
          :data="analysisData"
          :is-multi-class="isMultiClassAnalysis"
          :selected-classes="selectedClasses"
        />

        <ClassComparisonChart
          v-else-if="selectedAnalysisType === 'class-comparison' && allClassData.length"
          :class-data="allClassData"
        />

        <CommentAnalysisChart
          v-else-if="selectedAnalysisType === 'teacher-comment' && analysisData.length"
          :data="analysisData"
          :is-multi-class="isMultiClassAnalysis"
          :selected-classes="selectedClasses"
        />

        <LLMAnalysis
          v-else-if="selectedAnalysisType === 'llm-analysis'"
          :data="analysisData"
          :sheet-name="sheetName"
          :is-multi-class="isMultiClassAnalysis"
          :all-class-data="allClassData"
        />

        <div v-else class="no-data">
          <el-empty description="暂无数据或选择的分析类型" />
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import ScoreDistributionChart from './charts/ScoreDistributionChart.vue'
import DimensionAnalysisChart from './charts/DimensionAnalysisChart.vue'
import ClassComparisonChart from './charts/ClassComparisonChart.vue'
import CommentAnalysisChart from './charts/CommentAnalysisChart.vue'
import LLMAnalysis from './LLMAnalysis.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  excelData: {
    type: Array,
    default: () => []
  },
  sheetName: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

const visible = ref(false)
const selectedAnalysisType = ref('score-distribution')
const selectedClasses = ref([])

// 检查是否是多班级分析（目录表）
const isMultiClassAnalysis = computed(() => {
  return props.sheetName === '目录' && window.allClassData && window.allClassData.length > 0
})

// 获取所有班级数据
const allClassData = computed(() => {
  return window.allClassData || []
})

// 分析标题
const analysisTitle = computed(() => {
  const baseTitle = '数据可视化分析'
  if (isMultiClassAnalysis.value) {
    return `${baseTitle} - 多班级综合分析`
  }
  return `${baseTitle} - ${props.sheetName}`
})

// 当前分析使用的数据
const analysisData = computed(() => {
  if (isMultiClassAnalysis.value && selectedClasses.value.length > 0) {
    // 返回选中的班级数据
    const selectedData = allClassData.value
      .filter(classData => selectedClasses.value.includes(classData.className))
      .flatMap(classData => classData.data)
    return selectedData
  } else if (isMultiClassAnalysis.value) {
    // 返回所有班级数据
    return allClassData.value.flatMap(classData => classData.data)
  } else {
    // 返回单个表格数据
    return props.excelData
  }
})

watch(() => props.modelValue, (newVal) => {
  visible.value = newVal
  if (newVal && isMultiClassAnalysis.value) {
    // 默认选中所有班级
    selectedClasses.value = allClassData.value.map(classData => classData.className)
  }
})

watch(visible, (newVal) => {
  emit('update:modelValue', newVal)
})

const handleAnalysisTypeChange = (type) => {
  selectedAnalysisType.value = type
}

const handleClose = () => {
  selectedAnalysisType.value = 'score-distribution'
  selectedClasses.value = []
}
</script>

<style scoped>
.class-selector {
  margin: 16px 0;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.class-checkboxes {
  margin-top: 12px;
}

.class-checkboxes .el-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.class-checkboxes .el-checkbox {
  margin-right: 0;
}
</style>