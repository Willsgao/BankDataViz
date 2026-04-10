// router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import TwoColumnPage from '@/views/TwoColumnPage.vue'
import ThreeColumnPage from '@/views/ThreeColumnPage.vue'
import LoginPage from '@/views/LoginPage.vue'
import BankWarehousePage from '@/views/BankWarehousePage.vue'
import BankDashboardPage from '@/views/BankDashboardPage.vue'
import BankDataPage from '@/views/BankDataPage.vue'

const routes = [
  {
    path: '/two-column',
    name: 'TwoColumn',
    component: TwoColumnPage,
    meta: { requiredRole: 'admin', title: '管理后台' }
  },
  {
    path: '/three-column',
    name: 'ThreeColumn',
    component: ThreeColumnPage,
    meta: { requiredRole: 'user', title: '审核后台' }
  },
  {
    path: '/bank-dashboard',
    name: 'BankDashboard',
    component: BankDashboardPage,
    meta: { requiredRole: 'user', title: '数据看板-图表' }
  },
  {
    path: '/bank-data',
    name: 'BankData',
    component: BankDataPage,
    meta: { requiredRole: 'user', title: '数据看板-文档' }
  },
  {
    path: '/bank-warehouse',
    redirect: '/bank-data'
  },
  {
    path: '/login',
    name: 'Login',
    component: LoginPage
  },
  {
    path: '/',
    redirect: '/three-column'
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

  // 不需要登录的页面（公开页面）
  const publicPages = ['/login']
  const authRequired = !publicPages.includes(to.path)

  // 如果需要登录但未登录，重定向到登录页
  if (authRequired && !token) {
    next('/login')
    return
  }

  // 检查页面所需的权限
  if (to.meta && to.meta.requiredRole) {
    const requiredRole = to.meta.requiredRole

    // 管理员可以访问所有页面
    if (userRole === 'admin') {
      next()
    }
    // 普通用户只能访问user权限的页面
    else if (userRole === 'user' && requiredRole === 'user') {
      next()
    }
    // 权限不足的情况
    else {
      // 如果用户是普通用户但尝试访问管理员页面，重定向到审核后台
      if (userRole === 'user') {
        next('/three-column')
      }
      // 其他情况（guest或权限不匹配）重定向到登录页
      else {
        next('/login')
      }
    }
  } else {
    // 没有权限要求的页面，直接放行
    next()
  }
})

export default router