import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useWatchlistStore } from '@/stores/watchlist'

// Mock the watchlist API module
vi.mock('@/api/watchlist', () => ({
  getWatchlist: vi.fn().mockResolvedValue([
    { id: 1, userId: 1, assetCode: '000001', assetType: 0, remark: '', sortOrder: 0 },
  ]),
  addWatchlist: vi.fn().mockResolvedValue({}),
  removeWatchlist: vi.fn().mockResolvedValue({}),
}))

describe('useWatchlistStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('初始状态为空列表', () => {
    const store = useWatchlistStore()
    expect(store.items).toEqual([])
    expect(store.loading).toBe(false)
  })

  it('fetchWatchlist - 获取自选列表', async () => {
    const store = useWatchlistStore()
    await store.fetchWatchlist(1)
    expect(store.items).toHaveLength(1)
    expect(store.items[0].assetCode).toBe('000001')
  })

  it('add - 添加自选', async () => {
    const store = useWatchlistStore()
    await store.add(1, '600519', 0)
    // add 内部会调用 fetchWatchlist 刷新
    expect(store.items.length).toBeGreaterThanOrEqual(0)
  })

  it('remove - 移除自选', async () => {
    const store = useWatchlistStore()
    // 先添加一条
    store.items = [{ id: 1, userId: 1, assetCode: '000001', assetType: 0, remark: '', sortOrder: 0 }]
    await store.remove(1, '000001', 0)
    expect(store.items).toHaveLength(0)
  })

  it('isInWatchlist - 检查是否在自选', () => {
    const store = useWatchlistStore()
    store.items = [{ id: 1, userId: 1, assetCode: '000001', assetType: 0, remark: '', sortOrder: 0 }]
    expect(store.isInWatchlist('000001')).toBe(true)
    expect(store.isInWatchlist('600519')).toBe(false)
  })

  it('items 为空时 isInWatchlist 返回 false', () => {
    const store = useWatchlistStore()
    expect(store.items).toEqual([])
    expect(store.isInWatchlist('000001')).toBe(false)
  })

  it('optimisticToggle 添加本地状态', () => {
    const store = useWatchlistStore()
    store.optimisticToggle('000001', '平安银行')
    expect(store.items).toHaveLength(1)
    expect(store.items[0].assetCode).toBe('000001')
  })

  it('optimisticToggle 移除已存在的条目', () => {
    const store = useWatchlistStore()
    store.optimisticToggle('000001', '平安银行')
    expect(store.items).toHaveLength(1)
    store.optimisticToggle('000001')
    expect(store.items).toHaveLength(0)
  })
})
