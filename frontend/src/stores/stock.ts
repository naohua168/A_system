import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as marketApi from '@/api/market'
import type { StockListItem, StockDetail, StockDaily } from '@/types'
import type { MarketListParams } from '@/types'

/**
 * 行情层状态管理 — 对应后端 MarketController
 */
export const useStockStore = defineStore('stock', () => {
  // ── 状态 ──
  const records = ref<StockListItem[]>([])
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(20)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const keyword = ref('')
  const selectedIndustry = ref('')
  const selectedMarket = ref('')
  const isEtfMode = computed(() => selectedMarket.value === 'etf')

  const stockDetail = ref<StockDetail | null>(null)
  const klineData = ref<StockDaily[]>([])
  const klineLoading = ref(false)
  const klineError = ref<string | null>(null)

  // 用于竞态控制的 AbortController
  let listController: AbortController | null = null
  let detailController: AbortController | null = null
  let klineController: AbortController | null = null

  // ── 计算属性 ──
  const totalPages = computed(() => Math.ceil(total.value / pageSize.value))
  const hasMore = computed(() => currentPage.value < totalPages.value)

  // ── 列表操作 ──
  async function fetchList(params?: MarketListParams) {
    listController?.abort()
    listController = new AbortController()

    loading.value = true
    error.value = null
    try {
      const mkt = params?.market ?? selectedMarket.value
      if (mkt === 'etf') {
        // ETF 模式：调用独立 ETF API
        const res = await marketApi.getEtfList({
          page: params?.page ?? currentPage.value,
          size: params?.size ?? pageSize.value,
          keyword: params?.keyword ?? keyword.value,
        })
        // 将 ETF 数据映射为统一的 StockListItem 格式
        records.value = (res.records || []).map((r: any) => ({
          stockCode: r.fund_code || '',
          stockName: r.fund_name || '',
          price: r.price,
          changePct: r.change_pct,
          change: r.change_amount,
          volume: r.volume,
          amount: r.amount,
          open: r.open_price,
          high: r.high_price,
          low: r.low_price,
          preClose: r.pre_close,
        }))
        total.value = res.total
        currentPage.value = res.page
        pageSize.value = res.size
      } else {
        // 市场过滤（后端不支持，前端本地按 stockCode 前缀过滤）
        if (mkt && mkt !== '') {
          // 读取全量股票列表
          const allRes = await marketApi.getStockList({
            page: 1, size: 5000,
            keyword: params?.keyword ?? keyword.value,
            industry: params?.industry ?? selectedIndustry.value,
          }, listController.signal)
          const allStocks = allRes.records || []
          const prefixMap: Record<string, string[]> = {
            'sh': ['6','9'], 'sz': ['0','2','3'],
            'sh-kcb': ['688','689'], 'sz-cyb': ['300','301'],
            'bj': ['4','8'],
            'hs': ['6','0','3','688','689','300','301','9'],
          }
          const prefixes = prefixMap[mkt] || []
          const filtered = allStocks.filter((s: any) =>
            prefixes.some(p => (s.stockCode || '').startsWith(p))
          )
          // 搜索过滤
          const kw = ((params?.keyword ?? keyword.value) || '').toLowerCase()
          const searchFiltered = kw ? filtered.filter((s: any) =>
            (s.stockName || '').toLowerCase().includes(kw) ||
            (s.stockCode || '').toLowerCase().includes(kw)
          ) : filtered
          // 本地分页
          const page = params?.page ?? currentPage.value
          const size = params?.size ?? pageSize.value
          const from = (page - 1) * size
          records.value = searchFiltered.slice(from, from + size)
          total.value = searchFiltered.length
          currentPage.value = page
          pageSize.value = size
        } else {
          const res = await marketApi.getStockList({
            page: params?.page ?? currentPage.value,
            size: params?.size ?? pageSize.value,
            keyword: params?.keyword ?? keyword.value,
            industry: params?.industry ?? selectedIndustry.value,
            market: mkt,
            sortField: params?.sortField,
            sortOrder: params?.sortOrder,
          }, listController.signal)
          records.value = res.records
          total.value = res.total
          currentPage.value = res.page
          pageSize.value = res.size
        }
      }
    } catch (e: unknown) {
      const canceled = e instanceof Error && (e.name === 'CanceledError' || (e as any)?.code === 'ERR_CANCELED')
      if (canceled) return
      console.error('获取股票列表失败:', e)
      error.value = '获取股票列表失败'
      records.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  function setKeyword(kw: string) {
    keyword.value = kw
    fetchList({ page: 1 })
  }

  function setIndustry(ind: string) {
    selectedIndustry.value = ind
    fetchList({ page: 1 })
  }

  function setMarket(mkt: string) {
    selectedMarket.value = mkt
    fetchList({ page: 1 })
  }

  function setPage(page: number) {
    fetchList({ page })
  }

  // ── 详情操作 ──
  async function fetchDetail(code: string) {
    detailController?.abort()
    detailController = new AbortController()

    loading.value = true
    error.value = null
    try {
      stockDetail.value = await marketApi.getStockByCode(code, detailController.signal)
    } catch (e: unknown) {
      const canceled = e instanceof Error && (e.name === 'CanceledError' || (e as any)?.code === 'ERR_CANCELED')
      if (canceled) return
      console.error('获取股票详情失败:', e)
      error.value = '获取股票详情失败'
      stockDetail.value = null
    } finally {
      loading.value = false
    }
  }

  async function fetchKline(code: string, days = 60) {
    klineController?.abort()
    klineController = new AbortController()

    klineLoading.value = true
    klineError.value = null
    try {
      klineData.value = await marketApi.getKlineData(code, days, klineController.signal)
    } catch (e: unknown) {
      const canceled = e instanceof Error && (e.name === 'CanceledError' || (e as any)?.code === 'ERR_CANCELED')
      if (canceled) return
      console.error('获取K线数据失败:', e)
      klineError.value = '获取K线数据失败'
      klineData.value = []
    } finally {
      klineLoading.value = false
    }
  }

  // ── 重置 ──
  function reset() {
    records.value = []
    total.value = 0
    currentPage.value = 1
    keyword.value = ''
    selectedIndustry.value = ''
    selectedMarket.value = ''
    stockDetail.value = null
    klineData.value = []
    error.value = null
    klineError.value = null
  }

  return {
    records, total, currentPage, pageSize, loading, error,
    keyword, selectedIndustry, selectedMarket,
    stockDetail, klineData, klineLoading, klineError,
    totalPages, hasMore,
    fetchList, setKeyword, setIndustry, setMarket, setPage,
    fetchDetail, fetchKline, reset,
  }
})
