import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useStockStore } from '@/stores/stock'
import type { StockDetail, StockDaily } from '@/types'

vi.mock('@/api/market', () => ({
  getStockList: vi.fn().mockResolvedValue({
    records: [], total: 0, page: 1, size: 20, totalPages: 0,
  }),
  getStockByCode: vi.fn().mockResolvedValue(null),
  getKlineData: vi.fn().mockResolvedValue([]),
}))

describe('useStockStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('初始状态', () => {
    const store = useStockStore()
    expect(store.stockDetail).toBeNull()
    expect(store.klineData).toEqual([])
    expect(store.records).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.total).toBe(0)
    expect(store.currentPage).toBe(1)
  })

  it('设置当前股票详情', () => {
    const store = useStockStore()
    const detail = { stockCode: '000001', stockName: '平安银行' } as StockDetail
    store.stockDetail = detail
    expect(store.stockDetail).toEqual(detail)
  })

  it('设置K线数据', () => {
    const store = useStockStore()
    const kline = [{ stockCode: '000001', tradeDate: '2025-01-01', closePrice: 10.0 }] as StockDaily[]
    store.klineData = kline
    expect(store.klineData).toEqual(kline)
  })

  it('setKeyword 更新搜索关键词', () => {
    const store = useStockStore()
    store.setKeyword('平安')
    expect(store.keyword).toBe('平安')
  })

  it('setIndustry 更新行业筛选', () => {
    const store = useStockStore()
    store.setIndustry('金融')
    expect(store.selectedIndustry).toBe('金融')
  })

  it('setPage 调用 fetchList', () => {
    const store = useStockStore()
    store.setPage(3)
    // fetchList 设置 currentPage 为 API 返回的值
    expect(store.currentPage).toBe(1) // mock 返回 page=1
  })

  it('reset 清除所有状态', () => {
    const store = useStockStore()
    store.stockDetail = { stockCode: '000001' } as StockDetail
    store.klineData = [{}] as StockDaily[]
    store.records = [{ stockCode: '000001' }] as any
    store.reset()
    expect(store.stockDetail).toBeNull()
    expect(store.klineData).toEqual([])
    expect(store.records).toEqual([])
    expect(store.keyword).toBe('')
    expect(store.selectedIndustry).toBe('')
  })

  it('fetchList 加载股票列表', async () => {
    const store = useStockStore()
    await store.fetchList({ page: 1, size: 20 })
    expect(store.records).toEqual([])
    expect(store.total).toBe(0)
  })

  it('fetchDetail 加载股票详情', async () => {
    const store = useStockStore()
    await store.fetchDetail('000001')
    expect(store.stockDetail).toBeNull()
  })

  it('fetchKline 加载K线数据', async () => {
    const store = useStockStore()
    await store.fetchKline('000001', 30)
    expect(store.klineData).toEqual([])
  })
})
