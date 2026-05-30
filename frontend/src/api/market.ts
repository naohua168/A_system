import request from './request'
import type { StockListItem, StockDetail, StockDaily, SectorRanking } from '@/types'
import type { MarketListParams, PageResult, StockFilterParams } from './types'

/**
 * 行情层 API — 数据来源: Hive→Redis 管道 (每60s同步)
 *
 * 新链路: 采集器→CSV→HDFS→Hive→Python管道→Redis→API
 * MySQL 已不再存储市场数据（仅存 user/watchlist）
 */

/** 股票列表（Redis 新数据源） */
export function getStockList(params?: MarketListParams, signal?: AbortSignal): Promise<PageResult<StockListItem>> {
  return request.get('/v2/market/list', { params, signal })
}

export function getStockByCode(code: string, signal?: AbortSignal): Promise<StockDetail> {
  return request.get(`/v2/market/detail/${code}`, { signal })
}

export function getKlineData(code: string, days?: number, signal?: AbortSignal): Promise<StockDaily[]> {
  return request.get(`/v2/market/kline/${code}`, { params: { days }, signal })
}

export function getKlineRange(code: string, startDate?: string, endDate?: string): Promise<StockDaily[]> {
  return request.get('/v2/market/kline/range', { params: { code, startDate, endDate } })
}

export function searchStocks(keyword: string): Promise<StockDetail[]> {
  return request.get('/v2/market/search', { params: { keyword, size: 10 } })
}

export function getIndustries(): Promise<string[]> {
  return request.get('/v2/market/industries')
}

export function getSectorRanking(tradeDate?: string): Promise<{ tradeDate: string; records: SectorRanking[] }> {
  return request.get('/v2/market/sector-ranking', { params: { tradeDate } })
}

/** ETF 行情列表 */
export function getEtfList(params?: { page?: number; size?: number; keyword?: string }): Promise<PageResult<any>> {
  return request.get('/v2/market/etf', { params })
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
  return request.get('/v2/market/industry-treemap', { params: { tradeDate } })
}

export function filterStocks(params: StockFilterParams): Promise<StockDetail[]> {
  return request.get('/v2/market/filter', { params })
}

export function getMaxTradeDate(): Promise<{ tradeDate: string }> {
  return request.get('/v2/market/max-date')
}

/** 获取市场分类列表 */
export function getMarkets(): Promise<string[]> {
  return request.get('/v2/market/markets')
}

/** 获取板块K线数据 */
export function getSectorKline(industry: string, days = 60): Promise<StockDaily[]> {
  return request.get('/v2/market/sector-kline', { params: { industry, days } })
}
