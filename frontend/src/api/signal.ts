import request from './request'
import type { HotReason, DragonTigerDetail, Northbound, LockupDetail, ConceptBlock, FundFlow } from '@/types'

/**
 * 信号层 API — 对应后端 SignalDataController (/api/signal)
 *
 * 数据来源: data-collector(同花顺/百度/akshare) → MySQL
 */

// ── 题材热点 ──
export function getHotReason(date?: string): Promise<{ date: string; records: HotReason[]; total: number }> {
  return request.get('/signal/hot-reason', { params: { date } })
}
export function getHotReasonDates(): Promise<string[]> {
  return request.get('/signal/hot-reason/dates')
}

// ── 龙虎榜 ──
export function getDragonTigerDaily(date?: string): Promise<{ date: string; records: any[]; total: number }> {
  return request.get('/signal/dragon-tiger/daily', { params: { date } })
}
export function getDragonTigerByStock(code: string): Promise<any[]> {
  return request.get(`/signal/dragon-tiger/stock/${code}`)
}

// ── 龙虎榜明细(新) ──
export function getDragonTigerDetail(date?: string): Promise<{ date: string; records: DragonTigerDetail[]; total: number }> {
  return request.get('/signal/dragon-tiger-detail', { params: { date } })
}
export function getDragonTigerDetailByStock(code: string): Promise<DragonTigerDetail[]> {
  return request.get(`/signal/dragon-tiger-detail/stock/${code}`)
}

// ── 北向资金 ──
export function getNorthboundLatest(days = 30): Promise<Northbound[]> {
  return request.get('/signal/northbound/latest', { params: { days } })
}
export function getNorthboundByDate(date?: string): Promise<Northbound> {
  return request.get('/signal/northbound/date', { params: { date } })
}

// ── 概念板块(新) ──
export function getConceptBlocks(code: string): Promise<ConceptBlock[]> {
  return request.get(`/signal/concept-blocks/${code}`)
}

// ── 资金流向(新) ──
export function getFundFlow(code: string, limit = 20): Promise<FundFlow[]> {
  return request.get(`/signal/fund-flow/${code}`, { params: { limit } })
}

// ── 限售解禁 ──
export function getLockupByStock(code: string): Promise<LockupDetail[]> {
  return request.get(`/signal/lockup/stock/${code}`)
}
export function getUpcomingLockup(limit = 50): Promise<LockupDetail[]> {
  return request.get('/signal/lockup/upcoming', { params: { limit } })
}

// ── 解禁明细(新) ──
export function getLockupDetail(code: string): Promise<LockupDetail[]> {
  return request.get(`/signal/lockup-detail/${code}`)
}

// ── 行业对比 ──
export function getIndustryCompare(date?: string): Promise<{ date: string; records: any[]; total: number }> {
  return request.get('/signal/industry-compare', { params: { date } })
}
export function getIndustryDates(): Promise<string[]> {
  return request.get('/signal/industry-compare/dates')
}
