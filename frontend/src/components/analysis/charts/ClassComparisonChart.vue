<template>
  <div class="class-comparison-chart">
    <div class="chart-row">
      <div class="chart-item">
        <h4>班级平均分对比</h4>
        <div
          ref="avgScoreChart"
          class="chart"
        />
      </div>
      <div class="chart-item">
        <h4>班级等级分布</h4>
        <div
          ref="gradeDistributionChart"
          class="chart"
        />
      </div>
    </div>
    <div class="chart-row">
      <div class="chart-item full-width">
        <h4>各维度班级对比</h4>
        <div
          ref="dimensionComparisonChart"
          class="chart"
        />
      </div>
    </div>
    <div class="class-stats">
      <el-card
        v-for="classData in classStats"
        :key="classData.className"
        class="stat-card"
      >
        <template #header>
          <span>{{ classData.className }}</span>
        </template>
        <div class="stat-content">
          <div class="stat-item">
            <span class="label">平均总分:</span>
            <span class="value">{{ classData.avgTotalScore }}</span>
          </div>
          <div class="stat-item">
            <span class="label">最高分:</span>
            <span class="value">{{ classData.maxScore }}</span>
          </div>
          <div class="stat-item">
            <span class="label">最低分:</span>
            <span class="value">{{ classData.minScore }}</span>
          </div>
          <div class="stat-item">
            <span class="label">A等级:</span>
            <span class="value">{{ classData.gradeA }}人</span>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  classData: {
    type: Array,
    required: true
  }
})

const avgScoreChart = ref(null)
const gradeDistributionChart = ref(null)
const dimensionComparisonChart = ref(null)

let avgScoreChartInstance = null
let gradeDistributionChartInstance = null
let dimensionComparisonChartInstance = null

// 计算班级统计信息
const classStats = computed(() => {
  return props.classData.map(classData => {
    const scores = classData.data.map(row => parseInt(row.总分 || row['总分'] || 0)).filter(score => !isNaN(score))
    const grades = classData.data.map(row => row.等级 || row['等级'] || '').filter(grade => grade)

    return {
      className: classData.className,
      avgTotalScore: scores.length ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : 0,
      maxScore: scores.length ? Math.max(...scores) : 0,
      minScore: scores.length ? Math.min(...scores) : 0,
      gradeA: grades.filter(grade => grade === 'A').length,
      totalStudents: classData.data.length
    }
  })
})

const renderCharts = () => {
  if (!props.classData.length) return

  // 班级平均分柱状图
  if (avgScoreChart.value) {
    if (!avgScoreChartInstance) {
      avgScoreChartInstance = echarts.init(avgScoreChart.value)
    }

    const option = {
      title: {
        text: '班级平均分对比',
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        formatter: '{b}: {c}分'
      },
      xAxis: {
        type: 'category',
        data: classStats.value.map(stat => stat.className),
        axisLabel: {
          rotate: 45
        }
      },
      yAxis: {
        type: 'value',
        name: '平均分'
      },
      series: [{
        data: classStats.value.map(stat => stat.avgTotalScore),
        type: 'bar',
        itemStyle: {
          color: function(params) {
            const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de']
            return colors[params.dataIndex % colors.length]
          }
        }
      }]
    }
    avgScoreChartInstance.setOption(option)
  }

  // 班级等级分布堆叠柱状图
  if (gradeDistributionChart.value) {
    if (!gradeDistributionChartInstance) {
      gradeDistributionChartInstance = echarts.init(gradeDistributionChart.value)
    }

    const grades = ['A', 'B', 'C']
    const seriesData = grades.map(grade => ({
      name: grade,
      type: 'bar',
      stack: 'total',
      data: props.classData.map(classData => {
        const classGrades = classData.data.map(row => row.等级 || row['等级'] || '')
        return classGrades.filter(g => g === grade).length
      })
    }))

    const option = {
      title: {
        text: '班级等级分布',
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        }
      },
      legend: {
        data: grades
      },
      xAxis: {
        type: 'category',
        data: props.classData.map(classData => classData.className),
        axisLabel: {
          rotate: 45
        }
      },
      yAxis: {
        type: 'value',
        name: '人数'
      },
      series: seriesData
    }
    gradeDistributionChartInstance.setOption(option)
  }

  // 各维度班级对比雷达图
  if (dimensionComparisonChart.value) {
    if (!dimensionComparisonChartInstance) {
      dimensionComparisonChartInstance = echarts.init(dimensionComparisonChart.value)
    }

    const dimensions = ['内容相关度', '语言表达', '文章结构', '卷面书写', '字数维度']
    const seriesData = props.classData.map(classData => {
      const dimensionAverages = dimensions.map(dim => {
        const scores = classData.data.map(row => parseInt(row[dim] || row[dim] || 0)).filter(score => !isNaN(score))
        return scores.length ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : 0
      })

      return {
        name: classData.className,
        value: dimensionAverages,
        type: 'radar'
      }
    })

    const option = {
      title: {
        text: '各维度班级对比',
        left: 'center'
      },
      tooltip: {},
      radar: {
        indicator: dimensions.map(dim => ({ name: dim, max: 10 }))
      },
      series: [{
        type: 'radar',
        data: seriesData
      }]
    }
    dimensionComparisonChartInstance.setOption(option)
  }
}

onMounted(() => {
  renderCharts()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  [avgScoreChartInstance, gradeDistributionChartInstance, dimensionComparisonChartInstance].forEach(instance => {
    if (instance) {
      instance.dispose()
      instance = null
    }
  })
  window.removeEventListener('resize', handleResize)
})

const handleResize = () => {
  avgScoreChartInstance?.resize()
  gradeDistributionChartInstance?.resize()
  dimensionComparisonChartInstance?.resize()
}

watch(() => props.classData, () => {
  renderCharts()
}, { deep: true })
</script>

<style scoped>
.class-comparison-chart {
  width: 100%;
}

.chart-row {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  height: 400px;
}

.chart-item {
  flex: 1;
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
}

.chart-item.full-width {
  flex: 2;
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

.class-stats {
  display: flex;
  gap: 16px;
  margin-top: 20px;
}

.stat-card {
  flex: 1;
}

.stat-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-item .label {
  color: #606266;
  font-size: 14px;
}

.stat-item .value {
  color: #303133;
  font-weight: bold;
}
</style>