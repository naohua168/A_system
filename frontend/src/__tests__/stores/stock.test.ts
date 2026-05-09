import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useStockStore } from '@/stores/stock'
import type { Stock } from '@/types'

describe('useStockStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  const mockStock1: Stock = { stockCode: '000001', stockName: '平安银行', industry: '金融', market: 'SZ' } as Stock
  const mockStock2: Stock = { stockCode: '600519', stockName: '贵州茅台', industry: '白酒', market: 'SH' } as Stock

  it('初始状态', () => {
    const store = useStockStore()
    expect(store.currentStock).toBeNull()
    expect(store.klineData).toEqual([])
    expect(store.watchlist).toEqual([])
    expect(store.loading).toBe(false)
  })

  it('setCurrentStock - 设置当前股票', () => {
    const store = useStockStore()
    store.setCurrentStock(mockStock1)
    expect(store.currentStock).toEqual(mockStock1)
  })

  it('setKlineData - 设置K线数据', () => {
    const store = useStockStore()
    const kline = [{ stockCode: '000001', tradeDate: '2025-01-01', closePrice: 10.0 }]
    store.setKlineData(kline as any)
    expect(store.klineData).toEqual(kline)
  })

  it('toggleStockInWatchlist - 添加到自选', () => {
    const store = useStockStore()
    store.toggleStockInWatchlist(mockStock1)
    expect(store.watchlist).toHaveLength(1)
    expect(store.watchlist[0].stockCode).toBe('000001')
  })

  it('toggleStockInWatchlist - 从自选移除', () => {
    const store = useStockStore()
    store.toggleStockInWatchlist(mockStock1)
    expect(store.watchlist).toHaveLength(1)
    store.toggleStockInWatchlist(mockStock1)
    expect(store.watchlist).toHaveLength(0)
  })

  it('toggleStockInWatchlist - 添加多只互不影响的股票', () => {
    const store = useStockStore()
    store.toggleStockInWatchlist(mockStock1)
    store.toggleStockInWatchlist(mockStock2)
    expect(store.watchlist).toHaveLength(2)
    // 移除第一只，仅剩第二只
    store.toggleStockInWatchlist(mockStock1)
    expect(store.watchlist).toHaveLength(1)
    expect(store.watchlist[0].stockCode).toBe('600519')
  })

  it('isInWatchlist - 检查是否在自选', () => {
    const store = useStockStore()
    expect(store.isInWatchlist('000001')).toBe(false)
    store.toggleStockInWatchlist(mockStock1)
    expect(store.isInWatchlist('000001')).toBe(true)
    expect(store.isInWatchlist('600519')).toBe(false)
  })
})
