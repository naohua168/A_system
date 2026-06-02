<template>
  <div class="home-view">
    <!-- 市场概览 -->
    <section class="section market-overview">
      <template v-if="!homeLoaded">
        <div class="stats-bar skeleton-bar">
          <div v-for="i in 4" :key="i" class="stat-item">
            <div class="skeleton-line" style="width:50px;height:12px" />
            <div class="skeleton-line" style="width:70px;height:20px;margin-top:4px" />
          </div>
        </div>
      </template>
      <template v-else>
        <div class="stats-bar">
          <div class="stat-item">
            <span class="stat-label">总股票数</span>
            <span class="stat-value">{{ marketStats.total }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">上涨</span>
            <span class="stat-value rise">{{ marketStats.up }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">下跌</span>
            <span class="stat-value fall">{{ marketStats.down }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">平盘</span>
            <span class="stat-value flat">{{ marketStats.flat }}</span>
          </div>
        </div>
      </template>
    </section>

    <!-- 大盘指数 - 东方财富风格 -->
    <section class="section">
      <div class="section-header">
        <h4>大盘指数</h4>
        <div class="section-actions">
          <el-button v-if="!homeLoaded" disabled text size="small"><Setting /> 管理指数</el-button>
          <el-button v-else text type="primary" size="small" @click="showIndexManager = true">
            <el-icon><Setting /></el-icon> 管理指数
          </el-button>
        </div>
      </div>
      <template v-if="!homeLoaded">
        <div class="indices-carousel">
          <div class="indices-viewport">
            <div class="indices-track skeleton-indices">
              <div v-for="i in 4" :key="i" class="skeleton-index-card">
                <div>
                  <div class="skeleton-line" style="width:60px;height:14px" />
                  <div class="skeleton-line" style="width:80px;height:22px;margin-top:6px" />
                </div>
                <div style="text-align:right">
                  <div class="skeleton-line" style="width:50px;height:16px;margin-left:auto" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
      <template v-else>
      <div class="indices-carousel">
        <button class="scroll-arrow left" @click="scrollIndices(-1)" :disabled="scrollAtStart">
          <el-icon><ArrowLeft /></el-icon>
        </button>
        <div class="indices-viewport" ref="scrollRef">
          <div class="indices-track" :style="{ transform: `translateX(-${scrollPos}px)` }">
            <div
              v-for="(idx, i) in visibleIndices"
              :key="idx.code"
              class="index-card"
              :class="getChangeClass(idx.changePercent)"
              @click="goToIndex(idx.code)"
            >
              <div class="card-left">
                <div class="index-name">{{ idx.name }}</div>
                <div class="index-price">{{ formatPrice(idx.price) }}</div>
              </div>
              <div class="card-right">
                <div class="change-pct">{{ formatPercent(idx.changePercent) }}</div>
                <div class="change-points">{{ formatPoints(idx.changePoints) }}</div>
              </div>
              <div v-if="idx.isCustom" class="custom-dot" title="自定义"></div>
            </div>
          </div>
        </div>
        <button class="scroll-arrow right" @click="scrollIndices(1)" :disabled="scrollAtEnd">
          <el-icon><ArrowRight /></el-icon>
        </button>
      </div>
      </template>
    </section>

    <!-- 指数管理弹窗 -->
    <el-dialog v-model="showIndexManager" title="管理自选指数" width="520px" :close-on-click-modal="true">
      <div class="manager-body">
        <p class="manager-desc caption">点击指数添加到首页大盘，点击 × 移除。</p>
        <div class="available-list">
          <div class="list-title">可选指数</div>
          <div class="index-chips">
            <div v-for="idx in availableIndices" :key="idx.code" class="chip" @click="addIndex(idx)">
              <span>{{ idx.name }}</span>
              <span class="chip-code caption">{{ idx.code }}</span>
              <el-icon class="add-icon"><Plus /></el-icon>
            </div>
          </div>
        </div>
        <div class="current-list">
          <div class="list-title">已添加 ({{ visibleIndices.length }}/15)</div>
          <div class="current-chips">
            <div v-for="(idx, i) in visibleIndices" :key="idx.code" class="chip chip-added">
              <span>{{ idx.name }}</span>
              <span class="chip-code caption">{{ idx.code }}</span>
              <el-icon class="remove-icon" @click="removeIndex(i)"><Close /></el-icon>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 信号层快捷卡片 -->
    <section class="section signal-cards">
      <div class="signal-grid">
        <!-- 北向资金 -->
        <div class="signal-card" @click="$router.push('/northbound')">
          <div class="card-header">
            <div class="card-icon-wrap" style="background:rgba(41,151,255,0.12);color:#2997ff">
              <el-icon :size="20"><TrendCharts /></el-icon>
            </div>
            <div class="card-meta">
              <div class="card-title">北向资金</div>
              <div class="card-subtitle">沪/深股通资金流向</div>
            </div>
          </div>
          <template v-if="signalLoaded.nb">
            <div class="card-value" :class="nbTotal >= 0 ? 'text-rise' : 'text-fall'">
              {{ nbTotal >= 0 ? '+' : '' }}{{ nbTotal }}<small>亿</small>
            </div>
            <div class="card-foot">沪 {{ safeNum(nbHgt) }} 亿 / 深 {{ safeNum(nbSgt) }} 亿</div>
          </template>
          <template v-else>
            <div class="card-skeleton"><div class="sk-line" style="width:55%;height:28px" /><div class="sk-line" style="width:70%;height:12px" /></div>
          </template>
        </div>
        <!-- 题材热点 -->
        <div class="signal-card" @click="$router.push('/hot-reason')">
          <div class="card-header">
            <div class="card-icon-wrap" style="background:rgba(239,83,80,0.12);color:#ef5350">
              <el-icon :size="20"><DataAnalysis /></el-icon>
            </div>
            <div class="card-meta">
              <div class="card-title">题材热点</div>
              <div class="card-subtitle">今日强势个股</div>
            </div>
          </div>
          <template v-if="signalLoaded.hot">
            <div class="card-tags" v-if="hotReasons.length">
              <span v-for="r in hotReasons.slice(0,3)" :key="r.stockCode" class="hot-tag"
                @click.stop="$router.push(`/stock/${r.stockCode}`)">{{ r.stockName }}</span>
            </div>
            <div class="card-foot" v-if="hotReasons.length">{{ hotReasons.length }} 只个股今日强势</div>
            <div class="card-empty" v-else>暂无数据</div>
          </template>
          <template v-else>
            <div class="card-skeleton"><div class="sk-line" style="width:80%;height:24px" /><div class="sk-line" style="width:50%;height:12px" /></div>
          </template>
        </div>
        <!-- 行业排行 -->
        <div class="signal-card" @click="$router.push('/industry-compare')">
          <div class="card-header">
            <div class="card-icon-wrap" style="background:rgba(82,196,26,0.12);color:#52c41a">
              <el-icon :size="20"><Histogram /></el-icon>
            </div>
            <div class="card-meta">
              <div class="card-title">行业排行</div>
              <div class="card-subtitle">各行业涨跌排名</div>
            </div>
          </div>
          <template v-if="signalLoaded.ind">
            <div class="card-rank-list" v-if="industryTop.length">
              <div v-for="ind in industryTop.slice(0,3)" :key="ind.industryName" class="rank-row">
                <span class="rank-name">{{ ind.industryName }}</span>
                <span :class="(ind.changePct || 0) >= 0 ? 'text-rise' : 'text-fall'">
                  {{ (ind.changePct || 0) >= 0 ? '+' : '' }}{{ safeNum(ind.changePct, 2) }}%
                </span>
              </div>
            </div>
            <div class="card-empty" v-else>暂无数据</div>
          </template>
          <template v-else>
            <div class="card-skeleton"><div class="sk-line" style="width:85%;height:20px" /><div class="sk-line" style="width:60%;height:12px" /></div>
          </template>
        </div>
        <!-- 龙虎榜 -->
        <div class="signal-card" @click="$router.push('/dragon-tiger')">
          <div class="card-header">
            <div class="card-icon-wrap" style="background:rgba(255,140,0,0.12);color:#ff8c00">
              <el-icon :size="20"><Aim /></el-icon>
            </div>
            <div class="card-meta">
              <div class="card-title">龙虎榜</div>
              <div class="card-subtitle">每日上榜异动个股</div>
            </div>
          </div>
          <template v-if="signalLoaded.dt">
            <div class="card-count">{{ dtCount || '0' }}</div>
            <div class="card-foot">{{ dtCount ? dtCount + ' 只个股今日上榜' : '今日暂无上榜' }}</div>
          </template>
          <template v-else>
            <div class="card-skeleton"><div class="sk-line" style="width:40%;height:28px" /><div class="sk-line" style="width:65%;height:12px" /></div>
          </template>
        </div>
      </div>
    </section>

    <!-- Spark 涨跌排行 -->
    <AnalysisPanel />

    <!-- 板块涨跌云图 -->
    <section class="section map-section">
      <div class="section-header">
        <h4>板块涨跌云图</h4>
        <div class="chart-legend">
          <span class="legend-item"><span class="dot dot-rise"></span>涨</span>
          <span class="legend-item"><span class="dot dot-fall"></span>跌</span>
          <span class="zoom-hint"><el-icon><Pointer /></el-icon> 点击板块查看详情</span>
        </div>
      </div>
      <div class="chart-container" ref="chartRef">
        <template v-if="homeLoaded && sectorData.length">
          <TreemapChart
            ref="treemapRef"
            :data="sectorData"
            @click="onSectorClick"
          />
        </template>
        <template v-else-if="homeLoaded && !sectorData.length">
          <EmptyState type="empty" title="暂无板块数据" inline />
        </template>
        <template v-else>
          <SkeletonLoader type="chart" height="600px" />
        </template>
      </div>
    </section>

    <!-- 热门股票 -->
    <section class="section quick-market">
      <div class="section-header">
        <h4>热门股票</h4>
        <router-link to="/stocks" class="view-all">查看所有股票 <el-icon><ArrowRight /></el-icon></router-link>
      </div>
      <template v-if="homeLoaded && hotStocks.length">
        <div class="stock-grid">
          <div
            v-for="stock in hotStocks"
            :key="stock.code"
            class="stock-card"
            :class="getChangeClass(stock.changePercent)"
            @click="$router.push(`/stock/${stock.code}`)"
          >
            <div class="stock-info">
              <div class="stock-name">{{ stock.name }}</div>
              <div class="stock-code">{{ stock.code }}</div>
            </div>
            <div class="stock-price">{{ formatPrice(stock.price) }}</div>
            <div class="stock-change">{{ formatPercent(stock.changePercent) }}</div>
          </div>
        </div>
      </template>
      <template v-else-if="homeLoaded && !hotStocks.length">
        <EmptyState type="empty" title="暂无热门股票数据" inline size="sm" />
      </template>
      <template v-else>
        <div class="stock-grid">
          <div v-for="i in 4" :key="i" class="stock-card skeleton-stock-card">
            <div class="stock-info">
              <div class="skeleton-line" style="width:80px;height:15px" />
              <div class="skeleton-line" style="width:60px;height:12px;margin-top:4px" />
            </div>
            <div style="margin:0 24px"><div class="skeleton-line" style="width:60px;height:18px" /></div>
            <div><div class="skeleton-line" style="width:50px;height:15px" /></div>
          </div>
        </div>
      </template>
    </section>

    <!-- 行业详情右侧面板 -->
    <SectorDetailPanel
      v-model="showSectorPanel"
      :sector-name="selectedSectorName"
      :sector-change="selectedSectorChange"
      :stocks="selectedSectorStocks"
      :kline-data="sectorKlineData"
      @stock-click="onStockClick"
      @go-detail="(name:string) => router.push({ path: `/sector/${encodeURIComponent(name)}` })"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, ArrowLeft, Setting, Pointer, Plus, Close, TrendCharts, DataAnalysis, Histogram, Aim } from '@element-plus/icons-vue'
import TreemapChart from '@/components/chart/TreemapChart.vue'
import SectorDetailPanel from '@/components/chart/SectorDetailPanel.vue'
import { getStockList, getIndustryTreemap, getSectorKline } from '@/api/market'
import { getIndexList } from '@/api/index'
import { getNorthboundLatest, getHotReason, getDragonTigerDaily, getIndustryCompare } from '@/api/signal'
import { formatPrice, formatPercent, formatPoints, getChangeClass } from '@/utils/format'
import { safeNum } from '@/composables/useApiRetry'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import AnalysisPanel from '@/components/chart/AnalysisPanel.vue'
import type {
  HotReason, IndustryTopItem, IndexCard, SectorNode, HomeStockCard,
  Northbound, HotReasonResponse, IndustryCompareResponse, DragonTigerDaily,
} from '@/types'

const router = useRouter()
const scrollRef = ref<HTMLElement>()
const scrollPos = ref(0)
const showIndexManager = ref(false)

/** 主页面数据加载完成标记 */
const homeLoaded = ref(false)

/** 各信号卡片加载状态（函数末尾批量赋值，避免逐项触发重渲染） */
const signalLoaded = reactive({ nb: false, hot: false, ind: false, dt: false })

/** 信号层数据 — 业务类型见 @/types */
const nbHgt = ref(0)
const nbSgt = ref(0)
const nbTotal = computed(() => Number((safeNum(nbHgt.value) + safeNum(nbSgt.value)).toFixed(2)))
const hotReasons = ref<HotReason[]>([])
const industryTop = ref<IndustryTopItem[]>([])
const dtCount = ref(0)

/** 工具函数：无论 API 返回数组还是 {records} 都提取为数组 */
function asArray(raw: any): any[] {
  if (!raw) return []
  if (Array.isArray(raw)) return raw
  if (Array.isArray(raw.records)) return raw.records
  if (Array.isArray(raw.data)) return raw.data
  return []
}

/** 并行加载信号层数据（各接口独立容错，无论成功失败都标记加载完成） */
async function loadSignalData() {
  const [nbRes, hotRes, indRes, dtRes] = await Promise.allSettled([
    getNorthboundLatest(1).catch(() => null),
    getHotReason().catch(() => null),
    getIndustryCompare().catch(() => null),
    getDragonTigerDaily().catch(() => null),
  ])
  // 北向资金 — 取最后一条（最新时间）
  if (nbRes.status === 'fulfilled' && nbRes.value) {
    const nbData = asArray(nbRes.value)
    if (nbData.length > 0) {
      const last = nbData[nbData.length - 1]
      nbHgt.value = safeNum(last.hgtYi) + safeNum(last.sgtYi)
    }
  }
  // 题材热点 — 适配数组或 {records} 格式
  if (hotRes.status === 'fulfilled' && hotRes.value) {
    hotReasons.value = asArray(hotRes.value)
  }
  // 行业排行 — 适配数组或 {records} 格式
  if (indRes.status === 'fulfilled' && indRes.value) {
    const all = asArray(indRes.value)
    if (all.length > 0) {
      try {
        industryTop.value = all
          .filter((a: any) => a && a.industryName)
          .sort((a: any, b: any) => (b.changePct || 0) - (a.changePct || 0))
          .slice(0, 5)
          .map((item: any) => ({ industryName: item.industryName || item.industry, changePct: safeNum(item.changePct) }))
      } catch { /* ignore */ }
    }
  }
  // 龙虎榜 — 适配多种返回格式
  if (dtRes.status === 'fulfilled' && dtRes.value) {
    const raw = dtRes.value as any
    if (raw && typeof raw.total === 'number') {
      dtCount.value = raw.total
    } else {
      dtCount.value = asArray(raw).length
    }
  }
  // 批量更新信号卡片加载状态（合并为一次渲染）
  signalLoaded.nb = true
  signalLoaded.hot = true
  signalLoaded.ind = true
  signalLoaded.dt = true
}

/** 大盘指数 — 从后端 API 实时加载 */
const allIndexData = ref<IndexCard[]>([])
// 中国大盘指数默认展示核心4个，其他可手动添加
const DEFAULT_INDICES_CODES = [
  '000001',  // 上证指数
  '399001',  // 深证成指
  '399006',  // 创业板指
  '000688',  // 科创50
]

const visibleIndices = ref<IndexCard[]>([])

const availableIndices = computed(() =>
  allIndexData.value.filter(i => !visibleIndices.value.find(v => v.code === i.code))
)

/** 从后端加载指数数据 */
async function loadIndices() {
  try {
    const data = await getIndexList()
    if (Array.isArray(data) && data.length > 0) {
      allIndexData.value = data.map((item) => ({
        code: item.indexCode,
        name: item.indexName,
        price: Number(item.closePoint) || 0,
        changePercent: Number(item.changePct ?? item.changePercent) || 0,
        changePoints: Number(item.closePoint) ? (Number(item.closePoint) * Number(item.changePct ?? item.changePercent) / 100) : 0,
        isCustom: !DEFAULT_INDICES_CODES.includes(item.indexCode),
      }))
      const defaults = allIndexData.value.filter(d => DEFAULT_INDICES_CODES.includes(d.code))
      visibleIndices.value = defaults.length ? defaults : allIndexData.value.slice(0, 4)
    }
  } catch (_e) {
    console.warn('[Home] loadIndices failed:', _e)
  }
}

const CARD_GAP = 12
const CARD_WIDTH = 188

// Scroll state computed from track width
const trackWidth = computed(() =>
  visibleIndices.value.length * (CARD_WIDTH + CARD_GAP) - CARD_GAP
)

const scrollAtStart = computed(() => scrollPos.value <= 0)
const scrollAtEnd = computed(() => {
  const viewport = scrollRef.value?.clientWidth || 800
  return scrollPos.value >= trackWidth.value - viewport
})

function scrollIndices(dir: number) {
  const step = CARD_WIDTH + CARD_GAP
  const viewport = scrollRef.value?.clientWidth || 800
  const maxScroll = Math.max(0, trackWidth.value - viewport)
  scrollPos.value = Math.max(0, Math.min(maxScroll, scrollPos.value + dir * step * 2))
}

function addIndex(idx: IndexCard) {
  if (visibleIndices.value.length >= 15) return
  visibleIndices.value.push({ ...idx })
}

function removeIndex(i: number) {
  visibleIndices.value.splice(i, 1)
}

function goToIndex(code: string) {
  // 优先跳转到指数详情（如果路由已配置），否则跳转到股票详情
  router.push(`/index/${code}`)
}

/** 板块云图数据 */
const sectorData = ref<SectorNode[]>([])

/** 行业成分股映射表（行业名 → 股票列表，供详情面板使用） */
const sectorStockMap = ref<Map<string, { stockCode: string; stockName: string; changePercent: number }[]>>(new Map())

/** 行业详情面板状态 */
const showSectorPanel = ref(false)
const selectedSectorName = ref('')
const selectedSectorChange = ref(0)
const selectedSectorStocks = ref<{ stockCode: string; stockName: string; changePercent: number }[]>([])
const sectorKlineData = ref<{ date: string; open: number; high: number; low: number; close: number; volume: number }[]>([])

/** 加载行业 K 线数据 */
async function loadSectorKline(industry: string) {
  try {
    const data = await getSectorKline(industry, 60)
    if (Array.isArray(data) && data.length > 0) {
      sectorKlineData.value = data.map((d: any) => {
        const open = Number(d.openPrice) || 0
        const close = Number(d.closePrice) || 0
        const low = Number(d.lowPrice) || 0
        const high = Number(d.highPrice) || 0
        // 裁剪极端影线（MAX(high)/MIN(low) 跨价格层级）
        const bodyLen = Math.abs(close - open)
        const shadowLen = high - low
        let cappedHigh = high
        let cappedLow = low
        if (bodyLen > 0.01 && shadowLen > bodyLen * 5) {
          const mid = (open + close) / 2
          const maxShadow = bodyLen * 3
          cappedHigh = Math.min(high, mid + maxShadow)
          cappedLow = Math.max(low, mid - maxShadow)
        }
        return {
          date: d.tradeDate || '',
          open,
          high: cappedHigh,
          low: cappedLow,
          close,
          volume: Number(d.volume) || 0,
        }
      })
    } else {
      sectorKlineData.value = []
    }
  } catch {
    sectorKlineData.value = []
  }
}

/** 热门股票网格 */
const hotStocks = ref<HomeStockCard[]>([])

/** 加载热门股票（首页前12只） */
async function loadHotStocks() {
  try {
    const res = await getStockList({ page: 1, size: 12 })
    const list = res?.records?.length ? res.records : (Array.isArray(res) ? res : [])
    if (list.length) {
      hotStocks.value = list.map((r: any) => ({
        code: r.stockCode || r.code,
        name: r.stockName || r.name,
        price: r.price || r.mcapYi || 0,
        changePercent: r.changePct || r.changePercent || 0,
      }))
    }
  } catch (_e) { console.warn('[Home] loadHotStocks failed:', _e) }
}

/** 市场整体涨跌家数 — 从 stock_basic 实时价格统计 */
const marketStats = ref({ total: 0, up: 0, down: 0, flat: 0 })
async function loadMarketStats() {
  try {
    // 获取全市场涨跌统计（从 stock_basic 全量数据计算）
    const res = await getStockList({ page: 1, size: 6000 }).catch(() => null)
    const list = res?.records?.length ? res.records : (Array.isArray(res) ? res : [])
    if (list.length > 0) {
      let up = 0, down = 0, flat = 0
      for (const s of list) {
        const pct = Number(s.changePercent || s.changePct || 0)
        if (pct > 0) up++
        else if (pct < 0) down++
        else flat++
      }
      const total = res?.total || list.length
      marketStats.value = { total, up, down, flat }
    }
  } catch { /* 非关键功能，静默失败 */ }
}

/** 加载板块云图数据（双层钻取：一级行业 → 成分股） */
async function loadSectorData() {
  try {
    // 读取 industry_treemap API — 返回 [{industryName, mcapYi, changePercent, stocks(count)}]
    let rawData: any[] | null = null
    try {
      const newApi = getIndustryTreemap()
      const timeout = new Promise<null>(resolve => setTimeout(() => resolve(null), 8000))
      const res = await Promise.race([newApi, timeout])
      if (res) {
        const arr = Array.isArray(res) ? res : (res as any)?.records || []
        if (arr.length) rawData = arr
      }
    } catch { /* fallback */ }
    if (!rawData) {
      // Fallback: 从 industry_compare 数据构建
      const indData = await getIndustryCompare().catch(() => null)
      const arr = indData ? (Array.isArray(indData) ? indData : (indData as any)?.records || []) : []
      if (arr.length) {
        sectorData.value = arr
          .filter((a: any) => a && a.industryName)
          .map((a: any) => ({
            name: a.industryName || '',
            value: Number(a.stockCount) || 0,
            changePercent: Number(a.changePct) || 0,
          }))
          .sort((a: any, b: any) => b.value - a.value)
      }
    } else {
      // industry_treemap 格式: {industryName, mcapYi, changePercent, stocks(数量)}
      sectorData.value = rawData
        .filter((r: any) => r && r.industryName)
        .map((r: any) => ({
          name: r.industryName || '',
          value: Number(r.stocks) || Number(r.stockCount) || Number(r.mcapYi) || 0,
          changePercent: Number(r.changePct ?? r.changePercent) || 0,
        }))
        .sort((a: any, b: any) => b.value - a.value)
    }
    // 云图数据已加载，如果行业排行卡片为空则补充
    if (industryTop.value.length === 0 && sectorData.value.length > 0) {
      const top3 = sectorData.value
        .slice()
        .sort((a, b) => (b.changePercent || 0) - (a.changePercent || 0))
        .slice(0, 3)
        .map((item) => ({ industryName: item.name, changePct: item.changePercent || 0 }))
      if (top3.length > 0) industryTop.value = top3
    }
    return
  } catch (_e) { console.warn('[Home] loadSectorData failed:', _e) }
}

function onSectorClick(data: { name?: string }) {
  const name = data?.name || ''
  if (!name || !sectorData.value.find(s => s.name === name)) return
  // 弹出右侧详情面板
  selectedSectorName.value = name
  selectedSectorChange.value = sectorData.value.find(s => s.name === name)?.changePercent || 0
  selectedSectorStocks.value = sectorStockMap.value.get(name) || []
  sectorKlineData.value = []
  showSectorPanel.value = true
  // 异步加载 K 线
  loadSectorKline(name)
}

function onStockClick(code: string) {
  router.push(`/stock/${code}`)
}

onMounted(async () => {
  await Promise.allSettled([
    loadIndices(),
    loadHotStocks(),
    loadSectorData(),
    loadMarketStats(),
    loadSignalData(),
  ])
  homeLoaded.value = true
})
</script>

<style scoped lang="scss">
.home-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: $spacing-lg;
}

.section { margin-bottom: $spacing-xl; }

/* ======== 市场概览 ======== */
.market-overview { margin-bottom: $spacing-lg; }
.stats-bar {
  display: flex;
  gap: $spacing-lg;
  background: $canvas-parchment;
  border-radius: $rounded-lg;
  padding: $spacing-md $spacing-lg;
}
.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  .stat-label { font-size: 12px; color: $ink-muted-48; }
  .stat-value { font-family: $font-display; font-size: 20px; font-weight: 700; }
  .stat-value.rise { color: $rise; }
  .stat-value.fall { color: $fall; }
  .stat-value.flat { color: $flat; }
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-md;
  h4 { margin: 0; }

  .view-all {
    font-size: 14px;
    color: $primary;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .chart-legend {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    .legend-item { display: flex; align-items: center; gap: 6px; font-size: 13px; color: $ink-muted-48; }
    .dot { width: 8px; height: 8px; border-radius: 50%;
      &.dot-rise { background: $rise; }
      &.dot-fall { background: $fall; }
    }
    .zoom-hint { display: flex; align-items: center; gap: 4px; font-size: 12px; color: $ink-muted-48; }
  }

  .section-actions {
    display: flex;
    align-items: center;
    gap: $spacing-md;
  }
}

/* ======== 大盘指数 - 东方财富风格轮播 ======== */
.indices-carousel {
  display: flex;
  align-items: center;
  gap: 6px;
}

.scroll-arrow {
  flex-shrink: 0;
  width: 32px;
  height: 64px;
  border: 1px solid $divider-soft;
  background: $canvas;
  border-radius: $rounded-sm;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: $ink-muted-48;
  transition: all 0.15s;

  &:hover:not(:disabled) {
    border-color: $primary;
    color: $primary;
  }

  &:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }
}

.indices-viewport {
  flex: 1;
  overflow: hidden;
  border-radius: $rounded-lg;
  background: $canvas-parchment;
  padding: 6px 0;
}

.indices-track {
  display: flex;
  gap: 12px;
  padding: 0 8px;
  transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  will-change: transform;
}

.index-card {
  flex-shrink: 0;
  width: 188px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: $rounded-md;
  cursor: pointer;
  transition: all 0.15s;
  position: relative;

  &:hover {
    box-shadow: $shadow-elevated;
    transform: translateY(-1px);
  }

  .card-left {
    .index-name { font-size: 13px; font-weight: 500; margin-bottom: 4px; }
    .index-price { font-family: $font-display; font-size: 18px; font-weight: 600; }
  }

  .card-right {
    text-align: right;
    .change-pct { font-size: 16px; font-weight: 600; margin-bottom: 2px; }
    .change-points { font-size: 12px; opacity: 0.7; }
  }

  .custom-dot {
    position: absolute;
    top: 4px;
    right: 4px;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: $primary;
    opacity: 0.4;
  }

  &.rise { color: $rise; background: linear-gradient(135deg, $rise-bg, $canvas); }
  &.fall { color: $fall; background: linear-gradient(135deg, $fall-bg, $canvas); }
  &.flat { color: $flat; background: $canvas-parchment; }
}

/* ======== 指数管理 ======== */
.manager-body {
  .manager-desc { margin-bottom: $spacing-md; }

  .list-title { font-size: 13px; font-weight: 600; color: $ink-muted-48; margin-bottom: $spacing-xs; }

  .index-chips, .current-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: $spacing-lg;
  }

  .chip {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border: 1px solid $hairline;
    border-radius: $rounded-pill;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.15s;
    &:hover { border-color: $primary; color: $primary; }
    .chip-code { color: $ink-muted-48; }
    .add-icon { font-size: 14px; color: $primary; }
  }

  .chip-added {
    background: $primary;
    border-color: $primary;
    color: white;
    .chip-code { color: rgba(255,255,255,0.7); }
    .remove-icon { font-size: 14px; cursor: pointer; opacity: 0.7; &:hover { opacity: 1; } }
  }
}

/* ======== 云图 ======== */
.chart-container {
  background: $canvas-parchment;
  border-radius: $rounded-lg;
  padding: $spacing-xs;
  height: 750px;
}

/* ======== 热门股票 ======== */
.stock-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-md;
}

.stock-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: $canvas-parchment;
  border-radius: $rounded-lg;
  padding: $spacing-md $spacing-lg;
  cursor: pointer;
  transition: all 0.2s;

  &:hover { transform: translateY(-2px); box-shadow: $shadow-elevated; }

  .stock-info { flex: 1; }
  .stock-name { font-size: 15px; font-weight: 600; }
  .stock-code { font-size: 12px; color: $ink-muted-48; margin-top: 2px; }

  .stock-price {
    font-family: $font-display;
    font-size: 18px;
    font-weight: 600;
    margin: 0 $spacing-lg;
  }

  .stock-change { font-size: 15px; font-weight: 600; min-width: 80px; text-align: right; }

  &.rise { .stock-price, .stock-change { color: $rise; } }
  &.fall { .stock-price, .stock-change { color: $fall; } }
}

/* 信号层快捷卡片 */
.signal-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.signal-card {
  cursor: pointer; border-radius: 12px; padding: 18px;
  display: flex; flex-direction: column; gap: 14px;
  background: $canvas-parchment;
  border: 1px solid $divider-soft;
  transition: all 0.2s ease;
}
.signal-card:hover {
  border-color: rgba(255,255,255,0.12);
  box-shadow: 0 6px 20px rgba(0,0,0,0.18);
  transform: translateY(-1px);
}
.signal-card .card-header {
  display: flex; align-items: center; gap: 12px;
}
.signal-card .card-icon-wrap {
  width: 38px; height: 38px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.signal-card .card-meta { flex: 1; min-width: 0; }
.signal-card .card-title {
  font-size: 14px; font-weight: 600; color: $ink;
  line-height: 1.3;
}
.signal-card .card-subtitle {
  font-size: 11px; color: $ink-muted-48; margin-top: 1px;
}
.signal-card .card-value {
  font-size: 28px; font-weight: 700; font-family: $font-display;
}
.signal-card .card-value small {
  font-size: 12px; font-weight: 400; opacity: 0.45; margin-left: 3px;
}
.signal-card .card-foot {
  font-size: 11px; color: $ink-muted-48;
}
.signal-card .card-count {
  font-size: 28px; font-weight: 700; font-family: $font-display; color: $ink;
}
.signal-card .card-empty {
  font-size: 13px; color: $ink-muted-48; padding: 8px 0;
}
.signal-card .card-tags {
  display: flex; flex-wrap: wrap; gap: 6px;
}
.signal-card .hot-tag {
  display: inline-block; padding: 3px 10px; border-radius: 6px;
  font-size: 12px; font-weight: 500;
  background: rgba(239,83,80,0.1); color: #ef5350;
  border: 1px solid rgba(239,83,80,0.15);
  cursor: pointer; transition: all 0.12s;
  &:hover { background: rgba(239,83,80,0.18); }
}
.signal-card .card-rank-list {
  display: flex; flex-direction: column; gap: 5px;
}
.signal-card .rank-row {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 13px; padding: 3px 8px; border-radius: 6px;
  background: rgba(255,255,255,0.03);
}
.signal-card .rank-row .rank-name {
  color: $ink-muted-48; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-right: 8px;
}
.signal-card .card-skeleton {
  display: flex; flex-direction: column; gap: 8px;
}
.signal-card .sk-line {
  border-radius: 4px; background: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%);
  background-size: 200% 100%; animation: sk-shimmer 1.5s infinite;
}
@keyframes sk-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ======== 骨架屏 ======== */
.skeleton-bar .stat-item { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 4px 0; }
.skeleton-index-card {
  flex-shrink: 0; width: 188px; display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; border-radius: 8px; background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.04);
}
.skeleton-stock-card {
  display: flex; align-items: center; justify-content: space-between;
  background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
  border-radius: 12px; padding: 16px 24px;
}
.card-value-skeleton { margin-bottom: 4px; }
.card-empty { font-size: 13px; color: rgba(255,255,255,0.25); padding: 6px 0; }

/* 移动端点击优化 */
@media (hover: none) and (pointer: coarse) {
  .signal-card {
    -webkit-tap-highlight-color: transparent;
    touch-action: manipulation;
  }
}
</style>
