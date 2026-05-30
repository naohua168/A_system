import request from './request'
import type {
  HotReasonResponse, DragonTigerResponse,
  NorthboundResponse, ConceptBlockResponse,
  FundFlowResponse, LockupResponse, IndustryCompareResponse
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
/** 概念板块 */
export function getConceptBlocks(code: string): Promise<ConceptBlockResponse> {
  return request.get('/v2/signal/concept-blocks/' + code)
}
/** 资金流向 */
export function getFundFlow(code: string, limit = 20): Promise<FundFlowResponse> {
  return request.get('/v2/signal/fund-flow/' + code, { params: { limit } })
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
