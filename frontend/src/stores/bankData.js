import { defineStore } from 'pinia'
import { getBankStatistics, getBankList, searchBanks } from '@/api/bank'

/**
 * 银行数据 Store
 * 管理银行列表、统计信息等跨页面共享状态
 */
export const useBankDataStore = defineStore('bankData', {
  state: () => ({
    // 统计数据
    stats: {
      total_banks: 0,
      total_reports: 0,
      total_table_data: 0
    },

    // 银行列表
    banks: [],
    selectedBank: null,

    // 分页与筛选
    filterType: '',
    searchKeyword: '',
    currentPage: 1,
    pageSize: 20,

    // 加载状态
    loading: false,
    seeding: false
  }),

  getters: {
    /** 分页后的银行列表 */
    displayBanks: (state) => {
      let filtered = state.banks
      if (state.searchKeyword.trim()) {
        const kw = state.searchKeyword.toLowerCase()
        filtered = state.banks.filter(bank =>
          bank.bank_name?.toLowerCase().includes(kw) ||
          bank.bank_code?.toLowerCase().includes(kw) ||
          bank.bank_type?.toLowerCase().includes(kw)
        )
      }
      if (state.filterType) {
        filtered = filtered.filter(bank => bank.bank_type === state.filterType)
      }
      const start = (state.currentPage - 1) * state.pageSize
      return filtered.slice(start, start + state.pageSize)
    },

    /** 筛选后的总数 */
    filteredTotal: (state) => {
      let filtered = state.banks
      if (state.searchKeyword.trim()) {
        const kw = state.searchKeyword.toLowerCase()
        filtered = state.banks.filter(bank =>
          bank.bank_name?.toLowerCase().includes(kw) ||
          bank.bank_code?.toLowerCase().includes(kw) ||
          bank.bank_type?.toLowerCase().includes(kw)
        )
      }
      if (state.filterType) {
        filtered = filtered.filter(bank => bank.bank_type === state.filterType)
      }
      return filtered.length
    }
  },

  actions: {
    /** 加载银行统计信息 */
    async loadStats() {
      try {
        const res = await getBankStatistics()
        if (res) {
          this.stats = { ...this.stats, ...res }
        }
      } catch (e) {
        console.error('加载银行统计失败:', e)
      }
    },

    /** 加载银行列表 */
    async loadBanks() {
      this.loading = true
      try {
        const params = { page: this.currentPage, per_page: 9999 }
        if (this.filterType) params.bank_type = this.filterType
        const res = await getBankList(params)
        this.banks = res?.banks || res || []
      } catch (e) {
        console.error('加载银行列表失败:', e)
        this.banks = []
      } finally {
        this.loading = false
      }
    },

    /** 搜索银行（全量后端搜索） */
    async searchBanks(keyword) {
      if (!keyword || !keyword.trim()) {
        await this.loadBanks()
        return
      }
      this.searchKeyword = keyword
      this.loading = true
      try {
        const res = await searchBanks(keyword, 200)
        this.banks = res?.banks || res || []
        this.currentPage = 1
      } catch (e) {
        console.error('搜索银行失败:', e)
      } finally {
        this.loading = false
      }
    },

    /** 选中银行 */
    selectBank(bank) {
      this.selectedBank = bank
    },

    /** 清除选中 */
    clearSelection() {
      this.selectedBank = null
    },

    /** 设置筛选类型 */
    setFilterType(type) {
      this.filterType = type || ''
      this.currentPage = 1
    },

    /** 重置所有状态 */
    reset() {
      this.banks = []
      this.selectedBank = null
      this.filterType = ''
      this.searchKeyword = ''
      this.currentPage = 1
      this.loading = false
      this.seeding = false
    }
  }
})
