/**
 * useAuth Composable 测试
 * 验证认证 composable 正确代理 auth store
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuth } from '@/composables/useAuth'
import { useAuthStore } from '@/stores/auth'

describe('useAuth', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('应返回 store 中的所有 computed 属性', () => {
    const auth = useAuth()

    // 初始值
    expect(auth.username.value).toBe('')
    expect(auth.userRole.value).toBe('')
    expect(auth.isLoggedIn.value).toBe(false)
    expect(auth.userInitial.value).toBe('U')
    expect(auth.isSuperAdmin.value).toBe(false)
    expect(auth.hasAdminPermission.value).toBe(false)
    expect(auth.userRoleName.value).toBe('普通用户')
    expect(auth.isInitialized.value).toBe(false)
  })

  it('hasPermission 应调用 store 的 hasPermission', () => {
    const auth = useAuth()
    const store = useAuthStore()

    store.userRole = 'admin'
    store.permissions = ['data']

    expect(auth.hasPermission('data')).toBe(true)
    expect(auth.hasPermission('admin_only')).toBe(false)
  })

  it('loadUserInfo 应从 localStorage 加载', () => {
    localStorage.setItem('username', 'test')
    localStorage.setItem('user_role', 'admin')
    localStorage.setItem('permissions', JSON.stringify(['parse']))

    const auth = useAuth()
    auth.loadUserInfo()

    expect(auth.username.value).toBe('test')
    expect(auth.isLoggedIn.value).toBe(false) // 需要 token
  })

  it('logout 应触发 store 的 logout', () => {
    localStorage.setItem('token', 'abc')
    localStorage.setItem('username', 'test')

    const auth = useAuth()
    auth.loadUserInfo()

    expect(auth.username.value).toBe('test')

    auth.logout()

    expect(auth.username.value).toBe('')
    expect(auth.isLoggedIn.value).toBe(false)
  })

  it('saveUserInfo 应保存到 store', () => {
    const auth = useAuth()
    auth.saveUserInfo({
      username: 'saved_user',
      userRole: 'super_admin',
      permissions: ['all'],
      token: 'saved_token'
    })

    expect(auth.username.value).toBe('saved_user')
    expect(auth.userRole.value).toBe('super_admin')
    expect(auth.isSuperAdmin.value).toBe(true)
  })

  it('computed 属性应跟随 store 变化自动更新', () => {
    const auth = useAuth()
    const store = useAuthStore()

    store.username = 'dynamic'
    expect(auth.username.value).toBe('dynamic')
    expect(auth.userInitial.value).toBe('D')

    store.userRole = 'super_admin'
    expect(auth.userRoleName.value).toBe('超级管理员')
    expect(auth.isSuperAdmin.value).toBe(true)
    expect(auth.hasAdminPermission.value).toBe(true)
  })
})
