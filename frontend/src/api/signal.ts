import request from './request'

export interface HotReasonRecord {
  id: number
  tradeDate: string
  stockCode: string
  stockName: string
  reason: string
  changePct: number
  turnoverPct: number
}

export interface DragonTigerRecord {
  id: number
  tradeDate: string
  stockCode: string
  stockName: string
  reason: string
  netBuyWan: number
  buyWan: number
  sellWan: number
  changePct: number
  turnoverPct: number
}

export interface NorthboundRecord {
  id: number
  tradeDate: string
  hgtYi: number
  sgtYi: number
}

export interface LockupRecord {
  id: number
  stockCode: string
  lockupDate: string
  lockupType: string
  shares: number
  floatRatio: number
  isUpcoming: number
}

export interface IndustryCompareRecord {
  id: number
  tradeDate: string
  rankNum: number
  industryName: string
  changePct: number
  turnoverYi: number
  netInflowYi: number
  upCount: number
  downCount: number
  leader: string
}

// 题材热点
export function getHotReason(date?: string) {
  return request.get('/signal/hot-reason', { params: { date } })
}
export function getHotReasonDates() {
  return request.get('/signal/hot-reason/dates')
}

// 龙虎榜
export function getDragonTigerDaily(date?: string) {
  return request.get('/signal/dragon-tiger/daily', { params: { date } })
}
export function getDragonTigerByStock(code: string) {
  return request.get(`/signal/dragon-tiger/stock/${code}`)
}
export function getDragonTigerDetail(date: string, code: string) {
  return request.get('/signal/dragon-tiger/detail', { params: { date, code } })
}
export function getDragonTigerDates() {
  return request.get('/signal/dragon-tiger/dates')
}

// 北向资金
export function getNorthboundLatest(days = 30) {
  return request.get('/signal/northbound/latest', { params: { days } })
}
export function getNorthboundByDate(date?: string) {
  return request.get('/signal/northbound/date', { params: { date } })
}
export function getNorthboundDates() {
  return request.get('/signal/northbound/dates')
}

// 限售解禁
export function getLockupByStock(code: string) {
  return request.get(`/signal/lockup/stock/${code}`)
}
export function getUpcomingLockup() {
  return request.get('/signal/lockup/upcoming')
}
export function getLockupHistory() {
  return request.get('/signal/lockup/history')
}

// 行业对比
export function getIndustryCompare(date?: string) {
  return request.get('/signal/industry-compare', { params: { date } })
}
export function getIndustryDates() {
  return request.get('/signal/industry-compare/dates')
}
