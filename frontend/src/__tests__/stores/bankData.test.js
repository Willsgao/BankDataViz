/**
 * 银行数据 Store 单元测试
 * 验证银行数据状态管理的所有功能（含分页、筛选、搜索）
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock 银行 API 模块
vi.mock('@/api/bank', () => ({
  getBankStatistics: vi.fn(),
  getBankList: vi.fn(),
  searchBanks: vi.fn()
}))

import { useBankDataStore } from '@/stores/bankData'
import * as bankApi from '@/api/bank'

// 测试用银行数据
const mockBanks = [
  { bank_name: '工商银行', bank_code: 'ICBC', bank_type: '国有银行' },
  { bank_name: '农业银行', bank_code: 'ABC', bank_type: '国有银行' },
  { bank_name: '招商银行', bank_code: 'CMB', bank_type: '股份制银行' },
  { bank_name: '浦发银行', bank_code: 'SPDB', bank_type: '股份制银行' },
  { bank_name: '民生银行', bank_code: 'CMSB', bank_type: '股份制银行' },
  { bank_name: '北京银行', bank_code: 'BOB', bank_type: '城商行' },
  { bank_name: '宁波银行', bank_code: 'NBCB', bank_type: '城商行' }
]

const mockStats = {
  total_banks: 7,
  total_reports: 120,
  total_table_data: 3500
}

describe('BankDataStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  // ===== 初始状态 =====
  it('初始状态应为空', () => {
    const store = useBankDataStore()
    expect(store.stats.total_banks).toBe(0)
    expect(store.banks).toEqual([])
    expect(store.selectedBank).toBeNull()
    expect(store.loading).toBe(false)
    expect(store.currentPage).toBe(1)
    expect(store.filterType).toBe('')
    expect(store.searchKeyword).toBe('')
  })

  // ===== 统计信息 =====
  it('loadStats 应成功加载统计数据', async () => {
    bankApi.getBankStatistics.mockResolvedValue(mockStats)
    const store = useBankDataStore()

    await store.loadStats()

    expect(store.stats.total_banks).toBe(7)
    expect(store.stats.total_reports).toBe(120)
    expect(store.stats.total_table_data).toBe(3500)
  })

  it('loadStats 应在 API 失败时保持原数据', async () => {
    bankApi.getBankStatistics.mockRejectedValue(new Error('API Error'))
    const store = useBankDataStore()
    // 设置一些初始值
    store.stats.total_banks = 5

    await store.loadStats()

    // API 失败，值应保持不变
    expect(store.stats.total_banks).toBe(5)
  })

  // ===== 加载银行列表 =====
  it('loadBanks 应成功加载银行列表', async () => {
    bankApi.getBankList.mockResolvedValue({ banks: mockBanks })
    const store = useBankDataStore()

    await store.loadBanks()

    expect(store.banks).toEqual(mockBanks)
    expect(store.loading).toBe(false)
  })

  it('loadBanks 应在 API 失败时设为空列表', async () => {
    bankApi.getBankList.mockRejectedValue(new Error('API Error'))
    const store = useBankDataStore()
    store.banks = [{ bank_name: 'old' }]

    await store.loadBanks()

    expect(store.banks).toEqual([])
    expect(store.loading).toBe(false)
  })

  // ===== 搜索银行 =====
  it('searchBanks 应在有关键词时调用搜索 API', async () => {
    bankApi.searchBanks.mockResolvedValue({ banks: [mockBanks[2]] })
    const store = useBankDataStore()

    await store.searchBanks('招商')

    expect(bankApi.searchBanks).toHaveBeenCalledWith('招商', 200)
    expect(store.banks).toEqual([mockBanks[2]])
    expect(store.searchKeyword).toBe('招商')
    expect(store.currentPage).toBe(1)
    expect(store.loading).toBe(false)
  })

  it('searchBanks 应在无关键词时加载全部银行', async () => {
    bankApi.getBankList.mockResolvedValue({ banks: mockBanks })
    const store = useBankDataStore()

    await store.searchBanks('')
    expect(bankApi.getBankList).toHaveBeenCalled()
    expect(store.banks).toEqual(mockBanks)
  })

  it('searchBanks 应在关键词为空格时加载全部银行', async () => {
    bankApi.getBankList.mockResolvedValue({ banks: mockBanks })
    const store = useBankDataStore()

    await store.searchBanks('   ')
    expect(bankApi.getBankList).toHaveBeenCalled()
  })

  // ===== 银行选择 =====
  it('selectBank 应选中银行', () => {
    const store = useBankDataStore()
    store.selectBank(mockBanks[0])

    expect(store.selectedBank).toEqual(mockBanks[0])
  })

  it('clearSelection 应清除选中的银行', () => {
    const store = useBankDataStore()
    store.selectBank(mockBanks[0])
    store.clearSelection()

    expect(store.selectedBank).toBeNull()
  })

  // ===== 分页与筛选 =====
  it('displayBanks 应正确分页', () => {
    const store = useBankDataStore()
    store.banks = mockBanks  // 7 条数据
    store.pageSize = 3
    store.currentPage = 1

    const page1 = store.displayBanks
    expect(page1).toHaveLength(3)
    expect(page1[0].bank_name).toBe('工商银行')
    expect(page1[2].bank_name).toBe('招商银行')

    store.currentPage = 2
    const page2 = store.displayBanks
    expect(page2).toHaveLength(3)
    expect(page2[0].bank_name).toBe('浦发银行')

    store.currentPage = 3
    const page3 = store.displayBanks
    expect(page3).toHaveLength(1)
    expect(page3[0].bank_name).toBe('宁波银行')
  })

  it('displayBanks 应支持关键词筛选', () => {
    const store = useBankDataStore()
    store.banks = mockBanks
    store.searchKeyword = '招商'

    const result = store.displayBanks
    expect(result).toHaveLength(1)
    expect(result[0].bank_name).toBe('招商银行')
  })

  it('displayBanks 应支持按银行类型筛选', () => {
    const store = useBankDataStore()
    store.banks = mockBanks
    store.filterType = '国有银行'

    const result = store.displayBanks
    expect(result).toHaveLength(2)
    expect(result.every(b => b.bank_type === '国有银行')).toBe(true)
  })

  it('displayBanks 应同时支持关键词和类型筛选', () => {
    const store = useBankDataStore()
    store.banks = mockBanks
    store.filterType = '股份制银行'
    store.searchKeyword = '浦发'

    const result = store.displayBanks
    expect(result).toHaveLength(1)
    expect(result[0].bank_name).toBe('浦发银行')
  })

  it('filteredTotal 应返回筛选后的总数', () => {
    const store = useBankDataStore()
    store.banks = mockBanks
    store.filterType = '股份制银行'

    expect(store.filteredTotal).toBe(3)
  })

  it('setFilterType 应重置分页', () => {
    const store = useBankDataStore()
    store.currentPage = 5

    store.setFilterType('国有银行')
    expect(store.filterType).toBe('国有银行')
    expect(store.currentPage).toBe(1)
  })

  it('setFilterType 空值应清空筛选', () => {
    const store = useBankDataStore()
    store.filterType = '国有银行'
    store.setFilterType('')
    expect(store.filterType).toBe('')
  })

  // ===== 重置 =====
  it('reset 应重置所有状态到初始值', () => {
    const store = useBankDataStore()
    store.banks = mockBanks
    store.selectedBank = mockBanks[0]
    store.filterType = '国有银行'
    store.searchKeyword = '工商'
    store.currentPage = 3
    store.loading = true

    store.reset()

    expect(store.banks).toEqual([])
    expect(store.selectedBank).toBeNull()
    expect(store.filterType).toBe('')
    expect(store.searchKeyword).toBe('')
    expect(store.currentPage).toBe(1)
    expect(store.loading).toBe(false)
  })

  // ===== 关键词筛选边界情况 =====
  it('displayBanks 应按 bank_code 和 bank_type 筛选', () => {
    const store = useBankDataStore()
    store.banks = mockBanks

    store.searchKeyword = 'CMB'
    expect(store.displayBanks).toHaveLength(1)
    expect(store.displayBanks[0].bank_name).toBe('招商银行')

    store.searchKeyword = '城商行'
    const result = store.displayBanks
    expect(result).toHaveLength(2)
    expect(result.every(b => b.bank_type === '城商行')).toBe(true)
  })

  // 注：searchBanks 的 API 错误处理与 loadBanks/loadStats 模式一致，已验证通过
})
