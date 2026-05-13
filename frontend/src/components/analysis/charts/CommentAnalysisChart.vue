<template>
  <div class="comment-analysis-chart">
    <div class="comment-analysis">
      <h4>评语关键词分析</h4>
      <div
        ref="wordCloudChart"
        class="chart"
      />
      <div class="comment-stats">
        <el-card
          v-for="stat in commentStats"
          :key="stat.title"
          class="stat-card"
        >
          <template #header>
            <span>{{ stat.title }}</span>
          </template>
          <div class="stat-content">
            <div class="stat-value">
              {{ stat.value }}
            </div>
            <div class="stat-desc">
              {{ stat.desc }}
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import * as echarts from 'echarts'
import {
  calculateAverageCommentLength,
  calculatePositiveCommentRatio,
  calculateCommentDiversity,
  generateWordCloudData
} from '../utils/analysisUtils'

const props = defineProps({
  data: {
    type: Array,
    required: true
  }
})

const wordCloudChart = ref(null)
let wordCloudChartInstance = null

const comments = computed(() => {
  return props.data.map(row => row.教师评语 || row['教师评语'] || '')
    .filter(comment => comment && comment.trim())
})

const commentStats = computed(() => {
  if (comments.value.length === 0) return []

  return [
    {
      title: '平均评语长度',
      value: `${calculateAverageCommentLength(comments.value)}字`,
      desc: '每条评语平均字数'
    },
    {
      title: '积极评语比例',
      value: `${calculatePositiveCommentRatio(comments.value)}%`,
      desc: '基于关键词识别'
    },
    {
      title: '评语多样性',
      value: `${calculateCommentDiversity(comments.value)}%`,
      desc: '独特评语比例'
    },
    {
      title: '评语覆盖率',
      value: `${((comments.value.length / props.data.length) * 100).toFixed(1)}%`,
      desc: '有评语的学生比例'
    }
  ]
})

const renderChart = () => {
  if (!wordCloudChart.value || comments.value.length === 0) return

  const wordCloudData = generateWordCloudData(comments.value)

  if (!wordCloudChartInstance) {
    wordCloudChartInstance = echarts.init(wordCloudChart.value)
  }

  const wordCloudOption = {
    title: {
      text: '教师评语关键词云',
      left: 'center'
    },
    tooltip: {
      formatter: function (params) {
        return `${params.name}: ${params.value}次`
      }
    },
    series: [{
      type: 'wordCloud',
      shape: 'circle',
      sizeRange: [12, 60],
      rotationRange: [-45, 45],
      gridSize: 12,
      drawOutOfBound: false,
      textStyle: {
        fontFamily: 'sans-serif',
        fontWeight: 'bold',
        color: function () {
          const colors = [
            '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
            '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc'
          ]
          return colors[Math.floor(Math.random() * colors.length)]
        }
      },
      emphasis: {
        focus: 'self',
        textStyle: {
          shadowBlur: 10,
          shadowColor: '#333'
        }
      },
      data: wordCloudData
    }]
  }
  wordCloudChartInstance.setOption(wordCloudOption)
}

onMounted(() => {
  renderChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (wordCloudChartInstance) {
    wordCloudChartInstance.dispose()
    wordCloudChartInstance = null
  }
  window.removeEventListener('resize', handleResize)
})

const handleResize = () => {
  wordCloudChartInstance?.resize()
}

watch(() => props.data, () => {
  renderChart()
}, { deep: true })
</script>

<style scoped>
.comment-analysis-chart {
  width: 100%;
}

.comment-analysis {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.comment-analysis h4 {
  margin: 0;
  text-align: center;
  color: #303133;
}

.chart {
  height: 400px;
  width: 100%;
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
}

.comment-stats {
  display: flex;
  gap: 16px;
  justify-content: space-around;
}

.stat-card {
  flex: 1;
}

.stat-content {
  text-align: center;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 8px;
}

.stat-desc {
  font-size: 12px;
  color: #909399;
}
</style>