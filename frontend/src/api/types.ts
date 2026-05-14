// ============================================================
// API 响应类型定义 — 用于消除 any 滥用
// ============================================================

import type { Stock, Fund, FundNav, FundHolding, StockDaily, MarketIndex } from '@/types'

/** 分页响应 */
export interface PageResponse<T> {
  records: T[]
  total: number
  page: number
  size: number
}

/** 股票列表项（表格展示用） */
export interface StockRecord {
  stockCode: string
  stockName: string
  market?: string
  industry?: string
  price?: number
  changePct?: number
  change?: number
  volume?: number
  highPrice?: number
  lowPrice?: number
  pe?: number
}

/** 股票详情响应（含最新行情） */
export interface StockDetailResponse {
  id: number
  stockCode: string
  stockName: string
  market?: string
  industry?: string
  listingDate?: string
  totalShares?: number
  circulatedShares?: number
  pe?: number
  pb?: number
  totalMarketCap?: number
  floatMarketCap?: number
  price?: number
  changePercent?: number
  open?: number
  high?: number
  low?: number
  preClose?: number
  volume?: number
  amount?: number
  turnoverRate?: number
}

/** 指数列表项 */
export interface IndexRecord {
  indexCode: string
  indexName: string
  market?: string
  category?: string
  closePoint?: number
  changePercent?: number
  tradeDate?: string
}

/** 登录响应 */
export interface LoginResponse {
  token: string
  user: {
    id: number
    username: string
    email: string
    avatar: string
    role: number
  }
}

/** 行业排行项（板块云图用） */
export interface SectorRankRecord {
  industry: string
  stockCount: number
  avgChangePct: number
  upCount: number
  upRatio: number
}

/** 年收益率项 */
export interface YearlyReturnRecord {
  year: number
  yearlyReturn: number
  startPrice: number
  endPrice: number
}

/** 趋势分析响应 */
export interface TrendResponse {
  stockCode: string
  trend: string
  ma5: number
  ma10: number
  ma20: number
  dataCount: number
}

/** 相关性响应 */
export interface CorrelationResponse {
  codeA: string
  codeB: string
  correlation: number
}

/** 自选项 */
export interface WatchlistRecord {
  id: number
  userId: number
  assetType: number
  assetCode: string
  remark?: string
  sortOrder: number
}

/** API 端点返回类型映射 */
export interface ApiEndpoints {
  '/stock/list': PageResponse<StockRecord>
  '/stock/{code}': StockDetailResponse
  '/stock/kline/{code}': StockDaily[]
  '/stock/search': Stock[]
  '/stock/industries': string[]
  '/fund/list': PageResponse<Fund>
  '/fund/{code}': Fund
  '/fund/{code}/nav': FundNav[]
  '/fund/{code}/holdings': FundHolding[]
  '/index/list': IndexRecord[]
  '/index/{code}': MarketIndex
  '/index/{code}/kline': StockDaily[]
  '/analysis/{assetCode}': import('@/types').AnalysisResult[]
  '/analysis/{stockCode}/yearly-return': YearlyReturnRecord[]
  '/analysis/{stockCode}/trend': TrendResponse
  '/analysis/sector-ranking': SectorRankRecord[]
  '/analysis/correlation': CorrelationResponse
  '/user/login': LoginResponse
  '/user/info': import('@/types').UserInfo
  '/watchlist/{userId}': WatchlistRecord[]
  '/ai/status': import('@/types').AIStatus
}

/** 通用 Map 响应类型（后端部分端点返回 Map） */
export type MapResponse = Record<string, unknown>
