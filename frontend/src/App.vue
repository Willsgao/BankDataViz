<!-- frontend/src/App.vue -->
<template>
  <div id="app">
    <!-- 顶部导航栏 -->
    <div class="top-nav">
      <!-- 布局切换 -->
      <div class="layout-switcher">
        <el-button-group>
          <el-button
            :type="$route.name === 'TwoColumn' ? 'primary' : ''"
            @click="goToTwoColumn"
            size="small"
          >
            两栏布局
          </el-button>
          <el-button
            :type="$route.name === 'ThreeColumn' ? 'primary' : ''"
            @click="$router.push('/three-column')"
            size="small"
          >
            三栏布局
          </el-button>
        </el-button-group>
      </div>

      <!-- 搜索框 -->
      <div class="search-box">
        <el-input
          v-model="searchKeyword"
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

      <!-- 右侧：用户信息和登出 -->
      <div class="user-info" v-if="isLoggedIn">
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
              <el-dropdown-item divided command="logout">
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      <div class="login-prompt" v-else>
        <el-button type="text" @click="$router.push('/login')" size="small">
          请先登录
        </el-button>
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
import { Search, ArrowDown } from '@element-plus/icons-vue'
import { ref, computed, provide, onMounted, watch } from 'vue'
import { getApiUrl } from '@/utils/config'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const searchKeyword = ref('')

// 用户信息
const username = ref('')
const userRole = ref('')

// 计算属性
const isLoggedIn = computed(() => {
  return !!localStorage.getItem('token')
})

const hasAdminPermission = computed(() => {
  return userRole.value === 'admin'
})

const userRoleName = computed(() => {
  return userRole.value === 'admin' ? '管理员' : '普通用户'
})

const userInitial = computed(() => {
  return username.value ? username.value.charAt(0).toUpperCase() : 'U'
})

// 初始化用户信息
const updateUserInfo = () => {
  username.value = localStorage.getItem('username') || ''
  userRole.value = localStorage.getItem('user_role') || ''
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

// 两栏布局导航（检查权限）
const goToTwoColumn = () => {
  if (hasAdminPermission.value) {
    router.push('/two-column')
  } else {
    ElMessage.warning('权限不足，只有管理员可以访问两栏布局')
  }
}

// 用户命令处理
const handleUserCommand = (command) => {
  if (command === 'logout') {
    handleLogout()
  }
}

// 登出处理
const handleLogout = () => {
  ElMessageBox.confirm('确定要退出登录吗？', '退出确认', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    // 清除用户信息
    localStorage.removeItem('token')
    localStorage.removeItem('user_role')
    localStorage.removeItem('username')

    // 更新用户信息
    updateUserInfo()

    // 清除搜索状态
    searchResults.value = []
    searchKeyword.value = ''

    ElMessage.success('已退出登录')

    // 跳转到登录页面
    router.push('/login')
  }).catch(() => {
    // 用户取消操作
  })
}

// 提供搜索功能给子组件（保留原有功能）
const searchResults = ref([])
const isSearching = ref(false)

const handleSearch = async () => {
  if (!searchKeyword.value.trim()) {
    searchResults.value = []
    return
  }

  isSearching.value = true
  try {
    const response = await fetch(getApiUrl(`/search-pdf?keyword=${encodeURIComponent(searchKeyword.value)}`))
    if (response.ok) {
      const data = await response.json()
      searchResults.value = data.files || []
    } else {
      searchResults.value = []
    }
  } catch (error) {
    console.error('搜索失败:', error)
    searchResults.value = []
  } finally {
    isSearching.value = false
  }
}

const handleSearchClear = () => {
  searchResults.value = []
}

// 提供给子组件使用
provide('searchResults', searchResults)
provide('isSearching', isSearching)
provide('handleSearch', handleSearch)
provide('userRole', userRole)

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

.layout-switcher {
  /* 保持原有样式 */
}

.search-box {
  display: flex;
  align-items: center;
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

/* 为路由视图留出顶部空间 */
.router-view-container {
  height: calc(100vh - 60px);
  margin-top: 60px;
  overflow: auto;
}
</style>