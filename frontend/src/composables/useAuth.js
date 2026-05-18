import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

/**
 * 认证 Composable
 * 提供用户认证、权限检查的统一接口
 */
export function useAuth() {
  const authStore = useAuthStore()

  return {
    // 状态（只读）
    username: computed(() => authStore.username),
    userRole: computed(() => authStore.userRole),
    permissions: computed(() => authStore.permissions),
    isLoggedIn: computed(() => authStore.isLoggedIn),
    userInitial: computed(() => authStore.userInitial),
    isSuperAdmin: computed(() => authStore.isSuperAdmin),
    hasAdminPermission: computed(() => authStore.hasAdminPermission),
    userRoleName: computed(() => authStore.userRoleName),
    isInitialized: computed(() => authStore.isInitialized),

    // 操作
    hasPermission: (perm) => authStore.hasPermission(perm),
    loadUserInfo: () => authStore.loadUserInfo(),
    logout: () => authStore.logout(),
    saveUserInfo: (info) => authStore.saveUserInfo(info)
  }
}
