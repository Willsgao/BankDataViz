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

        <!-- 简化的数据展示 -->
        <div class="data-preview">
          <el-card header="数据预览">
            <el-table
              :data="sampleData"
              border
              stripe
              size="small"
              style="width: 100%"
              max-height="300"
            >
              <el-table-column
                v-for="header in tableHeaders"
                :key="header"
                :prop="header"
                :label="header"
                min-width="120"
                show-overflow-tooltip
              />
            </el-table>
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

        <div class="stats-display" v-if="selectedNumericColumn">
          <el-card :header="`${selectedNumericColumn} - 统计信息`">
            <div class="stats-grid">
              <div class="stat-item" v-for="(value, key) in numericStats" :key="key">
                <span class="stat-label">{{ key }}:</span>
                <span class="stat-value">{{ value }}</span>
              </div>
            </div>
          </el-card>
        </div>

        <div v-else class="no-data-hint">
          <el-empty description="请选择一个数值列进行分析" />
        </div>
      </div>

      <!-- 相关性分析 -->
      <div v-if="activeVizType === 'correlation'" class="viz-content">
        <div v-if="numericColumns.length > 1">
          <el-card header="相关性矩阵">
            <el-table
              :data="correlationMatrix"
              border
              size="small"
              style="width: 100%"
            >
              <el-table-column
                prop="column"
                label="列名"
                min-width="120"
                fixed
              />
              <el-table-column
                v-for="col in numericColumns"
                :key="col"
                :label="col"
                min-width="100"
              >
                <template #default="{ row }">
                  <span :class="getCorrelationClass(row[col])">
                    {{ formatCorrelation(row[col]) }}
                  </span>
                </template>
              </el-table-column>
            </el-table>
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

        <div v-if="selectedCategoricalColumn">
          <el-card :header="`${selectedCategoricalColumn} - 分类统计`">
            <el-table
              :data="categoryStats"
              border
              size="small"
              style="width: 100%"
              max-height="300"
            >
              <el-table-column
                prop="value"
                label="分类值"
                min-width="150"
              />
              <el-table-column
                prop="count"
                label="数量"
                width="100"
              />
              <el-table-column
                prop="percentage"
                label="百分比"
                width="100"
              />
            </el-table>
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
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

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

// 计算属性
const currentSheet = computed(() => {
  return props.excelData.sheets?.find(sheet => sheet.sheetName === activeSheet.value) ||
         props.excelData.sheets?.[0]
})

const sheetData = computed(() => {
  return currentSheet.value?.data || props.excelData.data || []
})

const tableHeaders = computed(() => {
  if (!sheetData.value || sheetData.value.length === 0) return []
  return Object.keys(sheetData.value[0] || {})
})

const sampleData = computed(() => {
  return sheetData.value.slice(0, 10) // 只显示前10行作为样本
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

const numericStats = computed(() => {
  if (!selectedNumericColumn.value || !sheetData.value.length) return {}

  const values = sheetData.value
    .map(row => parseFloat(row[selectedNumericColumn.value]))
    .filter(val => !isNaN(val))

  if (values.length === 0) return {}

  const sum = values.reduce((a, b) => a + b, 0)
  const mean = sum / values.length
  const sorted = [...values].sort((a, b) => a - b)
  const median = sorted[Math.floor(sorted.length / 2)]
  const min = Math.min(...values)
  const max = Math.max(...values)

  return {
    '平均值': mean.toFixed(2),
    '中位数': median.toFixed(2),
    '最小值': min.toFixed(2),
    '最大值': max.toFixed(2),
    '数据量': values.length
  }
})

const correlationMatrix = computed(() => {
  if (numericColumns.value.length < 2) return []

  const matrix = []
  numericColumns.value.forEach(col1 => {
    const row = { column: col1 }
    numericColumns.value.forEach(col2 => {
      if (col1 === col2) {
        row[col2] = 1
      } else {
        row[col2] = calculateCorrelation(col1, col2)
      }
    })
    matrix.push(row)
  })

  return matrix
})

const categoryStats = computed(() => {
  if (!selectedCategoricalColumn.value || !sheetData.value.length) return []

  const valueCounts = {}
  sheetData.value.forEach(row => {
    const value = row[selectedCategoricalColumn.value]
    if (value !== null && value !== undefined && value !== '') {
      valueCounts[value] = (valueCounts[value] || 0) + 1
    }
  })

  const total = Object.values(valueCounts).reduce((sum, count) => sum + count, 0)

  return Object.entries(valueCounts)
    .sort(([,a], [,b]) => b - a)
    .slice(0, 20) // 只显示前20个分类
    .map(([value, count]) => ({
      value,
      count,
      percentage: ((count / total) * 100).toFixed(1) + '%'
    }))
})

const overviewStats = computed(() => {
  const data = sheetData.value
  if (!data || data.length === 0) return []

  const totalRows = data.length
  const totalCols = tableHeaders.value.length
  const numericCols = numericColumns.value.length
  const categoricalCols = categoricalColumns.value.length

  // 计算缺失值
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
      content: `数据集包含 ${data.length} 行，${tableHeaders.value.length} 列，其中数值型列 ${numericColumns.value.length} 个，分类型列 ${categoricalColumns.value.length} 个。`
    },
    {
      type: 'quality',
      title: '数据质量',
      content: overviewStats.value.find(stat => stat.title === '数据完整性')?.value ?
               `数据完整性为 ${overviewStats.value.find(stat => stat.title === '数据完整性')?.value}，建议关注数据清理工作。` :
               '数据质量良好。'
    },
    {
      type: 'recommendation',
      title: '分析建议',
      content: numericColumns.value.length > 0 ?
               '建议重点关注数值列的分布情况和相关性分析。' :
               '建议进行分类数据的频次分析和交叉分析。'
    }
  ]
})

// 方法
const calculateCorrelation = (col1, col2) => {
  const values1 = sheetData.value.map(row => parseFloat(row[col1])).filter(val => !isNaN(val))
  const values2 = sheetData.value.map(row => parseFloat(row[col2])).filter(val => !isNaN(val))

  if (values1.length !== values2.length || values1.length === 0) return 0

  const mean1 = values1.reduce((sum, val) => sum + val, 0) / values1.length
  const mean2 = values2.reduce((sum, val) => sum + val, 0) / values2.length

  let numerator = 0
  let denominator1 = 0
  let denominator2 = 0

  for (let i = 0; i < values1.length; i++) {
    const diff1 = values1[i] - mean1
    const diff2 = values2[i] - mean2
    numerator += diff1 * diff2
    denominator1 += diff1 * diff1
    denominator2 += diff2 * diff2
  }

  if (denominator1 === 0 || denominator2 === 0) return 0
  return numerator / Math.sqrt(denominator1 * denominator2)
}

const formatCorrelation = (value) => {
  return value.toFixed(3)
}

const getCorrelationClass = (value) => {
  const absValue = Math.abs(value)
  if (absValue > 0.7) return 'high-correlation'
  if (absValue > 0.3) return 'medium-correlation'
  return 'low-correlation'
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
    loading.value = false
    ElMessage.success('分析已刷新')
  }, 500)
}

const onSheetChange = () => {
  console.log('切换工作表:', activeSheet.value)
}

// 监听器
watch(() => props.visible, (newVal) => {
  if (newVal) {
    // 设置默认激活的工作表
    if (props.excelData.sheets && props.excelData.sheets.length > 0) {
      activeSheet.value = props.excelData.sheets[0].sheetName
    }
  }
})

watch(() => activeSheet.value, () => {
  // 重置选择
  selectedNumericColumn.value = ''
  selectedCategoricalColumn.value = ''
})
</script>

<style scoped>
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

.data-preview {
  margin-bottom: 20px;
}

.stats-display {
  margin-bottom: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.stat-label {
  font-weight: 500;
  color: #606266;
}

.stat-value {
  color: #1890ff;
  font-weight: bold;
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

.high-correlation {
  color: #f56c6c;
  font-weight: bold;
}

.medium-correlation {
  color: #e6a23c;
}

.low-correlation {
  color: #909399;
}
</style>