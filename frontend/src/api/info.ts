import request from './request'
import type { ResearchReportResponse, ConsensusEps, ClsNewsResponse, GlobalNewsResponse, FilingResponse } from '@/types'

/** 研报 */
export function getResearchReports(code: string): Promise<ResearchReportResponse> {
  return request.get('/v2/info/research/' + code)
}
export function getResearchByDateRange(code: string, startDate: string, endDate: string): Promise<ResearchReportResponse> {
  return request.get('/v2/info/research/range', { params: { code, startDate, endDate } })
}
/** 一致预期 */
export function getConsensusEps(code: string): Promise<ConsensusEps> {
  return request.get('/v2/info/consensus-eps/' + code)
}
/** 个股新闻 */
export function getStockNews(code: string, days = 30): Promise<any> {
  return request.get('/v2/info/news/' + code, { params: { days } })
}
/** 财联社快讯（兼容后端返回原始数组和 {records,total} 两种格式） */
async function wrapArray<T>(res: any): Promise<{ records: T[]; total: number }> {
  if (Array.isArray(res)) return { records: res as T[], total: res.length }
  return res as { records: T[]; total: number }
}

export function getClsNews(limit = 50, since?: string): Promise<ClsNewsResponse> {
  return request.get('/v2/info/cls-news', { params: { limit, since } }).then(wrapArray)
}
export function getClsNewsSince(since: string): Promise<ClsNewsResponse> {
  return request.get('/v2/info/cls-news', { params: { since } }).then(wrapArray)
}
/** 全球资讯 */
export function getGlobalNews(limit = 20): Promise<GlobalNewsResponse> {
  return request.get('/v2/info/global-news', { params: { limit } }).then(wrapArray)
}
/** 巨潮公告 */
export function getFilings(code: string, page = 1, size = 20): Promise<FilingResponse> {
  return request.get('/v2/info/filings/' + code, { params: { page, size } })
}
