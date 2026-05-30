import request from './request'
import type { Fund, FundNav, FundHolding } from '@/types'
import type { PageResult } from './types'

/** 获取基金列表（分页）— Redis 数据源 */
export function getFundList(params?: { page?: number; size?: number; fundType?: string }): Promise<PageResult<Fund>> {
  return request.get('/v2/fund/list', { params })
}
/** 获取基金基本信息 */
export function getFundInfo(code: string): Promise<Fund> {
  return request.get('/v2/fund/' + code)
}
/** 获取基金净值 */
export function getFundNav(code: string, days?: number): Promise<FundNav[]> {
  return request.get('/v2/fund/' + code + '/nav', { params: { days } })
}
/** 获取基金持仓 */
export function getFundHoldings(code: string): Promise<FundHolding[]> {
  return request.get('/v2/fund/' + code + '/holdings')
}
