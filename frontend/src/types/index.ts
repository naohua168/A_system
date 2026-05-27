// ============================================================
// 领域模型类型 — 适配 L1~L4 后端三层架构
// ============================================================

// ── 基础设施 ──

export interface UserInfo {
  id: number
  username: string
  email: string
  avatar: string
  role: number
  password?: never
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

export interface AIStatus {
  service: string
  aiServiceUrl: string
  status: string
}

// ── 行情层 (Market) — 对应后端 MarketController ──

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
  turnoverRate?: number
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

export interface MarketIndexItem {
  indexCode: string
  indexName: string
  market?: string
  category?: string
  closePoint?: number
  changePercent?: number
  tradeDate?: string
}

export interface MarketIndex {
  id: number
  indexCode: string
  indexName: string
  market: string
  category: string
}

export interface IndexDaily {
  id: number
  indexCode: string
  tradeDate: string
  openPoint: number
  closePoint: number
  highPoint: number
  lowPoint: number
  changePercent: number
  volume: number
  amount: number
}

// ── 信号层 (Signal) — 对应后端 SignalDataController ──

export interface HotReason {
  id: number
  tradeDate: string
  stockCode: string
  stockName: string
  reason: string
  changePct: number
  turnoverPct: number
}

export interface DragonTiger {
  id: number
  tradeDate: string
  stockCode: string
  stockName: string
  reason: string
  netBuyWan: number
  changePct: number
}

export interface DragonTigerDaily {
  date: string
  records: DragonTiger[]
  total: number
}

export interface DragonTigerDetail {
  id: number
  tradeDate: string
  stockCode: string
  stockName: string
  reason: string
  netBuyWan: number
  buyWan: number
  sellWan: number
  changePct: number
}

export interface Northbound {
  id: number
  tradeDate: string
  hgtYi: number
  sgtYi: number
}

export interface LockupDetail {
  id: number
  stockCode: string
  lockupDate: string
  lockupType: string
  shares: number
  typeTag: string
  floatRatio?: number
  isUpcoming?: boolean
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
  industryName: string
  changePct: number
  turnoverYi: number
  upCount: number
  downCount: number
  leader: string
}

export interface IndustryCompareResponse {
  date: string
  records: IndustryCompare[]
  total: number
}

// ── 资讯层 (Information) — 对应后端 InfoController ──

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

export interface ResearchReportResponse {
  stockCode: string
  records: ResearchReport[]
  total: number
  note?: string
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
  stockCode: string
  title: string
  publishTime: string
  contentSummary: string
  source: string
  url: string
}

export interface NewsResponse {
  stockCode?: string
  records: NewsItem[]
  total: number
  note?: string
}

export interface ClsNewsItem {
  id: number
  title: string
  publishTime: string
  content: string
}

export interface ClsNewsResponse {
  records: ClsNewsItem[]
  total: number
}

export interface GlobalNewsItem {
  id: number
  title: string
  publishTime: string
  summary: string
  source: string
  url: string
}

export interface GlobalNewsResponse {
  records: GlobalNewsItem[]
  total: number
}

export interface Filing {
  id: number
  stockCode: string
  title: string
  publishDate: string
  filingType: string
  contentSummary: string
}

export interface FilingResponse {
  stockCode: string
  records: Filing[]
  total: number
  note?: string
}

export interface InfoPdf {
  id: number
  reportId: number
  stockCode: string
  pdfTitle: string
  pdfUrl: string
  fileSize: number
}

export interface AllInfoResponse {
  stockCode: string
  researchReports: { total: number; records: ResearchReport[] }
  consensusEps: ConsensusEps[]
  stockNews: { total: number; records: NewsItem[] }
  filings: { total: number; records: Filing[] }
  reportPdfs: { total: number; records: InfoPdf[] }
}

// ── 基金层 (Fund) — 对应后端 FundController ──

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

// ── 分析层 (Analysis) — 对应后端 AnalysisController ──

export interface AnalysisResult {
  id: number
  assetCode: string
  analysisType: string
  resultJson: string
  summary: string
  analysisDate: string
}

export interface YearlyReturn {
  year: number
  yearlyReturn: number
  startPrice: number
  endPrice: number
}

export interface MonthlyReturn {
  yearMonth: string
  monthlyReturn: number
  avgPrice: number
}

export interface TrendAnalysis {
  stockCode: string
  trend: string
  ma5: number
  ma10: number
  ma20: number
  dataCount: number
}

export interface StockFilterCondition {
  industry?: string
  minPrice?: number
  maxPrice?: number
  minChange?: number
  limit?: number
}

export interface CorrelationResult {
  codeA: string
  codeB: string
  correlation: number
}

export interface SectorRanking {
  industry: string
  stockCount: number
  avgChangePct: number
  upCount: number
  upRatio: number
}

// ── 缠论分析 (Chanlun) ──

export interface ChanlunBi {
  x0: number
  y0: number
  x1: number
  y1: number
}

export interface ChanlunZhongshu {
  startX: number
  endX: number
  high: number
  low: number
}

export interface ChanlunFengxing {
  type: 'ding' | 'di'
  x: number
  price: number
}

export interface ChanlunBuySellPoint {
  type: string
  date: string
  price: number
  strength?: number
  description?: string
}

export interface ChanlunStats {
  top_fractals: number
  bottom_fractals: number
  pens: number
  centers: number
  signals: number
}

export interface ChanlunAnalysis {
  bi: ChanlunBi[]
  zhongshu: ChanlunZhongshu[]
  fengxing: ChanlunFengxing[]
  buy_sell_points: ChanlunBuySellPoint[]
  stats: ChanlunStats
}

export interface ChanlunStatsDisplay {
  dingCount: number
  diCount: number
  biCount: number
  zhongshuCount: number
  trendType: string
  level: string
  currentBi: string
  zhongshuInfo: { zg: number; zd: number; name: string }[]
  pricePosition: string
  lastDingFeng: { price: number; date: string }
  lastDiFeng: { price: number; date: string }
  buyPoints: { type: string; price: number; desc: string }[]
  sellPoints: { type: string; price: number; desc: string }[]
  beichi: string
  signals: { type: string; text: string }[]
}

// ── 行业详情 (Sector) ──

export interface SectorInfo {
  code: string
  name: string
  price: number
  changePercent: number
  upCount: number
  downCount: number
  amount: string
  leader: string
  totalMarketCap: string
  stockCount: number
}

export interface SectorConstituent {
  code: string
  name: string
  price: number
  changePercent: number
  change: number
}

// ── 大盘指数首页展示 ──

export interface IndexCard {
  code: string
  name: string
  price: number
  changePercent: number
  changePoints: number
  isCustom: boolean
}

// ── 自选股 ──

export interface HomeStockCard {
  code: string
  name: string
  price: number
  changePercent: number
}

// ── 板块云图 ──

export interface SectorNode {
  name: string
  value: number
  changePercent: number
  /** 成分股列表（云图钻取二级） */
  children?: SectorNode[]
  /** API原始字段（仅后端返回用） */
  stockCode?: string
  stockName?: string
}

// ── 首页大盘 ──

/** 热点题材响应包装 */
export interface HotReasonResponse {
  date: string
  records: HotReason[]
  total: number
}

/** 行业排行前几名（排序后） */
export interface IndustryTopItem {
  industryName: string
  changePct: number
}

// ── 个股详情—缠论展示 ──

/** 买卖点展示项 */
export interface BuySellDisplayItem {
  type: string
  price: number
  desc: string
}

/** 背驰展示 */
export interface BeiChiDisplay {
  beichi: string
}

/** 信号展示 */
export interface SignalDisplayItem {
  type: string
  text: string
}

// ── 个股详情—信号层表格 ──

/** 资金流向表格行 */
export interface FundFlowRow {
  date: string
  close: number
  changePct: number
  mainIn: number
  superNetIn?: number
  largeNetIn?: number
  littleNetIn?: number
}

/** 龙虎榜个股详情 */
export interface DragonTigerStockRow extends DragonTiger {
  buyWan?: number
  sellWan?: number
}

/** 财务指标项 */
export interface FinancialMetric {
  label: string
  value: string
}

/** 解禁展示行 */
export interface LockupDisplayRow extends LockupDetail {
  stockName?: string
}

// ── 持仓管理 ──

export interface PortfolioItem {
  code: string
  name: string
  price: number
  changePercent: number
  shares: number
  marketValue: number
  profit: number
}

// ── API 层通用类型（原 api/types.ts，统一到此文件）──

/** 统一分页响应结构 */
export interface PageResult<T> {
  records: T[]
  total: number
  page: number
  size: number
  totalPages: number
}

/** 市场行情列表查询参数 */
export interface MarketListParams {
  page?: number
  size?: number
  keyword?: string
  industry?: string
  sortField?: string
  sortOrder?: 'asc' | 'desc'
}

/** 股票筛选参数 */
export interface StockFilterParams {
  industry?: string
  minPrice?: number
  maxPrice?: number
  minChange?: number
  limit?: number
}

/** 技术指标参数（K线渲染用） */
export interface IndicatorParams {
  macd: { fast: number; slow: number; signal: number }
  kdj: { period: number }
  rsi: { period: number }
  ma: { periods: number[] }
  boll: { period: number; multiplier: number }
}

// ── 层架构详情 (Layer Detail) — L1~L6 系统架构展示 ──

/** 层状态枚举 */
export type LayerStatus = 'completed' | 'in_progress' | 'blocked' | 'pending'

/** 层状态中文映射 */
export const LAYER_STATUS_LABEL: Record<LayerStatus, string> = {
  completed: '已完成',
  in_progress: '开发中',
  blocked: '阻塞',
  pending: '待开始',
}

/** 层状态 CSS 类名 */
export const LAYER_STATUS_CLASS: Record<LayerStatus, string> = {
  completed: 'status-completed',
  in_progress: 'status-in-progress',
  blocked: 'status-blocked',
  pending: 'status-pending',
}

/** 层进度百分比颜色 */
export const LAYER_STATUS_COLOR: Record<LayerStatus, string> = {
  completed: '#67C23A',
  in_progress: '#409EFF',
  blocked: '#F56C6C',
  pending: '#C0C4CC',
}

/** 单个功能模块项 */
export interface LayerModule {
  name: string
  status: LayerStatus
  description: string
  files?: string[]
}

/** 层的基本信息 */
export interface LayerInfo {
  id: string              // L1, L2, ...
  name: string            // 中文名
  directory: string       // 项目目录
  description: string     // 角色定位描述
  techStack: string       // 技术栈
  status: LayerStatus
  completion: number      // 完成度 0-100
  fileCount: number       // 文件数
  moduleCount: number     // 模块数
  testCount: number       // 测试用例数
  modules: LayerModule[]
  issues: string[]        // 待解决项
  lastUpdated: string     // 最后更新
}

/** 层间数据流方向 */
export interface LayerFlow {
  from: string
  to: string
  via: string
  description: string
}
