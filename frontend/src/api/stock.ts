import request from './request'
import type { StockListItem, StockDetail, StockDaily } from '@/types'

export function getStockList(params?: {
  page?: number
  size?: number
  keyword?: string
  industry?: string
  sortField?: string
  sortOrder?: 'asc' | 'desc'
}): Promise<{ records: StockListItem[]; total: number; page: number; size: number }> {
  return request.get('/stock/list', { params }) as any
}

export function getStockByCode(code: string): Promise<StockDetail> {
  return request.get(`/stock/${code}`) as any
}

export function getKlineData(code: string, params?: { days?: number; freq?: string }): Promise<StockDaily[]> {
  return request.get(`/stock/kline/${code}`, { params }) as any
}

/** 搜索股票（自动补全） */
export function searchStocks(keyword: string): Promise<StockListItem[]> {
  return request.get('/stock/search', { params: { keyword, size: 10 } }) as any
}

/** 获取行业列表 */
export function getIndustries(): Promise<string[]> {
  return request.get('/stock/industries') as any
}
