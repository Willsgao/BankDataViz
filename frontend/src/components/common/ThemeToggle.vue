<template>
  <el-dropdown 
    trigger="click" 
    placement="bottom-start"
    @command="handleThemeChange"
    class="theme-toggle-dropdown"
  >
    <div class="theme-toggle-button">
      <el-icon v-if="currentTheme === 'light'" :size="18"><Sunny /></el-icon>
      <el-icon v-else-if="currentTheme === 'dark'" :size="18"><Moon /></el-icon>
      <el-icon v-else :size="18"><Sunrise /></el-icon>
      <span class="theme-label">{{ themeLabel }}</span>
      <el-icon class="arrow"><ArrowDown /></el-icon>
    </div>
    
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="light" :class="{ active: currentTheme === 'light' }">
          <div class="theme-option">
            <el-icon><Sunny /></el-icon>
            <span>亮色主题</span>
            <el-icon v-if="currentTheme === 'light'" class="checkmark"><CircleCheck /></el-icon>
          </div>
        </el-dropdown-item>
        
        <el-dropdown-item command="dark" :class="{ active: currentTheme === 'dark' }">
          <div class="theme-option">
            <el-icon><Moon /></el-icon>
            <span>暗色主题</span>
            <el-icon v-if="currentTheme === 'dark'" class="checkmark"><CircleCheck /></el-icon>
          </div>
        </el-dropdown-item>
        
        <el-dropdown-item command="system" :class="{ active: currentTheme === 'system' }">
          <div class="theme-option">
            <el-icon><Sunrise /></el-icon>
            <span>跟随系统</span>
            <el-icon v-if="currentTheme === 'system'" class="checkmark"><CircleCheck /></el-icon>
          </div>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { Sunny, Moon, Sunrise, ArrowDown, CircleCheck } from '@element-plus/icons-vue'

// 主题状态
const currentTheme = ref('system')
const themeLabel = computed(() => {
  switch (currentTheme.value) {
    case 'light': return '亮色'
    case 'dark': return '暗色'
    case 'system': return '系统'
    default: return '系统'
  }
})

// 检查系统主题偏好
const checkSystemTheme = () => {
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

// 应用主题
const applyTheme = (theme) => {
  // 移除所有主题类
  document.documentElement.classList.remove('light-theme', 'dark-theme')
  
  let actualTheme = theme
  if (theme === 'system') {
    actualTheme = checkSystemTheme()
  }
  
  // 应用主题类
  document.documentElement.classList.add(`${actualTheme}-theme`)
  
  // 存储到localStorage
  localStorage.setItem('preferred-theme', theme)
  
  // 应用Element Plus主题
  if (actualTheme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark')
  } else {
    document.documentElement.removeAttribute('data-theme')
  }
}

// 处理主题切换
const handleThemeChange = (theme) => {
  currentTheme.value = theme
  applyTheme(theme)
}

// 初始化主题
const initTheme = () => {
  const savedTheme = localStorage.getItem('preferred-theme') || 'system'
  currentTheme.value = savedTheme
  applyTheme(savedTheme)
}

// 监听系统主题变化
const watchSystemTheme = () => {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  const handleChange = (e) => {
    if (currentTheme.value === 'system') {
      applyTheme('system')
    }
  }
  mediaQuery.addEventListener('change', handleChange)
  
  return () => mediaQuery.removeEventListener('change', handleChange)
}

onMounted(() => {
  initTheme()
  watchSystemTheme()
})

// 暴露方法给其他组件
defineExpose({
  currentTheme,
  applyTheme
})
</script>

<style scoped>
.theme-toggle-dropdown {
  margin-right: 12px;
}

.theme-toggle-button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-light);
  color: var(--el-text-color-regular);
}

.theme-toggle-button:hover {
  background: var(--el-fill-color-lighter);
  border-color: var(--el-border-color);
}

.theme-label {
  font-size: 14px;
  font-weight: 500;
}

.arrow {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.theme-option {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 120px;
  padding: 2px 0;
}

.theme-option .el-icon {
  color: var(--el-text-color-secondary);
}

.active .theme-option .el-icon:not(.checkmark) {
  color: var(--el-color-primary);
}

.checkmark {
  margin-left: auto;
  color: var(--el-color-primary) !important;
}
</style>

<style>
/* 全局主题样式 */
.light-theme {
  --docuvista-bg: #f8fafc;
  --docuvista-card-bg: #ffffff;
  --docuvista-border: #e2e8f0;
  --docuvista-text-primary: #1e293b;
  --docuvista-text-secondary: #64748b;
  --docuvista-accent: #3b82f6;
  --docuvista-accent-light: #dbeafe;
  --docuvista-success: #10b981;
  --docuvista-warning: #f59e0b;
  --docuvista-danger: #ef4444;
  --docuvista-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  --docuvista-shadow-lg: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.dark-theme {
  --docuvista-bg: #0f172a;
  --docuvista-card-bg: #1e293b;
  --docuvista-border: #334155;
  --docuvista-text-primary: #f1f5f9;
  --docuvista-text-secondary: #94a3b8;
  --docuvista-accent: #60a5fa;
  --docuvista-accent-light: #1e3a8a;
  --docuvista-success: #34d399;
  --docuvista-warning: #fbbf24;
  --docuvista-danger: #f87171;
  --docuvista-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  --docuvista-shadow-lg: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
}

/* 应用到App组件 */
.light-theme #app {
  background: var(--docuvista-bg);
}

.dark-theme #app {
  background: var(--docuvista-bg);
}

/* 应用到导航栏 */
.light-theme .top-nav {
  background: var(--docuvista-card-bg);
  box-shadow: var(--docuvista-shadow);
  border-bottom: 1px solid var(--docuvista-border);
}

.dark-theme .top-nav {
  background: var(--docuvista-card-bg);
  box-shadow: var(--docuvista-shadow);
  border-bottom: 1px solid var(--docuvista-border);
}

/* 应用到两栏布局 */
.light-theme .two-column-layout {
  background: var(--docuvista-bg);
}

.dark-theme .two-column-layout {
  background: var(--docuvista-bg);
}

.light-theme .left-panel,
.light-theme .right-panel {
  background: var(--docuvista-card-bg);
  box-shadow: var(--docuvista-shadow);
  border: 1px solid var(--docuvista-border);
}

.dark-theme .left-panel,
.dark-theme .right-panel {
  background: var(--docuvista-card-bg);
  box-shadow: var(--docuvista-shadow);
  border: 1px solid var(--docuvista-border);
}

/* 应用到PDF文件项 */
.light-theme .current-pdf-item {
  background: var(--docuvista-accent-light);
  border-color: var(--docuvista-accent);
}

.dark-theme .current-pdf-item {
  background: var(--docuvista-accent-light);
  border-color: var(--docuvista-accent);
}

/* 平滑主题切换 */
* {
  transition: background-color 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
}
</style>