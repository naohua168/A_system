// ============================================================
// 类型定义
// ============================================================

export interface UserInfo {
  id: number
  username: string
  email: string
  avatar: string
  role: number
}

export interface Stock {
  id: number
  stockCode: string
  stockName: string
  market: string
  industry: string
  listingDate: string
  totalShares: number
  circulatedShares: number
  pe?: number
  pb?: number
  totalMarketCap?: number
  floatMarketCap?: number
}

/** 股票列表项（含最新行情） */
export interface StockListItem {
  stockCode: string
  stockName: string
  market: string
  industry: string
  price: number
  changePct: number
  change?: number
  volume?: number
  highPrice?: number
  lowPrice?: number
  pe?: number
}

export interface StockDaily {
  id: number
  stockCode: string
  tradeDate: string
  openPrice: number
  highPrice: number
  lowPrice: number
  closePrice: number
  preClose: number
  volume: number
  amount: number
  changePercent: number
  turnoverRate: number
}

export interface Fund {
  id: number
  fundCode: string
  fundName: string
  fundType: string
  company: string
  manager: string
  establishDate: string
  nav: number
  accumulatedNav: number
  scale?: number
}

/** 基金持仓 */
export interface FundHolding {
  id: number
  fundCode: string
  stockCode: string
  stockName: string
  ratio: number
  rankNum: number
  reportDate: string
}

export interface FundNav {
  id: number
  fundCode: string
  navDate: string
  nav: number
  accumulatedNav: number
  dailyReturn: number
}

export interface WatchlistItem {
  id: number
  userId: number
  assetType: number // 0-股票, 1-基金
  assetCode: string
  remark: string
  sortOrder: number
}

export interface NewsItem {
  id: string
  title: string
  summary: string
  source: string
  publishTime: string
  url: string
  tags: string[]
}

export interface SectorData {
  name: string
  value: number
  changePercent: number
  items?: SectorData[]
}

export interface MarketIndex {
  name: string
  code: string
  price: number
  changePercent: number
  changePoints: number
}

export interface ChanlunPoint {
  type: 'ding' | 'di' | 'bi' | 'xian' | 'zhongshu'
  date: string
  price: number
  high?: number
  low?: number
}

export interface AnalysisResult {
  id: number
  assetCode: string
  analysisType: string
  resultJson: string
  summary: string
  analysisDate: string
}

// ── AI 对话 ──
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: number
}

export interface AIRequest {
  message: string
  stockCode?: string
  history?: { role: string; content: string }[]
}

export interface AIResponse {
  reply: string
  status?: string
}

export interface AIStatus {
  service: string
  aiServiceUrl: string
  status: string
}
