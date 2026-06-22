<template>
  <div class="loop-state-panel">
    <!-- 摘要行 -->
    <div class="ls-summary-row">
      <div class="ls-stat">
        <span class="ls-stat-num">{{ loopState.total_attempts }}</span>
        <span class="ls-stat-label">总尝试</span>
      </div>
      <div class="ls-stat success">
        <span class="ls-stat-num">{{ loopState.successful_tools?.length || 0 }}</span>
        <span class="ls-stat-label">成功 Tool</span>
      </div>
      <div class="ls-stat fail" v-if="loopState.failed_tools?.length">
        <span class="ls-stat-num">{{ loopState.failed_tools.length }}</span>
        <span class="ls-stat-label">失败 Tool</span>
      </div>
      <div class="ls-stat warn" v-if="loopState.consecutive_failures">
        <span class="ls-stat-num">{{ loopState.consecutive_failures }}</span>
        <span class="ls-stat-label">连续失败</span>
      </div>
    </div>

    <!-- 工具状态标签 -->
    <div class="ls-tool-tags" v-if="loopState.successful_tools?.length || loopState.failed_tools?.length">
      <span v-for="t in loopState.successful_tools" :key="'ok-'+t" class="ls-tool-tag ok">{{ t }}</span>
      <span v-for="t in loopState.failed_tools" :key="'fail-'+t" class="ls-tool-tag err">{{ t }}</span>
    </div>

    <!-- 详细记录表格 -->
    <div class="ls-table-wrap" v-if="loopState.records?.length">
      <table class="ls-table">
        <thead>
          <tr>
            <th>Step</th>
            <th>Tool</th>
            <th>策略</th>
            <th>结果</th>
            <th v-if="showAll">耗时</th>
            <th v-if="showAll">错误</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in loopState.records" :key="i" :class="'row-' + r.outcome">
            <td class="ls-step">{{ r.step }}</td>
            <td class="ls-tool">{{ r.tool }}</td>
            <td>
              <span class="ls-strategy-badge" :class="r.strategy">{{ getStrategyLabel(r.strategy) }}</span>
            </td>
            <td>
              <span class="ls-outcome-badge" :style="{ background: getOutcomeColor(r.outcome) }">
                {{ getOutcomeLabel(r.outcome) }}
              </span>
            </td>
            <td v-if="showAll" class="ls-latency">{{ formatLatency(r.latency_ms) }}</td>
            <td v-if="showAll" class="ls-error">{{ r.error?.slice(0, 60) || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  loopState: { type: Object, default: () => ({}) },
  showAll: { type: Boolean, default: false },
})

const outcomeLabels = {
  success: '成功', transient_failure: '瞬时失败', permanent_failure: '永久失败',
  timeout: '超时', verification_failed: '验证失败'
}
const outcomeColors = {
  success: '#16a34a', transient_failure: '#ea580c', permanent_failure: '#ef4444',
  timeout: '#f59e0b', verification_failed: '#8b5cf6'
}
const strategyLabels = {
  direct: '直接调用', retry_same: '同参重试', retry_adjusted: '调参重试',
  fallback: '降级', alternative: '替代方案', cached: '缓存', manual: '人工'
}

function getOutcomeLabel(o) { return outcomeLabels[o] || o }
function getOutcomeColor(o) { return outcomeColors[o] || '#94a3b8' }
function getStrategyLabel(s) { return strategyLabels[s] || s }
function formatLatency(ms) {
  if (!ms && ms !== 0) return '—'
  return ms < 1000 ? ms.toFixed(0) + 'ms' : (ms / 1000).toFixed(1) + 's'
}
</script>

<style scoped>
.loop-state-panel { font-size: 13px; }
.ls-summary-row { display: flex; gap: 16px; margin-bottom: 12px; }
.ls-stat { text-align: center; padding: 8px 16px; background: #f1f5f9; border-radius: 8px; min-width: 64px; }
.ls-stat.success { background: #f0fdf4; }
.ls-stat.fail { background: #fef2f2; }
.ls-stat.warn { background: #fffbeb; }
.ls-stat-num { display: block; font-size: 22px; font-weight: 700; color: #1e293b; }
.ls-stat.success .ls-stat-num { color: #16a34a; }
.ls-stat.fail .ls-stat-num { color: #ef4444; }
.ls-stat.warn .ls-stat-num { color: #f59e0b; }
.ls-stat-label { font-size: 11px; color: #64748b; }
.ls-tool-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }
.ls-tool-tag { font-size: 11px; padding: 2px 8px; border-radius: 10px; font-family: monospace; }
.ls-tool-tag.ok { background: #dcfce7; color: #16a34a; }
.ls-tool-tag.err { background: #fee2e2; color: #ef4444; }
.ls-table-wrap { overflow-x: auto; max-height: 360px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; }
.ls-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.ls-table th { background: #f8fafc; padding: 8px 10px; text-align: left; font-weight: 600; color: #475569; border-bottom: 2px solid #e2e8f0; position: sticky; top: 0; }
.ls-table td { padding: 7px 10px; border-bottom: 1px solid #f1f5f9; color: #334155; }
.ls-table tbody tr:hover { background: #f8fafc; }
.row-success { border-left: 3px solid #16a34a; }
.row-transient_failure { border-left: 3px solid #ea580c; }
.row-permanent_failure { border-left: 3px solid #ef4444; }
.row-timeout { border-left: 3px solid #f59e0b; }
.ls-step { font-weight: 600; color: #6366f1; width: 40px; }
.ls-tool { font-family: monospace; font-weight: 500; }
.ls-strategy-badge { font-size: 11px; padding: 1px 7px; border-radius: 10px; background: #e0e7ff; color: #4338ca; white-space: nowrap; }
.ls-strategy-badge.fallback { background: #f3e8ff; color: #7c3aed; }
.ls-strategy-badge.retry_adjusted, .ls-strategy-badge.retry_same { background: #ffedd5; color: #c2410c; }
.ls-strategy-badge.alternative { background: #fce7f3; color: #be185d; }
.ls-outcome-badge { font-size: 11px; padding: 1px 7px; border-radius: 10px; color: #fff; white-space: nowrap; }
.ls-latency { font-family: monospace; font-size: 11px; color: #64748b; }
.ls-error { font-size: 11px; color: #ef4444; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
