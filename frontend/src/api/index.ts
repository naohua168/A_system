import request from './request'
import type { MarketIndexItem, MarketIndex, IndexDaily } from '@/types'

/** 获取所有指数列表（含最新行情） */
export function getIndexList(): Promise<MarketIndexItem[]> {
  return request.get('/index/list')
}

/** 获取指数基本信息 */
export function getIndexInfo(code: string): Promise<MarketIndex> {
  return request.get(`/index/${code}`)
}

/** 获取指数K线数据 */
export function getIndexKline(code: string, days = 120): Promise<IndexDaily[]> {
  return request.get(`/index/${code}/kline`, { params: { days } })
}

/** 获取最近交易日 */
export function getMaxTradeDate(): Promise<{ tradeDate: string }> {
  return request.get('/index/max-date')
}
