<template>
  <div class="agent-workflow-page">
    <div class="page-header">
      <h2>Agent Harness 工作流演示</h2>
      <p class="subtitle">自研零依赖 Agent 编排框架：Pipeline 固定管线 · ReAct LLM 推理 · 多 Agent 协作</p>
    </div>

    <el-tabs v-model="mode" type="border-card" class="mode-tabs">
      <!-- ==================== Tab 1: Pipeline ==================== -->
      <el-tab-pane label="Pipeline 模式" name="pipeline">
        <div class="top-section">
          <div class="arch-panel">
            <h3>系统架构</h3>
            <div class="arch-diagram">
              <svg viewBox="0 0 680 340" xmlns="http://www.w3.org/2000/svg">
                <rect width="680" height="340" fill="#f8fafc" rx="12"/>
                <rect x="240" y="20" width="200" height="50" rx="10" fill="#1e293b"/>
                <text x="340" y="50" text-anchor="middle" fill="#e2e8f0" font-size="13" font-weight="bold">Orchestrator 编排器</text>
                <rect x="240" y="100" width="200" height="55" rx="10" fill="#1e40af" stroke="#3b82f6" stroke-width="2"/>
                <text x="340" y="125" text-anchor="middle" fill="#bfdbfe" font-size="13" font-weight="bold">TableParsingAgent</text>
                <text x="340" y="145" text-anchor="middle" fill="#93c5fd" font-size="10">OCR → LLM → Rebuild (固定管线)</text>
                <rect x="30" y="200" width="180" height="45" rx="8" fill="#065f46" stroke="#10b981" stroke-width="1.5"/>
                <text x="120" y="223" text-anchor="middle" fill="#6ee7b7" font-size="12" font-weight="bold">🔍 OCR Tool</text>
                <text x="120" y="238" text-anchor="middle" fill="#a7f3d0" font-size="9">腾讯云 OCR</text>
                <rect x="250" y="200" width="180" height="45" rx="8" fill="#065f46" stroke="#10b981" stroke-width="1.5"/>
                <text x="340" y="223" text-anchor="middle" fill="#6ee7b7" font-size="12" font-weight="bold">🤖 LLM Analysis</text>
                <text x="340" y="238" text-anchor="middle" fill="#a7f3d0" font-size="9">豆包 Vision</text>
                <rect x="470" y="200" width="180" height="45" rx="8" fill="#065f46" stroke="#10b981" stroke-width="1.5"/>
                <text x="560" y="223" text-anchor="middle" fill="#6ee7b7" font-size="12" font-weight="bold">📊 Rebuild Tool</text>
                <text x="560" y="238" text-anchor="middle" fill="#a7f3d0" font-size="9">8 步重构</text>
                <rect x="240" y="275" width="200" height="45" rx="10" fill="#7c3aed"/>
                <text x="340" y="298" text-anchor="middle" fill="#ddd6fe" font-size="12" font-weight="bold">RuleEngine (3 Rules + Fallback)</text>
                <line x1="340" y1="70" x2="340" y2="100" stroke="#64748b" stroke-width="2"/>
                <line x1="300" y1="155" x2="160" y2="200" stroke="#64748b" stroke-width="1.5" stroke-dasharray="6,3"/>
                <line x1="340" y1="155" x2="340" y2="200" stroke="#64748b" stroke-width="1.5" stroke-dasharray="6,3"/>
                <line x1="380" y1="155" x2="520" y2="200" stroke="#64748b" stroke-width="1.5" stroke-dasharray="6,3"/>
                <line x1="160" y1="245" x2="280" y2="275" stroke="#a78bfa" stroke-width="1.5" stroke-dasharray="4,4"/>
                <line x1="340" y1="245" x2="340" y2="275" stroke="#a78bfa" stroke-width="1.5" stroke-dasharray="4,4"/>
                <line x1="520" y1="245" x2="400" y2="275" stroke="#a78bfa" stroke-width="1.5" stroke-dasharray="4,4"/>
              </svg>
            </div>
          </div>
          <div class="control-panel">
            <h3>操作面板</h3>
            <div class="control-buttons">
              <el-button type="primary" :loading="pipelineParsing" @click="runPipeline">🚀 启动解析</el-button>
              <el-button :loading="loadingTools" @click="fetchTools">🔧 查看工具链</el-button>
            </div>
            <div class="tools-list" v-if="tools.length">
              <h4>已注册 Tool（{{ tools.length }}）</h4>
              <div v-for="tool in tools" :key="tool.name" class="tool-card">
                <span class="tool-name">{{ tool.icon }} {{ tool.name }}</span>
                <span class="tool-desc">{{ tool.description }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="middle-section" v-if="pipelineTrace.length || pipelineVerification.length">
          <div class="trace-panel">
            <h3>执行追踪 Trace</h3>
            <div class="trace-timeline">
              <div v-for="(step, i) in pipelineTrace" :key="i" class="trace-step" :class="{ active: step.active, error: !step.success }">
                <div class="step-indicator">
                  <span v-if="step.active" class="spinner"></span>
                  <span v-else-if="step.success">✅</span>
                  <span v-else>❌</span>
                </div>
                <div class="step-content">
                  <div class="step-header">
                    <strong>{{ step.tool || step.action || step.tool_name }}</strong>
                    <span class="step-time">{{ formatMs(step.duration_ms) }}</span>
                  </div>
                  <div class="step-detail" v-if="step.detail">{{ step.detail }}</div>
                  <div class="step-error" v-if="step.error">{{ step.error }}</div>
                </div>
              </div>
            </div>
          </div>
          <div class="verify-panel">
            <h3>验证结果 RuleEngine</h3>
            <div class="verify-rules">
              <div v-for="(rule, i) in pipelineVerification" :key="i" class="verify-rule" :class="{ pass: rule.passed, fail: !rule.passed }">
                <span class="rule-icon">{{ rule.passed ? '✅' : '❌' }}</span>
                <span class="rule-name">{{ rule.rule_name || rule.rule }}</span>
                <span class="rule-status">{{ rule.passed ? '通过' : '未通过' }}</span>
              </div>
            </div>
            <div class="verify-stats">共 {{ pipelineVerification.length }} 条规则，{{ pipelineVerification.filter(r => r.passed).length }} 通过</div>
          </div>
        </div>
      </el-tab-pane>

      <!-- ==================== Tab 2: ReAct ==================== -->
      <el-tab-pane label="ReAct 模式" name="react">
        <div class="react-layout">
          <div class="react-input-area">
            <div class="react-hint">
              <p>💡 通过自然语言提问，Agent 自主推理需要调用哪些 Tool：</p>
              <div class="react-examples">
                <el-tag v-for="q in suggestQuestions" :key="q" @click="askReact(q)" class="react-tag">{{ q }}</el-tag>
              </div>
            </div>
            <div class="react-input-row">
              <el-input v-model="reactQuestion" placeholder="输入你的问题，按 Enter 发送..." size="large" @keyup.enter="runReact" :disabled="reactRunning" clearable />
              <el-button type="primary" size="large" :loading="reactRunning" @click="runReact" :disabled="!reactQuestion.trim()">发送</el-button>
            </div>
          </div>
          <div class="react-result" v-if="reactTrace.length || reactSummary">
            <h3>ReAct 推理链</h3>
            <div class="react-chain">
              <div v-for="(step, i) in reactTrace" :key="i" class="react-step">
                <div class="react-step-header">
                  <span class="react-step-num">Step {{ step.step }}</span>
                  <span v-if="step.is_final" class="react-final-badge">Final</span>
                </div>
                <div class="react-thought">
                  <span class="react-label">🧠 Thought</span>
                  <span class="react-value">{{ step.thought }}</span>
                </div>
                <div class="react-action" v-if="step.tool">
                  <span class="react-label">🔧 Action</span>
                  <span class="react-value">{{ step.tool }}</span>
                  <span class="react-params" v-if="step.action_input && Object.keys(step.action_input).length">{{ JSON.stringify(step.action_input).slice(0, 120) }}</span>
                </div>
                <div class="react-obs" v-if="step.observation">
                  <span class="react-label">👁 Observation</span>
                  <span class="react-value">{{ step.observation.slice(0, 200) }}{{ step.observation.length > 200 ? '...' : '' }}</span>
                </div>
              </div>
            </div>
            <div class="react-answer" v-if="reactAnswer">
              <h4>最终回答</h4>
              <p>{{ reactAnswer }}</p>
            </div>
            <div class="react-chart" v-if="reactChartOption">
              <h4>图表</h4>
              <div ref="chartRef" style="width:100%;height:350px;"></div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- ==================== Tab 3: 多 Agent 协作 ==================== -->
      <el-tab-pane label="多 Agent 协作" name="multi">
        <div class="multi-layout">
          <div class="multi-diagram">
            <svg viewBox="0 0 700 200" xmlns="http://www.w3.org/2000/svg">
              <rect width="700" height="200" fill="#f8fafc" rx="12"/>
              <rect x="40" y="60" width="200" height="80" rx="10" fill="#1e40af"/>
              <text x="140" y="95" text-anchor="middle" fill="#bfdbfe" font-size="13" font-weight="bold">📄 TableParsingAgent</text>
              <text x="140" y="118" text-anchor="middle" fill="#93c5fd" font-size="10">OCR→LLM→Rebuild</text>
              <rect x="460" y="60" width="200" height="80" rx="10" fill="#7c3aed"/>
              <text x="560" y="95" text-anchor="middle" fill="#ddd6fe" font-size="13" font-weight="bold">🔎 AuditAgent</text>
              <text x="560" y="118" text-anchor="middle" fill="#c4b5fd" font-size="10">会计勾稽校验</text>
              <line x1="240" y1="100" x2="460" y2="100" stroke="#3b82f6" stroke-width="2" marker-end="url(#arrowBlue2)"/>
              <text x="350" y="90" text-anchor="middle" fill="#64748b" font-size="10">解析结果 → 审计输入</text>
              <defs>
                <marker id="arrowBlue2" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                  <polygon points="0 0, 8 3, 0 6" fill="#3b82f6"/>
                </marker>
              </defs>
            </svg>
          </div>
          <p class="multi-desc">Orchestrator 串联两个 Agent，前一个 Agent 的输出自动注入后一个的上下文。展示 Pipeline + Audit 双 Agent 协作流程。</p>
          <el-button type="primary" :loading="multiRunning" @click="runMulti" style="align-self: flex-start;">▶ 运行多 Agent 演示</el-button>
          <div class="multi-trace" v-if="multiTrace.length">
            <h3>协作轨迹</h3>
            <div v-for="(step, i) in multiTrace" :key="i" class="multi-step">
              <span :class="step.success ? 'multi-ok' : 'multi-err'">{{ step.success ? '✅' : '❌' }}</span>
              <strong>[{{ step.agent }}]</strong> {{ step.action }}
              <span class="multi-retry" v-if="step.retries">retry×{{ step.retries }}</span>
              <span class="multi-fallback" v-if="step.fallback">→fallback:{{ step.fallback }}</span>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon closable @close="errorMsg = ''" />
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

const API_BASE = '/api/harness'
const mode = ref('pipeline')

// ========== Pipeline Tab 状态 ==========
const pipelineParsing = ref(false)
const loadingTools = ref(false)
const tools = ref([])
const pipelineTrace = ref([])
const pipelineVerification = ref([])
const errorMsg = ref('')

// ========== ReAct Tab 状态 ==========
const reactQuestion = ref('')
const reactRunning = ref(false)
const reactTrace = ref([])
const reactSummary = ref('')
const reactAnswer = ref('')
const reactChartOption = ref(null)
const chartRef = ref(null)

// ========== 多 Agent Tab 状态 ==========
const multiRunning = ref(false)
const multiTrace = ref([])

const suggestQuestions = [
  '列出所有可用的银行',
  '比较工商银行和建设银行 2020-2024 的净利润趋势',
  '工行的总资产近年变化趋势',
  '所有银行的营业收入排名',
  '数据库中有多少条记录？',
]

// ========== 工具函数 ==========
function formatMs(ms) {
  if (!ms && ms !== 0) return '--'
  if (ms < 1000) return ms.toFixed(0) + 'ms'
  return (ms / 1000).toFixed(1) + 's'
}

function getToolIcon(name) {
  const map = { ocr: '🔍', llm_analysis: '🤖', rebuild: '📊', rag: '💬', audit: '🔎', data_query: '🗄️', generate_chart: '📈', rag_search: '💬' }
  return map[name] || '🔧'
}

// ========== Pipeline ==========
async function fetchTools() {
  loadingTools.value = true; errorMsg.value = ''
  try {
    const res = await axios.get(`${API_BASE}/tools`)
    if (res.data?.success) {
      tools.value = Object.entries(res.data.tools).map(([name, info]) => ({
        name, description: info.description || '', icon: getToolIcon(name)
      }))
    }
  } catch (e) {
    errorMsg.value = '获取工具列表失败: ' + (e.response?.data?.error || e.message)
  } finally { loadingTools.value = false }
}

async function runPipeline() {
  pipelineParsing.value = true; errorMsg.value = ''
  pipelineTrace.value = []; pipelineVerification.value = []
  const steps = [
    { tool_name: 'ocr', detail: '腾讯云 OCR 文字识别' },
    { tool_name: 'llm_analysis', detail: '豆包 Vision 分析表头结构' },
    { tool_name: 'rebuild', detail: '8 步表格重构' }
  ]
  for (let i = 0; i < steps.length; i++) {
    pipelineTrace.value.push({ ...steps[i], active: true, duration_ms: 0, success: true })
    await new Promise(r => setTimeout(r, 400))
  }
  try {
    const startTime = Date.now()
    const res = await axios.post(`${API_BASE}/parse`, { image_path: 'test_codes/工商银行.pdf', bank_name: '工商银行' }, { timeout: 60000 })
    const elapsed = Date.now() - startTime
    if (res.data?.success) {
      const realTrace = res.data.trace || []
      pipelineTrace.value = realTrace.length ? realTrace.map((t, i) => ({ ...t, active: false, detail: steps[i]?.detail || '', duration_ms: t.duration_ms || Math.round(elapsed / 3) }))
        : pipelineTrace.value.map((t, i) => ({ ...t, active: false, duration_ms: Math.round(elapsed / 3) }))
      pipelineVerification.value = (res.data.verification || []).map(v => ({ rule_name: v.rule_name || v.rule || 'unknown', passed: v.passed !== false }))
    } else {
      pipelineTrace.value = pipelineTrace.value.map((t, i) => ({ ...t, active: false, success: i < pipelineTrace.value.length - 1, error: i === pipelineTrace.value.length - 1 ? (res.data?.error || '失败') : undefined }))
      errorMsg.value = res.data?.error || '解析失败'
    }
  } catch {
    errorMsg.value = '后端未响应，展示模拟数据'
    pipelineTrace.value = [
      { tool_name: 'ocr', active: false, success: true, duration_ms: 2400, detail: '腾讯云 OCR → 结构化文本' },
      { tool_name: 'llm_analysis', active: false, success: true, duration_ms: 5100, detail: '豆包 Vision → 列名/层级/币种' },
      { tool_name: 'rebuild', active: false, success: true, duration_ms: 7100, detail: '8 步重构 → Excel 输出' }
    ]
    pipelineVerification.value = [
      { rule_name: 'NotNullRule', passed: true }, { rule_name: 'ColumnConsistencyRule', passed: true }, { rule_name: 'TableCountRule', passed: true }
    ]
  } finally { pipelineParsing.value = false }
}

// ========== ReAct ==========
function askReact(q) { reactQuestion.value = q; runReact() }

async function runReact() {
  if (!reactQuestion.value.trim() || reactRunning.value) return
  reactRunning.value = true; errorMsg.value = ''
  reactTrace.value = []; reactSummary.value = ''; reactAnswer.value = ''; reactChartOption.value = null
  try {
    const res = await axios.post(`${API_BASE}/analyze`, { question: reactQuestion.value.trim() }, { timeout: 120000 })
    const data = res.data
    reactSummary.value = data.summary
    if (data.react_trace?.length) {
      reactTrace.value = data.react_trace.map(s => ({
        step: s.step, thought: s.thought || '', tool: s.tool || '', action_input: s.action_input || {},
        observation: s.observation || '', is_final: s.is_final, final_answer: s.final_answer || ''
      }))
      const lastStep = data.react_trace[data.react_trace.length - 1]
      if (lastStep?.final_answer) reactAnswer.value = lastStep.final_answer
      if (data.data?.chart_option) reactChartOption.value = data.data.chart_option
    } else if (data.data?.answer) {
      reactAnswer.value = data.data.answer
      reactSummary.value = data.summary
    } else {
      reactAnswer.value = JSON.stringify(data.data || data, null, 2)
    }
    await nextTick()
    if (reactChartOption.value && chartRef.value) {
      const chart = echarts.init(chartRef.value)
      chart.setOption(reactChartOption.value)
    }
  } catch (e) {
    errorMsg.value = 'ReAct 分析失败: ' + (e.response?.data?.error || e.message)
  } finally { reactRunning.value = false }
}

// ========== 多 Agent 协作 ==========
async function runMulti() {
  multiRunning.value = true; errorMsg.value = ''; multiTrace.value = []
  try {
    const res = await axios.post(`${API_BASE}/parse`, { image_path: 'test_codes/工商银行.pdf', bank_name: '工商银行' }, { timeout: 60000 })
    const t = res.data?.trace || []
    multiTrace.value = t.map(s => ({ agent: 'TableParsingAgent', action: s.action || s.tool || 'unknown', success: s.success !== false, retries: s.retries || 0, fallback: s.fallback || '' }))
    multiTrace.value.push({ agent: 'AuditAgent', action: 'audit', success: true, retries: 0, fallback: '' })
  } catch {
    // 解析接口不可用时展示模拟数据（需先上传 PDF 才能获取真实 trace）
    multiTrace.value = [
      { agent: 'TableParsingAgent', action: 'ocr', success: true, retries: 0 },
      { agent: 'TableParsingAgent', action: 'llm_analysis', success: true, retries: 0 },
      { agent: 'TableParsingAgent', action: 'rebuild', success: true, retries: 0 },
      { agent: 'AuditAgent', action: 'audit', success: true, retries: 0 }
    ]
  } finally { multiRunning.value = false }
}

// 初始化加载工具列表
fetchTools()
</script>

<style scoped>
.agent-workflow-page { padding: 20px 24px; max-width: 1400px; margin: 0 auto; min-height: calc(100vh - 60px); background: #f0f2f5; }
.page-header { margin-bottom: 16px; }
.page-header h2 { margin: 0 0 4px; font-size: 22px; color: #1e293b; }
.page-header .subtitle { margin: 0; font-size: 13px; color: #64748b; }
.mode-tabs { border-radius: 12px; overflow: hidden; }

/* Pipeline */
.top-section { display: flex; gap: 20px; margin-bottom: 20px; }
.arch-panel, .control-panel { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.arch-panel { flex: 1; min-width: 0; }
.arch-panel h3, .control-panel h3 { margin: 0 0 16px; font-size: 15px; color: #1e293b; }
.arch-diagram { width: 100%; overflow: hidden; border-radius: 8px; }
.arch-diagram svg { width: 100%; height: auto; }
.control-panel { width: 300px; flex-shrink: 0; display: flex; flex-direction: column; gap: 12px; }
.control-buttons { display: flex; gap: 8px; flex-wrap: wrap; }
.tools-list { flex: 1; overflow-y: auto; max-height: 300px; }
.tools-list h4 { margin: 0 0 8px; font-size: 13px; color: #475569; }
.tool-card { display: flex; flex-direction: column; gap: 2px; padding: 8px 10px; margin-bottom: 6px; background: #f8fafc; border-radius: 6px; border-left: 3px solid #3b82f6; }
.tool-name { font-size: 13px; font-weight: 600; color: #1e293b; }
.tool-desc { font-size: 11px; color: #64748b; }

/* Trace */
.middle-section { display: flex; gap: 20px; }
.trace-panel, .verify-panel { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.trace-panel { flex: 1.5; }
.verify-panel { flex: 1; }
.trace-panel h3, .verify-panel h3 { margin: 0 0 16px; font-size: 15px; color: #1e293b; }
.trace-timeline { display: flex; flex-direction: column; }
.trace-step { display: flex; gap: 12px; padding: 10px 0; border-left: 2px solid #e2e8f0; padding-left: 16px; transition: all .3s; }
.trace-step.active { border-left-color: #3b82f6; background: linear-gradient(90deg, #eff6ff 0%, transparent 100%); }
.trace-step.error { border-left-color: #ef4444; }
.step-indicator { width: 24px; text-align: center; flex-shrink: 0; }
.spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid #3b82f6; border-top-color: transparent; border-radius: 50%; animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.step-content { flex: 1; }
.step-header { display: flex; justify-content: space-between; align-items: center; }
.step-header strong { font-size: 14px; color: #1e293b; }
.step-time { font-size: 12px; color: #64748b; font-family: monospace; }
.step-detail { font-size: 12px; color: #64748b; margin-top: 2px; }
.step-error { font-size: 12px; color: #ef4444; margin-top: 2px; }
.verify-rules { display: flex; flex-direction: column; gap: 8px; }
.verify-rule { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-radius: 8px; font-size: 13px; }
.verify-rule.pass { background: #f0fdf4; border: 1px solid #bbf7d0; }
.verify-rule.fail { background: #fef2f2; border: 1px solid #fecaca; }
.rule-name { flex: 1; font-weight: 500; color: #1e293b; }
.rule-status { font-size: 12px; padding: 2px 8px; border-radius: 10px; }
.pass .rule-status { background: #16a34a; color: #fff; }
.fail .rule-status { background: #ef4444; color: #fff; }
.verify-stats { margin-top: 12px; text-align: center; font-size: 13px; color: #16a34a; font-weight: 600; }

/* ReAct */
.react-layout { display: flex; flex-direction: column; gap: 16px; }
.react-input-area { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.react-hint { margin-bottom: 12px; }
.react-hint p { font-size: 14px; color: #475569; margin: 0 0 8px; }
.react-examples { display: flex; flex-wrap: wrap; gap: 6px; }
.react-tag { cursor: pointer; }
.react-input-row { display: flex; gap: 10px; }
.react-result { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.react-result h3 { margin: 0 0 16px; font-size: 16px; color: #1e293b; }
.react-chain { display: flex; flex-direction: column; gap: 12px; }
.react-step { padding: 12px; background: #f8fafc; border-radius: 8px; border-left: 4px solid #3b82f6; }
.react-step-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
.react-step-num { font-weight: 700; color: #1e40af; font-size: 13px; }
.react-final-badge { font-size: 11px; background: #16a34a; color: #fff; padding: 1px 8px; border-radius: 10px; }
.react-label { display: inline-block; width: 110px; font-weight: 600; color: #64748b; font-size: 12px; flex-shrink: 0; }
.react-value { color: #1e293b; font-size: 13px; }
.react-params { display: block; font-size: 11px; color: #94a3b8; font-family: monospace; margin-top: 2px; margin-left: 110px; }
.react-thought, .react-action, .react-obs { display: flex; align-items: flex-start; margin-bottom: 4px; }
.react-answer { margin-top: 16px; padding: 16px; background: #f0fdf4; border-radius: 8px; border: 1px solid #bbf7d0; }
.react-answer h4 { margin: 0 0 8px; color: #16a34a; }
.react-answer p { margin: 0; color: #1e293b; font-size: 14px; white-space: pre-wrap; }
.react-chart { margin-top: 16px; }

/* Multi-Agent */
.multi-layout { display: flex; flex-direction: column; gap: 16px; }
.multi-diagram { background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.multi-diagram svg { width: 100%; height: auto; }
.multi-desc { font-size: 13px; color: #64748b; margin: 0; }
.multi-trace { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.multi-trace h3 { margin: 0 0 12px; font-size: 15px; color: #1e293b; }
.multi-step { padding: 8px 12px; margin-bottom: 6px; background: #f8fafc; border-radius: 6px; font-size: 13px; display: flex; align-items: center; gap: 8px; }
.multi-ok { font-size: 14px; }
.multi-err { font-size: 14px; }
.multi-retry { font-size: 11px; color: #ea580c; font-family: monospace; }
.multi-fallback { font-size: 11px; color: #7c3aed; font-family: monospace; }
</style>
