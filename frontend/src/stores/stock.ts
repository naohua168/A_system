import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Stock, StockDaily } from '@/types'

export const useStockStore = defineStore('stock', () => {
  const currentStock = ref<Stock | null>(null)
  const klineData = ref<StockDaily[]>([])
  const watchlist = ref<Stock[]>([])
  const loading = ref(false)

  function setCurrentStock(stock: Stock) {
    currentStock.value = stock
  }

  function setKlineData(data: StockDaily[]) {
    klineData.value = data
  }

  function toggleStockInWatchlist(stock: Stock) {
    const idx = watchlist.value.findIndex(s => s.stockCode === stock.stockCode)
    if (idx >= 0) {
      watchlist.value.splice(idx, 1)
    } else {
      watchlist.value.push(stock)
    }
  }

  function isInWatchlist(code: string) {
    return watchlist.value.some(s => s.stockCode === code)
  }

  return {
    currentStock, klineData, watchlist, loading,
    setCurrentStock, setKlineData, toggleStockInWatchlist, isInWatchlist,
  }
})
