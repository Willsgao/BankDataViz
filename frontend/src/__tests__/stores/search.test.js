/**
 * 搜索 Store 单元测试
 * 验证 PDF 搜索、Excel 搜索和 Sheet 高亮状态管理
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSearchStore } from '@/stores/search'

describe('SearchStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // ===== PDF 搜索测试 =====
  it('初始 PDF 搜索状态应为空', () => {
    const store = useSearchStore()
    expect(store.pdfSearch.keyword).toBe('')
    expect(store.pdfSearch.results).toEqual([])
    expect(store.pdfSearch.isSearching).toBe(false)
    expect(store.pdfResultCount).toBe(0)
  })

  it('setPdfKeyword 应设置搜索关键词', () => {
    const store = useSearchStore()
    store.setPdfKeyword('招商银行')
    expect(store.pdfSearch.keyword).toBe('招商银行')
  })

  it('setPdfResults 应设置搜索结果', () => {
    const store = useSearchStore()
    const results = [{ id: 1, name: 'test.pdf' }, { id: 2, name: 'test2.pdf' }]
    store.setPdfResults(results)
    expect(store.pdfSearch.results).toEqual(results)
    expect(store.pdfResultCount).toBe(2)
  })

  it('clearPdfSearch 应重置 PDF 搜索状态', () => {
    const store = useSearchStore()
    store.setPdfKeyword('test')
    store.setPdfResults([{ id: 1 }])
    store.setPdfSearching(true)

    store.clearPdfSearch()

    expect(store.pdfSearch.keyword).toBe('')
    expect(store.pdfSearch.results).toEqual([])
    expect(store.pdfSearch.isSearching).toBe(false)
  })

  // ===== Excel 搜索测试 =====
  it('初始 Excel 搜索状态应为空', () => {
    const store = useSearchStore()
    expect(store.excelSearch.keyword).toBe('')
    expect(store.excelSearch.matchCount).toBe(0)
    expect(store.excelSearch.active).toBe(false)
    expect(store.isExcelSearchActive).toBe(false)
  })

  it('setExcelKeyword 应设置关键词', () => {
    const store = useSearchStore()
    store.setExcelKeyword('总资产')
    expect(store.excelSearch.keyword).toBe('总资产')
  })

  it('setExcelMatchedSheets 应更新匹配列表和计数', () => {
    const store = useSearchStore()
    const matches = [
      { excel_file: 'a.xlsx', sheet_name: 'Sheet1' },
      { excel_file: 'b.xlsx', sheet_name: 'Sheet2' }
    ]
    store.setExcelMatchedSheets(matches)

    expect(store.excelSearch.matchedSheetsList).toEqual(matches)
    expect(store.excelSearch.matchCount).toBe(2)
    expect(store.excelSearch.matchIndex).toBe(0)
  })

  it('goToNextMatch 应循环翻页', () => {
    const store = useSearchStore()
    store.setExcelMatchedSheets([
      { excel_file: 'a.xlsx', sheet_name: 'A' },
      { excel_file: 'b.xlsx', sheet_name: 'B' },
      { excel_file: 'c.xlsx', sheet_name: 'C' }
    ])

    expect(store.goToNextMatch()).toEqual({ excel_file: 'b.xlsx', sheet_name: 'B' })
    expect(store.excelSearch.matchIndex).toBe(1)

    expect(store.goToNextMatch()).toEqual({ excel_file: 'c.xlsx', sheet_name: 'C' })
    expect(store.excelSearch.matchIndex).toBe(2)

    // 应循环回第一项
    expect(store.goToNextMatch()).toEqual({ excel_file: 'a.xlsx', sheet_name: 'A' })
    expect(store.excelSearch.matchIndex).toBe(0)
  })

  it('goToPrevMatch 应反向翻页', () => {
    const store = useSearchStore()
    store.setExcelMatchedSheets([
      { excel_file: 'a.xlsx', sheet_name: 'A' },
      { excel_file: 'b.xlsx', sheet_name: 'B' },
      { excel_file: 'c.xlsx', sheet_name: 'C' }
    ])

    // matchIndex 初始为 0，prev 应到最后一页
    expect(store.goToPrevMatch()).toEqual({ excel_file: 'c.xlsx', sheet_name: 'C' })
    expect(store.excelSearch.matchIndex).toBe(2)

    expect(store.goToPrevMatch()).toEqual({ excel_file: 'b.xlsx', sheet_name: 'B' })
    expect(store.excelSearch.matchIndex).toBe(1)
  })

  it('空匹配列表时翻页应返回 null', () => {
    const store = useSearchStore()
    expect(store.goToNextMatch()).toBeNull()
    expect(store.goToPrevMatch()).toBeNull()
  })

  it('clearExcelSearch 应重置所有 Excel 搜索状态', () => {
    const store = useSearchStore()
    store.setExcelKeyword('test')
    store.setExcelMatchedSheets([{ excel_file: 'a.xlsx', sheet_name: 'A' }])
    store.setExcelActive(true)

    store.clearExcelSearch()

    expect(store.excelSearch.keyword).toBe('')
    expect(store.excelSearch.matchCount).toBe(0)
    expect(store.excelSearch.active).toBe(false)
    expect(store.excelSearch.matchedSheetsList).toEqual([])
  })

  it('clearAll 应清除所有搜索状态', () => {
    const store = useSearchStore()
    store.setPdfKeyword('pdf_search')
    store.setExcelKeyword('excel_search')
    store.sheetHighlight.keyword = 'highlight'

    store.clearAll()

    expect(store.pdfSearch.keyword).toBe('')
    expect(store.excelSearch.keyword).toBe('')
    expect(store.sheetHighlight.keyword).toBe('')
  })

  it('isAnySearching 应正确判断搜索中状态', () => {
    const store = useSearchStore()
    expect(store.isAnySearching).toBe(false)

    store.setPdfSearching(true)
    expect(store.isAnySearching).toBe(true)
  })
})
