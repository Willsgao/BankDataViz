<template>
  <div id="app">
    <!-- 顶部导航栏（登录页隐藏） -->
    <div
      v-show="route.path !== '/login'"
      class="top-nav"
    >
      <!-- 左侧区域：布局切换 + PDF 搜索 -->
      <div class="left-section">
        <!-- 布局切换按钮 -->
        <div class="layout-switcher">
          <el-button-group>
            <el-button
              v-if="hasPermission('parse')"
              :type="$route.name === 'TwoColumn' ? 'primary' : ''"
              size="small"
              @click="goToTwoColumn"
            >
              数据解析
            </el-button>
            <el-button
              v-if="hasPermission('review')"
              :type="$route.name === 'ThreeColumn' ? 'primary' : ''"
              size="small"
              @click="$router.push('/three-column')"
            >
              数据审核
            </el-button>
            <span class="nav-separator" />
            <el-button
              type="warning"
              size="small"
              @click="$router.push('/audit')"
            >
              会计勾稽
            </el-button>
            <el-button
              type="success"
              size="small"
              @click="$router.push('/smart-recognize')"
            >
              智能识别
            </el-button>
            <el-button
              :type="$route.name === 'RagChat' ? 'primary' : ''"
              size="small"
              class="rag-btn"
              @click="$router.push('/rag-chat')"
            >
              智能问答
            </el-button>
            <el-button
              :type="$route.name === 'PromptShowcase' ? 'primary' : ''"
              size="small"
              class="prompt-btn"
              @click="$router.push('/prompt-engineering')"
            >
              Prompt 工程
            </el-button>
            <el-button
              :type="$route.name === 'AgentWorkflow' ? 'primary' : 'success'"
              size="small"
              class="agent-btn"
              @click="$router.push('/agent-workflow')"
            >
              Agent 工作流
            </el-button>
            <span class="nav-separator" />
            <el-dropdown
              v-if="hasPermission('data')"
              trigger="hover"
              @command="handleBankDashboardCommand"
            >
              <el-button
                :type="['BankDashboard', 'BankData'].includes($route.name) ? 'primary' : ''"
                size="small"
                @click="handleBankDashboardClick"
              >
                数据看板
                <el-icon class="el-icon--right">
                  <ArrowDown />
                </el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="dashboard">
                    <el-icon><DataBoard /></el-icon>
                    数据看板-图表
                  </el-dropdown-item>
                  <el-dropdown-item command="data">
                    <el-icon><FolderOpened /></el-icon>
                    数据看板-文档
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </el-button-group>
        </div>

        <!-- PDF 文件搜索框（左侧） -->
        <div class="search-box pdf-search">
          <el-input
            v-model="searchState.keyword"
            placeholder="搜索PDF文件名称..."
            clearable
            size="small"
            style="width: 300px;"
            @input="handleSearch"
            @clear="handleSearchClear"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
      </div>

      <!-- 右侧区域：Excel 搜索 + 主题切换 + 用户信息 -->
      <div class="right-section">
        <!-- Excel 内容搜索框（右侧） -->
        <div class="excel-search-group">
          <el-input
            v-model="excelKeyword"
            placeholder="搜索Excel内容..."
            clearable
            size="small"
            style="width: 200px; flex-shrink: 0;"
            @input="handleExcelContentSearch"
            @clear="handleExcelContentSearchClear"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <!-- 翻页按钮：← N/M → -->
          <el-button
            v-if="hasExcelKeyword"
            size="small"
            circle
            plain
            style="margin-left: 2px; flex-shrink: 0;"
            :disabled="excelMatchCount <= 1"
            title="上一个匹配Sheet"
            @click="search.goToPrevMatch()"
          >
            <el-icon><ArrowLeft /></el-icon>
          </el-button>
          <span
            v-if="hasExcelKeyword"
            style="font-size: 11px; color: #909399; white-space: nowrap; min-width: 32px; text-align: center;"
          >
            {{ excelMatchCount > 0 ? (excelMatchIndex + 1 + '/' + excelMatchCount) : '-' }}
          </span>
          <el-button
            v-if="hasExcelKeyword"
            size="small"
            circle
            type="primary"
            plain
            style="flex-shrink: 0;"
            :disabled="excelMatchCount <= 1"
            title="下一个匹配Sheet"
            @click="search.goToNextMatch()"
          >
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>

        <!-- 主题切换 -->
        <ThemeToggle v-if="isLoggedIn" />

        <!-- 用户信息 -->
        <div
          v-if="isLoggedIn"
          class="user-info"
        >
          <el-dropdown @command="handleUserCommand">
            <div class="user-avatar">
              <el-avatar size="small">
                {{ userInitial }}
              </el-avatar>
              <span class="username">{{ username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  <span style="color: #909399;">
                    {{ userRoleName }}
                  </span>
                </el-dropdown-item>
                <el-dropdown-item
                  v-if="isSuperAdmin"
                  divided
                  command="admin-management"
                >
                  <el-icon><Setting /></el-icon>
                  子管理员管理
                </el-dropdown-item>
                <el-dropdown-item
                  divided
                  command="logout"
                >
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <div
          v-else
          class="login-prompt"
        >
          <el-button
            type="text"
            size="small"
            @click="$router.push('/login')"
          >
            请先登录
          </el-button>
        </div>
      </div>
    </div>

    <!-- 路由视图 -->
    <div class="router-view-container">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { useRoute, useRouter } from 'vue-router'
import { Search, ArrowDown, ArrowLeft, ArrowRight, DataBoard, FolderOpened, Setting } from '@element-plus/icons-vue'
import { ref, computed, provide, onMounted, watch, reactive, toRefs, toRef } from 'vue'
import { getApiUrl } from '@/utils/config'
import { ElMessage, ElMessageBox } from 'element-plus'
import ThemeToggle from '@/components/common/ThemeToggle.vue'
import { useAuth } from '@/composables/useAuth'
import { useSearch } from '@/composables/useSearch'

const route = useRoute()
const router = useRouter()

// ===== 使用 Auth Store 管理认证状态 =====
const auth = useAuth()
const search = useSearch()

// 模板中使用这些别名保持兼容
const username = auth.username
const userRole = auth.userRole
const permissions = auth.permissions
const isSuperAdmin = auth.isSuperAdmin
const hasAdminPermission = auth.hasAdminPermission
const userRoleName = auth.userRoleName
const isLoggedIn = auth.isLoggedIn
const userInitial = auth.userInitial
const hasPermission = (perm) => auth.hasPermission(perm)

// PDF搜索状态（保留在 App.vue，通过 provide/inject 与 TwoColumnPage/ThreeColumnPage 通信）
const searchState = reactive({
  keyword: '',
  results: [],
  isSearching: false
})

// ===== Excel 搜索状态统一使用 Search Store =====
// 通过 useSearch() composable 读写，单一数据源，不再维护局部 reactive 副本
const excelKeyword = search.excelKeyword
const excelMatchCount = search.excelMatchCount
const excelMatchIndex = search.excelMatchIndex
const isExcelSearchActive = search.isExcelSearchActive

const hasExcelKeyword = computed(() => excelKeyword.value.trim().length > 0)

// 初始化用户信息（从 localStorage 加载到 Auth Store）
const updateUserInfo = () => {
  auth.loadUserInfo()
}

onMounted(() => {
  updateUserInfo()

  // 检查是否登录，未登录时重定向到登录页（排除登录页本身）
  const token = localStorage.getItem('token')
  if (!token && route.path !== '/login') {
    router.push('/login')
  }
})

// 监听路由变化
watch(() => route.path, (newPath) => {
  if (newPath !== '/login') {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/login')
    }
  }
})

// 管理后台导航（检查权限）
const goToTwoColumn = () => {
  if (hasPermission('parse')) {
    router.push('/two-column')
  } else {
    ElMessage.warning('权限不足，您没有数据解析权限')
  }
}

// 数据看板下拉菜单命令处理
const handleBankDashboardCommand = (command) => {
  if (command === 'dashboard') {
    router.push('/bank-dashboard')
  } else if (command === 'data') {
    router.push('/bank-data')
  }
}

// 数据看板按钮点击显示下拉菜单
const handleBankDashboardClick = (event) => {
  // 触发下拉菜单显示
  const target = event.currentTarget
  if (target && target.parentElement) {
    const dropdown = target.parentElement.querySelector('.el-dropdown')
    if (dropdown && dropdown.__vue__) {
      dropdown.__vue__.handleClick()
    }
  }
}

// 用户命令处理
const handleUserCommand = (command) => {
  if (command === 'logout') {
    handleLogout()
  } else if (command === 'admin-management') {
    router.push('/admin-management')
  }
}

// 登出处理
const handleLogout = () => {
  ElMessageBox.confirm('确定要退出登录吗？', '退出确认', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    // 使用 Auth Store 清除用户信息
    auth.logout()

    // 更新用户信息
    updateUserInfo()

    // 清除搜索状态（通过 Store）
    searchState.results = []
    searchState.keyword = ''
    search.clearAll()

    ElMessage.success('已退出登录')

    // 跳转到登录页面
    router.push('/login')
  }).catch(() => {
    // 用户取消操作
  })
}



const handleExcelContentSearch = () => {
  const keyword = excelKeyword.value.trim()

  if (!keyword) {
    search.clearExcelSearch()
    console.log('🔍 Excel内容搜索：清空搜索条件')
    return
  }

  console.log(`🔍 Excel内容搜索: '${keyword}'`)
  search.setExcelActive(true)

  // 增强的路由逻辑：尝试直接高亮当前 Handsontable 中的内容
  const enhancedRouteSearch = () => {
    console.log('🔄 开始增强路由搜索...')
    const viewers = document.querySelectorAll('[class*="handsontable"]')
    console.log(`找到 ${viewers.length} 个可能的组件`)
    let routed = false
    for (const viewer of viewers) {
      const vueInstance = viewer.__vue__ || viewer.__vueParentComponent
      if (vueInstance && vueInstance.props?.excelData?.length > 0) {
        console.log('✅ 找到有数据的组件:', {
          组件类型: vueInstance.props.sheetName,
          数据长度: vueInstance.props.excelData.length
        })
        if (vueInstance.performSearch) {
          console.log('🎯 调用组件的 performSearch 方法')
          vueInstance.performSearch(keyword)
          routed = true
          break
        }
        if (vueInstance.highlightCurrentSheetContent) {
          console.log('🔄 直接调用高亮函数')
          vueInstance.highlightCurrentSheetContent(keyword)
          routed = true
          break
        }
      }
    }
    return routed
  }

  // 方法2：通过 Search Store 调用当前活跃查看器的搜索函数（替代 window.performExcelSearch）
  const useGlobalSearch = () => {
    if (search.performViewerSearch(keyword)) {
      console.log('🚀 通过 Store 调用查看器搜索函数')
      return true
    }
    return false
  }

  // 按优先级执行搜索策略（高亮当前表格）
  if (!enhancedRouteSearch() && !useGlobalSearch()) {
    // fallback: 仍通过事件通知（Phase 3 将替换为 watch Store）
    console.log('📡 通过事件发射搜索请求')
    window.dispatchEvent(new CustomEvent('excel-content-search', {
      detail: { keyword }
    }))
  }

  // 始终发射跨Sheet搜索事件（ThreeColumnPage 负责调 API 更新 matchCount）
  // Phase 3 将用 watch(searchStore.excelSearch.keyword) 替代
  window.dispatchEvent(new CustomEvent('excel-content-search', {
    detail: { keyword }
  }))
}

// 跳转到指定索引的匹配 Sheet（通过 Store 管理索引）
const goToMatchByIndex = (index) => {
  const { matchedSheetsList } = search.excelMatchedSheetsList.value || {}
  const list = search.excelMatchedSheetsList.value
  if (!list || list.length === 0) return

  search.goToMatchByIndex(index)
  const match = list[index]
  // Phase 3 将替换为 watch Store — 当前仍通过事件通信
  window.dispatchEvent(new CustomEvent('excel-search-goto', {
    detail: {
      excel_file: match.excel_file,
      sheet_name: match.sheet_name,
      matchIndex: index,
      total: list.length
    }
  }))
  console.log(`🔄 跳转到第 ${index + 1}/${list.length} 个匹配:`, match)
}

// 跳转到下一个匹配 Sheet
const goToNextMatch = () => {
  const list = search.excelMatchedSheetsList.value
  if (!list || list.length === 0) return
  const nextIndex = (search.goToNextMatch()?.matchIndex ?? (search.excelMatchIndex.value + 1) % list.length)
  // Store 中的 goToNextMatch 已经更新了 matchIndex
  // 但我们需要通过事件通知 ThreeColumnPage（Phase 3 替换为 watch）
  const currentIndex = search.excelMatchIndex.value
  const match = list[currentIndex]
  if (match) {
    window.dispatchEvent(new CustomEvent('excel-search-goto', {
      detail: {
        excel_file: match.excel_file,
        sheet_name: match.sheet_name,
        matchIndex: currentIndex,
        total: list.length
      }
    }))
  }
}

// 跳转到上一个匹配 Sheet
const goToPrevMatch = () => {
  const list = search.excelMatchedSheetsList.value
  if (!list || list.length === 0) return
  search.goToPrevMatch()
  const currentIndex = search.excelMatchIndex.value
  const match = list[currentIndex]
  if (match) {
    window.dispatchEvent(new CustomEvent('excel-search-goto', {
      detail: {
        excel_file: match.excel_file,
        sheet_name: match.sheet_name,
        matchIndex: currentIndex,
        total: list.length
      }
    }))
  }
}


// ==================== Sheet 名称 DOM 高亮（已迁移到 useSheetHighlight.js） ====================
// 原 DOM 操作（highlightSheetNamesDirectly / cleanupFalseHighlights / clearSheetHighlights）
// 已完整迁移到 @/composables/useSheetHighlight.js，在 ThreeColumnPage 中通过 watch Store 自动触发

// performExcelContentSearch（供子组件通过 inject 调用）
provide('performExcelContentSearch', (keyword) => {
  const kw = keyword?.trim() || ''
  // 设置 Sheet 高亮关键词 → useSheetHighlight composable 在 ThreeColumnPage 中自动响应
  search.sheetHighlight.value.keyword = kw
  search.sheetHighlight.value.isHighlighting = !!kw
  // 设置 Excel 搜索关键词 → ThreeColumnPage 的 watch 自动触发跨 Sheet 搜索
  search.setExcelKeyword(kw)
  search.setExcelActive(!!kw)
  // dispatchEvent 保留给 ExcelContent/HandsontableExcelViewer 子组件（Phase 5 将统一迁移到 Store）
  if (kw) {
    window.dispatchEvent(new CustomEvent('excel-content-search', {
      detail: { keyword: kw }
    }))
  }
})

// Sheet名称高亮相关状态已统一到 Search Store 的 sheetHighlight
// 不再维护独立的局部 reactive

// 监听搜索清空事件
const handleExcelContentSearchClear = () => {
  search.clearExcelSearch()
  // 清除 Sheet 高亮（Store 设空 → useSheetHighlight composable 自动清理 DOM）
  search.sheetHighlight.value.keyword = ''
  search.sheetHighlight.value.matchedSheets = []
  search.sheetHighlight.value.isHighlighting = false
  console.log('🔍 Excel内容搜索：清空搜索条件')
}



// PDF搜索函数
const handleSearch = async () => {
  if (!searchState.keyword.trim()) {
    searchState.results = []
    console.log('🔍🔍🔍🔍 搜索关键词为空，清空结果')
    return
  }

  console.log(`🔍🔍🔍🔍🔍🔍🔍🔍 App.vue 搜索: '${searchState.keyword}'`)
  searchState.isSearching = true

  try {
    const apiUrl = `/search-pdf-compatible?keyword=${encodeURIComponent(searchState.keyword)}&limit=100`
    console.log('🔗🔗🔗🔗 请求URL:', apiUrl)

    const response = await fetch(getApiUrl(apiUrl))

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const result = await response.json()

    console.log('📥📥📥📥 后端返回:', {
      文件数: result.files ? result.files.length : 0,
      总数量: result.count
    })

    if (result.files) {
      searchState.results = result.files
      console.log(`✅ App.vue 搜索完成，找到 ${searchState.results.length} 个文件`)

      if (searchState.results.length > 0) {
        console.log('📊📊📊📊 第一个文件数据:', searchState.results[0])
      }
    } else {
      searchState.results = []
    }

  } catch (error) {
    console.error('❌❌❌❌❌❌❌❌ App.vue 搜索失败:', error)
    searchState.results = []
  } finally {
    searchState.isSearching = false

    console.log('🔍🔍🔍🔍 App.vue 搜索完成，检查数据传递:')
    console.log('searchState.results:', searchState.results)
    console.log('searchState.results 长度:', searchState.results.length)
  }
}

const handleSearchClear = () => {
  searchState.results = []
  console.log('🔍🔍🔍🔍🔍🔍🔍🔍 清除搜索结果')
}

// 把搜索状态提供给后代组件
provide('searchState', searchState)
provide('handleSearch', handleSearch)
provide('handleSearchClear', handleSearchClear)
provide('searchResults', toRef(searchState, 'results'))
provide('isSearching', toRef(searchState, 'isSearching'))

// 向后兼容：为仍使用 inject('excelContentSearchState') 的子组件提供 Store 代理
// Phase 3 完成后 ThreeColumnPage 改用 useSearch()，此 provide 可移除
const excelContentSearchStateProxy = computed(() => ({
  keyword: excelKeyword.value,
  matchCount: excelMatchCount.value,
  matchIndex: excelMatchIndex.value,
  matchedSheetsList: search.excelMatchedSheetsList.value
}))
provide('excelContentSearchState', excelContentSearchStateProxy)
provide('handleExcelContentSearch', handleExcelContentSearch)
provide('handleExcelContentSearchClear', handleExcelContentSearchClear)

// 提供reloadUserInfo给登录页使用
provide('reloadUserInfo', updateUserInfo)

onMounted(() => {
  console.log('🚀🚀🚀🚀 App.vue 组件已挂载')
})

// 监听localStorage变化（用于跨标签页同步）
window.addEventListener('storage', (e) => {
  if (e.key === 'token' || e.key === 'user_role' || e.key === 'username') {
    updateUserInfo()
  }
})
</script>

<style>
#app {
  height: 100vh;
  background: #f5f5f5;
  overflow: hidden;
}

.top-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  z-index: 1000;
}

/* 左侧区域：布局切换 + PDF 搜索 */
.left-section {
  display: flex;
  align-items: center;
  gap: 20px;
}

.layout-switcher {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 导航栏分组分隔符（数据处理 | 工具 | 数据消费） */
.nav-separator {
  display: inline-block;
  width: 1px;
  height: 20px;
  background: rgba(255, 255, 255, 0.2);
  margin: 0 4px;
  vertical-align: middle;
  flex-shrink: 0;
}

/* 右侧区域：Excel 搜索 + 用户信息 */
.right-section {
  display: flex;
  align-items: center;
  gap: 20px;
}

/* 搜索框样式 */
.search-box {
  display: flex;
  align-items: center;
}

/* Excel搜索框 + 翻页按钮组 */
.excel-search-group {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.user-info, .login-prompt {
  display: flex;
  align-items: center;
}

.user-avatar {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.user-avatar:hover {
  background-color: #f5f5f5;
}

.username {
  margin: 0 8px;
  font-size: 14px;
  color: #303133;
  min-width: 60px;
  text-align: center;
}

/* 为路由视图留出顶部空间（登录页全屏） */
.router-view-container {
  height: calc(100vh - 60px);
  margin-top: 60px;
  overflow: auto;
}

/* 登录页全屏覆盖 */
.router-view-container:has(.login-page) {
  height: 100vh;
  margin-top: 0;
  overflow: hidden;
}

/* 空单元格高亮样式 */
.empty-cell-highlight {
  background-color: #e6f7ff !important;
  border: 2px solid #1890ff !important;
  box-shadow: 0 0 6px rgba(24, 144, 255, 0.3) !important;
}

.handsontable td.empty-cell-highlight {
  background-color: #e6f7ff !important;
  border: 2px solid #1890ff !important;
  position: relative;
}
</style>