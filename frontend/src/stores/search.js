import { defineStore } from 'pinia'

/**
 * 搜索状态管理 Store
 * 统一管理 PDF 文件名搜索和 Excel 内容搜索，替代 window.dispatchEvent 通信模式
 */
export const useSearchStore = defineStore('search', {
  state: () => ({
    // PDF 文件搜索
    pdfSearch: {
      keyword: '',
      results: [],
      isSearching: false
    },

    // Excel 内容搜索
    excelSearch: {
      keyword: '',
      isSearching: false,
      lastSearchTime: 0,
      matchCount: 0,
      active: false,
      matchIndex: 0,
      matchedSheetsList: []
    },

    // Sheet 名称高亮
    sheetHighlight: {
      keyword: '',
      matchedSheets: [],
      isHighlighting: false
    }
  }),

  getters: {
    /** PDF 搜索结果数量 */
    pdfResultCount: (state) => state.pdfSearch.results.length,

    /** Excel 搜索是否激活 */
    isExcelSearchActive: (state) => state.excelSearch.active && state.excelSearch.keyword.trim().length > 0,

    /** 当前是否正在搜索 */
    isAnySearching: (state) => state.pdfSearch.isSearching || state.excelSearch.isSearching
  },

  actions: {
    // ===== PDF 搜索 =====

    /** 设置 PDF 搜索关键词 */
    setPdfKeyword(keyword) {
      this.pdfSearch.keyword = keyword
    },

    /** 设置 PDF 搜索结果 */
    setPdfResults(results) {
      this.pdfSearch.results = results
    },

    /** 设置 PDF 搜索中状态 */
    setPdfSearching(searching) {
      this.pdfSearch.isSearching = searching
    },

    /** 清除 PDF 搜索 */
    clearPdfSearch() {
      this.pdfSearch.keyword = ''
      this.pdfSearch.results = []
      this.pdfSearch.isSearching = false
    },

    // ===== Excel 内容搜索 =====

    /** 设置 Excel 搜索关键词 */
    setExcelKeyword(keyword) {
      this.excelSearch.keyword = keyword
    },

    /** 设置 Excel 搜索匹配计数 */
    setExcelMatchCount(count) {
      this.excelSearch.matchCount = count
    },

    /** 设置 Excel 搜索匹配列表 */
    setExcelMatchedSheets(list) {
      this.excelSearch.matchedSheetsList = list
      this.excelSearch.matchCount = list ? list.length : 0
      this.excelSearch.matchIndex = 0
    },

    /** 设置 Excel 搜索激活状态 */
    setExcelActive(active) {
      this.excelSearch.active = active
    },

    /** 跳转到指定索引的匹配项 */
    goToMatchByIndex(index) {
      const { matchedSheetsList } = this.excelSearch
      if (!matchedSheetsList || matchedSheetsList.length === 0) return

      this.excelSearch.matchIndex = index
      return matchedSheetsList[index]
    },

    /** 跳转到下一个匹配 Sheet */
    goToNextMatch() {
      const { matchIndex, matchedSheetsList } = this.excelSearch
      if (!matchedSheetsList || matchedSheetsList.length === 0) return null
      const nextIndex = (matchIndex + 1) % matchedSheetsList.length
      return this.goToMatchByIndex(nextIndex)
    },

    /** 跳转到上一个匹配 Sheet */
    goToPrevMatch() {
      const { matchIndex, matchedSheetsList } = this.excelSearch
      if (!matchedSheetsList || matchedSheetsList.length === 0) return null
      const prevIndex = (matchIndex - 1 + matchedSheetsList.length) % matchedSheetsList.length
      return this.goToMatchByIndex(prevIndex)
    },

    /** 清除 Excel 搜索 */
    clearExcelSearch() {
      this.excelSearch.keyword = ''
      this.excelSearch.isSearching = false
      this.excelSearch.matchCount = 0
      this.excelSearch.active = false
      this.excelSearch.lastSearchTime = Date.now()
      this.excelSearch.matchIndex = 0
      this.excelSearch.matchedSheetsList = []
    },

    /** 清除所有搜索状态 */
    clearAll() {
      this.clearPdfSearch()
      this.clearExcelSearch()
      this.sheetHighlight.keyword = ''
      this.sheetHighlight.matchedSheets = []
      this.sheetHighlight.isHighlighting = false
    }
  }
})
