import request from './request'
import type { Fund, FundNav } from '@/types'

/** 获取基金基本信息 */
export function getFundInfo(code: string) {
  return request.get(`/fund/${code}`)
}

/** 获取基金净值 */
export function getFundNav(code: string, params?: { days?: number }) {
  return request.get(`/fund/${code}/nav`, { params })
}

/** 获取基金持仓 */
export function getFundHoldings(code: string) {
  return request.get(`/fund/${code}/holdings`)
}

/** 获取热门基金列表 */
export function getFundList(params?: { page?: number; size?: number; type?: string }) {
  return request.get('/fund/list', { params })
}
