import { computed } from 'vue'
import { useSearchStore } from '@/stores/search'

/**
 * 搜索 Composable
 * 统一的搜索状态管理接口，替代原有的 window.dispatchEvent 通信模式
 */
export function useSearch() {
  const searchStore = useSearchStore()

  return {
    // PDF 搜索状态（只读计算属性）
    pdfKeyword: computed({
      get: () => searchStore.pdfSearch.keyword,
      set: (val) => { searchStore.setPdfKeyword(val) }
    }),
    pdfResults: computed(() => searchStore.pdfSearch.results),
    pdfIsSearching: computed(() => searchStore.pdfSearch.isSearching),

    // Excel 搜索状态（只读计算属性）
    excelKeyword: computed({
      get: () => searchStore.excelSearch.keyword,
      set: (val) => { searchStore.setExcelKeyword(val) }
    }),
    excelIsSearching: computed(() => searchStore.excelSearch.isSearching),
    excelMatchCount: computed(() => searchStore.excelSearch.matchCount),
    excelActive: computed(() => searchStore.excelSearch.active),
    excelMatchIndex: computed(() => searchStore.excelSearch.matchIndex),
    excelMatchedSheetsList: computed(() => searchStore.excelSearch.matchedSheetsList),
    isExcelSearchActive: computed(() => searchStore.isExcelSearchActive),

    // Sheet 高亮状态
    sheetHighlight: computed(() => searchStore.sheetHighlight),

    // 操作
    setPdfKeyword: (kw) => searchStore.setPdfKeyword(kw),
    setPdfResults: (results) => searchStore.setPdfResults(results),
    setPdfSearching: (s) => searchStore.setPdfSearching(s),
    clearPdfSearch: () => searchStore.clearPdfSearch(),

    setExcelKeyword: (kw) => searchStore.setExcelKeyword(kw),
    setExcelMatchCount: (count) => searchStore.setExcelMatchCount(count),
    setExcelMatchedSheets: (list) => searchStore.setExcelMatchedSheets(list),
    setExcelActive: (active) => searchStore.setExcelActive(active),
    goToNextMatch: () => searchStore.goToNextMatch(),
    goToPrevMatch: () => searchStore.goToPrevMatch(),
    clearExcelSearch: () => searchStore.clearExcelSearch(),
    clearAll: () => searchStore.clearAll(),

    // 查看器搜索（替代 window.performExcelSearch）
    registerViewerSearch: (fn, meta) => searchStore.registerViewerSearch(fn, meta),
    unregisterViewerSearch: (name) => searchStore.unregisterViewerSearch(name),
    performViewerSearch: (kw) => searchStore.performViewerSearch(kw)
  }
}
