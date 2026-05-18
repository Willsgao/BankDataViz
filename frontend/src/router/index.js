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
    path: '/',
    redirect: '/rag-chat'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 添加路由守卫进行权限控制
router.beforeEach((to, from, next) => {
  // 从localStorage获取用户信息和token
  const userRole = localStorage.getItem('user_role') || 'guest'
  const token = localStorage.getItem('token')
  const permissions = JSON.parse(localStorage.getItem('permissions') || '[]')

  // 不需要登录的页面（公开页面）
  const publicPages = ['/login']
  const authRequired = !publicPages.includes(to.path)

  // 如果需要登录但未登录，重定向到登录页
  if (authRequired && !token) {
    next('/login')
    return
  }

  // 超级管理员可以访问所有页面
  if (userRole === 'super_admin') {
    next()
    return
  }

  // 检查页面所需的权限
  if (to.meta && to.meta.requiredPermission) {
    const requiredPermission = to.meta.requiredPermission

    // 管理员拥有所有权限（除了 super_admin 专属页面）
    if (userRole === 'admin') {
      // 检查具体权限
      if (requiredPermission === 'parse' && !permissions.includes('parse')) {
        next('/bank-data')
        return
      }
      if (requiredPermission === 'review' && !permissions.includes('review')) {
        next('/bank-data')
        return
      }
      if (requiredPermission === 'data' && !permissions.includes('data')) {
        next('/login')
        return
      }
      next()
      return
    }

    // 普通用户只能访问 data 权限的页面
    if (userRole === 'user') {
      if (requiredPermission === 'data') {
        next()
        return
      }
      // 尝试访问其他页面时重定向到数据看板
      next('/bank-data')
      return
    }

    // 其他情况重定向到登录页
    next('/login')
    return
  }

  // 没有特定权限要求的页面，根据角色默认跳转
  if (userRole === 'user') {
    // 普通用户只能看到数据看板
    if (to.path === '/two-column' || to.path === '/three-column') {
      next('/bank-data')
      return
    }
  }

  // 直接放行
  next()
})

export default router