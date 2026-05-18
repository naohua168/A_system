import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as marketApi from '@/api/market'
import * as signalApi from '@/api/signal'
import * as infoApi from '@/api/info'
import type { StockListItem, StockDetail, StockDaily } from '@/types'

/** 创建一个可中止的 fetch controller */
function createAbortController(): AbortController {
  return new AbortController()
}

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
  async function fetchList(params?: {
    page?: number
    size?: number
    keyword?: string
    industry?: string
    sortField?: string
    sortOrder?: 'asc' | 'desc'
  }) {
    // 取消上一次请求
    listController?.abort()
    listController = createAbortController()

    loading.value = true
    error.value = null
    try {
      const res = await marketApi.getStockList({
        page: params?.page ?? currentPage.value,
        size: params?.size ?? pageSize.value,
        keyword: params?.keyword ?? keyword.value,
        industry: params?.industry ?? selectedIndustry.value,
        sortField: params?.sortField,
        sortOrder: params?.sortOrder,
      })
      records.value = res.records
      total.value = res.total
      currentPage.value = res.page
      pageSize.value = res.size
    } catch (e: any) {
      if (e?.name === 'CanceledError' || e?.code === 'ERR_CANCELED') return // 主动取消忽略
      console.error('获取股票列表失败:', e)
      error.value = e?.message || '获取股票列表失败'
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

  function setPage(page: number) {
    fetchList({ page })
  }

  // ── 详情操作 ──
  async function fetchDetail(code: string) {
    detailController?.abort()
    detailController = createAbortController()

    loading.value = true
    error.value = null
    try {
      stockDetail.value = await marketApi.getStockByCode(code)
    } catch (e: any) {
      if (e?.name === 'CanceledError' || e?.code === 'ERR_CANCELED') return
      console.error('获取股票详情失败:', e)
      error.value = e?.message || '获取股票详情失败'
      stockDetail.value = null
    } finally {
      loading.value = false
    }
  }

  async function fetchKline(code: string, days = 60) {
    klineController?.abort()
    klineController = createAbortController()

    klineLoading.value = true
    klineError.value = null
    try {
      klineData.value = await marketApi.getKlineData(code, days)
    } catch (e: any) {
      if (e?.name === 'CanceledError' || e?.code === 'ERR_CANCELED') return
      console.error('获取K线数据失败:', e)
      klineError.value = e?.message || '获取K线数据失败'
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
    stockDetail.value = null
    klineData.value = []
    error.value = null
    klineError.value = null
  }

  return {
    records, total, currentPage, pageSize, loading, error,
    keyword, selectedIndustry,
    stockDetail, klineData, klineLoading, klineError,
    totalPages, hasMore,
    fetchList, setKeyword, setIndustry, setPage,
    fetchDetail, fetchKline, reset,
  }
})

// ── 信号层共享类型 ──
interface HotReason { name: string; count: number; stocks?: string[] }
interface NorthboundItem { date: string; netInflow: number; total: number }

/**
 * 信号层状态管理 — 对应 SignalDataController
 */
export const useSignalStore = defineStore('signal', () => {
  const hotReasons = ref<HotReason[]>([])
  const northboundData = ref<NorthboundItem[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchHotReason(date?: string) {
    loading.value = true
    error.value = null
    try {
      const res = await signalApi.getHotReason(date)
      hotReasons.value = res.records
    } catch (e: any) {
      error.value = e?.message || '获取题材归因失败'
      hotReasons.value = []
    } finally {
      loading.value = false
    }
  }

  async function fetchNorthbound(days = 30) {
    error.value = null
    try {
      northboundData.value = await signalApi.getNorthboundLatest(days)
    } catch (e: any) {
      error.value = e?.message || '获取北向资金数据失败'
      northboundData.value = []
    }
  }

  return { hotReasons, northboundData, loading, error, fetchHotReason, fetchNorthbound }
})

/**
 * 资讯层状态管理 — 对应 InfoController
 */
export const useInfoStore = defineStore('info', () => {
  const news = ref<any[]>([])
  const filings = ref<any[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchNews(code: string) {
    loading.value = true
    error.value = null
    try {
      const res = await infoApi.getStockNews(code)
      news.value = res.records
    } catch (e: any) {
      error.value = e?.message || '获取新闻失败'
      news.value = []
    } finally {
      loading.value = false
    }
  }

  async function fetchFilings(code: string) {
    error.value = null
    try {
      const res = await infoApi.getFilings(code)
      filings.value = res.records
    } catch (e: any) {
      error.value = e?.message || '获取公告失败'
      filings.value = []
    }
  }

  return { news, filings, loading, error, fetchNews, fetchFilings }
})
