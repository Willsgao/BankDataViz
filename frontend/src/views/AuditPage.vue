<template>
  <div class="audit-page">
    <!-- 顶部标题 -->
    <div class="page-header">
      <div class="header-title">
        <span class="icon">&#128202;</span>
        会计勾稽验证
        <el-tag
          size="small"
          type="warning"
          style="margin-left: 10px"
        >
          NEW
        </el-tag>
      </div>
      <div class="header-actions">
        <el-button
          size="small"
          @click="loadRules"
        >
          <span>&#128260;</span> 刷新规则
        </el-button>
      </div>
    </div>

    <!-- 主体内容 -->
    <div class="page-body">
      <div class="layout">
        <!-- 左侧：档案列表 -->
        <div class="sidebar">
          <div class="sidebar-header">
            <span>&#128193;</span> 档案列表
            <span class="count">{{ files.length }}</span>
          </div>
          <div class="file-list">
            <div
              v-for="file in files"
              :key="file.id"
              class="file-item"
              :class="{ selected: selectedFile && selectedFile.id === file.id }"
              @click="selectFile(file)"
            >
              <div
                class="file-name"
                :title="file.name"
              >
                {{ file.name }}
              </div>
              <div class="file-meta">
                <span
                  v-if="file.sheet_count"
                  class="sheet-count"
                >&#128196; {{ file.sheet_count }}个报表</span>
                <span
                  v-if="file.last_status === 'completed'"
                  class="status-ok"
                >&#10004;</span>
                <span
                  v-if="file.last_fail > 0"
                  class="status-fail"
                >&#10006; {{ file.last_fail }}</span>
              </div>
            </div>
            <div
              v-if="files.length === 0 && !loadingFiles"
              class="empty-tip"
            >
              暂无可校验档案<br>请先在数据解析中完成PDF处理
            </div>
          </div>
          <div class="sidebar-footer">
            <!-- Step 1: 选择档案后，显示"下一步" -->
            <template v-if="currentStep === 1">
              <el-button
                type="primary"
                :disabled="!selectedFile || loadingSheets"
                style="width: 100%"
                @click="goToStep2"
              >
                <span
                  v-if="loadingSheets"
                  class="spinner"
                />
                <span v-else>&#9654;</span>
                {{ loadingSheets ? '加载中...' : '下一步：选择规则' }}
              </el-button>
            </template>
            <!-- Step 2: 显示"开始校验"和"返回" -->
            <template v-else-if="currentStep === 2">
              <el-button
                style="width: 100%; margin-bottom: 8px"
                @click="goToStep1"
              >
                &#8592; 返回
              </el-button>
              <el-button
                type="warning"
                :loading="isRunning"
                :disabled="isRunning"
                style="width: 100%"
                @click="runAudit"
              >
                <span
                  v-if="isRunning"
                  class="spinner"
                />
                <span v-else>&#9654;</span>
                {{ isRunning ? '校验中...' : '开始校验' }}
              </el-button>
            </template>
            <!-- Step 3: 显示"重新选择" -->
            <template v-else-if="currentStep === 3">
              <el-button
                type="primary"
                style="width: 100%"
                @click="goToStep1"
              >
                &#8592; 重新选择档案
              </el-button>
            </template>
          </div>
        </div>

        <!-- 右侧主区域 -->
        <div class="main-area">
          <!-- ========== Step 1: 规则配置 ========== -->
          <div
            v-if="currentStep === 1"
            class="rules-panel"
          >
            <div
              class="panel-header"
              @click="rulesExpanded = !rulesExpanded"
            >
              <span>&#9881; 校验规则配置</span>
              <span class="rule-count">已选择 {{ enabledRuleCount }} / {{ rules.length }} 条</span>
              <span
                class="toggle-icon"
                :style="{ transform: rulesExpanded ? 'rotate(0deg)' : 'rotate(-90deg)' }"
              >
                &#9660;
              </span>
            </div>
            <div
              v-show="rulesExpanded"
              class="rules-grid"
            >
              <div
                v-for="rule in rules"
                :key="rule.id"
                class="rule-card"
                :class="{ disabled: !rule.enabled }"
              >
                <div class="rule-card-left">
                  <el-checkbox v-model="rule.enabled" />
                  <span
                    class="rule-icon"
                    :style="{ background: getRuleColor(rule.category) }"
                  >
                    {{ getRuleIcon(rule.rule_type) }}
                  </span>
                </div>
                <div class="rule-info">
                  <div class="rule-name">
                    {{ rule.name }}
                  </div>
                  <div class="rule-desc">
                    {{ rule.description }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- ========== Step 2: Sheet 预览 + 规则映射 + 字段分析 ========== -->
          <div
            v-else-if="currentStep === 2"
            class="mapping-panel"
          >
            <div class="panel-header">
              <span>&#128196; 规则 → Sheet 映射确认</span>
              <span class="rule-count">已勾选 {{ enabledRuleCount }} 条规则</span>
            </div>

            <!-- 字段分析提示 -->
            <div
              v-if="uncertainFields.length > 0"
              class="field-analysis-banner"
            >
              <div class="banner-icon">
                &#9888;
              </div>
              <div class="banner-content">
                <div class="banner-title">
                  检测到 {{ uncertainFields.length }} 个需要确认的字段映射
                </div>
                <div class="banner-desc">
                  部分字段在 Sheet 中未找到精确匹配，建议在执行前确认
                </div>
              </div>
              <el-button
                size="small"
                @click="reanalyzeMapping"
              >
                重新分析
              </el-button>
            </div>

            <!-- 启用规则列表 + 每条规则的 Sheet 选择 -->
            <div class="mapping-rules">
              <div
                v-for="rule in enabledRules"
                :key="rule.id"
                class="mapping-rule-item"
                :class="{ 'has-warning': getRuleUncertainCount(rule.id) > 0 }"
              >
                <div class="mapping-rule-header">
                  <span
                    class="rule-icon-sm"
                    :style="{ background: getRuleColor(rule.category) }"
                  >
                    {{ getRuleIcon(rule.rule_type) }}
                  </span>
                  <span class="rule-name-sm">{{ rule.name }}</span>
                  <!-- 自动推荐标签 -->
                  <el-tag
                    v-if="autoSuggested[rule.id]"
                    size="small"
                    type="info"
                    style="margin-left: 8px"
                  >
                    自动推荐
                  </el-tag>
                  <!-- 字段确认状态 -->
                  <el-tag 
                    v-if="sheetMapping[rule.id]" 
                    size="small" 
                    :type="getRuleUncertainCount(rule.id) > 0 ? 'warning' : 'success'"
                    style="margin-left: 4px"
                  >
                    {{ getRuleUncertainCount(rule.id) > 0 ? '⚠ ' + getRuleUncertainCount(rule.id) + ' 字段待确认' : '字段已确认' }}
                  </el-tag>
                </div>
                <div class="mapping-rule-body">
                  <span class="mapping-label">使用 Sheet：</span>
                  <el-select
                    v-model="sheetMapping[rule.id]"
                    placeholder="请选择 Sheet"
                    style="flex: 1"
                    filterable
                    clearable
                    @change="() => onSheetChange(rule.id)"
                  >
                    <el-option
                      v-for="sheet in sheets"
                      :key="sheet.name"
                      :label="sheet.name"
                      :value="sheet.name"
                    >
                      <div class="sheet-option">
                        <span class="sheet-option-name">{{ sheet.name }}</span>
                        <span class="sheet-option-meta">{{ sheet.row_count }}行 x {{ sheet.col_count }}列</span>
                      </div>
                    </el-option>
                  </el-select>
                  <!-- 预览按钮 -->
                  <el-button
                    v-if="sheetMapping[rule.id]"
                    size="small"
                    type="text"
                    @click="previewSheet(sheetMapping[rule.id])"
                  >
                    &#128065; 预览
                  </el-button>
                </div>
                
                <!-- 字段映射状态详情 -->
                <div
                  v-if="sheetMapping[rule.id]"
                  class="field-mapping-status"
                >
                  <div 
                    v-for="field in getRuleFields(rule.id)" 
                    :key="field.role"
                    class="field-status-item"
                    :class="{ uncertain: field.confidence === 'low' }"
                  >
                    <span class="field-role">{{ field.role }}:</span>
                    <span class="field-name">{{ field.field || '-' }}</span>
                    <span
                      v-if="field.confidence === 'high'"
                      class="field-badge success"
                    >✓ 已匹配</span>
                    <span
                      v-else
                      class="field-badge warning"
                    >? 待确认</span>
                  </div>
                </div>
                
                <!-- Sheet 摘要提示 -->
                <div
                  v-if="sheetMapping[rule.id]"
                  class="sheet-hint"
                >
                  {{ getSheetHint(sheetMapping[rule.id]) }}
                </div>
              </div>

              <div
                v-if="enabledRules.length === 0"
                class="no-rules-tip"
              >
                请先在左侧选择档案，然后勾选要执行的规则
              </div>
            </div>
          </div>

          <!-- ========== Step 3: 结果展示 ========== -->
          <template v-else-if="currentStep === 3">
            <!-- 统计概览 -->
            <div class="stats-row">
              <div class="stat-card pass">
                <div class="stat-icon">
                  &#10004;
                </div>
                <div class="stat-num green">
                  {{ stats.pass }}
                </div>
                <div class="stat-label">
                  通过
                </div>
              </div>
              <div class="stat-card warn">
                <div class="stat-icon">
                  &#9888;
                </div>
                <div class="stat-num orange">
                  {{ stats.warn }}
                </div>
                <div class="stat-label">
                  警告
                </div>
              </div>
              <div class="stat-card fail">
                <div class="stat-icon">
                  &#10006;
                </div>
                <div class="stat-num red">
                  {{ stats.fail }}
                </div>
                <div class="stat-label">
                  失败
                </div>
              </div>
              <div class="stat-card total">
                <div class="stat-info">
                  <div class="stat-num blue">
                    {{ stats.total }}
                  </div>
                  <div class="stat-label">
                    总规则
                  </div>
                </div>
                <div class="pass-rate">
                  <div class="rate-num">
                    {{ passRate }}%
                  </div>
                  <div class="rate-label">
                    通过率
                  </div>
                </div>
              </div>
            </div>

            <!-- 结果详情 -->
            <div class="result-panel">
              <div class="panel-header">
                <span>&#128203; 校验详情</span>
                <div class="filter-tabs">
                  <div
                    v-for="tab in filterTabs"
                    :key="tab.value"
                    class="filter-tab"
                    :class="{ active: filter === tab.value }"
                    @click="filter = tab.value"
                  >
                    {{ tab.label }}
                  </div>
                </div>
              </div>

              <!-- 有结果 -->
              <div
                v-if="hasResults"
                class="result-list"
              >
                <div
                  v-for="item in filteredResults"
                  :key="item.rule_id + item.sheet_name"
                  class="result-item"
                  :class="item.status"
                  @click="showDetail(item)"
                >
                  <div class="result-status-icon">
                    <span v-if="item.status === 'pass'">&#10004;</span>
                    <span v-else-if="item.status === 'warn'">&#9888;</span>
                    <span v-else>&#10006;</span>
                  </div>
                  <div class="result-main">
                    <div class="result-title">
                      <span class="rule-tag">{{ item.rule_id }}</span>
                      {{ item.rule_name }}
                    </div>
                    <div class="result-formula">
                      {{ item.detail || '无详情' }}
                    </div>
                  </div>
                  <div class="result-meta">
                    <div class="result-period">
                      {{ item.sheet_name }}
                    </div>
                    <div class="result-values">
                      <span v-if="item.actual_value">实际: {{ item.actual_value }}</span>
                      <span v-if="item.expected_value">理论: {{ item.expected_value }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 空状态 -->
              <div
                v-else
                class="empty-state"
              >
                <div class="empty-icon">
                  &#128202;
                </div>
                <div class="empty-title">
                  暂无校验结果
                </div>
                <div class="empty-desc">
                  选择档案和规则后，点击"开始校验"
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- Sheet 预览弹窗 -->
    <el-dialog
      v-model="previewVisible"
      :title="'Sheet 预览: ' + previewSheetName"
      width="700px"
      :close-on-click-modal="true"
    >
      <div
        v-if="previewSheetData"
        class="sheet-preview"
      >
        <div class="preview-section">
          <div class="preview-label">
            横向表头（前3行）：
          </div>
          <div class="preview-table-wrap">
            <table class="preview-table">
              <tbody>
                <tr
                  v-for="(row, ri) in previewSheetData.row_headers"
                  :key="ri"
                >
                  <td class="row-num">
                    {{ '行' + (ri + 1) }}
                  </td>
                  <td
                    v-for="(cell, ci) in row"
                    :key="ci"
                    class="preview-cell"
                  >
                    {{ cell || '-' }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div
          class="preview-section"
          style="margin-top: 12px"
        >
          <div class="preview-label">
            纵向表头（前3列 x 前6行）：
          </div>
          <div class="preview-table-wrap">
            <table class="preview-table">
              <tbody>
                <tr
                  v-for="(row, ri) in previewSheetData.col_previews"
                  :key="ri"
                >
                  <td class="row-num">
                    {{ '列' + (ri + 1) }}
                  </td>
                  <td
                    v-for="(cell, ci) in row"
                    :key="ci"
                    class="preview-cell"
                  >
                    {{ cell || '-' }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      :title="'校验详情 - ' + (currentDetail?.rule_name || '')"
      width="600px"
      :close-on-click-modal="true"
    >
      <div v-if="currentDetail">
        <div
          class="detail-status-banner"
          :class="currentDetail.status"
        >
          <span v-if="currentDetail.status === 'pass'">&#10004; 校验通过</span>
          <span v-else-if="currentDetail.status === 'warn'">&#9888; 警告</span>
          <span v-else>&#10006; 校验失败</span>
          <span class="detail-sheet">{{ currentDetail.sheet_name }}</span>
        </div>
        <div class="detail-table">
          <div class="detail-row">
            <span class="detail-key">规则</span>
            <span class="detail-val">{{ currentDetail.rule_name }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-key">Sheet</span>
            <span class="detail-val">{{ currentDetail.sheet_name }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-key">实际值</span>
            <span class="detail-val highlight">{{ currentDetail.actual_value || '-' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-key">理论值</span>
            <span class="detail-val">{{ currentDetail.expected_value || '-' }}</span>
          </div>
          <div
            v-if="currentDetail.diff !== null"
            class="detail-row"
          >
            <span class="detail-key">差值</span>
            <span
              class="detail-val"
              :class="currentDetail.status === 'fail' ? 'fail-text' : ''"
            >
              {{ currentDetail.diff }}
            </span>
          </div>
          <div class="detail-row">
            <span class="detail-key">详细说明</span>
            <span class="detail-val detail-full">{{ currentDetail.detail || '无' }}</span>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '@/api/index'

// ==================== 状态 ====================
const files = ref([])
const selectedFile = ref(null)
const rules = ref([])
const results = ref([])
const isRunning = ref(false)
const loadingFiles = ref(false)
const loadingSheets = ref(false)
const rulesExpanded = ref(true)
const filter = ref('all')
const detailVisible = ref(false)
const currentDetail = ref(null)

// Step 流程控制
const currentStep = ref(1)  // 1: 规则配置, 2: Sheet映射, 3: 结果

// Step 2 相关
const sheets = ref([])           // 当前档案的所有 Sheet
const sheetMapping = ref({})     // {rule_id: sheet_name}
const autoSuggested = ref({})    // {rule_id: bool}
const suggestions = ref([])      // 后端推荐的映射
const fieldAnalysis = ref([])    // 字段分析结果
const uncertainFields = ref([])  // 需要人工确认的字段

// Sheet 预览
const previewVisible = ref(false)
const previewSheetName = ref('')
const previewSheetData = ref(null)

const filterTabs = [
  { label: '全部', value: 'all' },
  { label: '失败', value: 'fail' },
  { label: '警告', value: 'warn' },
  { label: '通过', value: 'pass' }
]

// ==================== 计算属性 ====================
const hasResults = computed(() => results.value.length > 0)

const enabledRuleCount = computed(() => rules.value.filter(r => r.enabled).length)

const enabledRules = computed(() => rules.value.filter(r => r.enabled))

const stats = computed(() => ({
  pass: results.value.filter(r => r.status === 'pass').length,
  warn: results.value.filter(r => r.status === 'warn').length,
  fail: results.value.filter(r => r.status === 'fail').length,
  total: results.value.length
}))

const passRate = computed(() => {
  if (stats.value.total === 0) return 0
  return Math.round((stats.value.pass / stats.value.total) * 100)
})

const filteredResults = computed(() => {
  if (filter.value === 'all') return results.value
  return results.value.filter(r => r.status === filter.value)
})

// ==================== 方法 ====================
function selectFile(file) {
  selectedFile.value = file
}

async function loadFiles() {
  loadingFiles.value = true
  try {
    // 优先使用 DAL API
    let res
    try {
      res = await http.get('/api/audit/files/dal')
    } catch {
      // 降级到旧 API
      res = await http.get('/api/audit/files/available')
      files.value = res.files || []
      return
    }
    
    if (res.success) {
      files.value = res.files || []
    } else {
      // 降级到旧 API
      res = await http.get('/api/audit/files/available')
      files.value = res.files || []
    }
  } catch (e) {
    console.error('加载档案列表失败:', e)
    ElMessage.error('加载档案列表失败: ' + (e.message || ''))
  } finally {
    loadingFiles.value = false
  }
}

async function loadRules() {
  try {
    const res = await http.get('/api/audit/rules')
    rules.value = res.rules || []
  } catch (e) {
    console.error('加载规则失败:', e)
    ElMessage.error('加载规则失败')
  }
}

// ========== Step 流程 ==========

// Step 1 → Step 2: 加载 Sheet 列表 + 获取推荐映射
async function goToStep2() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择一个档案')
    return
  }
  const enabled = enabledRules.value
  if (enabled.length === 0) {
    ElMessage.warning('请至少勾选一条校验规则')
    return
  }

  loadingSheets.value = true
  currentStep.value = 2
  sheetMapping.value = {}
  autoSuggested.value = {}
  suggestions.value = []
  fieldAnalysis.value = []  // 清空字段分析结果
  uncertainFields.value = []  // 清空待确认字段

  try {
    // 1. 优先使用 DAL API 加载所有 Sheet 摘要
    let sheetsRes
    try {
      sheetsRes = await http.get(`/api/audit/sheets/dal/${selectedFile.value.id}`)
    } catch {
      // 降级到旧 API
      sheetsRes = await http.get(`/api/audit/sheets/${selectedFile.value.id}`)
    }
    
    if (!sheetsRes.success) {
      ElMessage.error('加载 Sheet 列表失败: ' + (sheetsRes.error || ''))
      return
    }
    sheets.value = sheetsRes.sheets || []

    // 2. 获取规则推荐映射
    try {
      const suggestRes = await http.post('/api/audit/mapping/suggest', {
        sheets: sheetsRes.sheets,
        rules: enabled
      })
      if (suggestRes.success) {
        suggestions.value = suggestRes.rule_suggestions || []
        // 应用推荐映射
        for (const sug of suggestions.value) {
          if (sug.suggested_sheet) {
            sheetMapping.value[sug.rule_id] = sug.suggested_sheet
            autoSuggested.value[sug.rule_id] = true
          }
        }
      }
    } catch (e) {
      console.warn('获取推荐映射失败，使用自动匹配:', e)
    }

    // 3. 加载 Sheet 详情并进行分析
    await loadSheetAnalysis()

    if (sheets.value.length === 0) {
      ElMessage.warning('该档案没有找到任何 Sheet')
    }
  } catch (e) {
    console.error('加载 Sheet 失败:', e)
    ElMessage.error('加载 Sheet 列表失败: ' + (e.message || ''))
  } finally {
    loadingSheets.value = false
  }
}

// 加载 Sheet 分析（字段映射分析）
async function loadSheetAnalysis() {
  // 对每个已映射 Sheet 进行字段分析
  fieldAnalysis.value = []
  uncertainFields.value = []
  
  for (const [ruleId, sheetName] of Object.entries(sheetMapping.value)) {
    if (!sheetName) continue
    
    try {
      const res = await http.post('/api/audit/fields/analyze', {
        file_id: selectedFile.value.id,
        sheet_name: sheetName,
        rules: [rules.value.find(r => r.id === ruleId)].filter(Boolean)
      })
      
      if (res.success) {
        fieldAnalysis.value.push(...(res.field_analysis || []))
        uncertainFields.value.push(...(res.uncertain_fields || []))
      }
    } catch (e) {
      console.warn(`分析 Sheet ${sheetName} 失败:`, e)
    }
  }
}

// 重新分析当前映射
async function reanalyzeMapping() {
  sheetMapping.value = {}
  autoSuggested.value = {}
  
  // 应用推荐映射
  for (const sug of suggestions.value) {
    if (sug.suggested_sheet) {
      sheetMapping.value[sug.rule_id] = sug.suggested_sheet
      autoSuggested.value[sug.rule_id] = true
    }
  }
  
  // 重新分析
  await loadSheetAnalysis()
}

function goToStep1() {
  currentStep.value = 1
  results.value = []
  fieldAnalysis.value = []
  uncertainFields.value = []
}

function goToStep3() {
  currentStep.value = 3
}

async function runAudit() {
  // 检查映射
  const enabled = enabledRules.value
  const unmapped = enabled.filter(r => !sheetMapping.value[r.id])
  if (unmapped.length > 0) {
    ElMessage.warning(`请为以下规则选择 Sheet：${unmapped.map(r => r.name).join('、')}`)
    return
  }

  isRunning.value = true
  results.value = []
  try {
    // 优先使用 DAL API
    let res
    try {
      res = await http.post('/api/audit/run-dal', {
        file_id: selectedFile.value.id,
        file_name: selectedFile.value.name,
        rule_ids: enabled.map(r => r.id),
        sheet_mapping: sheetMapping.value
      })
    } catch {
      // 降级到旧 API
      res = await http.post('/api/audit/run', {
        file_id: selectedFile.value.id,
        file_name: selectedFile.value.name,
        rule_ids: enabled.map(r => r.id),
        sheet_mapping: sheetMapping.value
      })
    }

    if (res.success) {
      results.value = res.results || []
      ElMessage.success(
        `校验完成：通过 ${res.pass_count} | 警告 ${res.warn_count} | 失败 ${res.fail_count}`
      )
      goToStep3()
    } else {
      ElMessage.error('校验失败: ' + (res.error || ''))
    }
  } catch (e) {
    console.error('校验请求失败:', e)
    ElMessage.error('校验请求失败: ' + (e.message || ''))
  } finally {
    isRunning.value = false
  }
}

// Sheet 预览
async function previewSheet(sheetName) {
  previewSheetName.value = sheetName
  
  // 先用已有的缓存数据
  const sheet = sheets.value.find(s => s.name === sheetName)
  if (sheet) {
    // 尝试从缓存获取详细数据
    previewSheetData.value = {
      row_headers: sheet.header_preview ? [sheet.header_preview] : (sheet.row_headers || []),
      col_previews: sheet.row_preview ? sheet.row_preview.slice(0, 3) : []
    }
  }
  
  previewVisible.value = true
  
  // 如果需要更详细的数据，可以调用 API
  // const res = await http.get(`/api/audit/sheet/${selectedFile.value.id}/${sheetName}`)
}

function getSheetHint(sheetName) {
  const sheet = sheets.value.find(s => s.name === sheetName)
  if (!sheet) return ''
  
  // 新 DAL API 格式
  if (sheet.header_preview && sheet.header_preview.length > 0) {
    const preview = sheet.header_preview.slice(0, 3).join(' | ')
    return preview || `${sheet.row_count}行 x ${sheet.col_count}列`
  }
  
  // 旧 API 格式
  const firstRow = sheet.row_headers?.[0] || []
  const preview = firstRow.filter(Boolean).slice(0, 3).join(' | ')
  return preview || `${sheet.row_count || sheet.max_row}行 x ${sheet.col_count || sheet.max_col}列`
}

function showDetail(item) {
  currentDetail.value = item
  detailVisible.value = true
}

function getRuleColor(category) {
  const map = {
    '资本充足率': '#e6f4ff',
    '杠杆率': '#f9f0ff',
    '风险加权资产': '#fff7e6',
    '流动性覆盖率': '#fff1f0',
    '净稳定资金比例': '#f6ffed',
    '跨期一致性': '#e6fffb',
    '流动性风险': '#fff1f0',
    '操作风险': '#f0f5ff'
  }
  return map[category] || '#f5f5f5'
}

// 获取规则需要确认的字段数量
function getRuleUncertainCount(ruleId) {
  const analysis = fieldAnalysis.value.find(a => a.rule_id === ruleId)
  if (!analysis) return 0
  return analysis.fields.filter(f => f.confidence === 'low').length
}

// 获取规则的字段分析结果
function getRuleFields(ruleId) {
  const analysis = fieldAnalysis.value.find(a => a.rule_id === ruleId)
  if (!analysis) return []
  return analysis.fields
}

// Sheet 选择变化时，重新分析字段
async function onSheetChange(ruleId) {
  if (!sheetMapping.value[ruleId]) {
    // 清空该规则的字段分析
    fieldAnalysis.value = fieldAnalysis.value.filter(a => a.rule_id !== ruleId)
    uncertainFields.value = uncertainFields.value.filter(f => f.rule_id !== ruleId)
    return
  }
  
  // 重新分析该 Sheet
  try {
    const res = await http.post('/api/audit/fields/analyze', {
      file_id: selectedFile.value.id,
      sheet_name: sheetMapping.value[ruleId],
      rules: [rules.value.find(r => r.id === ruleId)].filter(Boolean)
    })
    
    if (res.success) {
      // 替换或添加该规则的字段分析
      fieldAnalysis.value = [
        ...fieldAnalysis.value.filter(a => a.rule_id !== ruleId),
        ...(res.field_analysis || [])
      ]
      uncertainFields.value = [
        ...uncertainFields.value.filter(f => f.rule_id !== ruleId),
        ...(res.uncertain_fields || [])
      ]
    }
  } catch (e) {
    console.warn('字段分析失败:', e)
  }
}

function getRuleIcon(ruleType) {
  const map = {
    'formula': '=',
    'sum_check': '\u03A3',
    'periodicity': '\u2194'
  }
  return map[ruleType] || '?'
}

// ==================== 生命周期 ====================
onMounted(() => {
  loadFiles()
  loadRules()
})
</script>

<style scoped>
.audit-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f0f2f5;
}

/* ===== 顶部标题 ===== */
.page-header {
  background: #fff;
  padding: 14px 24px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #262626;
}

.header-title .icon {
  margin-right: 8px;
}

/* ===== 页面主体 ===== */
.page-body {
  flex: 1;
  padding: 16px 24px;
  overflow: hidden;
}

.layout {
  display: flex;
  gap: 16px;
  height: 100%;
}

/* ===== 左侧边栏 ===== */
.sidebar {
  width: 260px;
  background: #fff;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
}

.sidebar-header {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  font-size: 14px;
  font-weight: 600;
  color: #262626;
  display: flex;
  align-items: center;
  gap: 6px;
}

.sidebar-header .count {
  margin-left: auto;
  background: #f5f5f5;
  color: #8c8c8c;
  font-size: 12px;
  padding: 1px 8px;
  border-radius: 10px;
  font-weight: 400;
}

.file-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.file-item {
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
  margin-bottom: 4px;
}

.file-item:hover { background: #f5f8ff; }

.file-item.selected {
  background: #e6f4ff;
  border-color: #1890ff;
}

.file-name {
  font-size: 13px;
  color: #262626;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.file-meta {
  font-size: 11px;
  color: #8c8c8c;
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-ok { color: #52c41a; }
.status-fail { color: #ff4d4f; }

.empty-tip {
  text-align: center;
  padding: 24px 12px;
  color: #8c8c8c;
  font-size: 13px;
  line-height: 1.8;
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid #f0f0f0;
}

/* ===== 主内容区 ===== */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}

/* ===== 规则配置（Step 1） ===== */
.rules-panel {
  background: #fff;
  border-radius: 8px;
  flex-shrink: 0;
}

.panel-header {
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  font-size: 14px;
  font-weight: 600;
  color: #262626;
}

.panel-header:hover { background: #fafafa; }

.rule-count {
  font-size: 12px;
  color: #8c8c8c;
  font-weight: 400;
  margin-left: 4px;
}

.toggle-icon {
  margin-left: auto;
  font-size: 12px;
  transition: transform 0.2s;
  color: #8c8c8c;
}

.rules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 8px;
  padding: 12px 16px;
  max-height: 300px;
  overflow-y: auto;
}

.rule-card {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  transition: border-color 0.2s;
}

.rule-card:hover { border-color: #1890ff; }
.rule-card.disabled { opacity: 0.6; }

.rule-card-left {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.rule-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;
}

.rule-info { flex: 1; min-width: 0; }

.rule-name {
  font-size: 13px;
  font-weight: 500;
  color: #262626;
  margin-bottom: 2px;
}

.rule-desc {
  font-size: 11px;
  color: #8c8c8c;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ===== 规则映射（Step 2） ===== */
.mapping-panel {
  background: #fff;
  border-radius: 8px;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.mapping-rules {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
}

.mapping-rule-item {
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 12px;
  background: #fafafa;
}

.mapping-rule-item:hover {
  border-color: #1890ff;
  background: #f0f7ff;
}

.mapping-rule-item.has-warning {
  border-color: #fa8c16;
  background: #fffbf0;
}

.mapping-rule-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.rule-icon-sm {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.rule-name-sm {
  font-size: 14px;
  font-weight: 600;
  color: #262626;
}

.mapping-rule-body {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mapping-label {
  font-size: 13px;
  color: #595959;
  flex-shrink: 0;
}

.sheet-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.sheet-option-name {
  font-size: 13px;
}

.sheet-option-meta {
  font-size: 11px;
  color: #8c8c8c;
}

.sheet-hint {
  margin-top: 6px;
  font-size: 11px;
  color: #8c8c8c;
  padding-left: 4px;
  border-left: 2px solid #d9d9d9;
}

/* ===== 字段分析 Banner ===== */
.field-analysis-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #fffbe6;
  border-bottom: 1px solid #ffe58f;
  margin: -12px -16px 12px -16px;
}

.banner-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.banner-content {
  flex: 1;
}

.banner-title {
  font-size: 13px;
  font-weight: 600;
  color: #d46b08;
  margin-bottom: 2px;
}

.banner-desc {
  font-size: 12px;
  color: #8c8c8c;
}

/* ===== 字段映射状态 ===== */
.field-mapping-status {
  margin-top: 8px;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  padding: 4px 0;
}

.field-status-item.uncertain {
  color: #fa8c16;
}

.field-role {
  color: #8c8c8c;
  min-width: 60px;
  font-weight: 500;
}

.field-name {
  color: #262626;
  flex: 1;
}

.field-badge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
}

.field-badge.success {
  background: #f6ffed;
  color: #52c41a;
}

.field-badge.warning {
  background: #fff7e6;
  color: #fa8c16;
}

.no-rules-tip {
  text-align: center;
  padding: 40px 20px;
  color: #8c8c8c;
  font-size: 14px;
}

/* ===== 统计卡片 ===== */
.stats-row {
  display: flex;
  gap: 16px;
  flex-shrink: 0;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px 20px;
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-card.total { flex: 2; }

.stat-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.stat-num {
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}

.stat-label {
  font-size: 12px;
  color: #8c8c8c;
  margin-top: 4px;
}

.green { color: #52c41a; }
.orange { color: #fa8c16; }
.red { color: #ff4d4f; }
.blue { color: #1890ff; }

.pass-rate {
  margin-left: auto;
  text-align: right;
}

.rate-num {
  font-size: 22px;
  font-weight: 700;
  color: #52c41a;
}

.rate-label {
  font-size: 11px;
  color: #8c8c8c;
}

/* ===== 结果面板 ===== */
.result-panel {
  background: #fff;
  border-radius: 8px;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.filter-tabs {
  display: flex;
  gap: 0;
  background: #f5f5f5;
  border-radius: 6px;
  padding: 3px;
  margin-left: auto;
}

.filter-tab {
  padding: 3px 12px;
  font-size: 12px;
  border-radius: 4px;
  cursor: pointer;
  color: #595959;
  transition: all 0.2s;
}

.filter-tab.active {
  background: #fff;
  color: #1890ff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.result-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
}

.result-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.result-item:hover { border-color: #1890ff; }

.result-item.pass { border-left: 3px solid #52c41a; }
.result-item.warn { border-left: 3px solid #fa8c16; }
.result-item.fail { border-left: 3px solid #ff4d4f; }

.result-status-icon {
  font-size: 18px;
  flex-shrink: 0;
  margin-top: 2px;
}

.result-item.pass .result-status-icon { color: #52c41a; }
.result-item.warn .result-status-icon { color: #fa8c16; }
.result-item.fail .result-status-icon { color: #ff4d4f; }

.result-main { flex: 1; min-width: 0; }

.result-title {
  font-size: 14px;
  font-weight: 500;
  color: #262626;
  margin-bottom: 4px;
}

.rule-tag {
  display: inline-block;
  background: #f0f5ff;
  color: #597ef7;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
  margin-right: 4px;
  font-weight: 600;
}

.result-formula {
  font-size: 12px;
  color: #8c8c8c;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.result-meta {
  text-align: right;
  flex-shrink: 0;
}

.result-period {
  font-size: 11px;
  color: #8c8c8c;
  margin-bottom: 4px;
}

.result-values {
  display: flex;
  flex-direction: column;
  font-size: 11px;
  color: #595959;
  gap: 2px;
}

/* ===== 空状态 ===== */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #8c8c8c;
}

.empty-icon { font-size: 64px; opacity: 0.5; margin-bottom: 16px; }

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: #595959;
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 13px;
  text-align: center;
  line-height: 1.8;
}

/* ===== Sheet 预览弹窗 ===== */
.sheet-preview {
  font-size: 13px;
}

.preview-section { }

.preview-label {
  font-size: 12px;
  color: #8c8c8c;
  margin-bottom: 6px;
}

.preview-table-wrap {
  overflow-x: auto;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
}

.preview-table {
  border-collapse: collapse;
  width: 100%;
  font-size: 12px;
}

.preview-table td {
  border: 1px solid #f0f0f0;
  padding: 4px 8px;
  white-space: nowrap;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.preview-table .row-num {
  background: #fafafa;
  color: #8c8c8c;
  font-size: 11px;
  width: 40px;
  text-align: center;
}

.preview-cell {
  color: #262626;
}

/* ===== 详情弹窗 ===== */
.detail-status-banner {
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-weight: 600;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.detail-status-banner.pass { background: #f6ffed; color: #52c41a; }
.detail-status-banner.warn { background: #fffbe6; color: #fa8c16; }
.detail-status-banner.fail { background: #fff2f0; color: #ff4d4f; }

.detail-sheet {
  font-size: 12px;
  font-weight: 400;
  opacity: 0.8;
}

.detail-table { font-size: 14px; }

.detail-row {
  display: flex;
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
}

.detail-key {
  width: 100px;
  color: #8c8c8c;
  flex-shrink: 0;
}

.detail-val { color: #262626; flex: 1; }
.detail-val.highlight { color: #1890ff; font-weight: 600; }
.detail-val.fail-text { color: #ff4d4f; font-weight: 600; }
.detail-full { word-break: break-all; }

/* ===== 加载动画 ===== */
.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
  margin-right: 4px;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
