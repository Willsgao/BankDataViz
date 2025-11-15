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
            @click="$router.push('/two-column')"
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
    </div>

    <!-- 路由视图 -->
    <div class="router-view-container">
      <router-view />
    </div>
  </div>
</template>

<script setup>

import { useRoute, useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { ref, provide } from 'vue'
import { getApiUrl } from '@/utils/config'

const route = useRoute()
const router = useRouter()
const searchKeyword = ref('')

// 提供搜索功能给子组件
const searchResults = ref([])
const isSearching = ref(false)

// 搜索处理函数
const handleSearch = async () => {
  if (!searchKeyword.value.trim()) {
    searchResults.value = []
    return
  }

  isSearching.value = true
  try {
    // 调用搜索API - 修改为正确的接口路径
    // const response = await fetch(`/api/search-pdf?keyword=${encodeURIComponent(searchKeyword.value)}`)
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

// 清除搜索
const handleSearchClear = () => {
  searchResults.value = []
}

// 提供给子组件使用
provide('searchResults', searchResults)
provide('isSearching', isSearching)
provide('handleSearch', handleSearch)

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

/* 为路由视图留出顶部空间 */
.router-view-container {
  height: calc(100vh - 60px);
  margin-top: 60px;
  overflow: auto;
}
</style>