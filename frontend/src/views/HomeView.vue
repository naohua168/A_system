<template>
  <div class="home-view">
    <!-- ─── 复盘日期选择器 ─── -->
    <div class="review-bar">
      <ReviewDatePicker @change="onDateChange" />
    </div>
    <!-- ─── 市场情绪横幅 ─── -->
    <section class="section sentiment-banner">
      <template v-if="!homeLoaded">
        <div class="skeleton-sentiment">
          <div v-for="i in 5" :key="i" class="sk-line" style="width:60px;height:36px" />
        </div>
      </template>
      <template v-else>
        <div class="sentiment-inner">
          <div class="sentiment-stat">
            <span class="sent-label">上涨</span>
            <span class="sent-value rise">{{ marketStats.up }}</span>
          </div>
          <div class="sentiment-stat">
            <span class="sent-label">下跌</span>
            <span class="sent-value fall">{{ marketStats.down }}</span>
          </div>
          <div class="sentiment-stat">
            <span class="sent-label">平盘</span>
            <span class="sent-value flat">{{ marketStats.flat }}</span>
          </div>
          <!-- 涨跌比例条 -->
          <div class="ratio-bar-wrap">
            <div class="ratio-bar">
              <div
                class="ratio-fill rise-bar"
                :style="{ flex: marketStats.up || 1 }"
              ></div>
              <div
                v-if="marketStats.flat"
                class="ratio-fill flat-bar"
                :style="{ flex: marketStats.flat || 1 }"
              ></div>
              <div
                class="ratio-fill fall-bar"
                :style="{ flex: marketStats.down || 1 }"
              ></div>
            </div>
            <div class="ratio-labels">
              <span class="ratio-pct rise">{{ calcPct(marketStats.up) }}%</span>
              <span class="ratio-pct flat">{{ calcPct(marketStats.flat) }}%</span>
              <span class="ratio-pct fall">{{ calcPct(marketStats.down) }}%</span>
            </div>
          </div>
          <div class="sentiment-divider"></div>
          <div class="sentiment-extra">
            <div class="extra-item">
              <span class="sent-label">涨跌比</span>
              <span class="sent-value accent">{{ calcRatio(marketStats.up, marketStats.down) }}</span>
            </div>
            <div class="extra-item">
              <span class="sent-label">总股票</span>
              <span class="sent-value muted">{{ marketStats.total }}</span>
            </div>
          </div>
        </div>
      </template>
    </section>

    <!-- ─── 大盘指数 ─── -->
    <section class="section">
      <div class="section-header">
        <h4>大盘指数</h4>
        <div class="section-actions">
          <el-button v-if="!homeLoaded" disabled text size="small"><el-icon><Setting /></el-icon> 管理指数</el-button>
          <el-button v-else text type="primary" size="small" @click="showIndexManager = true">
            <el-icon><Setting /></el-icon> 管理指数
          </el-button>
        </div>
      </div>
      <template v-if="!homeLoaded">
        <div class="indices-carousel">
          <div class="indices-viewport"><div class="indices-track skeleton-indices">
            <div v-for="i in 4" :key="i" class="skeleton-index-card">
              <div><div class="sk-line" style="width:60px;height:14px" /><div class="sk-line" style="width:80px;height:22px;margin-top:6px" /></div>
              <div style="text-align:right"><div class="sk-line" style="width:50px;height:16px;margin-left:auto" /></div>
            </div>
          </div></div>
        </div>
      </template>
      <template v-else>
      <div class="indices-carousel">
        <button class="scroll-arrow left" @click="scrollIndices(-1)" :disabled="scrollAtStart">
          <el-icon><ArrowLeft /></el-icon>
        </button>
        <div class="indices-viewport" ref="scrollRef">
          <div class="indices-track" :style="{ transform: `translateX(-${scrollPos}px)` }">
            <div v-for="(idx, i) in visibleIndices" :key="idx.code" class="index-card" :class="getChangeClass(idx.changePercent)" @click="goToIndex(idx.code)">
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

    <!-- ─── 信号卡片（加强版） ─── -->
    <section class="section">
      <div class="signal-grid">
        <!-- 北向资金 -->
        <div class="signal-card" @click="$router.push('/northbound')">
          <div class="card-header">
            <div class="card-icon-wrap" style="background:rgba(41,151,255,0.12);color:#2997ff">
              <el-icon :size="20"><TrendCharts /></el-icon>
            </div>
            <div class="card-meta">
              <div class="card-title">北向资金</div>
              <div class="card-subtitle">沪/深股通</div>
            </div>
          </div>
          <template v-if="signalLoaded.nb">
            <div class="card-big-row">
              <span class="card-big-num" :class="nbTotal >= 0 ? 'text-rise' : 'text-fall'">
                {{ nbTotal >= 0 ? '+' : '' }}{{ nbTotal }}<small>亿</small>
              </span>
              <span class="card-badge" :class="nbTotal >= 0 ? 'badge-rise' : 'badge-fall'">
                {{ nbTotal >= 0 ? '净流入' : '净流出' }}
              </span>
            </div>
            <div class="card-detail-row">
              <span class="detail-label text-rise">沪股通 +{{ safeNum(nbHgt) }}亿</span>
              <span class="detail-sep">|</span>
              <span class="detail-label text-fall">深股通 {{ safeNum(nbSgtDelta) >= 0 ? '+' : '' }}{{ safeNum(nbSgtDelta) }}亿</span>
            </div>
          </template>
          <template v-else>
            <div class="card-skeleton"><div class="sk-line" style="width:60%;height:24px" /><div class="sk-line" style="width:80%;height:12px;margin-top:6px" /></div>
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
              <div class="card-subtitle">{{ hotReasons.length }} 只个股强势</div>
            </div>
          </div>
          <template v-if="signalLoaded.hot">
            <div class="card-tags" v-if="hotReasons.length">
              <span v-for="r in hotReasons.slice(0,4)" :key="r.stockCode" class="hot-tag"
                @click.stop="$router.push(`/stock/${r.stockCode}`)">{{ r.stockName }}</span>
            </div>
            <div v-else class="card-empty">暂无强势个股</div>
          </template>
          <template v-else>
            <div class="card-skeleton"><div class="sk-line" style="width:85%;height:22px" /><div class="sk-line" style="width:50%;height:12px;margin-top:6px" /></div>
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
              <div class="card-subtitle">涨幅 TOP5</div>
            </div>
          </div>
          <template v-if="signalLoaded.ind">
            <div class="card-rank-list" v-if="industryTop.length">
              <div v-for="(ind, idx) in industryTop.slice(0,5)" :key="ind.industryName" class="rank-row">
                <span class="rank-num">{{ idx + 1 }}</span>
                <span class="rank-name">{{ ind.industryName }}</span>
                <span :class="(ind.changePct || 0) >= 0 ? 'text-rise' : 'text-fall'">
                  {{ (ind.changePct || 0) >= 0 ? '+' : '' }}{{ safeNum(ind.changePct, 2) }}%
                </span>
              </div>
            </div>
            <div v-else class="card-empty">暂无数据</div>
          </template>
          <template v-else>
            <div class="card-skeleton"><div class="sk-line" style="width:90%;height:18px" /><div class="sk-line" style="width:70%;height:12px;margin-top:6px" /></div>
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
              <div class="card-subtitle">{{ dtCount }} 只个股上榜</div>
            </div>
          </div>
          <template v-if="signalLoaded.dt">
            <div class="card-big-row">
              <span class="card-big-num">{{ dtCount }}</span>
              <span class="card-badge badge-hint">今日上榜</span>
            </div>
            <div class="card-detail-row" v-if="dtTop3.length">
              <span v-for="(item, i) in dtTop3" :key="i" class="detail-chip" @click.stop="$router.push(`/stock/${item.stockCode}`)">
                {{ item.stockName }}
              </span>
            </div>
            <div v-else class="card-empty">暂无上榜个股</div>
          </template>
          <template v-else>
            <div class="card-skeleton"><div class="sk-line" style="width:45%;height:24px" /><div class="sk-line" style="width:70%;height:12px;margin-top:6px" /></div>
          </template>
        </div>
      </div>
    </section>

    <!-- ─── 热门股票横向滚动 ─── -->
    <section class="section">
      <div class="section-header">
        <h4>热门股票</h4>
        <router-link to="/stocks" class="view-all">查看全部 <el-icon><ArrowRight /></el-icon></router-link>
      </div>
      <template v-if="homeLoaded && hotStocks.length">
        <div class="hot-scroll-wrap">
          <div class="hot-scroll-track">
            <div v-for="stock in hotStocks" :key="stock.code" class="hot-mini-card" :class="getChangeClass(stock.changePercent)" @click="$router.push(`/stock/${stock.code}`)">
              <div class="mini-name">{{ stock.name }}</div>
              <div class="mini-code">{{ stock.code }}</div>
              <div class="mini-price">{{ formatPrice(stock.price) }}</div>
              <div class="mini-change" :class="stock.changePercent >= 0 ? 'text-rise' : 'text-fall'">
                {{ formatPercent(stock.changePercent) }}
              </div>
            </div>
          </div>
        </div>
      </template>
      <template v-else-if="homeLoaded && !hotStocks.length">
        <EmptyState type="empty" title="暂无数据" inline size="sm" />
      </template>
      <template v-else>
        <div class="hot-scroll-wrap">
          <div class="hot-scroll-track skeleton-scroll">
            <div v-for="i in 8" :key="i" class="skeleton-mini-card">
              <div class="sk-line" style="width:70px;height:14px" />
              <div class="sk-line" style="width:50px;height:11px;margin-top:4px" />
              <div class="sk-line" style="width:60px;height:16px;margin-top:6px" />
            </div>
          </div>
        </div>
      </template>
    </section>

    <!-- ─── 板块涨跌云图（全宽） ─── -->
    <section class="section map-section">
      <div class="section-header">
        <h4>板块涨跌云图</h4>
        <div class="chart-legend">
          <span class="legend-item"><span class="dot dot-rise"></span>涨</span>
          <span class="legend-item"><span class="dot dot-fall"></span>跌</span>
          <span class="zoom-hint"><el-icon><Pointer /></el-icon> 点击查看成分</span>
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
          <SkeletonLoader type="chart" height="520px" />
        </template>
      </div>
    </section>

    <!-- ─── 涨跌排行 ─── -->
    <AnalysisPanel />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, ArrowLeft, Setting, Pointer, Plus, Close, TrendCharts, DataAnalysis, Histogram, Aim } from '@element-plus/icons-vue'
import TreemapChart from '@/components/chart/TreemapChart.vue'
import { getStockList, getIndustryTreemap } from '@/api/market'
import { getIndexList, getHistoryIndexList } from '@/api/index'
import { getNorthboundLatest, getHotReason, getDragonTigerDaily, getIndustryCompare,
         getHistoryIndustryCompare, getHistoryNorthbound, getHistoryHotReason, getHistoryDragonTiger } from '@/api/signal'
import { formatPrice, formatPercent, formatPoints, getChangeClass } from '@/utils/format'
import { useAutoRefresh } from '@/composables/useAutoRefresh'
import { useMarketWebSocket } from '@/composables/useMarketWebSocket'
import { safeNum } from '@/composables/useApiRetry'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ReviewDatePicker from '@/components/common/ReviewDatePicker.vue'
import AnalysisPanel from '@/components/chart/AnalysisPanel.vue'
import type {
  HotReason, IndustryTopItem, IndexCard, SectorNode, HomeStockCard,
  Northbound, HotReasonResponse, IndustryCompareResponse, DragonTigerDaily,
} from '@/types'

const router = useRouter()
const scrollRef = ref<HTMLElement>()
const scrollPos = ref(0)
const showIndexManager = ref(false)
const chartRef = ref<HTMLElement>()
const reviewDate = ref('')
const treemapRef = ref()

/** 主页面数据加载完成标记 */
const homeLoaded = ref(false)

/** 各信号卡片加载状态 */
const signalLoaded = reactive({ nb: false, hot: false, ind: false, dt: false })

/** 信号层数据 */
const nbHgt = ref(0)
const nbSgtDelta = ref(0)
const nbTotal = computed(() => Number((safeNum(nbHgt.value) + safeNum(nbSgtDelta.value)).toFixed(2)))
const hotReasons = ref<HotReason[]>([])
const industryTop = ref<IndustryTopItem[]>([])
const dtCount = ref(0)
const dtTop3 = ref<{ stockCode: string; stockName: string }[]>([])

/** 通用数组提取 */
function asArray(raw: any): any[] {
  if (!raw) return []
  if (Array.isArray(raw)) return raw
  if (Array.isArray(raw.records)) return raw.records
  if (Array.isArray(raw.data)) return raw.data
  return []
}

/** 复盘日期切换 */
function onDateChange(date: string) {
  reviewDate.value = date
  loadSignalData()
  loadIndices()
  loadMarketStats()
  loadHotStocks()
  loadSectorData()
}

/** 并行加载信号层数据（复盘模式走历史API） */
async function loadSignalData() {
  const isReview = !!reviewDate.value
  const [nbRes, hotRes, indRes, dtRes] = await Promise.allSettled([
    isReview ? getHistoryNorthbound(reviewDate.value) : getNorthboundLatest(1).catch(() => null),
    isReview ? getHistoryHotReason(reviewDate.value) : getHotReason().catch(() => null),
    isReview ? getHistoryIndustryCompare(reviewDate.value) : getIndustryCompare().catch(() => null),
    isReview ? getHistoryDragonTiger(reviewDate.value) : getDragonTigerDaily().catch(() => null),
  ])
  // 北向资金 — 取最后一条
  if (nbRes.status === 'fulfilled' && nbRes.value) {
    const nbData = asArray(nbRes.value)
    if (nbData.length > 0) {
      const last = nbData[nbData.length - 1]
      nbHgt.value = safeNum(last.hgtYi)
      nbSgtDelta.value = safeNum(last.sgtYi)
    }
  }
  // 题材热点
  if (hotRes.status === 'fulfilled' && hotRes.value) {
    hotReasons.value = asArray(hotRes.value)
  }
  // 行业排行
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
  // 龙虎榜
  if (dtRes.status === 'fulfilled' && dtRes.value) {
    const raw = dtRes.value as any
    if (raw && typeof raw.total === 'number') {
      dtCount.value = raw.total
      const list = asArray(raw)
      dtTop3.value = list.slice(0, 3).map((r: any) => ({ stockCode: r.stockCode || r.code, stockName: r.stockName || r.name }))
    } else {
      const list = asArray(raw)
      dtCount.value = list.length
      dtTop3.value = list.slice(0, 3).map((r: any) => ({ stockCode: r.stockCode || r.code, stockName: r.stockName || r.name }))
    }
  }
  signalLoaded.nb = true
  signalLoaded.hot = true
  signalLoaded.ind = true
  signalLoaded.dt = true
}

/** 大盘指数 */
const allIndexData = ref<IndexCard[]>([])
const DEFAULT_INDICES_CODES = ['000001','399001','399006','000688']
const visibleIndices = ref<IndexCard[]>([])
const availableIndices = computed(() =>
  allIndexData.value.filter(i => !visibleIndices.value.find(v => v.code === i.code))
)

/** 将后端指数数据映射为前端卡片格式 */
function toIndexCard(item: any): IndexCard {
  const price = Number(item.closePoint) || 0
  const changePct = Number(item.changePct ?? item.changePercent) || 0
  // 涨跌点数 = 当前价 - 昨收盘；昨收盘 = 当前价 / (1 + 涨跌幅%)
  const preClose = price / (1 + changePct / 100)
  const changePoints = price - preClose
  return {
    code: item.indexCode,
    name: item.indexName,
    price,
    changePercent: changePct,
    changePoints,
    isCustom: !DEFAULT_INDICES_CODES.includes(item.indexCode),
  }
}

async function loadIndices() {
  try {
    const data = reviewDate.value
      ? await getHistoryIndexList(reviewDate.value)
      : await getIndexList()
    if (Array.isArray(data) && data.length > 0) {
      allIndexData.value = data.map(toIndexCard)
      const defaults = allIndexData.value.filter(d => DEFAULT_INDICES_CODES.includes(d.code))
      visibleIndices.value = defaults.length ? defaults : allIndexData.value.slice(0, 4)
    }
  } catch { /* ignore */ }
}

const CARD_GAP = 12, CARD_WIDTH = 188
const trackWidth = computed(() => visibleIndices.value.length * (CARD_WIDTH + CARD_GAP) - CARD_GAP)
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

function addIndex(idx: IndexCard) { if (visibleIndices.value.length < 15) visibleIndices.value.push({ ...idx }) }
function removeIndex(i: number) { visibleIndices.value.splice(i, 1) }
function goToIndex(code: string) { router.push(`/index/${code}`) }

/** 板块云图 */
const sectorData = ref<SectorNode[]>([])
/** 热门股票 — 取涨跌幅绝对值最高的前10只 */
const hotStocks = ref<HomeStockCard[]>([])
async function loadHotStocks() {
  try {
    const res = await getStockList({ page: 1, size: 200 }).catch(() => null)
    const list = res?.records?.length ? res.records : (Array.isArray(res) ? res : [])
    if (list.length) {
      // 过滤有涨跌幅的，按绝对值排序取前10
      const withChange = list
        .filter((r: any) => {
          const pct = Number(r.changePct || r.changePercent || 0)
          return Math.abs(pct) > 0.01
        })
        .sort((a: any, b: any) => {
          const pa = Math.abs(Number(a.changePct || a.changePercent || 0))
          const pb = Math.abs(Number(b.changePct || b.changePercent || 0))
          return pb - pa
        })
        .slice(0, 10)
      hotStocks.value = withChange.map((r: any) => ({
        code: r.stockCode || r.code,
        name: r.stockName || r.name,
        price: r.price || 0,
        changePercent: Number(r.changePct || r.changePercent || 0),
      }))
    }
  } catch { /* ignore */ }
}

/** 市场统计 */
const marketStats = ref({ total: 0, up: 0, down: 0, flat: 0 })
async function loadMarketStats() {
  try {
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
  } catch { /* ignore */ }
}

/** 工具函数 */
function calcPct(n: number): string {
  const total = marketStats.value.total || 1
  return ((n / total) * 100).toFixed(1)
}
function calcRatio(a: number, b: number): string {
  if (b === 0) return a > 0 ? '∞' : '-'
  return (a / b).toFixed(2) + ':1'
}

/** 板块云图数据 */
async function loadSectorData() {
  try {
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
      const indData = await getIndustryCompare().catch(() => null)
      const arr = indData ? (Array.isArray(indData) ? indData : (indData as any)?.records || []) : []
      if (arr.length) {
        sectorData.value = arr.filter((a: any) => a && a.industryName)
          .map((a: any) => ({ name: a.industryName || '', value: Number(a.stockCount) || 0, changePercent: Number(a.changePct) || 0 }))
          .sort((a: any, b: any) => b.value - a.value)
      }
    } else {
      // industry_treemap: {industryName, changePct, stockCount, mcapYi} — 实时更新
      sectorData.value = rawData.filter((r: any) => r && r.industryName)
        .map((r: any) => ({ name: r.industryName || '', value: Number(r.stocks) || Number(r.stockCount) || Number(r.mcapYi) || 0, changePercent: Number(r.changePct ?? r.changePercent) || 0 }))
        .sort((a: any, b: any) => b.value - a.value)
    }
    if (industryTop.value.length === 0 && sectorData.value.length > 0) {
      const top3 = sectorData.value.slice().sort((a, b) => (b.changePercent || 0) - (a.changePercent || 0)).slice(0, 3)
        .map(item => ({ industryName: item.name, changePct: item.changePercent || 0 }))
      if (top3.length > 0) industryTop.value = top3
    }
  } catch { /* ignore */ }
}

function onSectorClick(_data: { name?: string }) {
  // 行业详情面板已移除（企业防火墙屏蔽成分股API）
}

onMounted(async () => {
  await Promise.allSettled([loadIndices(), loadHotStocks(), loadSectorData(), loadMarketStats(), loadSignalData()])
  homeLoaded.value = true
})

// WebSocket 实时推送（替代轮询的主力）
const ws = useMarketWebSocket()
ws.subscribe('indices', (data: any) => {
  if (reviewDate.value) return  // 复盘模式不覆盖历史数据
  if (Array.isArray(data) && data.length > 0) {
    allIndexData.value = data.map(toIndexCard)
    const defaults = allIndexData.value.filter(d => DEFAULT_INDICES_CODES.includes(d.code))
    if (defaults.length) visibleIndices.value = defaults
  }
})
ws.subscribe('signals', (data: any) => {
  if (reviewDate.value) return  // 复盘模式不覆盖历史数据
  if (!data) return
  // 北向资金
  if (data.northbound?.length) {
    const last = data.northbound[data.northbound.length - 1]
    nbHgt.value = safeNum(last.hgtYi)
    nbSgtDelta.value = safeNum(last.sgtYi)
  }
  // 题材热点
  if (data.hotReason?.length) hotReasons.value = data.hotReason
  // 行业排行
  if (data.industryCompare?.length) {
    try {
      industryTop.value = data.industryCompare
        .filter((a: any) => a && a.industryName)
        .sort((a: any, b: any) => (b.changePct || 0) - (a.changePct || 0))
        .slice(0, 5)
        .map((item: any) => ({ industryName: item.industryName || item.industry, changePct: safeNum(item.changePct) }))
    } catch { /* ignore */ }
  }
  // 龙虎榜
  if (data.dragonTiger) {
    try {
      const raw = typeof data.dragonTiger === 'string' ? JSON.parse(data.dragonTiger) : data.dragonTiger
      dtCount.value = raw.total || (Array.isArray(raw) ? raw.length : 0)
      const list = Array.isArray(raw) ? raw : (raw.records || [])
      dtTop3.value = list.slice(0, 3).map((r: any) => ({ stockCode: r.stockCode || r.code, stockName: r.stockName || r.name }))
    } catch { /* ignore */ }
  }
})
ws.subscribe('stats', (data: any) => {
  if (reviewDate.value) return  // 复盘模式不覆盖历史数据
  if (data) marketStats.value = { total: data.total || 0, up: data.up || 0, down: data.down || 0, flat: data.flat || 0 }
})
ws.subscribe('sector', (data: any) => {
  if (reviewDate.value) return  // 复盘模式不覆盖历史数据
  if (Array.isArray(data) && data.length) {
    sectorData.value = data.filter((r: any) => r && r.industryName)
      .map((r: any) => ({ name: r.industryName || '', value: Number(r.stocks) || Number(r.stockCount) || Number(r.mcapYi) || 0, changePercent: Number(r.changePct ?? r.changePercent) || 0 }))
      .sort((a: any, b: any) => b.value - a.value)
  }
})

// 轮询作为 WS 降级保障（间隔拉长为兜底）
useAutoRefresh(() => {
  if (!reviewDate.value) loadSignalData()
  if (!reviewDate.value) loadIndices()
}, 60_000)
useAutoRefresh(() => {
  if (!reviewDate.value) loadMarketStats()
  if (!reviewDate.value) loadHotStocks()
}, 120_000)
useAutoRefresh(() => { if (!reviewDate.value) loadSectorData() }, 300_000)
</script>

<style scoped lang="scss">
.home-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: $spacing-lg;
}
.review-bar {
  display: flex;
  justify-content: flex-end;
  padding: 8px 0 4px;
}
.section { margin-bottom: $spacing-xl; }
.section-header {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: $spacing-md;
  h4 { margin: 0; }
  .view-all { font-size: 13px; color: $primary; display: flex; align-items: center; gap: 3px; text-decoration: none; }
  .chart-legend { display: flex; align-items: center; gap: $spacing-md;
    .legend-item { display: flex; align-items: center; gap: 6px; font-size: 13px; color: $ink-muted-48; }
    .dot { width: 8px; height: 8px; border-radius: 50%;
      &.dot-rise { background: $rise; }
      &.dot-fall { background: $fall; }
    }
    .zoom-hint { display: flex; align-items: center; gap: 4px; font-size: 12px; color: $ink-muted-48; }
  }
  .section-actions { display: flex; align-items: center; gap: $spacing-md; }
}

/* ======== 市场情绪横幅 ======== */
.sentiment-banner { margin-bottom: $spacing-lg; }
.sentiment-inner {
  display: flex; align-items: center; gap: 20px;
  background: $canvas-parchment; border-radius: $rounded-lg; padding: $spacing-md $spacing-lg;
}
.sentiment-stat { display: flex; flex-direction: column; align-items: center; gap: 2px; min-width: 60px;
  .sent-label { font-size: 11px; color: $ink-muted-48; }
  .sent-value { font-family: $font-display; font-size: 22px; font-weight: 700;
    &.rise { color: $rise; } &.fall { color: $fall; } &.flat { color: $flat; }
  }
}
/* 涨跌比例条 */
.ratio-bar-wrap { flex: 1; min-width: 160px; }
.ratio-bar { display: flex; height: 10px; border-radius: 5px; overflow: hidden; }
.ratio-fill { transition: flex 0.3s; }
.rise-bar { background: $rise; }
.fall-bar { background: $fall; }
.flat-bar { background: #999; }
.ratio-labels { display: flex; justify-content: space-between; margin-top: 4px; }
.ratio-pct { font-size: 11px; font-weight: 500;
  &.rise { color: $rise; } &.fall { color: $fall; } &.flat { color: $ink-muted-48; }
}
.sentiment-divider { width: 1px; height: 44px; background: $divider-soft; flex-shrink: 0; }
.sentiment-extra { display: flex; gap: 18px; flex-shrink: 0; }
.extra-item { display: flex; flex-direction: column; align-items: center; gap: 2px;
  .sent-value { font-family: $font-display; font-size: 18px; font-weight: 700;
    &.accent { color: $primary; }
    &.muted { color: $ink-muted-48; }
  }
}

/* ======== 大盘指数 ======== */
.indices-carousel { display: flex; align-items: center; gap: 6px; }
.scroll-arrow {
  flex-shrink: 0; width: 32px; height: 64px; border: 1px solid $divider-soft; background: $canvas;
  border-radius: $rounded-sm; display: flex; align-items: center; justify-content: center; cursor: pointer;
  color: $ink-muted-48; transition: all 0.15s;
  &:hover:not(:disabled) { border-color: $primary; color: $primary; }
  &:disabled { opacity: 0.3; cursor: not-allowed; }
}
.indices-viewport { flex: 1; overflow: hidden; border-radius: $rounded-lg; background: $canvas-parchment; padding: 6px 0; }
.indices-track { display: flex; gap: 12px; padding: 0 8px; transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94); will-change: transform; }
.index-card {
  flex-shrink: 0; width: 188px; display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; border-radius: $rounded-md; cursor: pointer; transition: all 0.15s; position: relative;
  &:hover { box-shadow: $shadow-elevated; transform: translateY(-1px); }
  .card-left {
    .index-name { font-size: 13px; font-weight: 500; margin-bottom: 4px; color: $ink; }
    .index-price { font-family: $font-display; font-size: 18px; font-weight: 600; }
  }
  .card-right { text-align: right;
    .change-pct { font-size: 16px; font-weight: 600; margin-bottom: 2px; }
    .change-points { font-size: 12px; opacity: 0.7; }
  }
  .custom-dot { position: absolute; top: 4px; right: 4px; width: 6px; height: 6px; border-radius: 50%; background: $primary; opacity: 0.4; }
  &.rise { .index-price, .change-pct, .change-points { color: $rise; } background: linear-gradient(135deg, $rise-bg, $canvas); }
  &.fall { .index-price, .change-pct, .change-points { color: $fall; } background: linear-gradient(135deg, $fall-bg, $canvas); }
  &.flat { .index-price, .change-pct, .change-points { color: $flat; } background: $canvas-parchment; }
}

/* ======== 指数管理 ======== */
.manager-body {
  .manager-desc { margin-bottom: $spacing-md; }
  .list-title { font-size: 13px; font-weight: 600; color: $ink-muted-48; margin-bottom: $spacing-xs; }
  .index-chips, .current-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: $spacing-lg; }
  .chip {
    display: flex; align-items: center; gap: 6px; padding: 6px 14px; border: 1px solid $hairline;
    border-radius: $rounded-pill; font-size: 13px; cursor: pointer; transition: all 0.15s;
    &:hover { border-color: $primary; color: $primary; }
    .chip-code { color: $ink-muted-48; }
    .add-icon { font-size: 14px; color: $primary; }
  }
  .chip-added { background: $primary; border-color: $primary; color: white;
    .chip-code { color: rgba(255,255,255,0.7); }
    .remove-icon { font-size: 14px; cursor: pointer; opacity: 0.7; &:hover { opacity: 1; } }
  }
}

/* ======== 信号卡片（加强版） ======== */
.signal-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.signal-card {
  cursor: pointer; border-radius: 12px; padding: 18px;
  display: flex; flex-direction: column; gap: 14px;
  background: $canvas-parchment; border: 1px solid $divider-soft;
  transition: all 0.2s ease;
  &:hover { border-color: rgba($primary, 0.25); box-shadow: 0 4px 14px rgba(0,0,0,0.10); transform: translateY(-2px); }
}
.signal-card .card-header { display: flex; align-items: center; gap: 12px; }
.signal-card .card-icon-wrap { width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.signal-card .card-meta { flex: 1; min-width: 0; }
.signal-card .card-title { font-size: 14px; font-weight: 600; color: $ink; line-height: 1.3; }
.signal-card .card-subtitle { font-size: 11px; color: $ink-muted-48; margin-top: 1px; }

/* 大数字行 */
.card-big-row { display: flex; align-items: baseline; gap: 10px; }
.card-big-num { font-size: 26px; font-weight: 700; font-family: $font-display; line-height: 1;
  small { font-size: 12px; font-weight: 400; opacity: 0.5; margin-left: 2px; }
}
.card-badge { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 10px; line-height: 1.4;
  &.badge-rise { background: rgba($rise, 0.12); color: $rise; }
  &.badge-fall { background: rgba($fall, 0.12); color: $fall; }
  &.badge-hint { background: rgba(255,140,0,0.12); color: #ff8c00; }
}
/* 明细行 */
.card-detail-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.detail-label { font-size: 12px; font-weight: 500; }
.detail-sep { color: $divider-soft; font-size: 12px; }
.detail-chip {
  display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500;
  background: rgba(255,140,0,0.08); color: #cc7700; border: 1px solid rgba(255,140,0,0.12);
  cursor: pointer; &:hover { background: rgba(255,140,0,0.15); }
}
/* 题材标签 */
.card-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.hot-tag {
  display: inline-block; padding: 3px 10px; border-radius: 6px; font-size: 12px; font-weight: 500;
  background: rgba(239,83,80,0.10); color: #ef5350; border: 1px solid rgba(239,83,80,0.15);
  cursor: pointer; transition: all 0.12s; &:hover { background: rgba(239,83,80,0.18); }
}
/* 行业排行列表 */
.card-rank-list { display: flex; flex-direction: column; gap: 5px; }
.rank-row {
  display: flex; align-items: center; gap: 6px; font-size: 13px; padding: 3px 8px; border-radius: 6px;
  transition: background 0.12s;
  &:hover { background: rgba(0,0,0,0.02); }
}
.rank-num { width: 16px; font-size: 11px; font-weight: 600; color: $ink-muted-48; text-align: center; flex-shrink: 0; }
.rank-name { flex: 1; color: $ink; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card-empty { font-size: 13px; color: $ink-muted-48; padding: 8px 0; }
.card-skeleton { display: flex; flex-direction: column; gap: 8px; }
.card-detail-row .text-rise { color: $rise; }
.card-detail-row .text-fall { color: $fall; }

/* ======== 云图（全宽） ======== */
.map-section { margin-bottom: $spacing-xl; }
.chart-container { background: $canvas-parchment; border-radius: $rounded-lg; padding: 4px; height: 520px; }

/* ======== 热门股票横向滚动 ======== */
.hot-scroll-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; padding-bottom: 6px;
  &::-webkit-scrollbar { height: 4px; }
  &::-webkit-scrollbar-thumb { background: $divider-soft; border-radius: 4px; }
}
.hot-scroll-track { display: flex; gap: 10px; min-width: max-content; }
.hot-mini-card {
  flex-shrink: 0; width: 140px; padding: 12px 16px; border-radius: 10px;
  cursor: pointer; background: $canvas-parchment; border: 1px solid $divider-soft;
  transition: all 0.15s; display: flex; flex-direction: column; gap: 4px;
  &:hover { transform: translateY(-2px); box-shadow: $shadow-elevated; border-color: rgba($primary,0.25); }
  .mini-name { font-size: 14px; font-weight: 600; }
  .mini-code { font-size: 11px; color: $ink-muted-48; }
  .mini-price { font-family: $font-display; font-size: 16px; font-weight: 600; margin-top: 4px; }
  .mini-change { font-size: 13px; font-weight: 600;
    &.text-rise { color: $rise; } &.text-fall { color: $fall; }
  }
}

/* ======== 骨架屏 ======== */
.skeleton-sentiment { display: flex; gap: 16px; }
.skeleton-index-card {
  flex-shrink: 0; width: 188px; display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; border-radius: 8px; background: rgba(0,0,0,0.02); border: 1px solid rgba(0,0,0,0.04);
}
.skeleton-mini-card {
  flex-shrink: 0; width: 140px; padding: 12px 16px; border-radius: 10px;
  background: rgba(0,0,0,0.02); border: 1px solid rgba(0,0,0,0.04);
}
.sk-line { border-radius: 4px; background: linear-gradient(90deg, rgba(0,0,0,0.04) 25%, rgba(0,0,0,0.08) 50%, rgba(0,0,0,0.04) 75%); background-size: 200% 100%; animation: sk-shimmer 1.5s infinite; }
@keyframes sk-shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* 移动端点击优化 */
@media (hover: none) and (pointer: coarse) {
  .signal-card { -webkit-tap-highlight-color: transparent; touch-action: manipulation; }
}
</style>
