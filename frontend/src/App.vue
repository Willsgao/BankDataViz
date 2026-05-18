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
            v-model="excelContentSearchState.keyword"
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
            v-if="excelContentSearchState.keyword.trim().length > 0"
            size="small"
            circle
            plain
            style="margin-left: 2px; flex-shrink: 0;"
            :disabled="excelContentSearchState.matchCount <= 1"
            title="上一个匹配Sheet"
            @click="goToPrevMatch"
          >
            <el-icon><ArrowLeft /></el-icon>
          </el-button>
          <span
            v-if="excelContentSearchState.keyword.trim().length > 0"
            style="font-size: 11px; color: #909399; white-space: nowrap; min-width: 32px; text-align: center;"
          >
            {{ excelContentSearchState.matchCount > 0 ? (excelContentSearchState.matchIndex + 1 + '/' + excelContentSearchState.matchCount) : '-' }}
          </span>
          <el-button
            v-if="excelContentSearchState.keyword.trim().length > 0"
            size="small"
            circle
            type="primary"
            plain
            style="flex-shrink: 0;"
            :disabled="excelContentSearchState.matchCount <= 1"
            title="下一个匹配Sheet"
            @click="goToNextMatch"
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
import { useSearchStore } from '@/stores/search'

const route = useRoute()
const router = useRouter()

// ===== 使用 Auth Store 管理认证状态 =====
const auth = useAuth()
const searchStore = useSearchStore()

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

// PDF搜索状态
const searchState = reactive({
  keyword: '',
  results: [],
  isSearching: false
})

// Excel内容搜索状态
const excelContentSearchState = reactive({
  keyword: '',
  isSearching: false,
  lastSearchTime: 0,
  matchCount: 0,
  active: false,
  matchIndex: 0,           // 当前匹配位置（从0开始）
  matchedSheetsList: []    // 匹配 Sheet 列表 [{excel_file, sheet_name}]
})

// 暴露到 window，供 ThreeColumnPage 事件监听器更新 matchCount
if (typeof window !== 'undefined') {
  window.excelContentSearchState = excelContentSearchState
}

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

    // 清除搜索状态（包括 Store）
    searchState.results = []
    searchState.keyword = ''
    excelContentSearchState.keyword = ''
    excelContentSearchState.matchCount = 0
    excelContentSearchState.active = false
    searchStore.clearAll()

    ElMessage.success('已退出登录')

    // 跳转到登录页面
    router.push('/login')
  }).catch(() => {
    // 用户取消操作
  })
}


const handleExcelContentSearch = () => {
  const keyword = excelContentSearchState.keyword.trim()

  if (!keyword) {
    excelContentSearchState.isSearching = false
    excelContentSearchState.matchCount = 0
    excelContentSearchState.active = false
    excelContentSearchState.lastSearchTime = Date.now()
    excelContentSearchState.matchIndex = 0
    excelContentSearchState.matchedSheetsList = []
    // 同步清除 Search Store
    searchStore.clearExcelSearch()
    console.log('🔍 Excel内容搜索：清空搜索条件')
    return
  }

  console.log(`🔍 Excel内容搜索: '${keyword}'`)
  excelContentSearchState.isSearching = true
  excelContentSearchState.active = true
  excelContentSearchState.lastSearchTime = Date.now()
  // 同步关键词到 Search Store
  searchStore.setExcelKeyword(keyword)

  // 增强的路由逻辑
  const enhancedRouteSearch = () => {
    console.log('🔄 开始增强路由搜索...')

    // 方法1：查找所有可能的组件
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

        // 优先尝试 performSearch 方法
        if (vueInstance.performSearch) {
          console.log('🎯 调用组件的 performSearch 方法')
          vueInstance.performSearch(keyword)
          routed = true
          break
        }

        // 备用方案：直接调用高亮函数
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

  // 方法2：检查全局搜索函数
  const useGlobalSearch = () => {
    if (window.performExcelSearch) {
      console.log('🚀 使用全局搜索函数')
      window.performExcelSearch(keyword)
      return true
    }
    return false
  }

  // 方法3：最后尝试通过事件发射
  const useEventEmit = () => {
    console.log('📡 通过事件发射搜索请求')
    window.dispatchEvent(new CustomEvent('excel-content-search', {
      detail: { keyword }
    }))
    return true
  }

  // 按优先级执行搜索策略（高亮当前表格）
  if (!enhancedRouteSearch() && !useGlobalSearch()) {
    useEventEmit()
  }

  // 始终发射跨Sheet搜索事件，确保 ThreeColumnPage 能更新 matchCount 和翻页按钮
  // （enhancedRouteSearch 只做当前表格高亮，不负责跨Sheet搜索和计数）
  console.log('📡📡📡 App.vue 发射 excel-content-search 事件, keyword=', keyword)
  window.dispatchEvent(new CustomEvent('excel-content-search', {
    detail: { keyword }
  }))

  setTimeout(() => {
    excelContentSearchState.isSearching = false
  }, 300)
}


// 跳转到指定索引的匹配 Sheet（公共逻辑）
const goToMatchByIndex = (index) => {
  const { matchedSheetsList } = excelContentSearchState
  if (!matchedSheetsList || matchedSheetsList.length === 0) return

  excelContentSearchState.matchIndex = index
  // 同步到 Search Store
  excelContentSearchState.matchedSheetsList && searchStore.setExcelMatchedSheets(excelContentSearchState.matchedSheetsList)
  searchStore.goToMatchByIndex(index)

  const match = matchedSheetsList[index]
  window.dispatchEvent(new CustomEvent('excel-search-goto', {
    detail: {
      excel_file: match.excel_file,
      sheet_name: match.sheet_name,
      matchIndex: index,
      total: matchedSheetsList.length
    }
  }))

  console.log(`🔄 跳转到第 ${index + 1}/${matchedSheetsList.length} 个匹配:`, match)
}

// 跳转到下一个匹配 Sheet
const goToNextMatch = () => {
  const { matchIndex, matchedSheetsList } = excelContentSearchState
  if (!matchedSheetsList || matchedSheetsList.length === 0) return
  const nextIndex = (matchIndex + 1) % matchedSheetsList.length
  goToMatchByIndex(nextIndex)
}

// 跳转到上一个匹配 Sheet
const goToPrevMatch = () => {
  const { matchIndex, matchedSheetsList } = excelContentSearchState
  if (!matchedSheetsList || matchedSheetsList.length === 0) return
  const prevIndex = (matchIndex - 1 + matchedSheetsList.length) % matchedSheetsList.length
  goToMatchByIndex(prevIndex)
}


// 在 App.vue 的 script setup 中修正高亮函数

// 直接DOM操作高亮Sheet名称（精确匹配表格名）
const highlightSheetNamesDirectly = (keyword) => {
  const lowerKeyword = keyword.toLowerCase()
  sheetHighlightState.matchedSheets.clear()

  let matchCount = 0
  const allMatches = new Set()

  // 更精确的选择器，只针对表格名称元素
  const sheetNameSelectors = [
    // 表格名称特有的选择器
    '.sheet-name',
    '.table-name',
    '.excel-sheet-name',
    '.pdf-sheet-name',
    '[class*="sheet-name"]',
    '[class*="table-name"]',
    '.el-tree-node__label', // 但需要进一步过滤
    '.el-collapse-item__label' // 但需要进一步过滤
  ]

  console.log('🔍 开始搜索表格名称:', keyword)

  // 方法1：精确匹配表格名称元素
  sheetNameSelectors.forEach(selector => {
    try {
      const elements = document.querySelectorAll(selector)
      elements.forEach(element => {
        const text = element.textContent?.toLowerCase()?.trim() || ''
        const innerText = element.innerText?.toLowerCase()?.trim() || ''

        // 精确检查：文本内容必须包含关键词
        if (text.includes(lowerKeyword) || innerText.includes(lowerKeyword)) {
          // 进一步验证：这确实是一个表格名称（包含sheet/表等关键词）
          const isLikelySheetName = text.includes('sheet') ||
                                   text.includes('表') ||
                                   text.includes('p0') || // 常见的表格前缀
                                   text.match(/[pP]\d+/) // P开头的数字编号

          if (isLikelySheetName) {
            // 添加高亮样式
            element.classList.add('excel-sheet-highlight')
            element.style.setProperty('background-color', '#fff566', 'important')
            element.style.setProperty('color', '#000', 'important')
            element.style.setProperty('font-weight', 'bold', 'important')
            element.style.setProperty('border', '2px solid #ffc53d', 'important')
            element.style.borderRadius = '4px'
            element.style.padding = '2px 6px'
            element.style.margin = '2px 0'
            element.style.display = 'inline-block'

            // 记录匹配的表格名称
            const sheetName = element.textContent?.trim() || element.innerText?.trim()
            if (sheetName) {
              allMatches.add(sheetName)
              console.log('✅ 找到匹配的表格名称:', sheetName)
            }
            matchCount++
          }
        } else {
          // 清除不匹配元素的高亮
          element.classList.remove('excel-sheet-highlight')
          element.style.removeProperty('background-color')
          element.style.removeProperty('color')
          element.style.removeProperty('font-weight')
          element.style.removeProperty('border')
        }
      })
    } catch (error) {
      console.warn('⚠️ 处理选择器时出错:', selector, error)
    }
  })

  // 方法2：智能搜索包含表格关键词的元素
  if (matchCount === 0) {
    console.log('🔄 尝试智能搜索表格名称...')

    // 搜索包含表格特征的关键词
    const sheetKeywords = ['sheet', '表', '表格', '报表', 'P0', 'P1', 'P2', 'P3']
    const allTextElements = document.querySelectorAll('*')

    allTextElements.forEach(element => {
      if (element.children.length === 0) { // 只处理叶子文本节点
        const text = element.textContent?.toLowerCase()?.trim() || ''

        if (text && text.includes(lowerKeyword)) {
          // 检查是否包含表格特征关键词
          const hasSheetKeyword = sheetKeywords.some(keyword =>
            text.includes(keyword.toLowerCase())
          )

          if (hasSheetKeyword) {
            // 找到父级容器元素进行高亮
            let highlightElement = element
            // 向上查找合适的容器元素（避免高亮单个文本节点）
            while (highlightElement.parentElement &&
                   highlightElement.parentElement.children.length === 1) {
              highlightElement = highlightElement.parentElement
            }

            highlightElement.classList.add('excel-sheet-highlight')
            highlightElement.style.setProperty('background-color', '#fff566', 'important')
            highlightElement.style.setProperty('color', '#000', 'important')
            highlightElement.style.setProperty('font-weight', 'bold', 'important')
            highlightElement.style.setProperty('border', '2px solid #ffc53d', 'important')
            highlightElement.style.borderRadius = '4px'
            highlightElement.style.padding = '2px 6px'
            highlightElement.style.margin = '2px 0'
            highlightElement.style.display = 'inline-block'

            const sheetName = highlightElement.textContent?.trim()
            if (sheetName) {
              allMatches.add(sheetName)
              console.log('✅ 智能找到匹配的表格名称:', sheetName)
            }
            matchCount++
          }
        }
      }
    })
  }

  sheetHighlightState.matchedSheets = allMatches

  // 清理其他可能误高亮的元素
  cleanupFalseHighlights(lowerKeyword)

  console.log('✅ 表格名称高亮完成:', {
    关键词: keyword,
    匹配表格数: matchCount,
    匹配的表格名称: Array.from(allMatches)
  })
}

// 清理误高亮的元素
const cleanupFalseHighlights = (keyword) => {
  const allHighlighted = document.querySelectorAll('.excel-sheet-highlight')
  allHighlighted.forEach(element => {
    const text = element.textContent?.toLowerCase()?.trim() || ''
    if (!text.includes(keyword)) {
      element.classList.remove('excel-sheet-highlight')
      element.style.removeProperty('background-color')
      element.style.removeProperty('color')
      element.style.removeProperty('font-weight')
      element.style.removeProperty('border')
    }
  })
}

// 增强的清除函数
const clearSheetHighlights = () => {
  const elements = document.querySelectorAll('.excel-sheet-highlight')
  elements.forEach(element => {
    element.classList.remove('excel-sheet-highlight')
    element.style.removeProperty('background-color')
    element.style.removeProperty('color')
    element.style.removeProperty('font-weight')
    element.style.removeProperty('border')
    element.style.removeProperty('border-radius')
    element.style.removeProperty('padding')
    element.style.removeProperty('margin')
    element.style.removeProperty('display')
  })

  console.log('🧹 清除所有表格名称高亮')
}

// Sheet名称高亮相关状态
const sheetHighlightState = reactive({
  keyword: '',
  matchedSheets: new Set(),
  isHighlighting: false
})

// 修改 performExcelContentSearch 函数
provide('performExcelContentSearch', (keyword) => {
  console.log('🎯 执行Excel内容搜索:', keyword)

  // 1. 高亮Sheet名称（中间栏）
  highlightSheetNames(keyword)

  // 2. 通过全局事件触发搜索（ThreeColumnPage 负责调 API 更新 matchCount）
  window.dispatchEvent(new CustomEvent('excel-content-search', {
    detail: { keyword }
  }))

  // 注意：不再调用 updateMatchCount，matchCount 由 ThreeColumnPage 的 API 搜索结果设置
})

// 实现Sheet名称高亮函数
const highlightSheetNames = (keyword) => {
  const searchKeyword = keyword?.trim() || ''

  if (!searchKeyword) {
    // 清空搜索时清除高亮
    clearSheetHighlights()
    sheetHighlightState.keyword = ''
    sheetHighlightState.matchedSheets.clear()
    sheetHighlightState.isHighlighting = false
    console.log('🔍 Sheet名称高亮：清空搜索条件')
    return
  }

  console.log('🔍 高亮Sheet名称:', searchKeyword)
  sheetHighlightState.keyword = searchKeyword
  sheetHighlightState.isHighlighting = true

  // 延迟执行以避免阻塞UI
  setTimeout(() => {
    highlightSheetNamesDirectly(searchKeyword)
    sheetHighlightState.isHighlighting = false
  }, 50)
}


// 更新匹配计数
const updateMatchCount = (keyword) => {
  if (!keyword) {
    excelContentSearchState.matchCount = 0
    return
  }

  // 计算总匹配数：Sheet名称匹配数 + 内容匹配数（通过事件获取）
  const sheetMatchCount = sheetHighlightState.matchedSheets.size
  console.log('📊 更新匹配计数:', {
    Sheet名称匹配数: sheetMatchCount,
    关键词: keyword
  })

  // 这里可以结合后续从子组件获取的内容匹配数
  excelContentSearchState.matchCount = sheetMatchCount
}

// 监听搜索清空事件
const handleExcelContentSearchClear = () => {
  excelContentSearchState.keyword = ''
  excelContentSearchState.isSearching = false
  excelContentSearchState.matchCount = 0
  excelContentSearchState.active = false
  excelContentSearchState.lastSearchTime = Date.now()
  excelContentSearchState.matchIndex = 0
  excelContentSearchState.matchedSheetsList = []

  // 同步清除 Search Store
  searchStore.clearExcelSearch()

  // 清除Sheet高亮
  clearSheetHighlights()
  sheetHighlightState.matchedSheets.clear()
  sheetHighlightState.keyword = ''
  sheetHighlightState.isHighlighting = false

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

// 把Excel内容搜索状态提供给后代组件
provide('excelContentSearchState', excelContentSearchState)
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