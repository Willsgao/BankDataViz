<template>
  <div class="bank-warehouse-page">
    <!-- 顶部标题栏 -->
    <div class="page-header">
      <div class="header-left">
        <el-icon class="header-icon"><DataBoard /></el-icon>
        <div>
          <h1 class="page-title">银行数据仓库</h1>
          <p class="page-subtitle">{{ stats.total_banks || 0 }} 家银行 · {{ stats.total_reports || 0 }} 份报告 · {{ stats.total_table_data || 0 }} 条数据</p>
        </div>
      </div>
      <div class="header-actions">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索银行名称或代码..."
          prefix-icon="Search"
          clearable
          style="width: 260px"
          :loading="searchLoading"
          @input="handleSearch"
          @clear="handleSearchClear"
        />
        <el-button type="primary" :icon="Refresh" @click="loadData" :loading="loading">刷新</el-button>
        <el-button type="success" :icon="Download" @click="handleSeedData" :loading="seeding">
          {{ stats.total_banks > 0 ? '重新写入演示数据' : '写入演示数据' }}
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card" v-for="card in statCards" :key="card.key">
        <div class="stat-icon" :style="{ background: card.color }">
          <el-icon><component :is="card.icon" /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左：银行列表 -->
      <div class="bank-list-panel">
        <div class="panel-header">
          <span class="panel-title">银行列表</span>
          <div class="filter-group">
            <el-select v-model="filterType" placeholder="全部类型" clearable size="small" @change="loadBanks">
              <el-option label="国有大型银行" value="国有大型银行" />
              <el-option label="股份制银行" value="股份制银行" />
              <el-option label="城市商业银行" value="城市商业银行" />
              <el-option label="农村商业银行" value="农村商业银行" />
            </el-select>
          </div>
        </div>

        <div class="bank-list" v-loading="loading">
          <div
            v-for="bank in displayBanks"
            :key="bank.id"
            class="bank-item"
            :class="{ active: selectedBank?.id === bank.id }"
            @click="selectBank(bank)"
          >
            <div class="bank-avatar" :style="{ background: getBankColor(bank.bank_type) }">
              {{ bank.bank_name.slice(2, 4) }}
            </div>
            <div class="bank-info">
              <div class="bank-name">{{ bank.bank_name }}</div>
              <div class="bank-meta">
                <el-tag size="small" :type="getBankTagType(bank.bank_type)">{{ bank.bank_type }}</el-tag>
                <span class="bank-code">{{ bank.bank_code }}</span>
              </div>
            </div>
            <div class="bank-arrow">
              <el-icon><ArrowRight /></el-icon>
            </div>
          </div>
          <el-empty
            v-if="!loading && displayBanks.length === 0"
            :description="searchKeyword.trim() ? `未找到包含「${searchKeyword}」的银行` : '暂无数据，请先写入演示数据'"
          />
        </div>
      </div>

      <!-- 右：详情面板 -->
      <div class="detail-panel" v-if="selectedBank">
        <!-- 银行基本信息 -->
        <div class="detail-header">
          <div class="detail-avatar" :style="{ background: getBankColor(selectedBank.bank_type) }">
            {{ selectedBank.bank_name.slice(2, 4) }}
          </div>
          <div class="detail-title-block">
            <h2>{{ selectedBank.bank_name }}</h2>
            <p>{{ selectedBank.description || '暂无描述' }}</p>
            <div class="detail-tags">
              <el-tag :type="getBankTagType(selectedBank.bank_type)">{{ selectedBank.bank_type }}</el-tag>
              <el-tag type="success">{{ selectedBank.bank_code }}</el-tag>
              <el-tag type="info">{{ selectedBank.listed_status === 'listed' ? '已上市' : '未上市' }}</el-tag>
            </div>
          </div>
        </div>

        <!-- 指标切换 + 图表 -->
        <div class="chart-section">
          <div class="chart-toolbar">
            <span class="section-title">财务指标趋势</span>
            <el-radio-group v-model="selectedIndicator" size="small" @change="loadTrendChart">
              <el-radio-button v-for="ind in indicatorOptions" :key="ind.value" :value="ind.value">
                {{ ind.label }}
              </el-radio-button>
            </el-radio-group>
          </div>
          <div ref="trendChartRef" class="trend-chart" v-loading="chartLoading" />
        </div>

        <!-- 数据表格 -->
        <div class="data-table-section">
          <div class="section-header">
            <span class="section-title">原始数据表</span>
            <el-select v-model="selectedTable" size="small" placeholder="选择表格" @change="loadTableData" style="width:160px">
              <el-option v-for="t in tableList" :key="t" :label="t" :value="t" />
            </el-select>
          </div>
          <el-table
            :data="tableData"
            v-loading="tableLoading"
            size="small"
            stripe
            border
            height="280"
          >
            <el-table-column prop="indicator_name" label="指标名称" width="180" fixed />
            <el-table-column prop="unit" label="单位" width="60" align="center" />
            <el-table-column v-for="year in [2020,2021,2022,2023,2024]" :key="year" :label="`${year}年`" :prop="`year_${year}`" align="right" min-width="90">
              <template #default="{ row }">
                <span :class="getValueClass(row, year)">{{ formatValue(row, year) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- 未选择时的占位 -->
      <div class="detail-panel empty-panel" v-else>
        <el-empty description="点击左侧银行查看详情">
          <template #image>
            <el-icon style="font-size: 80px; color: #c0c4cc"><Bank /></el-icon>
          </template>
        </el-empty>
      </div>
    </div>

    <!-- 对比分析浮动按钮 -->
    <div class="compare-fab" v-if="compareList.length > 0" @click="showCompareDialog = true">
      <el-badge :value="compareList.length" type="danger">
        <el-button type="primary" circle size="large" :icon="DataAnalysis" />
      </el-badge>
      <span class="fab-label">对比分析</span>
    </div>

    <!-- 多银行对比弹窗 -->
    <el-dialog v-model="showCompareDialog" title="多银行横向对比" width="900px" :close-on-click-modal="false">
      <div class="compare-toolbar">
        <el-select v-model="compareIndicator" size="default" style="width:200px" @change="loadCompareChart">
          <el-option v-for="ind in indicatorOptions" :key="ind.value" :label="ind.label" :value="ind.value" />
        </el-select>
        <el-select v-model="compareYear" size="default" style="width:100px" @change="loadCompareChart">
          <el-option v-for="y in [2024,2023,2022,2021,2020]" :key="y" :label="`${y}年`" :value="y" />
        </el-select>
        <el-button size="small" type="danger" plain @click="compareList = []">清空选择</el-button>
      </div>
      <div ref="compareChartRef" class="compare-chart" v-loading="compareLoading" />
      <div class="compare-bank-list">
        <el-tag
          v-for="bank in compareList"
          :key="bank.id"
          closable
          @close="removeFromCompare(bank)"
          class="compare-tag"
        >{{ bank.bank_name }}</el-tag>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import {
  DataBoard, Search, Refresh, Download, ArrowRight,
  Bank, DataAnalysis, TrendCharts, Document, List
} from '@element-plus/icons-vue'
import {
  getBankList, searchBanks, getBankStatistics,
  getBankReports, getReportTables, getTableIndicators,
  getIndicatorTrend, compareMultipleBanks, seedDemoData
} from '@/api/bank'

// ============================================================
// 状态
// ============================================================
const loading = ref(false)
const seeding = ref(false)
const chartLoading = ref(false)
const tableLoading = ref(false)
const compareLoading = ref(false)
const searchLoading = ref(false)

const stats = ref({ total_banks: 0, total_reports: 0, total_table_data: 0 })
const banks = ref([])
const searchResults = ref(null)  // null = 未搜索；[] = 搜索无结果；[...] = 搜索有结果
const selectedBank = ref(null)
const filterType = ref('')
const searchKeyword = ref('')

// 防抖定时器
let searchTimer = null

const tableList = ref([])
const selectedTable = ref('')
const tableData = ref([])
const currentReportId = ref(null)

const selectedIndicator = ref('净利润')
const trendChartRef = ref(null)
const compareChartRef = ref(null)
let trendChart = null
let compareChart = null

const compareList = ref([])
const showCompareDialog = ref(false)
const compareIndicator = ref('净利润')
const compareYear = ref(2024)

// ============================================================
// 计算属性
// ============================================================
// searchResults === null：未搜索，显示全部；searchResults === [] 且关键词非空：无结果
const displayBanks = computed(() => {
  if (searchResults.value !== null) return searchResults.value
  return banks.value
})

const statCards = computed(() => [
  { key: 'banks',   label: '入库银行数',   value: stats.value.total_banks || 0,      icon: 'Bank',         color: 'linear-gradient(135deg,#667eea,#764ba2)' },
  { key: 'reports', label: '报告总数',      value: stats.value.total_reports || 0,    icon: 'Document',     color: 'linear-gradient(135deg,#f093fb,#f5576c)' },
  { key: 'data',    label: '指标数据条数',  value: stats.value.total_table_data || 0, icon: 'List',         color: 'linear-gradient(135deg,#4facfe,#00f2fe)' },
  { key: 'years',   label: '覆盖年份',      value: '2020-2024',                       icon: 'TrendCharts',  color: 'linear-gradient(135deg,#43e97b,#38f9d7)' },
])

const indicatorOptions = [
  { label: '净利润',    value: '净利润' },
  { label: '营业收入',  value: '营业收入' },
  { label: '总资产',    value: '总资产' },
  { label: '净息差',    value: '净息差(%)' },
  { label: '不良贷款率', value: '不良贷款率(%)' },
  { label: '资本充足率', value: '资本充足率(%)' },
]

// ============================================================
// 方法
// ============================================================
const loadData = async () => {
  loading.value = true
  try {
    await Promise.all([loadStats(), loadBanks()])
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    const res = await getBankStatistics()
    if (res.success) stats.value = res.data
  } catch (e) { /* ignore */ }
}

const loadBanks = async () => {
  try {
    const res = await getBankList({ bank_type: filterType.value || undefined, listed_only: false, page_size: 100 })
    if (res.success) banks.value = res.data.items || []
  } catch (e) { /* ignore */ }
}

const handleSearch = (val) => {
  // 清除上一次的防抖定时器
  if (searchTimer) clearTimeout(searchTimer)

  // 关键词为空，恢复显示全部银行
  if (!val || val.trim() === '') {
    searchResults.value = null
    return
  }

  // 防抖：300ms 后才真正发请求
  searchTimer = setTimeout(async () => {
    searchLoading.value = true
    try {
      const res = await searchBanks(val.trim(), 50)
      if (res && res.success) {
        // 搜索成功，更新结果（可能为空数组，但不再是 null）
        searchResults.value = Array.isArray(res.data) ? res.data : []
        if (searchResults.value.length === 0) {
          ElMessage.info(`未找到包含"${val.trim()}"的银行`)
        }
      } else {
        // 接口返回失败，回退到本地过滤
        const keyword = val.trim().toLowerCase()
        searchResults.value = banks.value.filter(b =>
          b.bank_name.includes(val.trim()) ||
          (b.bank_code && b.bank_code.toLowerCase().includes(keyword))
        )
        if (searchResults.value.length === 0) {
          ElMessage.info(`未找到包含"${val.trim()}"的银行`)
        }
      }
    } catch (e) {
      console.warn('[搜索] API 请求失败，回退本地过滤', e)
      // API 异常时，降级为本地过滤（不影响用户体验）
      const keyword = val.trim().toLowerCase()
      searchResults.value = banks.value.filter(b =>
        b.bank_name.includes(val.trim()) ||
        (b.bank_code && b.bank_code.toLowerCase().includes(keyword))
      )
      if (searchResults.value.length === 0) {
        ElMessage.warning(`搜索服务暂时不可用，本地未找到"${val.trim()}"`)
      }
    } finally {
      searchLoading.value = false
    }
  }, 300)
}

const handleSearchClear = () => { searchResults.value = null }

const selectBank = async (bank) => {
  selectedBank.value = bank
  compareList.value = compareList.value.find(b => b.id === bank.id)
    ? compareList.value
    : [...compareList.value, bank].slice(-5) // 最多5家

  await loadBankDetail(bank)
}

const loadBankDetail = async (bank) => {
  // 加载报告
  try {
    const res = await getBankReports(bank.id)
    if (res.success && res.data.length > 0) {
      currentReportId.value = res.data[0].id
      await loadTableList()
      await loadTrendChart()
    }
  } catch (e) { /* ignore */ }
}

const loadTableList = async () => {
  if (!currentReportId.value) return
  try {
    const res = await getReportTables(currentReportId.value)
    if (res.success) {
      tableList.value = res.data
      if (res.data.length > 0) {
        selectedTable.value = res.data[0]
        await loadTableData()
      }
    }
  } catch (e) { /* ignore */ }
}

const loadTableData = async () => {
  if (!currentReportId.value || !selectedTable.value) return
  tableLoading.value = true
  try {
    const res = await getTableIndicators(currentReportId.value, selectedTable.value)
    if (res.success) {
      tableData.value = res.data.map(row => {
        const valueDict = parseValueJson(row.value_json)
        const result = { ...row, value_dict: valueDict }
        for (const year of [2020, 2021, 2022, 2023, 2024]) {
          result[`year_${year}`] = valueDict[String(year)]
        }
        return result
      })
    }
  } finally {
    tableLoading.value = false
  }
}

const loadTrendChart = async () => {
  if (!selectedBank.value || !currentReportId.value) return
  chartLoading.value = true
  try {
    const res = await getIndicatorTrend(selectedBank.value.id, selectedIndicator.value)
    if (res.success) {
      await nextTick()
      renderTrendChart(res.data)
    }
  } finally {
    chartLoading.value = false
  }
}

const renderTrendChart = (data) => {
  if (!trendChartRef.value) return
  if (!trendChart) trendChart = echarts.init(trendChartRef.value)

  const years = (data.years || [2020, 2021, 2022, 2023, 2024]).map(String)
  const values = data.values || []
  const unit = selectedIndicator.value.includes('%') ? '%' : '亿元'

  trendChart.setOption({
    tooltip: { trigger: 'axis', formatter: (params) => {
      const p = params[0]
      return `${p.axisValue}年<br/>${selectedIndicator.value}: <b>${p.value} ${unit}</b>`
    }},
    grid: { left: 60, right: 20, top: 30, bottom: 40 },
    xAxis: { type: 'category', data: years, axisLabel: { formatter: v => `${v}年` } },
    yAxis: { type: 'value', name: unit, nameTextStyle: { color: '#999' },
      axisLabel: { formatter: v => unit === '%' ? `${v}%` : `${v}` } },
    series: [{
      name: selectedIndicator.value,
      type: 'line',
      data: values,
      smooth: true,
      lineStyle: { width: 3, color: '#409EFF' },
      itemStyle: { color: '#409EFF' },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [{ offset: 0, color: 'rgba(64,158,255,0.3)' }, { offset: 1, color: 'rgba(64,158,255,0)' }] } },
      label: { show: true, formatter: ({ value }) => unit === '%' ? `${value}%` : value }
    }]
  })
}

const loadCompareChart = async () => {
  if (compareList.value.length === 0) return
  compareLoading.value = true
  try {
    const bankIds = compareList.value.map(b => b.id).join(',')
    const res = await compareMultipleBanks(bankIds, compareIndicator.value, compareYear.value)
    if (res.success) {
      await nextTick()
      renderCompareChart(res.data)
    }
  } finally {
    compareLoading.value = false
  }
}

const renderCompareChart = (data) => {
  if (!compareChartRef.value) return
  if (!compareChart) compareChart = echarts.init(compareChartRef.value)

  const unit = compareIndicator.value.includes('%') ? '%' : '亿元'
  const bankNames = data.map(d => d.bank_name)
  const values = data.map(d => {
    const v = d.value || {}
    return v[String(compareYear.value)] ?? null
  })

  compareChart.setOption({
    tooltip: { trigger: 'axis', formatter: (params) => {
      const p = params[0]
      return `${p.name}<br/>${compareIndicator.value}: <b>${p.value} ${unit}</b>`
    }},
    grid: { left: 140, right: 30, top: 30, bottom: 20 },
    xAxis: { type: 'value', name: unit },
    yAxis: { type: 'category', data: bankNames, axisLabel: { fontSize: 12 } },
    series: [{
      type: 'bar',
      data: values,
      barMaxWidth: 40,
      itemStyle: {
        color: (params) => {
          const colors = ['#409EFF','#67C23A','#E6A23C','#F56C6C','#909399','#36cfc9','#ff85c0','#ffc069','#73d13d','#85a5ff']
          return colors[params.dataIndex % colors.length]
        },
        borderRadius: [0, 4, 4, 0]
      },
      label: { show: true, position: 'right', formatter: ({ value }) => value != null ? (unit === '%' ? `${value}%` : `${value}亿`) : 'N/A' }
    }]
  })
}

// ---- 辅助 ----
const parseValueJson = (jsonStr) => {
  if (!jsonStr) return {}
  try { return JSON.parse(jsonStr) } catch { return {} }
}

const formatValue = (row, year) => {
  const v = row[`year_${year}`]
  if (v == null) return '-'
  return row.unit === '%' ? `${v}%` : v.toLocaleString()
}

const getValueClass = (row, year) => {
  const v = row[`year_${year}`]
  const prev = row[`year_${year - 1}`]
  if (v == null || prev == null) return ''
  return v > prev ? 'value-up' : v < prev ? 'value-down' : ''
}

const getBankColor = (type) => {
  const map = {
    '国有大型银行': 'linear-gradient(135deg,#667eea,#764ba2)',
    '股份制银行':   'linear-gradient(135deg,#f093fb,#f5576c)',
    '城市商业银行': 'linear-gradient(135deg,#4facfe,#00f2fe)',
    '农村商业银行': 'linear-gradient(135deg,#43e97b,#38f9d7)',
  }
  return map[type] || 'linear-gradient(135deg,#a8a8a8,#7a7a7a)'
}

const getBankTagType = (type) => {
  const map = { '国有大型银行': '', '股份制银行': 'warning', '城市商业银行': 'success', '农村商业银行': 'info' }
  return map[type] || 'info'
}

const removeFromCompare = (bank) => {
  compareList.value = compareList.value.filter(b => b.id !== bank.id)
}

const handleSeedData = async () => {
  const force = stats.value.total_banks > 0
  if (force) {
    try {
      await ElMessageBox.confirm('已有数据，是否强制重新写入演示数据？', '确认', { type: 'warning' })
    } catch { return }
  }
  seeding.value = true
  try {
    const res = await seedDemoData(force)
    if (res.success) {
      ElMessage.success(`写入完成！银行: ${res.data.banks_created || 0}，报告: ${res.data.reports_created || 0}`)
      await loadData()
    } else {
      ElMessage.error(res.error || '写入失败')
    }
  } catch (e) {
    ElMessage.error('写入失败: ' + e.message)
  } finally {
    seeding.value = false
  }
}

// ---- 监听对比弹窗打开 ----
watch(showCompareDialog, (val) => {
  if (val) nextTick(() => loadCompareChart())
})

// ---- 图表 resize ----
const handleResize = () => {
  trendChart?.resize()
  compareChart?.resize()
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  compareChart?.dispose()
})
</script>

<style scoped>
.bank-warehouse-page {
  min-height: 100vh;
  background: #f0f2f5;
  padding: 20px;
  box-sizing: border-box;
}

/* 顶部标题 */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  background: #fff;
  padding: 16px 24px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
}
.header-left { display: flex; align-items: center; gap: 12px; }
.header-icon { font-size: 36px; color: #409EFF; }
.page-title { margin: 0; font-size: 20px; font-weight: 700; color: #1a1a2e; }
.page-subtitle { margin: 2px 0 0; font-size: 13px; color: #909399; }
.header-actions { display: flex; align-items: center; gap: 10px; }

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
}
.stat-icon {
  width: 52px; height: 52px;
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; color: #fff; flex-shrink: 0;
}
.stat-value { font-size: 22px; font-weight: 700; color: #1a1a2e; }
.stat-label { font-size: 13px; color: #909399; margin-top: 2px; }

/* 主内容 */
.main-content {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 16px;
  min-height: 600px;
}

/* 银行列表 */
.bank-list-panel {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
  overflow: hidden;
  display: flex; flex-direction: column;
}
.panel-header {
  padding: 14px 16px;
  border-bottom: 1px solid #f0f0f0;
  display: flex; align-items: center; justify-content: space-between;
}
.panel-title { font-weight: 600; font-size: 14px; color: #1a1a2e; }
.bank-list { flex: 1; overflow-y: auto; }
.bank-item {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 16px; cursor: pointer;
  border-bottom: 1px solid #f9f9f9;
  transition: all .2s;
}
.bank-item:hover { background: #f5f7ff; }
.bank-item.active { background: #ecf5ff; border-right: 3px solid #409EFF; }
.bank-avatar {
  width: 40px; height: 40px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 600; color: #fff; flex-shrink: 0;
}
.bank-info { flex: 1; min-width: 0; }
.bank-name { font-size: 13px; font-weight: 500; color: #303133; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bank-meta { display: flex; align-items: center; gap: 6px; margin-top: 4px; }
.bank-code { font-size: 11px; color: #c0c4cc; }
.bank-arrow { color: #c0c4cc; }

/* 详情面板 */
.detail-panel {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
  padding: 24px;
  overflow-y: auto;
}
.empty-panel {
  display: flex; align-items: center; justify-content: center;
}
.detail-header {
  display: flex; align-items: flex-start; gap: 16px;
  padding-bottom: 20px; border-bottom: 1px solid #f0f0f0; margin-bottom: 20px;
}
.detail-avatar {
  width: 64px; height: 64px; border-radius: 16px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; font-weight: 700; color: #fff; flex-shrink: 0;
}
.detail-title-block h2 { margin: 0 0 4px; font-size: 20px; color: #1a1a2e; }
.detail-title-block p { margin: 0 0 8px; font-size: 13px; color: #909399; }
.detail-tags { display: flex; gap: 8px; flex-wrap: wrap; }

/* 图表区 */
.chart-section {
  margin-bottom: 24px;
  border: 1px solid #f0f0f0;
  border-radius: 10px;
  overflow: hidden;
}
.chart-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; background: #fafafa; border-bottom: 1px solid #f0f0f0;
}
.section-title { font-size: 14px; font-weight: 600; color: #303133; }
.trend-chart { height: 240px; padding: 8px; }

/* 数据表格区 */
.data-table-section { border: 1px solid #f0f0f0; border-radius: 10px; overflow: hidden; }
.section-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; background: #fafafa; border-bottom: 1px solid #f0f0f0;
}

.value-up { color: #f56c6c; font-weight: 500; }
.value-down { color: #67c23a; font-weight: 500; }

/* 对比浮动按钮 */
.compare-fab {
  position: fixed; right: 32px; bottom: 40px;
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  cursor: pointer; z-index: 999;
}
.fab-label { font-size: 12px; color: #409EFF; background: #fff; padding: 2px 8px; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,.15); }

/* 对比弹窗 */
.compare-toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.compare-chart { height: 320px; }
.compare-bank-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
.compare-tag { cursor: default; }

/* 响应式 */
@media (max-width: 1200px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .main-content { grid-template-columns: 260px 1fr; }
}
</style>
