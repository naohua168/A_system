import request from './request'
import type { StockListItem, StockDetail, StockDaily, SectorRanking } from '@/types'

/**
 * 行情层 API — 对应后端 MarketController (/api/market)
 *
 * 数据来源: data-collector → Kafka → Spark Streaming → MySQL
 * 前端从此接口读取，与采集层完全解耦
 */

export interface MarketListParams {
  page?: number
  size?: number
  keyword?: string
  industry?: string
  sortField?: string
  sortOrder?: 'asc' | 'desc'
}

export function getStockList(params?: MarketListParams): Promise<{
  records: StockListItem[]
  total: number
  page: number
  size: number
}> {
  return request.get('/market/list', { params })
}

export function getStockByCode(code: string): Promise<StockDetail> {
  return request.get(`/market/${code}`)
}

export function getKlineData(code: string, days?: number): Promise<StockDaily[]> {
  return request.get(`/market/kline/${code}`, { params: { days } })
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

export function filterStocks(params: {
  industry?: string
  minPrice?: number
  maxPrice?: number
  minChange?: number
  limit?: number
}): Promise<any[]> {
  return request.get('/market/filter', { params })
}

export function getMaxTradeDate(): Promise<{ tradeDate: string }> {
  return request.get('/market/max-date')
}
