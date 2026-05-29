import request from './request'
import type { StockListItem, StockDetail, StockDaily, SectorRanking } from '@/types'
import type { MarketListParams, PageResult, StockFilterParams } from './types'

/**
 * 行情层 API — 对应后端 MarketController (/api/market)
 *
 * 数据来源: data-collector → Kafka → Spark Streaming → MySQL
 * 前端从此接口读取，与采集层完全解耦
 */
export function getStockList(params?: MarketListParams, signal?: AbortSignal): Promise<PageResult<StockListItem>> {
  return request.get('/market/list', { params, signal })
}

export function getStockByCode(code: string, signal?: AbortSignal): Promise<StockDetail> {
  return request.get(`/market/${code}`, { signal })
}

export function getKlineData(code: string, days?: number, signal?: AbortSignal): Promise<StockDaily[]> {
  return request.get(`/market/kline/${code}`, { params: { days }, signal })
}

export function getKlineRange(code: string, startDate?: string, endDate?: string): Promise<StockDaily[]> {
  return request.get('/market/kline/range', { params: { code, startDate, endDate } })
}

export function searchStocks(keyword: string): Promise<StockDetail[]> {
  return request.get('/market/search', { params: { keyword, size: 10 } })
}

export function getIndustries(): Promise<string[]> {
  return request.get('/market/industries')
}

export function getSectorRanking(tradeDate?: string): Promise<{ tradeDate: string; records: SectorRanking[] }> {
  return request.get('/market/sector-ranking', { params: { tradeDate } })
}

/** 行业分层云图（一级行业 + 成分股明细，前端钻取用） */
/** ETF 行情列表（股票行情下的子板块）*/
export function getEtfList(params?: { page?: number; size?: number; keyword?: string }): Promise<PageResult<any>> {
  return request.get('/market/etf', { params })
}

export function getIndustryTreemap(tradeDate?: string): Promise<{
  tradeDate: string
  records: {
    name: string
    stockCount: number
    avgChangePct: number
    children: { stockCode: string; stockName: string; changePercent: number }[]
  }[]
}> {
  return request.get('/market/industry-treemap', { params: { tradeDate } })
}

export function filterStocks(params: StockFilterParams): Promise<StockDetail[]> {
  return request.get('/market/filter', { params })
}

export function getMaxTradeDate(): Promise<{ tradeDate: string }> {
  return request.get('/market/max-date')
}

/** 获取市场分类列表（沪市/深市/创业板等） */
export function getMarkets(): Promise<string[]> {
  return request.get('/market/markets')
}

/** 获取板块K线数据（行业成分股均价聚合） */
export function getSectorKline(industry: string, days = 60): Promise<StockDaily[]> {
  return request.get('/market/sector-kline', { params: { industry, days } })
}
