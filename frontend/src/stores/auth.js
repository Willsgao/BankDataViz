import { defineStore } from 'pinia'

/**
 * 认证状态管理 Store
 * 管理用户登录状态、角色、权限，支持 localStorage 持久化和跨标签页同步
 */
export const useAuthStore = defineStore('auth', {
  state: () => ({
    username: '',
    userRole: '',
    permissions: [],
    isInitialized: false
  }),

  getters: {
    /** 是否已登录 */
    isLoggedIn: (state) => {
      return !!state.username && !!localStorage.getItem('token')
    },

    /** 用户首字母（用于头像） */
    userInitial: (state) => {
      return state.username ? state.username.charAt(0).toUpperCase() : 'U'
    },

    /** 是否超级管理员 */
    isSuperAdmin: (state) => state.userRole === 'super_admin',

    /** 是否拥有管理员权限（admin 或 super_admin） */
    hasAdminPermission: (state) => {
      return state.userRole === 'admin' || state.userRole === 'super_admin'
    },

    /** 角色中文名 */
    userRoleName: (state) => {
      if (state.userRole === 'super_admin') return '超级管理员'
      if (state.userRole === 'admin') return '管理员'
      return '普通用户'
    }
  },

  actions: {
    /** 检查是否拥有特定权限 */
    hasPermission(perm) {
      if (this.isSuperAdmin) return true
      return this.permissions.includes(perm)
    },

    /** 从 localStorage 加载用户信息 */
    loadUserInfo() {
      this.username = localStorage.getItem('username') || ''
      this.userRole = localStorage.getItem('user_role') || ''
      const perms = localStorage.getItem('permissions')
      this.permissions = perms ? JSON.parse(perms) : []
      this.isInitialized = true
    },

    /** 退出登录 */
    logout() {
      localStorage.removeItem('token')
      localStorage.removeItem('user_role')
      localStorage.removeItem('username')
      localStorage.removeItem('permissions')
      this.username = ''
      this.userRole = ''
      this.permissions = []
    },

    /** 保存用户信息到 localStorage 和 state */
    saveUserInfo({ username, userRole, permissions, token }) {
      if (token !== undefined) localStorage.setItem('token', token)
      if (username !== undefined) localStorage.setItem('username', username)
      if (userRole !== undefined) localStorage.setItem('user_role', userRole)
      if (permissions !== undefined) localStorage.setItem('permissions', JSON.stringify(permissions))
      this.loadUserInfo()
    }
  }
})
