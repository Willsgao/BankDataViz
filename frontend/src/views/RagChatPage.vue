<template>
  <div class="rag-chat-page">
    <!-- 左侧面板：文档选择 -->
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <h3 v-show="!sidebarCollapsed">文档列表</h3>
        <el-button size="small" text @click="sidebarCollapsed = !sidebarCollapsed" :title="sidebarCollapsed ? '展开文档列表' : '收起文档列表'">
          <el-icon><DArrowLeft v-if="!sidebarCollapsed" /><DArrowRight v-else /></el-icon>
        </el-button>
      </div>
      <div class="sidebar-body">
        <div v-if="documentsLoading" class="loading-state">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>加载文档列表...</span>
        </div>
        <div v-else-if="documents.length === 0" class="empty-state">
          <el-empty description="暂无可用PDF文档" :image-size="80" />
        </div>
        <div v-else class="document-list">
          <div
            v-for="doc in documents"
            :key="doc.name"
            class="doc-item"
            :class="{
              active: currentDocument === doc.name,
              indexed: indexedDocs.has(doc.name)
            }"
            @click="selectDocument(doc)"
          >
            <div class="doc-icon">
              <el-icon :size="20"><Document /></el-icon>
            </div>
            <div class="doc-info">
              <div class="doc-name">{{ doc.name }}</div>
              <div class="doc-meta">
                <span class="doc-size">{{ formatSize(doc.size) }}</span>
                <el-tag
                  v-if="indexedDocs.has(doc.name)"
                  size="small"
                  type="success"
                  effect="plain"
                >已索引</el-tag>
                <el-tag v-else size="small" type="info" effect="plain">未索引</el-tag>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="sidebar-footer">
        <el-button
          v-if="currentDocument && !indexedDocs.has(currentDocument)"
          type="primary"
          size="small"
          :loading="indexBuilding"
          @click="buildIndexForCurrent"
          style="width:100%"
        >
          构建索引
        </el-button>
        <el-button
          v-else
          size="small"
          @click="refreshDocuments"
          style="width:100%"
        >
          刷新列表
        </el-button>
      </div>
    </aside>

    <!-- 中间：对话区域 -->
    <main class="chat-area">
      <!-- 标题栏 -->
      <div class="chat-header">
        <div class="chat-title">
          <el-icon :size="18"><ChatRound /></el-icon>
          <span>{{ currentDocument || '请选择文档开始问答' }}</span>
          <el-tag v-if="indexStats.total_vectors" size="small" type="success" effect="dark">
            {{ indexStats.total_vectors }} 条向量
          </el-tag>
        </div>
        <div class="chat-actions">
          <el-button size="small" text @click="clearMessages" :disabled="messages.length === 0">
            清空对话
          </el-button>
        </div>
      </div>

      <!-- 消息列表 -->
      <div class="message-list" ref="messageListRef">
        <div v-if="messages.length === 0" class="welcome-area">
          <div class="welcome-icon">
            <el-icon :size="48"><Message /></el-icon>
          </div>
          <h2>智能文档问答</h2>
          <p>选择一个 PDF 文档，然后输入你的问题</p>
          <!-- 功能引导卡片 -->
          <div class="guide-cards">
            <div class="guide-card" @click="goToUpload">
              <el-icon :size="24" color="#409EFF"><Upload /></el-icon>
              <span class="guide-title">上传 PDF</span>
              <span class="guide-desc">前往「数据解析」页面上传文档</span>
            </div>
            <div class="guide-card" @click="handleGuideBuildIndex">
              <el-icon :size="24" color="#67C23A"><Connection /></el-icon>
              <span class="guide-title">构建索引</span>
              <span class="guide-desc">{{ currentDocument && !indexedDocs.has(currentDocument) ? '为当前文档构建向量索引' : '选中左侧未索引的文档后点击' }}</span>
            </div>
            <div class="guide-card" @click="focusInput">
              <el-icon :size="24" color="#E6A23C"><ChatDotRound /></el-icon>
              <span class="guide-title">开始提问</span>
              <span class="guide-desc">在下方输入框输入问题开始对话</span>
            </div>
          </div>
          <div class="suggest-questions" v-if="currentDocument">
            <span class="suggest-label">试试这些问题：</span>
            <el-button
              v-for="q in suggestQuestions"
              :key="q"
              size="small"
              round
              @click="askQuestion(q)"
            >{{ q }}</el-button>
          </div>
        </div>

        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          class="message-item"
          :class="msg.role"
        >
          <div class="message-avatar">
            <el-icon v-if="msg.role === 'user'" :size="18"><User /></el-icon>
            <el-icon v-else :size="18"><Monitor /></el-icon>
          </div>
          <div class="message-body">
            <div class="message-content" :class="{ streaming: msg.streaming }" v-html="renderMessageContent(msg)" />
            <!-- 来源引用 -->
            <div v-if="msg.sources && msg.sources.length > 0" class="message-sources">
              <div
                class="source-toggle"
                @click="toggleSources(idx)"
              >
                <el-icon :size="12"><Link /></el-icon>
                检索来源 ({{ msg.sources.length }})
                <el-icon :size="12">
                  <ArrowDown v-if="!expandedSources.has(idx)" />
                  <ArrowUp v-else />
                </el-icon>
              </div>
              <div v-if="expandedSources.has(idx)" class="source-list">
                <div v-for="src in msg.sources" :key="src.index" class="source-item">
                  <div class="source-header">
                    <span class="source-index">#{{ src.index }}</span>
                    <span class="source-score">相似度: {{ (src.score * 100).toFixed(1) }}%</span>
                  </div>
                  <div class="source-text">{{ src.text }}</div>
                </div>
              </div>
            </div>
            <!-- 耗时标注 -->
            <div v-if="msg.retrieval_time_ms" class="message-meta">
              检索 {{ msg.retrieval_time_ms }}ms
              <template v-if="msg.answer_time_ms"> · 生成 {{ msg.answer_time_ms }}ms</template>
              <template v-if="msg.total_time_ms"> · 总计 {{ msg.total_time_ms }}ms</template>
            </div>
          </div>
        </div>

        <!-- 流式等待动画：尚未收到首个 token 时显示 -->
        <div v-if="queryLoading && streamingMessageId < 0" class="message-item assistant">
          <div class="message-avatar">
            <el-icon :size="18"><Monitor /></el-icon>
          </div>
          <div class="message-body">
            <div class="typing-indicator">
              <span class="dot" />
              <span class="dot" />
              <span class="dot" />
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-area">
        <el-input
          ref="inputRef"
          v-model="inputQuestion"
          type="textarea"
          :rows="2"
          placeholder="输入你的问题，按 Enter 发送，Shift+Enter 换行..."
          resize="none"
          :disabled="!currentDocument || queryLoading"
          @keydown.enter.exact="sendMessage"
        />
        <el-button
          type="primary"
          :disabled="!inputQuestion.trim() || !currentDocument || queryLoading"
          :loading="queryLoading"
          @click="sendMessage"
        >
          <el-icon><Position /></el-icon>
          发送
        </el-button>
      </div>
    </main>

    <!-- 右侧：详情面板 -->
    <aside v-if="showDetailPanel" class="detail-panel">
      <div class="detail-header">
        <h3>检索详情</h3>
        <el-button size="small" text @click="showDetailPanel = false">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
      <div class="detail-body">
        <div class="index-stats">
          <h4>索引信息</h4>
          <div class="stat-grid">
            <div class="stat-item">
              <span class="stat-label">文档</span>
              <span class="stat-value">{{ currentDocument || '-' }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">向量数</span>
              <span class="stat-value">{{ indexStats.total_vectors || 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">索引类型</span>
              <span class="stat-value">{{ indexStats.index_type || '-' }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">向量维度</span>
              <span class="stat-value">{{ indexStats.dimension || 768 }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">聚类数</span>
              <span class="stat-value">{{ indexStats.nlist || 1024 }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">nprobe</span>
              <span class="stat-value">{{ indexStats.nprobe || 16 }}</span>
            </div>
          </div>
        </div>
        <div v-if="indexStats.saved_indices && indexStats.saved_indices.length > 0" class="saved-indices">
          <h4>已保存索引</h4>
          <div v-for="idx in indexStats.saved_indices" :key="idx.name" class="saved-index-item">
            <span>{{ idx.name }}</span>
            <span class="idx-size">{{ formatSize(idx.size_bytes) }}</span>
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Document, ChatRound, Message, Loading, DArrowLeft, DArrowRight,
  Monitor, User, Link, ArrowDown, ArrowUp, Close, Position,
  Upload, Connection, ChatDotRound
} from '@element-plus/icons-vue'
import { marked } from 'marked'
import { queryRag, queryRagStream, clearHistory, getRagStats, getDocuments, buildIndex } from '@/api/rag'

// --- 状态 ---
const documents = ref([])
const documentsLoading = ref(false)
const currentDocument = ref('')
const indexBuilding = ref(false)
const queryLoading = ref(false)
const inputQuestion = ref('')
const inputRef = ref(null)
const messages = ref([])
const sidebarCollapsed = ref(false)
const showDetailPanel = ref(false)
const expandedSources = reactive(new Set())
const messageListRef = ref(null)
const sessionId = ref('')
const streamAbortController = ref(null)
const streamingMessageId = ref(-1)  // 正在流式渲染的消息索引

const router = useRouter()

const indexStats = reactive({
  total_vectors: 0,
  index_type: '',
  dimension: 768,
  nlist: 1024,
  nprobe: 16,
  saved_indices: []
})

const indexedDocs = reactive(new Set())

// 推荐问题
const suggestQuestions = [
  '请总结这份文档的核心内容',
  '文档中提到了哪些关键数据和指标？',
  '帮我提取文档中的表格信息',
  '这篇文章的主要观点是什么？',
  '文档中涉及了哪些关键数据项？'
]

// --- 初始化 ---
const initSession = () => {
  sessionId.value = 'rag-' + Date.now() + '-' + Math.random().toString(36).slice(2, 9)
}

onMounted(async () => {
  initSession()
  await refreshDocuments()
  await loadStats()
})

onUnmounted(() => {
  if (streamAbortController.value) {
    streamAbortController.value.abort()
  }
})

const refreshDocuments = async () => {
  documentsLoading.value = true
  const res = await getDocuments()
  if (res.success) {
    documents.value = (res.documents || []).sort((a, b) => a.name.localeCompare(b.name))
  }
  documentsLoading.value = false
}

const loadStats = async () => {
  const res = await getRagStats()
  if (res.success && res.stats) {
    Object.assign(indexStats, res.stats)
    indexedDocs.clear()
    if (res.stats.saved_indices) {
      res.stats.saved_indices.forEach(idx => indexedDocs.add(idx.name))
    }
  }
}

const selectDocument = async (doc) => {
  currentDocument.value = doc.name
  if (indexedDocs.has(doc.name)) {
    const res = await getRagStats()
    if (res.success) {
      Object.assign(indexStats, res.stats)
    }
  }
}

const buildIndexForCurrent = async () => {
  if (!currentDocument.value) return
  const doc = documents.value.find(d => d.name === currentDocument.value)
  if (!doc) return

  indexBuilding.value = true
  const res = await buildIndex(doc.path)
  if (res.success) {
    indexedDocs.add(currentDocument.value)
    ElMessage.success(`索引构建成功！共 ${res.vector_count || res.chunk_count} 条数据`)
    await loadStats()
  } else {
    ElMessage.error(res.error || '索引构建失败')
  }
  indexBuilding.value = false
}

// --- 引导卡片点击处理 ---
const goToUpload = () => {
  router.push('/two-column')
}

const handleGuideBuildIndex = async () => {
  if (!currentDocument.value) {
    ElMessage.info('请先在左侧选择一个 PDF 文档')
    return
  }
  if (indexedDocs.has(currentDocument.value)) {
    ElMessage.info('该文档已构建索引，可以直接提问')
    return
  }
  await buildIndexForCurrent()
}

const focusInput = () => {
  if (!currentDocument.value) {
    ElMessage.warning('请先在左侧选择一个 PDF 文档')
    return
  }
  nextTick(() => {
    const el = inputRef.value?.$el || inputRef.value
    const textarea = el?.querySelector?.('textarea') || el
    if (textarea) {
      textarea.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
      textarea.focus?.()
      ElMessage.success('请在下方输入框输入问题')
    }
  })
}

// --- 消息发送（流式） ---
const sendMessage = async () => {
  const question = inputQuestion.value.trim()
  if (!question || !currentDocument.value || queryLoading.value) return

  inputQuestion.value = ''

  // 添加用户消息
  messages.value.push({ role: 'user', content: question })

  // 添加空的 assistant 占位消息（流式追加内容）
  const assistantIdx = messages.value.length
  messages.value.push({
    role: 'assistant',
    content: '',
    streaming: true,
    sources: [],
    retrieval_time_ms: 0,
    total_time_ms: 0
  })
  streamingMessageId.value = assistantIdx
  await scrollToBottom()

  queryLoading.value = true

  // 发起流式请求
  streamAbortController.value = queryRagStream(
    question,
    currentDocument.value,
    5,
    sessionId.value,
    {
      onRetrieval: (data) => {
        if (messages.value[assistantIdx]) {
          messages.value[assistantIdx].retrieval_time_ms = data.retrieval_time_ms || 0
        }
      },
      onToken: (token) => {
        if (messages.value[assistantIdx]) {
          messages.value[assistantIdx].content += token
        }
      },
      onDone: (data) => {
        if (messages.value[assistantIdx]) {
          messages.value[assistantIdx].streaming = false
          messages.value[assistantIdx].sources = data.sources || []
        }
        streamingMessageId.value = -1
        queryLoading.value = false
        scrollToBottom()
      },
      onError: (errMsg) => {
        if (messages.value[assistantIdx]) {
          messages.value[assistantIdx].content = `抱歉，查询失败：${errMsg || '未知错误'}`
          messages.value[assistantIdx].streaming = false
        }
        streamingMessageId.value = -1
        queryLoading.value = false
        scrollToBottom()
      }
    }
  )
}

const askQuestion = (q) => {
  inputQuestion.value = q
  sendMessage()
}

const toggleSources = (idx) => {
  if (expandedSources.has(idx)) {
    expandedSources.delete(idx)
  } else {
    expandedSources.add(idx)
  }
}

const clearMessages = async () => {
  // 中止正在进行的流式请求
  if (streamAbortController.value) {
    streamAbortController.value.abort()
    streamAbortController.value = null
  }
  messages.value = []
  expandedSources.clear()
  streamingMessageId.value = -1
  queryLoading.value = false

  // 清除后端对话历史
  if (sessionId.value) {
    try {
      await clearHistory(sessionId.value)
    } catch (e) {
      // 静默失败
    }
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

const renderMarkdown = (text) => {
  if (!text) return ''
  return marked.parse(text, { breaks: true, gfm: true })
}

const renderMessageContent = (msg) => {
  const md = renderMarkdown(msg.content)
  if (msg.streaming) {
    return md + '<span class="typing-cursor">|</span>'
  }
  return md
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<style scoped>
.rag-chat-page {
  display: flex;
  height: calc(100vh - 50px);
  background: #f5f7fa;
  overflow: hidden;
}

/* ========== 左侧面板 ========== */
.sidebar {
  width: 260px;
  min-width: 260px;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  transition: width 0.3s, min-width 0.3s;
  overflow: hidden;
}
.sidebar.collapsed {
  width: 48px;
  min-width: 48px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 12px;
  border-bottom: 1px solid #ebeef5;
}
.collapsed .sidebar-header {
  justify-content: center;
  padding: 14px 0;
}
.sidebar-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
}

.sidebar-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  color: #909399;
  font-size: 13px;
}

.empty-state {
  padding: 16px;
}

.document-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.doc-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}
.doc-item:hover {
  background: #f0f5ff;
  border-color: #d9ecff;
}
.doc-item.active {
  background: #ecf5ff;
  border-color: #409eff;
}
.doc-item.indexed {
  border-left: 3px solid #67c23a;
}

.doc-icon {
  flex-shrink: 0;
  color: #409eff;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ecf5ff;
  border-radius: 6px;
}

.doc-info {
  flex: 1;
  min-width: 0;
}

.doc-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.doc-size {
  font-size: 11px;
  color: #909399;
}

.sidebar-footer {
  padding: 10px 12px;
  border-top: 1px solid #ebeef5;
}

/* ========== 中间对话区域 ========== */
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #f5f7fa;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}

.chat-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.chat-actions {
  display: flex;
  gap: 8px;
}

/* 消息列表 */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.welcome-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 12px;
}
.welcome-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  margin-bottom: 8px;
}
.welcome-area h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}
.welcome-area p {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.guide-cards {
  display: flex;
  gap: 16px;
  margin-top: 16px;
}
.guide-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 16px 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #ecf0f5 100%);
  border-radius: 12px;
  border: 1px solid #e4e7ed;
  min-width: 140px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
}
.guide-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
  border-color: #c0c4cc;
}
.guide-card .guide-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}
.guide-card .guide-desc {
  font-size: 11px;
  color: #909399;
  text-align: center;
  line-height: 1.4;
}

.suggest-questions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
  justify-content: center;
}
.suggest-label {
  width: 100%;
  text-align: center;
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

/* 消息项 */
.message-item {
  display: flex;
  gap: 12px;
  max-width: 80%;
  animation: fadeIn 0.3s ease;
}
.message-item.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}
.message-item.assistant {
  align-self: flex-start;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.message-item.user .message-avatar {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
}
.message-item.assistant .message-avatar {
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
}

.message-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.message-content {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
  color: #303133;
  word-break: break-word;
}
.message-content :deep(p) {
  margin: 0 0 8px 0;
}
.message-content :deep(p:last-child) {
  margin-bottom: 0;
}
.message-content :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
  width: 100%;
  font-size: 13px;
}
.message-content :deep(th),
.message-content :deep(td) {
  border: 1px solid #dcdfe6;
  padding: 6px 10px;
  text-align: left;
}
.message-content :deep(th) {
  background: #f5f7fa;
  font-weight: 600;
}
.message-content :deep(ul),
.message-content :deep(ol) {
  padding-left: 20px;
  margin: 4px 0;
}
.message-content :deep(strong) {
  font-weight: 600;
  color: #303133;
}
.message-content :deep(blockquote) {
  border-left: 3px solid #409eff;
  padding-left: 12px;
  margin: 8px 0;
  color: #606266;
  background: #f0f5ff;
  padding: 8px 12px;
  border-radius: 0 6px 6px 0;
}

.message-item.user .message-content {
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
}
.message-item.assistant .message-content {
  background: #fff;
  border: 1px solid #e4e7ed;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

/* 来源引用 */
.message-sources {
  margin-top: 4px;
}

.source-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #909399;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: all 0.2s;
}
.source-toggle:hover {
  background: #f0f5ff;
  color: #409eff;
}

.source-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 6px;
  padding: 8px;
  background: #fafbfc;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  max-height: 240px;
  overflow-y: auto;
}

.source-item {
  padding: 8px 10px;
  background: #fff;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}

.source-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.source-index {
  font-size: 12px;
  font-weight: 600;
  color: #409eff;
}

.source-score {
  font-size: 11px;
  color: #909399;
}

.source-text {
  font-size: 12px;
  color: #606266;
  line-height: 1.6;
  max-height: 80px;
  overflow-y: auto;
}

.message-meta {
  font-size: 11px;
  color: #c0c4cc;
  padding-left: 4px;
}

/* 打字机动画 */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
}
.typing-indicator .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #c0c4cc;
  animation: bounce 1.4s infinite both;
}
.typing-indicator .dot:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator .dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.message-content.streaming {
  position: relative;
}
.typing-cursor {
  display: inline-block;
  color: #409eff;
  font-weight: 700;
  animation: cursorBlink 0.8s infinite;
  margin-left: 1px;
}
@keyframes cursorBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* ========== 输入区域 ========== */
.input-area {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 14px 20px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
  flex-shrink: 0;
}
.input-area :deep(.el-textarea__inner) {
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.6;
  transition: border-color 0.3s;
}
.input-area :deep(.el-textarea__inner:focus) {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64,158,255,0.1);
}
.input-area .el-button {
  border-radius: 10px;
  height: 42px;
  min-width: 80px;
}

/* ========== 右侧详情面板 ========== */
.detail-panel {
  width: 300px;
  min-width: 300px;
  background: #fff;
  border-left: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #ebeef5;
}
.detail-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.index-stats h4,
.saved-indices h4 {
  margin: 0 0 12px 0;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.stat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 16px;
}

.stat-item {
  padding: 8px;
  background: #f5f7fa;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: 11px;
  color: #909399;
}

.stat-value {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.saved-indices {
  margin-top: 16px;
}

.saved-index-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  background: #f5f7fa;
  border-radius: 6px;
  margin-bottom: 6px;
  font-size: 12px;
  color: #606266;
}
.idx-size {
  color: #909399;
  font-size: 11px;
}
</style>
