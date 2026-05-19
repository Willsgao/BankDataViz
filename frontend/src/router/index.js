// router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import TwoColumnPage from '@/views/TwoColumnPage.vue'
import ThreeColumnPage from '@/views/ThreeColumnPage.vue'
import LoginPage from '@/views/LoginPage.vue'
import BankDashboardPage from '@/views/BankDashboardPage.vue'
import BankDataPage from '@/views/BankDataPage.vue'
import AdminManagement from '@/views/AdminManagement.vue'
import AuditPage from '@/views/AuditPage.vue'
import SmartRecognizePage from '@/views/SmartRecognizePage.vue'
import RagChatPage from '@/views/RagChatPage.vue'
import PromptShowcasePage from '@/views/PromptShowcasePage.vue'
import AgentWorkflowPage from '@/views/AgentWorkflowPage.vue'

const routes = [
  {
    path: '/two-column',
    name: 'TwoColumn',
    component: TwoColumnPage,
    meta: { requiredPermission: 'parse', title: '数据解析' }
  },
  {
    path: '/three-column',
    name: 'ThreeColumn',
    component: ThreeColumnPage,
    meta: { requiredPermission: 'review', title: '数据审核' }
  },
  {
    path: '/bank-dashboard',
    name: 'BankDashboard',
    component: BankDashboardPage,
    meta: { requiredPermission: 'data', title: '数据看板-图表' }
  },
  {
    path: '/bank-data',
    name: 'BankData',
    component: BankDataPage,
    meta: { requiredPermission: 'data', title: '数据看板-文档' }
  },
  {
    path: '/bank-warehouse',
    redirect: '/bank-data'
  },
  {
    path: '/audit',
    name: 'Audit',
    component: AuditPage,
    meta: { title: '会计勾稽' }
  },
  {
    path: '/smart-recognize',
    name: 'SmartRecognize',
    component: SmartRecognizePage,
    meta: { title: '智能识别' }
  },
  {
    path: '/login',
    name: 'Login',
    component: LoginPage
  },
  {
    path: '/admin-management',
    name: 'AdminManagement',
    component: AdminManagement,
    meta: { requiredPermission: 'super_admin', title: '子管理员管理' }
  },
  {
    path: '/rag-chat',
    name: 'RagChat',
    component: RagChatPage,
    meta: { title: '智能问答' }
  },
  {
    path: '/prompt-engineering',
    name: 'PromptShowcase',
    component: PromptShowcasePage,
    meta: { title: 'Prompt 工程' }
  },
  {
    path: '/agent-workflow',
    name: 'AgentWorkflow',
    component: AgentWorkflowPage,
    meta: { title: 'Agent 工作流' }
  },
  {
    path: '/',
    redirect: '/rag-chat'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 添加路由守卫进行权限控制
// 注意：此处直接读取 localStorage 而非使用 useAuthStore()，原因是：
// router.beforeEach 在 Pinia 初始化之前注册，此时 useAuthStore() 不可用
router.beforeEach((to, from, next) => {
  // 演示模式：无需登录，自动注入超级管理员会话
  const token = localStorage.getItem('token')
  if (!token) {
    localStorage.setItem('token', 'demo-token-' + Date.now())
    localStorage.setItem('user_role', 'super_admin')
    localStorage.setItem('username', 'demo')
    localStorage.setItem('permissions', JSON.stringify(['parse', 'review', 'data']))
  }

  // 重新读取（演示模式注入后 userRole 可能已更新）
  const effectiveRole = localStorage.getItem('user_role') || 'guest'
  const permissions = JSON.parse(localStorage.getItem('permissions') || '[]')

  // 超级管理员可以访问所有页面
  if (effectiveRole === 'super_admin') {
    next()
    return
  }

  // 检查页面所需的权限
  if (to.meta && to.meta.requiredPermission) {
    const requiredPermission = to.meta.requiredPermission

    // 管理员拥有所有权限（除了 super_admin 专属页面）
    if (effectiveRole === 'admin') {
      if (requiredPermission === 'parse' && !permissions.includes('parse')) {
        next('/bank-data')
        return
      }
      if (requiredPermission === 'review' && !permissions.includes('review')) {
        next('/bank-data')
        return
      }
      if (requiredPermission === 'data' && !permissions.includes('data')) {
        next('/rag-chat')
        return
      }
      next()
      return
    }

    // 普通用户只能访问 data 权限的页面
    if (effectiveRole === 'user') {
      if (requiredPermission === 'data') {
        next()
        return
      }
      next('/bank-data')
      return
    }

    next('/rag-chat')
    return
  }

  // 没有特定权限要求的页面，根据角色限制
  if (effectiveRole === 'user') {
    if (to.path === '/two-column' || to.path === '/three-column') {
      next('/bank-data')
      return
    }
  }

  next()
})

export default router