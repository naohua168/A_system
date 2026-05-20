<template>
  <div class="home-view">
    <!-- 市场概览 -->
    <section class="section market-overview">
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
    </section>

    <!-- 大盘指数 - 东方财富风格 -->
    <section class="section">
      <div class="section-header">
        <h4>大盘指数</h4>
        <div class="section-actions">
          <el-button text type="primary" size="small" @click="showIndexManager = true">
            <el-icon><Setting /></el-icon> 管理指数
          </el-button>
        </div>
      </div>
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
          <div class="list-title">已添加 ({{ visibleIndices.length }}/12)</div>
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
        <div class="signal-card signal-card-nb" @click="$router.push('/northbound')">
          <el-icon class="card-icon" :size="24"><TrendCharts /></el-icon>
          <div class="card-body">
            <div class="card-title">北向资金</div>
            <div class="card-value" :class="nbTotal >= 0 ? 'text-rise' : 'text-fall'">
              {{ nbTotal >= 0 ? '+' : '' }}{{ nbTotal }}<small>亿</small>
            </div>
            <div class="card-detail">
              沪 {{ nbHgt }} 深 {{ nbSgt }}
            </div>
          </div>
        </div>
        <div class="signal-card signal-card-hot" @click="$router.push('/hot-reason')">
          <el-icon class="card-icon" :size="24"><DataAnalysis /></el-icon>
          <div class="card-body">
            <div class="card-title">题材热点</div>
            <div class="card-tags" v-if="hotReasons.length">
              <el-tag v-for="r in hotReasons.slice(0,3)" :key="r.stockCode" size="small" class="hot-tag"
                @click.stop="$router.push(`/stock/${r.stockCode}`)">
                {{ r.stockName }}
              </el-tag>
            </div>
            <div class="card-detail">{{ hotReasons.length }} 只个股今日强势</div>
          </div>
        </div>
        <div class="signal-card signal-card-ind" @click="$router.push('/industry-compare')">
          <el-icon class="card-icon" :size="24"><Histogram /></el-icon>
          <div class="card-body">
            <div class="card-title">行业排行</div>
            <div class="card-ind-list" v-if="industryTop.length">
              <div v-for="ind in industryTop.slice(0,3)" :key="ind.industryName" class="ind-row">
                <span class="ind-name">{{ ind.industryName }}</span>
                <span :class="ind.changePct >= 0 ? 'text-rise' : 'text-fall'">
                  {{ ind.changePct >= 0 ? '+' : '' }}{{ ind.changePct }}%
                </span>
              </div>
            </div>
          </div>
        </div>
        <div class="signal-card signal-card-dt" @click="$router.push('/dragon-tiger')">
          <el-icon class="card-icon" :size="24"><Aim /></el-icon>
          <div class="card-body">
            <div class="card-title">龙虎榜</div>
            <div class="card-value">{{ dtCount }}</div>
            <div class="card-detail">只个股今日上榜</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 板块涨跌云图 -->
    <section class="section map-section">
      <div class="section-header">
        <h4>板块涨跌云图</h4>
        <div class="chart-legend">
          <span class="legend-item"><span class="dot dot-rise"></span>涨</span>
          <span class="legend-item"><span class="dot dot-fall"></span>跌</span>
          <span class="zoom-hint"><el-icon><Pointer /></el-icon> 点击板块跳转行情</span>
        </div>
      </div>
      <div class="chart-container" ref="chartRef">
        <TreemapChart
          ref="treemapRef"
          :data="sectorData"
          @click="onSectorClick"
        />
      </div>
    </section>

    <!-- 热门股票 -->
    <section class="section quick-market">
      <div class="section-header">
        <h4>热门股票</h4>
        <router-link to="/stocks" class="view-all">查看所有股票 <el-icon><ArrowRight /></el-icon></router-link>
      </div>
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
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, ArrowLeft, Setting, Pointer, Plus, Close, TrendCharts, DataAnalysis, Histogram, Aim } from '@element-plus/icons-vue'
import TreemapChart from '@/components/chart/TreemapChart.vue'
import { getStockList } from '@/api/market'
import { getIndexList } from '@/api/index'
import { getSectorRanking } from '@/api/analysis'
import { getNorthboundLatest, getHotReason, getDragonTigerDaily, getIndustryCompare } from '@/api/signal'
import { formatPrice, formatPercent, formatPoints, getChangeClass } from '@/utils/format'
import type {
  HotReason, IndustryTopItem, IndexCard, SectorNode, HomeStockCard,
  Northbound, HotReasonResponse, IndustryCompareResponse, DragonTigerDaily,
  SectorRanking,
} from '@/types'

const router = useRouter()
const scrollRef = ref<HTMLElement>()
const scrollPos = ref(0)
const showIndexManager = ref(false)

/** 信号层数据 — 业务类型见 @/types */
const nbHgt = ref(0)
const nbSgt = ref(0)
const nbTotal = computed(() => Number((nbHgt.value + nbSgt.value).toFixed(2)))
const hotReasons = ref<HotReason[]>([])
const industryTop = ref<IndustryTopItem[]>([])
const dtCount = ref(0)

/** 并行加载信号层数据（各接口独立容错） */
async function loadSignalData() {
  try {
    const [nbRes, hotRes, indRes, dtRes] = await Promise.allSettled([
      getNorthboundLatest(1),
      getHotReason(),
      getIndustryCompare(),
      getDragonTigerDaily(),
    ])
    if (nbRes.status === 'fulfilled' && Array.isArray(nbRes.value) && nbRes.value.length > 0) {
      const nbData = nbRes.value as Northbound[]
      nbHgt.value = nbData[0].hgtYi || 0
      nbSgt.value = nbData[0].sgtYi || 0
    }
    if (hotRes.status === 'fulfilled') {
      const data = hotRes.value as HotReasonResponse
      hotReasons.value = data.records || []
    }
    if (indRes.status === 'fulfilled') {
      const data = indRes.value as IndustryCompareResponse
      const all = data.records || []
      industryTop.value = all
        .sort((a, b) => b.changePct - a.changePct)
        .slice(0, 5)
        .map((item) => ({ industryName: item.industryName, changePct: item.changePct }))
    }
    if (dtRes.status === 'fulfilled') {
      const data = dtRes.value as DragonTigerDaily
      dtCount.value = data.total || 0
    }
  } catch {
    // 信号层数据非关键，静默失败
  }
}

/** 大盘指数 — 从后端 API 实时加载 */
const allIndexData = ref<IndexCard[]>([])
const DEFAULT_INDICES_CODES = ['000001', '399001', '399006', '000688']

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
        changePercent: Number(item.changePercent) || 0,
        changePoints: Number(item.closePoint) ? (Number(item.closePoint) * Number(item.changePercent) / 100) : 0,
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
  if (visibleIndices.value.length >= 12) return
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

/** 热门股票网格 */
const hotStocks = ref<HomeStockCard[]>([])

/** 加载热门股票（首页前12只） */
async function loadHotStocks() {
  try {
    const res = await getStockList({ page: 1, size: 12 })
    if (res?.records?.length) {
      hotStocks.value = res.records.map((r) => ({
        code: r.stockCode,
        name: r.stockName,
        price: r.price || 0,
        changePercent: r.changePct || 0,
      }))
    }
  } catch (_e) { console.warn('[Home] loadHotStocks failed:', _e) }
}

/** 市场整体涨跌家数 — 从行业排行汇总 */
const marketStats = ref({ total: 0, up: 0, down: 0, flat: 0 })
async function loadMarketStats() {
  try {
    const ranking = await getSectorRanking() as SectorRanking[]
    if (Array.isArray(ranking) && ranking.length > 0) {
      let total = 0, up = 0, down = 0
      ranking.forEach((s) => {
        total += Number(s.stockCount) || 0
        up += Number(s.upCount) || 0
        down += (Number(s.stockCount) || 0) - (Number(s.upCount) || 0)
      })
      marketStats.value = { total, up, down, flat: total - up - down }
    }
  } catch { /* 非关键功能，静默失败 */ }
}

/** 加载板块云图数据 */
async function loadSectorData() {
  try {
    const data = await getSectorRanking() as SectorRanking[]
    if (Array.isArray(data) && data.length > 0) {
      sectorData.value = data.map((d) => ({
        name: d.industry || '其他',
        value: Number(d.stockCount) || 1,
        changePercent: Number(d.avgChangePct) || 0,
      }))
      return
    }
  } catch (_e) { console.warn('[Home] loadSectorData failed:', _e) }
}

function onSectorClick(data: { name?: string }) {
  const name = data?.name || ''
  router.push({ path: `/sector/${encodeURIComponent(name)}` })
}

onMounted(() => {
  loadIndices()
  loadHotStocks()
  loadSectorData()
  loadMarketStats()
  loadSignalData()
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
  padding: $spacing-md;
  height: 600px;
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
  cursor: pointer; border-radius: 12px; padding: 16px; display: flex; gap: 12px; align-items: flex-start;
  transition: all 0.2s; border: 1px solid rgba(255,255,255,0.06);
  &:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
  .card-icon { font-size: 24px; flex-shrink: 0; }
  .card-body { flex: 1; min-width: 0; }
  .card-title { font-size: 12px; color: rgba(255,255,255,0.5); margin-bottom: 6px; font-weight: 500; }
  .card-value { font-size: 22px; font-weight: 700; margin-bottom: 4px;
    small { font-size: 12px; font-weight: 400; opacity: 0.4; margin-left: 2px; } }
  .card-detail { font-size: 12px; color: rgba(255,255,255,0.3); }
  .card-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 4px; }
  .card-ind-list { .ind-row { display: flex; justify-content: space-between; font-size: 12px; padding: 2px 0;
    .ind-name { color: rgba(255,255,255,0.6); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; } } }
}
.signal-card-nb { background: linear-gradient(135deg, rgba(41,151,255,0.08), rgba(41,151,255,0.02)); }
.signal-card-hot { background: linear-gradient(135deg, rgba(236,77,76,0.08), rgba(236,77,76,0.02)); }
.signal-card-ind { background: linear-gradient(135deg, rgba(82,196,26,0.08), rgba(82,196,26,0.02)); }
.signal-card-dt { background: linear-gradient(135deg, rgba(255,140,0,0.08), rgba(255,140,0,0.02)); }
.hot-tag { background: rgba(236,77,76,0.12); color: #ec4d4c; border: 1px solid rgba(236,77,76,0.2);
  cursor: pointer; &:hover { background: rgba(236,77,76,0.2); } }
</style>
