<template>
  <div class="dimension-analysis-chart">
    <div class="chart-row">
      <div class="chart-item">
        <h4>各维度平均分</h4>
        <div
          ref="radarChart"
          class="chart"
        />
      </div>
      <div class="chart-item">
        <h4>维度得分分布</h4>
        <div
          ref="boxChart"
          class="chart"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { calculateBoxData } from '../utils/analysisUtils'

const props = defineProps({
  data: {
    type: Array,
    required: true
  }
})

const radarChart = ref(null)
const boxChart = ref(null)
let radarChartInstance = null
let boxChartInstance = null

const renderCharts = () => {
  if (!props.data.length) return

  const dimensions = ['内容相关度', '语言表达', '文章结构', '卷面书写', '字数维度']
  const dimensionData = dimensions.map(dim => {
    const scores = props.data.map(row => {
      const score = parseInt(row[dim] || row[dim] || 0)
      return isNaN(score) ? 0 : score
    }).filter(score => score > 0)

    return {
      name: dim,
      scores: scores,
      average: scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0,
      max: scores.length ? Math.max(...scores) : 0,
      min: scores.length ? Math.min(...scores) : 0
    }
  }).filter(item => item.scores.length > 0)

  // 雷达图
  if (radarChart.value && dimensionData.length > 0) {
    if (!radarChartInstance) {
      radarChartInstance = echarts.init(radarChart.value)
    }

    const radarOption = {
      title: {
        text: '各维度平均分对比',
        left: 'center'
      },
      tooltip: {},
      radar: {
        indicator: dimensionData.map(item => ({
          name: item.name,
          max: Math.ceil(item.max * 1.2)
        }))
      },
      series: [{
        type: 'radar',
        data: [{
          value: dimensionData.map(item => Number(item.average.toFixed(1))),
          name: '平均分',
          areaStyle: {
            color: 'rgba(255, 153, 102, 0.6)'
          },
          lineStyle: {
            color: 'rgba(255, 153, 102, 1)'
          },
          itemStyle: {
            color: 'rgba(255, 153, 102, 1)'
          }
        }]
      }]
    }
    radarChartInstance.setOption(radarOption)
  }

  // 箱线图
  if (boxChart.value && dimensionData.length > 0) {
    if (!boxChartInstance) {
      boxChartInstance = echarts.init(boxChart.value)
    }

    const boxOption = {
      title: {
        text: '维度得分分布',
        left: 'center'
      },
      tooltip: {
        trigger: 'item',
        axisPointer: {
          type: 'shadow'
        },
        formatter: function (params) {
          const data = params.data
          return [
            params.name,
            `最大值: ${data[5]}`,
            `上四分位: ${data[4]}`,
            `中位数: ${data[3]}`,
            `下四分位: ${data[2]}`,
            `最小值: ${data[1]}`
          ].join('<br/>')
        }
      },
      grid: {
        left: '50px',
        right: '30px',
        bottom: '30px',
        top: '50px'
      },
      xAxis: {
        type: 'category',
        data: dimensionData.map(item => item.name),
        axisLabel: {
          rotate: 45
        }
      },
      yAxis: {
        type: 'value',
        name: '分数',
        min: 0
      },
      series: [{
        name: '维度得分',
        type: 'boxplot',
        data: dimensionData.map(item => calculateBoxData(item.scores)),
        itemStyle: {
          color: '#5470c6',
          borderColor: '#5470c6'
        }
      }]
    }
    boxChartInstance.setOption(boxOption)
  }
}

onMounted(() => {
  renderCharts()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (radarChartInstance) {
    radarChartInstance.dispose()
    radarChartInstance = null
  }
  if (boxChartInstance) {
    boxChartInstance.dispose()
    boxChartInstance = null
  }
  window.removeEventListener('resize', handleResize)
})

const handleResize = () => {
  radarChartInstance?.resize()
  boxChartInstance?.resize()
}

watch(() => props.data, () => {
  renderCharts()
}, { deep: true })
</script>

<style scoped>
.dimension-analysis-chart {
  width: 100%;
}

.chart-row {
  display: flex;
  gap: 20px;
  height: 400px;
}

.chart-item {
  flex: 1;
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
}

.chart-item h4 {
  margin: 0 0 16px 0;
  text-align: center;
  color: #303133;
}

.chart {
  height: 350px;
  width: 100%;
}
</style>