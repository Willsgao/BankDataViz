/**
 * 认证 Store 单元测试
 * 验证用户认证状态管理的所有功能
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

describe('AuthStore', () => {
  beforeEach(() => {
    // 每个测试前创建新的 Pinia 实例
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('初始状态应为未登录', () => {
    const auth = useAuthStore()
    expect(auth.username).toBe('')
    expect(auth.userRole).toBe('')
    expect(auth.permissions).toEqual([])
    expect(auth.isLoggedIn).toBe(false)
    expect(auth.isSuperAdmin).toBe(false)
    expect(auth.hasAdminPermission).toBe(false)
  })

  it('loadUserInfo 应从 localStorage 加载用户信息', () => {
    localStorage.setItem('username', 'testuser')
    localStorage.setItem('user_role', 'admin')
    localStorage.setItem('permissions', JSON.stringify(['parse', 'review']))
    localStorage.setItem('token', 'abc123')

    const auth = useAuthStore()
    auth.loadUserInfo()

    expect(auth.username).toBe('testuser')
    expect(auth.userRole).toBe('admin')
    expect(auth.permissions).toEqual(['parse', 'review'])
    expect(auth.isLoggedIn).toBe(true)
    expect(auth.isInitialized).toBe(true)
  })

  it('isSuperAdmin 应正确判断超级管理员', () => {
    const auth = useAuthStore()
    auth.userRole = 'super_admin'
    expect(auth.isSuperAdmin).toBe(true)
    expect(auth.hasAdminPermission).toBe(true)
  })

  it('hasPermission 应在超级管理员时返回 true', () => {
    const auth = useAuthStore()
    auth.userRole = 'super_admin'
    expect(auth.hasPermission('any_permission')).toBe(true)
  })

  it('hasPermission 应正确检查普通用户权限', () => {
    const auth = useAuthStore()
    auth.userRole = 'admin'
    auth.permissions = ['parse']

    expect(auth.hasPermission('parse')).toBe(true)
    expect(auth.hasPermission('review')).toBe(false)
    expect(auth.hasPermission('data')).toBe(false)
  })

  it('userRoleName 应返回正确中文角色名', () => {
    const auth = useAuthStore()

    auth.userRole = 'super_admin'
    expect(auth.userRoleName).toBe('超级管理员')

    auth.userRole = 'admin'
    expect(auth.userRoleName).toBe('管理员')

    auth.userRole = 'user'
    expect(auth.userRoleName).toBe('普通用户')
  })

  it('userInitial 应返回用户名首字母大写', () => {
    const auth = useAuthStore()
    auth.username = 'zhangsan'
    expect(auth.userInitial).toBe('Z')

    auth.username = ''
    expect(auth.userInitial).toBe('U')
  })

  it('logout 应清除所有认证信息', () => {
    localStorage.setItem('token', 'abc123')
    localStorage.setItem('username', 'test')
    localStorage.setItem('user_role', 'admin')
    localStorage.setItem('permissions', JSON.stringify(['parse']))

    const auth = useAuthStore()
    auth.loadUserInfo()

    expect(auth.username).toBe('test')
    expect(auth.isLoggedIn).toBe(true)

    auth.logout()

    expect(auth.username).toBe('')
    expect(auth.userRole).toBe('')
    expect(auth.permissions).toEqual([])
    expect(localStorage.getItem('token')).toBeNull()
    expect(auth.isLoggedIn).toBe(false)
  })

  it('saveUserInfo 应保存到 localStorage 和 state', () => {
    const auth = useAuthStore()

    auth.saveUserInfo({
      username: 'newuser',
      userRole: 'user',
      permissions: ['data'],
      token: 'newtoken'
    })

    expect(auth.username).toBe('newuser')
    expect(auth.userRole).toBe('user')
    expect(auth.permissions).toEqual(['data'])
    expect(localStorage.getItem('token')).toBe('newtoken')
    expect(localStorage.getItem('username')).toBe('newuser')
  })

  it('hasAdminPermission 应正确处理 admin 角色', () => {
    const auth = useAuthStore()
    auth.userRole = 'admin'
    expect(auth.hasAdminPermission).toBe(true)

    auth.userRole = 'user'
    expect(auth.hasAdminPermission).toBe(false)
  })
})
