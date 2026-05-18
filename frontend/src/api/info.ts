import request from './request'
import type { ResearchReport, ConsensusEps, NewsItem, Filing } from '@/types'

/**
 * 资讯层 API — 对应后端 InfoController (/api/info)
 *
 * 数据来源: data-collector(研报/新闻/公告) → MySQL
 * 从 a-stock-data 迁移合并
 */

// ── 研报 ──
export function getResearchReports(code: string): Promise<{ stockCode: string; records: ResearchReport[]; total: number }> {
  return request.get(`/info/research/${code}`)
}
export function getResearchByOrg(org: string, limit = 20): Promise<ResearchReport[]> {
  return request.get('/info/research/org', { params: { org, limit } })
}

// ── 一致预期EPS ──
export function getConsensusEps(code: string): Promise<ConsensusEps[]> {
  return request.get(`/info/consensus-eps/${code}`)
}

// ── 个股新闻 ──
export function getStockNews(code: string, limit = 20): Promise<{ stockCode: string; records: NewsItem[]; total: number }> {
  return request.get(`/info/news/${code}`, { params: { limit } })
}

// ── 财联社快讯 ──
export function getClsNews(limit = 30): Promise<{ records: NewsItem[]; total: number }> {
  return request.get('/info/cls-news', { params: { limit } })
}

// ── 全球资讯 ──
export function getGlobalNews(limit = 20): Promise<{ records: NewsItem[]; total: number }> {
  return request.get('/info/global-news', { params: { limit } })
}

// ── 巨潮公告 ──
export function getFilings(code: string, limit = 20): Promise<{ stockCode: string; records: Filing[]; total: number }> {
  return request.get(`/info/filing/${code}`, { params: { limit } })
}

// ── 全层聚合 ──
export function getAllInfo(code: string): Promise<any> {
  return request.get(`/info/all/${code}`)
}
