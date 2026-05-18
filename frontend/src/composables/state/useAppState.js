import { computed } from 'vue'
import { useAppStore } from '@/stores/app'

export function useAppState() {
  const appStore = useAppStore()

  return {
    // 状态
    currentView: computed(() => appStore.currentView),
    isLoading: computed(() => appStore.isLoading),
    activePdfFile: computed(() => appStore.activePdfFile),
    activeTable: computed(() => appStore.activeTable),

    // 操作
    setCurrentView: (view) => appStore.setCurrentView(view),
    setLoading: (loading) => appStore.setLoading(loading),
    setActivePdfFile: (file) => appStore.setActivePdfFile(file),
    setActiveTable: (table) => appStore.setActiveTable(table)
  }
}