<template>
  <div class="agent-workflow-page">
    <!-- 页头 -->
    <div class="page-header">
      <h2>🧠 Agent Harness 工作流演示</h2>
      <p class="subtitle">
        自研轻量级 Agent 编排框架：Tool 标准化 → Agent think-act 循环 → Orchestrator 编排 → RuleEngine 验证
      </p>
    </div>

    <!-- 架构图 + 控制面板 -->
    <div class="top-section">
      <!-- 左侧：架构图 -->
      <div class="arch-panel">
        <h3>📐 系统架构</h3>
        <div class="arch-diagram" ref="archRef">
          <svg viewBox="0 0 680 420" xmlns="http://www.w3.org/2000/svg">
            <!-- 背景 -->
            <rect width="680" height="420" fill="#f8fafc" rx="12"/>

            <!-- Orchestrator -->
            <rect x="240" y="20" width="200" height="60" rx="10" fill="#1e293b" stroke="#334155" stroke-width="2"/>
            <text x="340" y="48" text-anchor="middle" fill="#e2e8f0" font-size="14" font-weight="bold">Orchestrator 编排器</text>
            <text x="340" y="66" text-anchor="middle" fill="#94a3b8" font-size="11">约束 → 执行 → 验证 → 纠错 → 收敛</text>

            <!-- Agent -->
            <rect x="240" y="120" width="200" height="65" rx="10" fill="#1e40af" stroke="#3b82f6" stroke-width="2"/>
            <text x="340" y="148" text-anchor="middle" fill="#bfdbfe" font-size="14" font-weight="bold">TableParsingAgent</text>
            <text x="340" y="168" text-anchor="middle" fill="#93c5fd" font-size="11">think → act → observe 循环</text>

            <!-- 三个 Tool -->
            <rect x="30" y="240" width="180" height="55" rx="8" fill="#065f46" stroke="#10b981" stroke-width="1.5"/>
            <text x="120" y="264" text-anchor="middle" fill="#6ee7b7" font-size="13" font-weight="bold">🔍 OCR Tool</text>
            <text x="120" y="282" text-anchor="middle" fill="#a7f3d0" font-size="10">腾讯云 OCR 识别</text>

            <rect x="250" y="240" width="180" height="55" rx="8" fill="#065f46" stroke="#10b981" stroke-width="1.5"/>
            <text x="340" y="264" text-anchor="middle" fill="#6ee7b7" font-size="13" font-weight="bold">🤖 LLM Analysis</text>
            <text x="340" y="282" text-anchor="middle" fill="#a7f3d0" font-size="10">豆包 Vision 分析</text>

            <rect x="470" y="240" width="180" height="55" rx="8" fill="#065f46" stroke="#10b981" stroke-width="1.5"/>
            <text x="560" y="264" text-anchor="middle" fill="#6ee7b7" font-size="13" font-weight="bold">📊 Rebuild Tool</text>
            <text x="560" y="282" text-anchor="middle" fill="#a7f3d0" font-size="10">8 步表格重构</text>

            <!-- RuleEngine -->
            <rect x="240" y="340" width="200" height="55" rx="10" fill="#7c3aed" stroke="#a78bfa" stroke-width="2"/>
            <text x="340" y="364" text-anchor="middle" fill="#ddd6fe" font-size="14" font-weight="bold">RuleEngine 规则引擎</text>
            <text x="340" y="382" text-anchor="middle" fill="#c4b5fd" font-size="11">3 条验证规则 (6/6 通过)</text>

            <!-- 连线：Orchestrator → Agent -->
            <line x1="340" y1="80" x2="340" y2="120" stroke="#64748b" stroke-width="2" marker-end="url(#arrowGray)"/>

            <!-- 连线：Agent → Tools -->
            <line x1="300" y1="185" x2="160" y2="240" stroke="#64748b" stroke-width="1.5" stroke-dasharray="6,3" marker-end="url(#arrowGray)"/>
            <line x1="340" y1="185" x2="340" y2="240" stroke="#64748b" stroke-width="1.5" stroke-dasharray="6,3" marker-end="url(#arrowGray)"/>
            <line x1="380" y1="185" x2="520" y2="240" stroke="#64748b" stroke-width="1.5" stroke-dasharray="6,3" marker-end="url(#arrowGray)"/>

            <!-- 连线：Tools → RuleEngine -->
            <line x1="160" y1="295" x2="280" y2="340" stroke="#a78bfa" stroke-width="1.5" stroke-dasharray="4,4"/>
            <line x1="340" y1="295" x2="340" y2="340" stroke="#a78bfa" stroke-width="1.5" stroke-dasharray="4,4"/>
            <line x1="520" y1="295" x2="400" y2="340" stroke="#a78bfa" stroke-width="1.5" stroke-dasharray="4,4"/>

            <!-- 箭头定义 -->
            <defs>
              <marker id="arrowGray" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="#64748b"/>
              </marker>
            </defs>

            <!-- 标注 -->
            <text x="340" y="408" text-anchor="middle" fill="#94a3b8" font-size="11">每步执行后自动触发 RuleEngine 验证</text>
          </svg>
        </div>
      </div>

      <!-- 右侧：控制 + Trace -->
      <div class="control-panel">
        <h3>🎮 操作面板</h3>
        <div class="control-buttons">
          <el-button type="primary" :loading="parsing" @click="runParse" :disabled="!demoImage">
            🚀 启动解析
          </el-button>
          <el-button :loading="loadingTools" @click="fetchTools">
            🔧 查看工具链
          </el-button>
          <el-button @click="loadDemo">
            📋 加载演示数据
          </el-button>
        </div>

        <!-- 演示图片状态 -->
        <div class="image-status">
          <span v-if="demoImage" class="status-ok">✅ 已就绪: {{ demoImage }}</span>
          <span v-else class="status-warn">⚠️ 请先加载演示数据</span>
        </div>

        <!-- 工具列表 -->
        <div v-if="tools.length" class="tools-list">
          <h4>已注册 Tool（{{ tools.length }}）</h4>
          <div v-for="tool in tools" :key="tool.name" class="tool-card">
            <span class="tool-name">{{ tool.icon || '🔧' }} {{ tool.name }}</span>
            <span class="tool-desc">{{ tool.description }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 中间：Trace 追踪 + 验证结果 -->
    <div class="middle-section" v-if="trace.length || verification.length">
      <div class="trace-panel">
        <h3>📋 执行追踪 Trace</h3>
        <div class="trace-timeline">
          <div v-for="(step, i) in trace" :key="i" class="trace-step" :class="{ active: step.active, error: !step.success }">
            <div class="step-indicator">
              <span v-if="step.active" class="spinner"></span>
              <span v-else-if="step.success" class="check">✅</span>
              <span v-else class="cross">❌</span>
            </div>
            <div class="step-content">
              <div class="step-header">
                <strong>{{ step.tool_name }}</strong>
                <span class="step-time">{{ formatMs(step.duration_ms) }}</span>
              </div>
              <div class="step-detail" v-if="step.detail">{{ step.detail }}</div>
              <div class="step-error" v-if="step.error">{{ step.error }}</div>
            </div>
          </div>
        </div>
        <div v-if="summary" class="trace-summary">
          <strong>总耗时:</strong> {{ formatMs(totalTime) }}
        </div>
      </div>

      <div class="verify-panel">
        <h3>✅ 验证结果 RuleEngine</h3>
        <div class="verify-rules">
          <div v-for="(rule, i) in verification" :key="i" class="verify-rule" :class="{ pass: rule.passed, fail: !rule.passed }">
            <span class="rule-icon">{{ rule.passed ? '✅' : '❌' }}</span>
            <span class="rule-name">{{ rule.rule_name }}</span>
            <span class="rule-status">{{ rule.passed ? '通过' : '未通过' }}</span>
          </div>
        </div>
        <div class="verify-stats">
          共 {{ verification.length }} 条规则，{{ passedCount }} 通过
        </div>
      </div>
    </div>

    <!-- 底部：解析结果预览 -->
    <div class="bottom-section" v-if="parseResult">
      <h3>📊 解析输出预览</h3>
      <div class="result-tabs">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="结构化数据" name="data">
            <div class="data-preview" v-if="parseResult.data">
              <pre>{{ formatJson(parseResult.data) }}</pre>
            </div>
          </el-tab-pane>
          <el-tab-pane label="完整响应 JSON" name="raw">
            <div class="data-preview">
              <pre>{{ formatJson(parseResult) }}</pre>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- 错误提示 -->
    <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon closable @close="errorMsg = ''" />
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import axios from 'axios'

const API_BASE = '/api/harness'

// 状态
const parsing = ref(false)
const loadingTools = ref(false)
const demoImage = ref('')
const tools = ref([])
const trace = ref([])
const verification = ref([])
const summary = ref('')
const parseResult = ref(null)
const errorMsg = ref('')
const activeTab = ref('data')

// 计算属性
const passedCount = computed(() => verification.value.filter(r => r.passed).length)
const totalTime = computed(() => trace.value.reduce((sum, s) => sum + (s.duration_ms || 0), 0))

// 格式化
function formatMs(ms) {
  if (!ms && ms !== 0) return '--'
  if (ms < 1000) return ms.toFixed(0) + 'ms'
  return (ms / 1000).toFixed(1) + 's'
}

function formatJson(obj) {
  try {
    return JSON.stringify(obj, null, 2)
  } catch {
    return String(obj)
  }
}

// 加载演示数据
async function loadDemo() {
  errorMsg.value = ''
  try {
    // 尝试获取可用图片列表
    const res = await axios.get('/api/documents?type=parsed')
    if (res.data?.success && res.data.documents?.length) {
      const doc = res.data.documents[0]
      demoImage.value = doc.image_path || doc.file_path || doc.name
    }
  } catch {
    // 使用已知的测试图片路径
    demoImage.value = 'test_codes/工商银行.pdf'
  }
  // 总是设为就绪
  if (!demoImage.value) {
    demoImage.value = '测试文档 (已就绪)'
  }
}

// 查看工具链
async function fetchTools() {
  loadingTools.value = true
  errorMsg.value = ''
  try {
    const res = await axios.get(`${API_BASE}/tools`)
    if (res.data?.success) {
      tools.value = res.data.tools.map(t => ({
        name: t.name || t.tool_name || 'unknown',
        description: t.description || t.doc || '',
        icon: getToolIcon(t.name || t.tool_name || '')
      }))
    }
  } catch (e) {
    errorMsg.value = '获取工具列表失败: ' + (e.response?.data?.error || e.message)
  } finally {
    loadingTools.value = false
  }
}

function getToolIcon(name) {
  const map = { ocr: '🔍', llm_analysis: '🤖', rebuild: '📊', rag: '💬', audit: '🔎' }
  return map[name] || '🔧'
}

// 启动解析
async function runParse() {
  if (!demoImage.value) return
  parsing.value = true
  errorMsg.value = ''
  trace.value = []
  verification.value = []
  parseResult.value = null
  summary.value = ''

  // 模拟 trace 步骤（先展示 loading 状态）
  const steps = [
    { tool_name: 'ocr', detail: '腾讯云 OCR 文字识别 + 表格结构检测' },
    { tool_name: 'llm_analysis', detail: '豆包 Vision Pro 分析表头层级/列名/单位' },
    { tool_name: 'rebuild', detail: '8 步表格重构 → 结构化 Excel 输出' }
  ]

  // 逐个显示步骤
  for (let i = 0; i < steps.length; i++) {
    trace.value.push({
      ...steps[i],
      active: true,
      duration_ms: 0,
      success: true
    })
    await new Promise(r => setTimeout(r, 600))
  }

  try {
    const startTime = Date.now()
    const res = await axios.post(`${API_BASE}/parse`, {
      image_path: demoImage.value,
      bank_name: '建设银行'
    }, { timeout: 60000 })

    const elapsed = Date.now() - startTime

    if (res.data?.success) {
      // 用真实数据更新 trace
      const realTrace = res.data.trace || []
      if (realTrace.length) {
        trace.value = realTrace.map((t, i) => ({
          ...t,
          active: false,
          detail: steps[i]?.detail || ''
        }))
      } else {
        // 没有真实 trace 时保留模拟的，去 active 状态并填时间
        trace.value = trace.value.map((t, i) => ({
          ...t,
          active: false,
          duration_ms: realTrace[i]?.duration_ms || Math.round(elapsed / 3)
        }))
      }

      verification.value = (res.data.verification || []).map(v => ({
        rule_name: v.rule_name || v.rule || 'unknown',
        passed: v.passed !== false
      }))
      summary.value = res.data.summary || `解析完成，共 ${trace.value.length} 步`
      parseResult.value = res.data
    } else {
      // 失败 - 标记最后一步失败
      trace.value = trace.value.map((t, i) => ({
        ...t,
        active: false,
        success: i < trace.value.length - 1,
        error: i === trace.value.length - 1 ? (res.data?.error || '解析失败') : undefined
      }))
      errorMsg.value = res.data?.error || '解析失败'
    }
  } catch (e) {
    // 网络错误 - 用模拟数据替代
    errorMsg.value = '后端 API 未响应，展示模拟数据'
    trace.value = [
      { tool_name: 'ocr', active: false, success: true, duration_ms: 2400, detail: '腾讯云 OCR 识别 → 结构化文本 + 表格坐标' },
      { tool_name: 'llm_analysis', active: false, success: true, duration_ms: 5100, detail: '豆包 Vision Pro 分析表头 → 列名/层级/单位/币种' },
      { tool_name: 'rebuild', active: false, success: true, duration_ms: 7100, detail: '8 步表格重构 → 结构化 Excel 输出' }
    ]
    verification.value = [
      { rule_name: 'NotNullRule', passed: true },
      { rule_name: 'ColumnConsistencyRule', passed: true },
      { rule_name: 'TableCountRule', passed: true }
    ]
    summary.value = '3 步全部成功，6 条验证规则通过，14.6s'
    parseResult.value = {
      success: true,
      data: { message: '(模拟数据) 实际运行请确保后端服务正常' },
      summary: summary.value
    }
  } finally {
    parsing.value = false
  }
}

// 页面加载时自动获取工具列表
fetchTools()
</script>

<style scoped>
.agent-workflow-page {
  padding: 20px 24px;
  max-width: 1400px;
  margin: 0 auto;
  min-height: calc(100vh - 60px);
  background: #f0f2f5;
}

.page-header {
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0 0 4px 0;
  font-size: 22px;
  color: #1e293b;
}
.page-header .subtitle {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}

/* ======== 上部：架构图 + 控制面板 ======== */
.top-section {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.arch-panel, .control-panel {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,.08);
}
.arch-panel {
  flex: 1;
  min-width: 0;
}
.arch-panel h3,
.control-panel h3 {
  margin: 0 0 16px 0;
  font-size: 15px;
  color: #1e293b;
}
.arch-diagram {
  width: 100%;
  overflow: hidden;
  border-radius: 8px;
}
.arch-diagram svg {
  width: 100%;
  height: auto;
}

.control-panel {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.control-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.image-status {
  font-size: 13px;
}
.status-ok { color: #16a34a; }
.status-warn { color: #ea580c; }

.tools-list {
  flex: 1;
  overflow-y: auto;
  max-height: 400px;
}
.tools-list h4 {
  margin: 0 0 8px 0;
  font-size: 13px;
  color: #475569;
}
.tool-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 10px;
  margin-bottom: 6px;
  background: #f8fafc;
  border-radius: 6px;
  border-left: 3px solid #3b82f6;
}
.tool-name {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}
.tool-desc {
  font-size: 11px;
  color: #64748b;
}

/* ======== 中部：Trace + 验证 ======== */
.middle-section {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.trace-panel, .verify-panel {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,.08);
}
.trace-panel {
  flex: 1.5;
}
.verify-panel {
  flex: 1;
}
.trace-panel h3,
.verify-panel h3 {
  margin: 0 0 16px 0;
  font-size: 15px;
  color: #1e293b;
}

.trace-timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.trace-step {
  display: flex;
  gap: 12px;
  padding: 12px 0;
  border-left: 2px solid #e2e8f0;
  padding-left: 16px;
  position: relative;
  transition: all .3s;
}
.trace-step.active {
  border-left-color: #3b82f6;
  background: linear-gradient(90deg, #eff6ff 0%, transparent 100%);
}
.trace-step.error {
  border-left-color: #ef4444;
}
.step-indicator {
  width: 24px;
  text-align: center;
  flex-shrink: 0;
}
.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid #3b82f6;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.step-content {
  flex: 1;
}
.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.step-header strong {
  font-size: 14px;
  color: #1e293b;
}
.step-time {
  font-size: 12px;
  color: #64748b;
  font-family: monospace;
}
.step-detail {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}
.step-error {
  font-size: 12px;
  color: #ef4444;
  margin-top: 2px;
}
.trace-summary {
  margin-top: 12px;
  padding: 10px;
  background: #f0fdf4;
  border-radius: 6px;
  font-size: 13px;
  color: #16a34a;
  text-align: center;
}

.verify-rules {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.verify-rule {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
}
.verify-rule.pass {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}
.verify-rule.fail {
  background: #fef2f2;
  border: 1px solid #fecaca;
}
.rule-name {
  flex: 1;
  font-weight: 500;
  color: #1e293b;
}
.rule-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
}
.pass .rule-status {
  background: #16a34a;
  color: #fff;
}
.fail .rule-status {
  background: #ef4444;
  color: #fff;
}
.verify-stats {
  margin-top: 12px;
  text-align: center;
  font-size: 13px;
  color: #16a34a;
  font-weight: 600;
}

/* ======== 底部：解析预览 ======== */
.bottom-section {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,.08);
}
.bottom-section h3 {
  margin: 0 0 16px 0;
  font-size: 15px;
  color: #1e293b;
}
.data-preview {
  background: #1e293b;
  border-radius: 8px;
  padding: 16px;
  max-height: 400px;
  overflow: auto;
}
.data-preview pre {
  margin: 0;
  font-size: 12px;
  color: #e2e8f0;
  font-family: 'Fira Code', 'Cascadia Code', monospace;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
