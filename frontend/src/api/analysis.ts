import request from './request'

/** 获取股票基础分析（分页） */
export function getAnalysis(assetCode: string, type?: string) {
  return request.get(`/analysis/${assetCode}`, { params: { type } })
}

/** 年收益率 */
export function getYearlyReturn(stockCode: string, years = 3) {
  return request.get(`/analysis/${stockCode}/yearly-return`, { params: { years } })
}

/** 月收益率 */
export function getMonthlyReturn(stockCode: string, months = 12) {
  return request.get(`/analysis/${stockCode}/monthly-return`, { params: { months } })
}

/** 趋势分析 */
export function getTrend(stockCode: string, days = 30) {
  return request.get(`/analysis/${stockCode}/trend`, { params: { days } })
}

/** 股票筛选 */
export function filterStocks(conditions: {
  industry?: string
  minPrice?: number
  maxPrice?: number
  minChange?: number
  limit?: number
}) {
  return request.post('/analysis/filter', conditions)
}

/** 相关性分析 */
export function getCorrelation(codeA: string, codeB: string, days = 60) {
  return request.get('/analysis/correlation', { params: { codeA, codeB, days } })
}

/** 行业涨跌排行（板块云图数据） */
export function getSectorRanking(tradeDate?: string) {
  return request.get('/analysis/sector-ranking', { params: { tradeDate } })
}
