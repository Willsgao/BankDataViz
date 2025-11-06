<template>
  <div class="score-distribution-chart">
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { calculateScoreDistribution, calculateGradeDistribution, getGradeColor } from '../utils/analysisUtils'

const props = defineProps({
  data: {
    type: Array,
    required: true
  }
})

const chartRef = ref(null)
let chartInstance = null

const renderChart = () => {
  if (!chartRef.value || !props.data.length) return

  const scores = props.data.map(row => parseInt(row.总分 || row['总分'] || 0)).filter(score => !isNaN(score))
  const grades = props.data.map(row => row.等级 || row['等级'] || '未知').filter(grade => grade && grade !== '未知')

  const option = {
    title: {
      text: '分数与等级分布',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['分数分布', '等级分布'],
      top: '10%'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: ['0-10', '11-15', '16-20', '21-25']
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '分数分布',
        type: 'bar',
        data: calculateScoreDistribution(scores),
        itemStyle: {
          color: '#5470c6'
        }
      },
      {
        name: '等级分布',
        type: 'line',
        data: calculateGradeDistribution(grades).map(item => item.value),
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: {
          color: '#ee6666'
        },
        itemStyle: {
          color: '#ee6666'
        }
      }
    ]
  }

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  chartInstance.setOption(option)
}

onMounted(() => {
  renderChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  window.removeEventListener('resize', handleResize)
})

const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

watch(() => props.data, () => {
  renderChart()
}, { deep: true })
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 400px;
}
</style>