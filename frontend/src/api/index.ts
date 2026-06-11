import request from './request'
import type { MarketIndexItem, MarketIndex, IndexDaily } from '@/types'

/** 获取所有指数列表（含最新行情）— Redis 数据源 */
export function getIndexList(): Promise<MarketIndexItem[]> {
  return request.get('/v2/index/list')
}
/** 获取历史指数数据 */
export function getHistoryIndexList(date?: string): Promise<MarketIndexItem[]> {
  return request.get('/v2/history/index/list', { params: { date } })
}
/** 获取指数基本信息 */
export function getIndexInfo(code: string): Promise<MarketIndex> {
  return request.get('/v2/index/' + code)
}
/** 获取指数K线数据（支持多周期：day/week/month/5min/15min/30min/60min） */
export function getIndexKline(code: string, days = 120, period = 'day'): Promise<IndexDaily[]> {
  return request.get('/v2/index/' + code + '/kline', { params: { days, period } })
}
/** 获取最近交易日 */
export function getMaxTradeDate(): Promise<{ tradeDate: string }> {
  return request.get('/v2/index/max-date')
}

/** 历史数据：市场行情列表 */
export function getHistoryMarketList(date?: string): Promise<any[]> {
  return request.get('/v2/history/market/list', { params: { date } })
}
