/**
 * useSearch Composable 测试
 * 验证搜索 composable 正确代理 search store
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSearch } from '@/composables/useSearch'
import { useSearchStore } from '@/stores/search'

describe('useSearch', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // ===== PDF 搜索 =====
  it('pdfKeyword 应双向绑定 store', () => {
    const search = useSearch()

    search.pdfKeyword.value = '测试关键词'
    expect(search.pdfKeyword.value).toBe('测试关键词')

    // 验证 store 也已更新
    const store = useSearchStore()
    expect(store.pdfSearch.keyword).toBe('测试关键词')
  })

  it('pdfResults 应反映 store 中的结果', () => {
    const search = useSearch()
    const store = useSearchStore()

    store.setPdfResults([{ id: 1 }, { id: 2 }])
    expect(search.pdfResults.value).toEqual([{ id: 1 }, { id: 2 }])
  })

  it('setPdfSearching 应更新搜索状态', () => {
    const search = useSearch()

    search.setPdfSearching(true)
    expect(search.pdfIsSearching.value).toBe(true)

    search.setPdfSearching(false)
    expect(search.pdfIsSearching.value).toBe(false)
  })

  // ===== Excel 搜索 =====
  it('excelKeyword 应双向绑定 store', () => {
    const search = useSearch()

    search.excelKeyword.value = '净利润'
    expect(search.excelKeyword.value).toBe('净利润')

    const store = useSearchStore()
    expect(store.excelSearch.keyword).toBe('净利润')
  })

  it('excelMatchCount 应反映匹配计数', () => {
    const search = useSearch()
    const store = useSearchStore()

    store.setExcelMatchCount(15)
    expect(search.excelMatchCount.value).toBe(15)
  })

  it('setExcelMatchedSheets 应更新匹配列表', () => {
    const search = useSearch()
    const matches = [
      { excel_file: 'a.xlsx', sheet_name: 'Sheet1' },
      { excel_file: 'b.xlsx', sheet_name: 'Sheet2' }
    ]

    search.setExcelMatchedSheets(matches)
    expect(search.excelMatchedSheetsList.value).toEqual(matches)
    expect(search.excelMatchCount.value).toBe(2)
  })

  it('goToNextMatch 和 goToPrevMatch 应正确导航', () => {
    const search = useSearch()
    const store = useSearchStore()

    store.setExcelMatchedSheets([
      { excel_file: 'a.xlsx', sheet_name: 'A' },
      { excel_file: 'b.xlsx', sheet_name: 'B' },
      { excel_file: 'c.xlsx', sheet_name: 'C' }
    ])

    expect(search.goToNextMatch()).toEqual({ excel_file: 'b.xlsx', sheet_name: 'B' })
    expect(search.goToPrevMatch()).toEqual({ excel_file: 'a.xlsx', sheet_name: 'A' })
  })

  it('excelActive 应反映搜索激活状态', () => {
    const search = useSearch()
    const store = useSearchStore()

    store.setExcelActive(true)
    store.setExcelKeyword('test_')
    // 有关键词且 active=true 时 isExcelSearchActive 才为 true
    expect(search.isExcelSearchActive.value).toBe(true)
  })

  // ===== 清除操作 =====
  it('clearPdfSearch 应清除 PDF 搜索', () => {
    const search = useSearch()
    search.setPdfKeyword('pdf')
    search.setPdfSearching(true)

    search.clearPdfSearch()
    expect(search.pdfKeyword.value).toBe('')
    expect(search.pdfIsSearching.value).toBe(false)
  })

  it('clearExcelSearch 应清除 Excel 搜索', () => {
    const search = useSearch()
    search.excelKeyword.value = 'excel'
    search.setExcelActive(true)

    search.clearExcelSearch()
    expect(search.excelKeyword.value).toBe('')
    expect(search.excelActive.value).toBe(false)
  })

  it('clearAll 应清除所有搜索', () => {
    const search = useSearch()
    search.pdfKeyword.value = 'pdf'
    search.excelKeyword.value = 'excel'

    search.clearAll()
    expect(search.pdfKeyword.value).toBe('')
    expect(search.excelKeyword.value).toBe('')
  })

  // ===== computed 属性响应式 =====
  it('computed 属性应跟随 store 变化', () => {
    const search = useSearch()
    const store = useSearchStore()

    store.setPdfKeyword('updated_pdf')
    expect(search.pdfKeyword.value).toBe('updated_pdf')

    store.setExcelMatchCount(42)
    expect(search.excelMatchCount.value).toBe(42)
  })
})
