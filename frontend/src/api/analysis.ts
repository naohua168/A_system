import request from './request'
import type { ChanlunAnalysis, SectorRanking } from '@/types'

/** 行业涨跌排行（缠论服务，port 8899） */
export function getSectorRanking(tradeDate?: string): Promise<SectorRanking[]> {
  return request.get('/analysis/sector-ranking', { params: { tradeDate } })
}

/** 获取缠论分析数据（前端K线图渲染用）
 * @param stockCode 股票代码
 * @param days K线条数
 * @param period K线周期: day/week/month/5min/15min/30min/60min
 * @param type 类型: stock/index
 */
export function getChanlunAnalysis(stockCode: string, days = 365, period = 'day', type: 'stock' | 'index' = 'stock'): Promise<ChanlunAnalysis> {
  return request.get(`/analysis/${stockCode}/chanlun`, { params: { days, period, type } })
}
