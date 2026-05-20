import request from './request'
import type {
  AnalysisResult,
  YearlyReturn,
  MonthlyReturn,
  TrendAnalysis,
  StockFilterCondition,
  CorrelationResult,
  SectorRanking,
  ChanlunAnalysis,
} from '@/types'

/** 获取股票基础分析（分页） */
export function getAnalysis(assetCode: string, type?: string): Promise<AnalysisResult[]> {
  return request.get(`/analysis/${assetCode}`, { params: { type } })
}

/** 年收益率 */
export function getYearlyReturn(stockCode: string, years = 3): Promise<YearlyReturn[]> {
  return request.get(`/analysis/${stockCode}/yearly-return`, { params: { years } })
}

/** 月收益率 */
export function getMonthlyReturn(stockCode: string, months = 12): Promise<MonthlyReturn[]> {
  return request.get(`/analysis/${stockCode}/monthly-return`, { params: { months } })
}

/** 趋势分析 */
export function getTrend(stockCode: string, days = 30): Promise<TrendAnalysis> {
  return request.get(`/analysis/${stockCode}/trend`, { params: { days } })
}

/** 股票筛选 */
export function filterStocks(conditions: StockFilterCondition): Promise<StockFilterCondition[]> {
  return request.post('/analysis/filter', conditions)
}

/** 相关性分析 */
export function getCorrelation(codeA: string, codeB: string, days = 60): Promise<CorrelationResult> {
  return request.get('/analysis/correlation', { params: { codeA, codeB, days } })
}

/** 行业涨跌排行（板块云图数据） */
export function getSectorRanking(tradeDate?: string): Promise<SectorRanking[]> {
  return request.get('/analysis/sector-ranking', { params: { tradeDate } })
}

/** 获取缠论分析数据（前端K线图渲染用） */
export function getChanlunAnalysis(stockCode: string, days = 365): Promise<ChanlunAnalysis> {
  return request.get(`/analysis/${stockCode}/chanlun`, { params: { days } })
}
