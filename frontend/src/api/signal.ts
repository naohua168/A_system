import request from './request'
import type {
  HotReasonResponse, DragonTigerResponse,
  NorthboundResponse, ConceptBlockResponse,
  LockupResponse, IndustryCompareResponse
} from '@/types'

/** 题材热点 */
export function getHotReason(date?: string): Promise<HotReasonResponse> {
  return request.get('/v2/signal/hot-reason', { params: { date } })
}
/** 龙虎榜 */
export function getDragonTigerDaily(date?: string): Promise<DragonTigerResponse> {
  return request.get('/v2/signal/dragon-tiger/daily', { params: { date } })
}
export function getDragonTigerByStock(code: string): Promise<DragonTigerResponse> {
  return request.get('/v2/signal/dragon-tiger/stock/' + code)
}
/** 北向资金 */
export function getNorthboundLatest(days = 10): Promise<NorthboundResponse> {
  return request.get('/v2/signal/northbound/latest', { params: { days } })
}
/** 北向资金分钟级时序（262 个时间点） */
export function getNorthboundMinute(date?: string): Promise<any[]> {
  return request.get('/v2/signal/northbound/minute', { params: { date } })
}
/** 概念板块 */
export function getConceptBlocks(code: string): Promise<ConceptBlockResponse> {
  return request.get('/v2/signal/concept-blocks/' + code)
}
/** 限售解禁 */
export function getLockupByStock(code: string): Promise<LockupResponse> {
  return request.get('/v2/signal/lockup/stock/' + code)
}
export function getUpcomingLockup(): Promise<LockupResponse> {
  return request.get('/v2/signal/lockup/upcoming')
}
/** 行业对比 */
export function getIndustryCompare(date?: string): Promise<IndustryCompareResponse> {
  return request.get('/v2/signal/industry-compare', { params: { date } })
}
/** 历史行业对比 */
export function getHistoryIndustryCompare(date?: string): Promise<IndustryCompareResponse> {
  return request.get('/v2/history/industry-compare', { params: { date } })
}
/** 历史北向资金 */
export function getHistoryNorthbound(date?: string): Promise<NorthboundResponse> {
  return request.get('/v2/history/northbound', { params: { date } })
}
/** 历史热点题材 */
export function getHistoryHotReason(date?: string): Promise<HotReasonResponse> {
  return request.get('/v2/history/hot-reason', { params: { date } })
}
/** 历史龙虎榜 */
export function getHistoryDragonTiger(date?: string): Promise<DragonTigerResponse> {
  return request.get('/v2/history/dragon-tiger', { params: { date } })
}
