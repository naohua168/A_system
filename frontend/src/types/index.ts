// ============================================================
// 类型定义 — 适配后端三层架构
// ============================================================

export interface Pageable<T> {
  records: T[]
  total: number
  page: number
  size: number
  totalPages: number
}

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
  timestamp: number
}

// ── 基础设施 ──

export interface UserInfo {
  id: number
  username: string
  email: string
  avatar: string
  role: number
}

export interface WatchlistItem {
  id: number
  userId: number
  assetType: number
  assetCode: string
  remark: string
  sortOrder: number
}

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

// ── 行情层 (Market) ──

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

export interface StockDetail extends Stock {
  price?: number
  changePercent?: number
  open?: number
  high?: number
  low?: number
  preClose?: number
  volume?: number
  amount?: number
  turnoverRate?: number
  tradeDate?: string
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

export interface SectorRanking {
  industry: string
  stockCount: number
  avgChangePct: number
  upCount: number
  upRatio: number
}

export interface MarketIndex {
  name: string
  code: string
  price: number
  changePercent: number
  changePoints: number
}

// ── 信号层 (Signal) ──

export interface HotReason {
  id: number
  tradeDate: string
  stockCode: string
  stockName: string
  reason: string
  changePct: number
  turnoverPct: number
}

export interface Northbound {
  id: number
  tradeDate: string
  hgtYi: number
  sgtYi: number
}

export interface DragonTigerDetail {
  id: number
  tradeDate: string
  stockCode: string
  stockName: string
  reason: string
  netBuyWan: number
  changePct: number
}

export interface ConceptBlock {
  id: number
  stockCode: string
  blockType: string
  blockName: string
  changePct: string
}

export interface FundFlow {
  id: number
  stockCode: string
  tradeDate: string
  close: number
  mainIn: string
  superNetIn: string
}

export interface IndustryCompare {
  rank: number
  name: string
  changePct: number
  turnoverYi: number
  upCount: number
  downCount: number
  leader: string
}

export interface LockupDetail {
  id: number
  stockCode: string
  lockupDate: string
  lockupType: string
  shares: number
  typeTag: string
}

// ── 资讯层 (Information) ──

export interface ResearchReport {
  id: number
  stockCode: string
  title: string
  publishDate: string
  orgName: string
  rating: string
  predictEpsThisYear?: number
  predictEpsNextYear?: number
}

export interface ConsensusEps {
  id: number
  stockCode: string
  year: string
  forecastCount: number
  minEps: number
  avgEps: number
  maxEps: number
}

export interface NewsItem {
  id: number
  title: string
  publishTime: string
  contentSummary: string
  source: string
  url: string
}

export interface Filing {
  id: number
  stockCode: string
  title: string
  publishDate: string
  filingType: string
  contentSummary: string
}

// ── 基金层 (Fund) ──

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

// ── 分析层 (Analysis) ──

export interface AnalysisResult {
  id: number
  assetCode: string
  analysisType: string
  resultJson: string
  summary: string
  analysisDate: string
}

export interface ChanlunPoint {
  type: 'ding' | 'di' | 'bi' | 'xian' | 'zhongshu'
  date: string
  price: number
  high?: number
  low?: number
}
