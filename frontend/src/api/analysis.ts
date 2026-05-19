import request from './request'

// ── 类型定义 ──
interface YearlyReturn { year: number; rate: number; rank?: number }
interface MonthlyReturn { month: string; rate: number }
interface TrendAnalysis { trend: string; ma5?: number; ma10?: number; ma20?: number }
interface SectorRanking { industry: string; avgChange: number; count: number }

/** 获取股票基础分析（分页） */
export function getAnalysis(assetCode: string, type?: string): Promise<any> {
  return request.get(`/analysis/${assetCode}`, { params: { type } }) as any
}

/** 年收益率 */
export function getYearlyReturn(stockCode: string, years = 3): Promise<YearlyReturn[]> {
  return request.get(`/analysis/${stockCode}/yearly-return`, { params: { years } }) as any
}

/** 月收益率 */
export function getMonthlyReturn(stockCode: string, months = 12): Promise<MonthlyReturn[]> {
  return request.get(`/analysis/${stockCode}/monthly-return`, { params: { months } }) as any
}

/** 趋势分析 */
export function getTrend(stockCode: string, days = 30): Promise<TrendAnalysis> {
  return request.get(`/analysis/${stockCode}/trend`, { params: { days } }) as any
}

/** 股票筛选 */
export function filterStocks(conditions: {
  industry?: string
  minPrice?: number
  maxPrice?: number
  minChange?: number
  limit?: number
}): Promise<any[]> {
  return request.post('/analysis/filter', conditions) as any
}

/** 相关性分析 */
export function getCorrelation(codeA: string, codeB: string, days = 60): Promise<{ coefficient: number }> {
  return request.get('/analysis/correlation', { params: { codeA, codeB, days } }) as any
}

/** 行业涨跌排行（板块云图数据） */
export function getSectorRanking(tradeDate?: string): Promise<SectorRanking[]> {
  return request.get('/analysis/sector-ranking', { params: { tradeDate } }) as any
}

/** ─── 缠论分析 ─── */

export interface ChanlunBi {
  x0: number; y0: number; x1: number; y1: number
}

export interface ChanlunZhongshu {
  startX: number; endX: number; high: number; low: number
}

export interface ChanlunFengxing {
  type: 'ding' | 'di'; x: number; price: number
}

export interface ChanlunBuySellPoint {
  type: string; date: string; price: number; strength?: number; description?: string
}

export interface ChanlunAnalysis {
  bi: ChanlunBi[]
  zhongshu: ChanlunZhongshu[]
  fengxing: ChanlunFengxing[]
  buy_sell_points: ChanlunBuySellPoint[]
  stats: {
    top_fractals: number
    bottom_fractals: number
    pens: number
    centers: number
    signals: number
  }
}

/** 获取缠论分析数据（前端K线图渲染用） */
export function getChanlunAnalysis(stockCode: string, days = 365): Promise<ChanlunAnalysis> {
  return request.get(`/analysis/${stockCode}/chanlun`, { params: { days } }) as any
}
