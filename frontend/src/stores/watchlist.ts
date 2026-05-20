import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getWatchlist as apiGetWatchlist, addWatchlist as apiAdd, removeWatchlist as apiRemove } from '@/api/watchlist'
import type { WatchlistItem } from '@/types'

export const useWatchlistStore = defineStore('watchlist', () => {
  const items = ref<WatchlistItem[]>([])
  const loading = ref(false)

  const stockCodes = computed(() =>
    items.value.filter((i) => i.assetType === 0).map((i) => i.assetCode)
  )

  function isInWatchlist(assetCode: string): boolean {
    return stockCodes.value.includes(assetCode)
  }

  async function fetchWatchlist(userId: number) {
    loading.value = true
    try {
      items.value = await apiGetWatchlist(userId)
    } catch {
      items.value = []
    } finally {
      loading.value = false
    }
  }

  async function add(userId: number, assetCode: string, assetType: number) {
    await apiAdd(userId, assetCode, assetType)
    await fetchWatchlist(userId)
  }

  async function remove(userId: number, assetCode: string, assetType: number) {
    await apiRemove(userId, assetCode, assetType)
    items.value = items.value.filter(
      (i) => !(i.assetCode === assetCode && i.assetType === assetType)
    )
  }

  function toggleInWatchlist(userId: number, assetCode: string, assetType: number) {
    if (isInWatchlist(assetCode)) {
      return remove(userId, assetCode, assetType)
    }
    return add(userId, assetCode, assetType)
  }

  /** 本地状态快速切换（不等待后端确认） */
  function optimisticToggle(stockCode: string, stockName?: string) {
    const exists = items.value.find((i) => i.assetCode === stockCode && i.assetType === 0)
    if (exists) {
      items.value = items.value.filter(
        (i) => !(i.assetCode === stockCode && i.assetType === 0)
      )
    } else {
      items.value.push({
        id: -Date.now(),
        userId: 0,
        assetCode: stockCode,
        assetType: 0,
        remark: stockName || '',
        sortOrder: items.value.length,
      })
    }
  }

  return {
    items,
    loading,
    stockCodes,
    isInWatchlist,
    fetchWatchlist,
    add,
    remove,
    toggleInWatchlist,
    optimisticToggle,
  }
})
