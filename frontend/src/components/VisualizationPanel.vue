<!-- components/VisualizationPanel.vue -->
<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    title="表格数据可视化分析"
    width="90%"
    top="5vh"
    class="visualization-dialog"
    :close-on-click-modal="false"
    @closed="handleClose"
  >
    <div class="visualization-container" v-loading="loading">
      <!-- 工作表选择 -->
      <div class="sheet-selector" v-if="excelData.sheets && excelData.sheets.length > 1">
        <el-radio-group v-model="activeSheet" size="small" @change="onSheetChange">
          <el-radio-button
            v-for="sheet in excelData.sheets"
            :key="sheet.sheetName"
            :label="sheet.sheetName"
          >
            {{ sheet.sheetName }} ({{ sheet.rowCount }}×{{ sheet.colCount }})
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- 可视化类型选择 -->
      <div class="viz-type-selector">
        <el-radio-group v-model="activeVizType" size="small">
          <el-radio-button label="overview">数据概览</el-radio-button>
          <el-radio-button label="distribution">分布分析</el-radio-button>
          <el-radio-button label="correlation">相关性分析</el-radio-button>
          <el-radio-button label="categorical">分类分析</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 数据概览 -->
      <div v-if="activeVizType === 'overview'" class="viz-content">
        <div class="overview-cards">
          <el-card v-for="stat in overviewStats" :key="stat.title" class="stat-card">
            <div class="stat-content">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-title">{{ stat.title }}</div>
            </div>
          </el-card>
        </div>

        <div class="charts-grid">
          <el-card class="chart-card" header="数据类型分布">
            <div ref="dataTypeChart" class="chart-container"></div>
          </el-card>

          <el-card class="chart-card" header="缺失值统计">
            <div ref="missingValueChart" class="chart-container"></div>
          </el-card>
        </div>
      </div>

      <!-- 分布分析 -->
      <div v-if="activeVizType === 'distribution'" class="viz-content">
        <div class="distribution-controls">
          <el-select v-model="selectedNumericColumn" placeholder="选择数值列" size="small">
            <el-option
              v-for="col in numericColumns"
              :key="col"
              :label="col"
              :value="col"
            />
          </el-select>
        </div>

        <div class="charts-grid" v-if="selectedNumericColumn">
          <el-card class="chart-card" header="分布直方图">
            <div :ref="el => setChartRef('histogram', el)" class="chart-container"></div>
          </el-card>

          <el-card class="chart-card" header="箱线图">
            <div :ref="el => setChartRef('boxplot', el)" class="chart-container"></div>
          </el-card>
        </div>

        <div v-else class="no-data-hint">
          <el-empty description="请选择一个数值列进行分析" />
        </div>
      </div>

      <!-- 相关性分析 -->
      <div v-if="activeVizType === 'correlation'" class="viz-content">
        <div v-if="numericColumns.length > 1">
          <el-card class="chart-card full-width" header="相关性热力图">
            <div ref="correlationChart" class="chart-container"></div>
          </el-card>
        </div>

        <div v-else class="no-data-hint">
          <el-empty description="需要至少两个数值列才能进行相关性分析" />
        </div>
      </div>

      <!-- 分类分析 -->
      <div v-if="activeVizType === 'categorical'" class="viz-content">
        <div class="categorical-controls">
          <el-select v-model="selectedCategoricalColumn" placeholder="选择分类列" size="small">
            <el-option
              v-for="col in categoricalColumns"
              :key="col"
              :label="col"
              :value="col"
            />
          </el-select>
        </div>

        <div class="charts-grid" v-if="selectedCategoricalColumn">
          <el-card class="chart-card" header="分类分布">
            <div :ref="el => setChartRef('barChart', el)" class="chart-container"></div>
          </el-card>

          <el-card class="chart-card" header="饼图">
            <div :ref="el => setChartRef('pieChart', el)" class="chart-container"></div>
          </el-card>
        </div>

        <div v-else class="no-data-hint">
          <el-empty description="请选择一个分类列进行分析" />
        </div>
      </div>

      <!-- 分析报告 -->
      <div class="analysis-report">
        <el-card header="数据分析报告">
          <div class="report-content">
            <div v-for="item in analysisReport" :key="item.type" class="report-item">
              <h4>{{ item.title }}</h4>
              <p>{{ item.content }}</p>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
      <el-button type="primary" @click="exportReport">导出报告</el-button>
      <el-button type="success" @click="refreshAnalysis">刷新分析</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
// 按需引入 ECharts - 放在其他导入之后，代码之前
import * as echarts from 'echarts'

// 定义props和emits
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  excelData: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:visible'])

// 状态管理
const loading = ref(false)
const activeSheet = ref('')
const activeVizType = ref('overview')
const selectedNumericColumn = ref('')
const selectedCategoricalColumn = ref('')

// 图表引用
const dataTypeChart = ref(null)
const missingValueChart = ref(null)
const correlationChart = ref(null)
const chartInstances = ref({})

// 计算属性（与之前相同）
const currentSheet = computed(() => {
  return props.excelData.sheets?.find(sheet => sheet.sheetName === activeSheet.value) ||
         props.excelData.sheets?.[0]
})

const sheetData = computed(() => {
  return currentSheet.value?.data || props.excelData.data || []
})

const numericColumns = computed(() => {
  if (!sheetData.value || sheetData.value.length === 0) return []

  const firstRow = sheetData.value[0]
  return Object.keys(firstRow).filter(key => {
    const value = firstRow[key]
    return !isNaN(parseFloat(value)) && isFinite(value) && value !== '' && value !== null
  })
})

const categoricalColumns = computed(() => {
  if (!sheetData.value || sheetData.value.length === 0) return []

  const firstRow = sheetData.value[0]
  return Object.keys(firstRow).filter(key => !numericColumns.value.includes(key))
})

const overviewStats = computed(() => {
  const data = sheetData.value
  if (!data || data.length === 0) return []

  const totalRows = data.length
  const totalCols = Object.keys(data[0] || {}).length
  const numericCols = numericColumns.value.length
  const categoricalCols = categoricalColumns.value.length

  let missingValues = 0
  data.forEach(row => {
    Object.values(row).forEach(value => {
      if (value === null || value === undefined || value === '') missingValues++
    })
  })

  const missingRate = ((missingValues / (totalRows * totalCols)) * 100).toFixed(1)

  return [
    { title: '总行数', value: totalRows },
    { title: '总列数', value: totalCols },
    { title: '数值列', value: numericCols },
    { title: '分类列', value: categoricalCols },
    { title: '缺失值比例', value: `${missingRate}%` },
    { title: '数据完整性', value: `${100 - parseFloat(missingRate)}%` }
  ]
})

const analysisReport = computed(() => {
  const data = sheetData.value
  if (!data || data.length === 0) return []

  return [
    {
      type: 'basic',
      title: '基础信息',
      content: `数据集包含 ${data.length} 行，${Object.keys(data[0] || {}).length} 列，其中数值型列 ${numericColumns.value.length} 个，分类型列 ${categoricalColumns.value.length} 个。`
    },
    {
      type: 'quality',
      title: '数据质量',
      content: overviewStats.value.find(stat => stat.title === '数据完整性')?.value ?
               `数据完整性为 ${overviewStats.value.find(stat => stat.title === '数据完整性')?.value}，建议关注数据清理工作。` :
               '数据质量良好。'
    }
  ]
})

// 方法
const setChartRef = (name, el) => {
  if (el) {
    chartInstances.value[name] = el
  }
}

const initCharts = async () => {
  await nextTick()

  if (activeVizType.value === 'overview') {
    initDataTypeChart()
    initMissingValueChart()
  } else if (activeVizType.value === 'distribution' && selectedNumericColumn.value) {
    initDistributionCharts()
  } else if (activeVizType.value === 'correlation' && numericColumns.value.length > 1) {
    initCorrelationChart()
  } else if (activeVizType.value === 'categorical' && selectedCategoricalColumn.value) {
    initCategoricalCharts()
  }
}

const initDataTypeChart = () => {
  if (!dataTypeChart.value) return

  const chart = echarts.init(dataTypeChart.value)
  const numericCount = numericColumns.value.length
  const categoricalCount = categoricalColumns.value.length

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left'
    },
    series: [
      {
        name: '数据类型',
        type: 'pie',
        radius: '50%',
        data: [
          { value: numericCount, name: '数值型' },
          { value: categoricalCount, name: '分类型' }
        ],
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  }

  chart.setOption(option)
}

const initMissingValueChart = () => {
  if (!missingValueChart.value) return

  const chart = echarts.init(missingValueChart.value)
  const data = sheetData.value
  if (!data || data.length === 0) return

  const columns = Object.keys(data[0] || {})
  const missingData = columns.map(col => {
    const missingCount = data.filter(row =>
      row[col] === null || row[col] === undefined || row[col] === ''
    ).length
    return {
      name: col,
      value: missingCount
    }
  }).filter(item => item.value > 0)

  if (missingData.length === 0) {
    chart.setOption({
      graphic: {
        type: 'text',
        left: 'center',
        top: 'middle',
        style: {
          text: '无缺失值',
          fontSize: 16,
          fill: '#999'
        }
      }
    })
    return
  }

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    xAxis: {
      type: 'category',
      data: missingData.map(item => item.name),
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      name: '缺失值数量'
    },
    series: [
      {
        name: '缺失值',
        type: 'bar',
        data: missingData.map(item => item.value),
        itemStyle: {
          color: '#ff4d4f'
        }
      }
    ]
  }

  chart.setOption(option)
}

const initDistributionCharts = () => {
  // 实现分布图表
  console.log('初始化分布图表')
}

const initCorrelationChart = () => {
  // 实现相关性图表
  console.log('初始化相关性图表')
}

const initCategoricalCharts = () => {
  // 实现分类图表
  console.log('初始化分类图表')
}

const handleClose = () => {
  emit('update:visible', false)
}

const exportReport = () => {
  ElMessage.info('导出报告功能开发中...')
}

const refreshAnalysis = () => {
  loading.value = true
  setTimeout(() => {
    initCharts()
    loading.value = false
    ElMessage.success('分析已刷新')
  }, 500)
}

const onSheetChange = () => {
  initCharts()
}

// 监听器
watch(() => props.visible, (newVal) => {
  if (newVal) {
    if (props.excelData.sheets && props.excelData.sheets.length > 0) {
      activeSheet.value = props.excelData.sheets[0].sheetName
    }
    setTimeout(() => {
      initCharts()
    }, 100)
  }
})

watch(() => activeSheet.value, () => {
  setTimeout(() => {
    initCharts()
  }, 100)
})

watch(() => activeVizType.value, () => {
  setTimeout(() => {
    initCharts()
  }, 100)
})

watch(() => selectedNumericColumn.value, () => {
  if (activeVizType.value === 'distribution') {
    setTimeout(() => {
      initCharts()
    }, 100)
  }
})

watch(() => selectedCategoricalColumn.value, () => {
  if (activeVizType.value === 'categorical') {
    setTimeout(() => {
      initCharts()
    }, 100)
  }
})

// 生命周期
onMounted(() => {
  window.addEventListener('resize', () => {
    Object.values(chartInstances.value).forEach(instance => {
      if (instance && !instance.isDisposed()) {
        instance.resize()
      }
    })
  })
})
</script>

<style scoped>
/* 样式与之前相同 */
.visualization-dialog {
  max-height: 85vh;
}

.visualization-container {
  height: 70vh;
  overflow-y: auto;
}

.sheet-selector, .viz-type-selector {
  margin-bottom: 16px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #1890ff;
  margin-bottom: 8px;
}

.stat-title {
  font-size: 14px;
  color: #666;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.chart-card {
  height: 300px;
}

.chart-container {
  width: 100%;
  height: 250px;
}

.full-width {
  grid-column: 1 / -1;
}

.analysis-report {
  margin-top: 20px;
}

.report-item {
  margin-bottom: 16px;
}

.report-item h4 {
  margin: 0 0 8px 0;
  color: #1890ff;
}

.report-item p {
  margin: 0;
  line-height: 1.6;
  color: #333;
}

.distribution-controls, .categorical-controls {
  margin-bottom: 16px;
}

.no-data-hint {
  text-align: center;
  padding: 40px 0;
  color: #999;
}
</style>