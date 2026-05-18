/**
 * useBankData Composable 测试
 * 验证银行数据 composable 正确代理 bankData store
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock API
vi.mock('@/api/bank', () => ({
  getBankStatistics: vi.fn(),
  getBankList: vi.fn(),
  searchBanks: vi.fn()
}))

import { useBankData } from '@/composables/useBankData'
import { useBankDataStore } from '@/stores/bankData'
import * as bankApi from '@/api/bank'

const mockBanks = [
  { bank_name: '工商银行', bank_code: 'ICBC', bank_type: '国有银行' },
  { bank_name: '招商银行', bank_code: 'CMB', bank_type: '股份制银行' }
]

describe('useBankData', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('应返回 store 中的只读状态', () => {
    const bank = useBankData()

    expect(bank.banks.value).toEqual([])
    expect(bank.selectedBank.value).toBeNull()
    expect(bank.stats.value.total_banks).toBe(0)
    expect(bank.loading.value).toBe(false)
    expect(bank.seeding.value).toBe(false)
  })

  it('filterType 应双向绑定', () => {
    const bank = useBankData()

    bank.filterType.value = '国有银行'
    expect(bank.filterType.value).toBe('国有银行')

    // 验证 store 也已更新
    const store = useBankDataStore()
    expect(store.filterType).toBe('国有银行')
  })

  it('searchKeyword 应双向绑定', () => {
    const bank = useBankData()

    bank.searchKeyword.value = '招商'
    expect(bank.searchKeyword.value).toBe('招商')

    const store = useBankDataStore()
    expect(store.searchKeyword).toBe('招商')
  })

  it('currentPage 应双向绑定', () => {
    const bank = useBankData()

    bank.currentPage.value = 3
    expect(bank.currentPage.value).toBe(3)

    const store = useBankDataStore()
    expect(store.currentPage).toBe(3)
  })

  it('selectBank 和 clearSelection 应正确操作', () => {
    const bank = useBankData()

    bank.selectBank(mockBanks[0])
    expect(bank.selectedBank.value).toEqual(mockBanks[0])

    bank.clearSelection()
    expect(bank.selectedBank.value).toBeNull()
  })

  it('displayBanks 应反映分页结果', () => {
    const bank = useBankData()
    const store = useBankDataStore()

    store.banks = mockBanks
    expect(bank.displayBanks.value).toHaveLength(2)
    expect(bank.displayBanks.value[0].bank_name).toBe('工商银行')
  })

  it('filteredTotal 应返回筛选总数', () => {
    const bank = useBankData()
    const store = useBankDataStore()

    store.banks = mockBanks
    expect(bank.filteredTotal.value).toBe(2)
  })

  it('loadBanks 应调用 store 的 loadBanks', async () => {
    bankApi.getBankList.mockResolvedValue({ banks: mockBanks })
    const bank = useBankData()

    await bank.loadBanks()
    expect(bank.banks.value).toEqual(mockBanks)
  })

  it('searchBanks 应调用 store 的搜索', async () => {
    bankApi.searchBanks.mockResolvedValue({ banks: [mockBanks[1]] })
    const bank = useBankData()

    await bank.searchBanks('招商')
    expect(bank.banks.value).toEqual([mockBanks[1]])
  })

  it('reset 应重置 store', () => {
    const bank = useBankData()
    const store = useBankDataStore()

    store.banks = mockBanks
    store.selectedBank = mockBanks[0]
    store.filterType = '国有银行'

    bank.reset()

    expect(bank.banks.value).toEqual([])
    expect(bank.selectedBank.value).toBeNull()
    expect(bank.filterType.value).toBe('')
  })

  it('computed 属性应跟随 store 更新', () => {
    const bank = useBankData()
    const store = useBankDataStore()

    store.banks = mockBanks
    expect(bank.banks.value).toEqual(mockBanks)

    store.selectedBank = mockBanks[0]
    expect(bank.selectedBank.value).toEqual(mockBanks[0])
  })
})
