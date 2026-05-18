import { computed } from 'vue'
import { useBankDataStore } from '@/stores/bankData'

/**
 * 银行数据 Composable
 * 共享银行数据状态
 */
export function useBankData() {
  const store = useBankDataStore()

  return {
    // 状态
    stats: computed(() => store.stats),
    banks: computed(() => store.banks),
    selectedBank: computed(() => store.selectedBank),
    filterType: computed({
      get: () => store.filterType,
      set: (val) => store.setFilterType(val)
    }),
    searchKeyword: computed({
      get: () => store.searchKeyword,
      set: (val) => { store.searchKeyword = val }
    }),
    currentPage: computed({
      get: () => store.currentPage,
      set: (val) => { store.currentPage = val }
    }),
    loading: computed(() => store.loading),
    seeding: computed(() => store.seeding),
    displayBanks: computed(() => store.displayBanks),
    filteredTotal: computed(() => store.filteredTotal),

    // 操作
    loadStats: () => store.loadStats(),
    loadBanks: () => store.loadBanks(),
    searchBanks: (keyword) => store.searchBanks(keyword),
    selectBank: (bank) => store.selectBank(bank),
    clearSelection: () => store.clearSelection(),
    setFilterType: (type) => store.setFilterType(type),
    reset: () => store.reset()
  }
}
