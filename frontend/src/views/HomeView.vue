<template>
  <div class="home-view">
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
import { ArrowRight, ArrowLeft, Setting, Pointer, Plus, Close } from '@element-plus/icons-vue'
import TreemapChart from '@/components/chart/TreemapChart.vue'
import { getStockList, getIndustries } from '@/api/stock'
import { getIndexList } from '@/api/index'

const router = useRouter()
const scrollRef = ref<HTMLElement>()
const scrollPos = ref(0)
const showIndexManager = ref(false)

// ======== 大盘指数 - 从后端API实时加载 ========
interface IndexCard {
  code: string
  name: string
  price: number
  changePercent: number
  changePoints: number
  isCustom: boolean
}

const allIndexData = ref<IndexCard[]>([])
const DEFAULT_INDICES_CODES = ['000001', '399001', '399006', '000688']

const visibleIndices = ref<IndexCard[]>([])

const availableIndices = computed(() =>
  allIndexData.value.filter(i => !visibleIndices.value.find(v => v.code === i.code))
)

/** 从后端加载指数数据 */
async function loadIndices() {
  try {
    const data: any = await getIndexList()
    if (Array.isArray(data) && data.length > 0) {
      // 后端返回 [{indexCode, indexName, closePoint, changePercent, category}]
      allIndexData.value = data.map((d: any) => ({
        code: d.indexCode,
        name: d.indexName,
        price: Number(d.closePoint) || 0,
        changePercent: Number(d.changePercent) || 0,
        changePoints: Number(d.closePoint) ? (Number(d.closePoint) * Number(d.changePercent) / 100) : 0,
        isCustom: !DEFAULT_INDICES_CODES.includes(d.indexCode),
      }))
      // 默认展示前4个 + 用户自定义的
      const defaults = allIndexData.value.filter(d => DEFAULT_INDICES_CODES.includes(d.code))
      visibleIndices.value = defaults.length ? defaults : allIndexData.value.slice(0, 4)
    }
  } catch (_e) {
    // API不可用时，使用静态备降数据
    allIndexData.value = [
      { code: '000001', name: '上证指数', price: 3356, changePercent: 0.68, changePoints: 22.45, isCustom: false },
      { code: '399001', name: '深证成指', price: 11245, changePercent: 1.12, changePoints: 124.56, isCustom: false },
      { code: '399006', name: '创业板指', price: 2234, changePercent: -0.35, changePoints: -7.89, isCustom: false },
      { code: '000688', name: '科创50',   price: 987,   changePercent: 1.56,  changePoints: 15.23,  isCustom: false },
    ]
    visibleIndices.value = allIndexData.value.slice(0, 4)
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

// ======== 板块数据 ========
const sectorData = ref([
  { name: '金融', value: 3500, changePercent: 1.2, items: [
    { name: '银行', value: 1800, changePercent: 0.8 },
    { name: '证券', value: 1200, changePercent: 1.5 },
    { name: '保险', value: 500, changePercent: 2.1 },
  ]},
  { name: '科技', value: 4200, changePercent: -0.5, items: [
    { name: '半导体', value: 1500, changePercent: -1.2 },
    { name: '消费电子', value: 1200, changePercent: 0.3 },
    { name: '软件服务', value: 800, changePercent: -0.8 },
    { name: '通信设备', value: 700, changePercent: 0.5 },
  ]},
  { name: '消费', value: 2800, changePercent: 0.6, items: [
    { name: '食品饮料', value: 1000, changePercent: 1.1 },
    { name: '家电', value: 800, changePercent: -0.2 },
    { name: '汽车', value: 600, changePercent: 0.8 },
    { name: '医药', value: 400, changePercent: 0.3 },
  ]},
  { name: '制造', value: 2200, changePercent: -0.8, items: [
    { name: '新能源', value: 1200, changePercent: -1.5 },
    { name: '军工', value: 600, changePercent: 0.2 },
    { name: '机械', value: 400, changePercent: -0.1 },
  ]},
  { name: '周期', value: 1800, changePercent: 0.2, items: [
    { name: '有色', value: 800, changePercent: 0.5 },
    { name: '钢铁', value: 500, changePercent: -0.3 },
    { name: '化工', value: 500, changePercent: 0.4 },
  ]},
  { name: '地产建筑', value: 1500, changePercent: -1.8, items: [
    { name: '房地产', value: 900, changePercent: -2.5 },
    { name: '建筑', value: 600, changePercent: -0.8 },
  ]},
  { name: '公用事业', value: 1000, changePercent: 0.15, items: [
    { name: '电力', value: 600, changePercent: 0.3 },
    { name: '水务', value: 400, changePercent: 0.0 },
  ]},
])

const hotStocks = ref([
  { code: '600519', name: '贵州茅台', price: 1685.00, changePercent: 1.25 },
  { code: '300750', name: '宁德时代', price: 198.56, changePercent: -0.85 },
  { code: '000858', name: '五粮液', price: 156.78, changePercent: 2.15 },
  { code: '601318', name: '中国平安', price: 45.23, changePercent: 0.56 },
  { code: '600036', name: '招商银行', price: 36.89, changePercent: -0.32 },
  { code: '000333', name: '美的集团', price: 68.45, changePercent: 1.08 },
])

async function loadHotStocks() {
  try {
    const res: any = await getStockList({ page: 1, size: 6 })
    if (res?.records?.length) {
      hotStocks.value = res.records.map((r: any) => ({
        code: r.stockCode,
        name: r.stockName,
        price: r.price || 0,
        changePercent: r.changePct || 0,
      }))
    }
  } catch (_e) { /* 保留 mock 数据 */ }
}

async function loadSectorData() {
  // 板块云图暂时保留mock数据，可供后续实现
}

function getChangeClass(pct: number) {
  const n = Number(pct)
  if (isNaN(n)) return 'flat'
  if (n > 0) return 'rise'
  if (n < 0) return 'fall'
  return 'flat'
}

function safeNum(v: any, decimals = 2): string {
  const n = Number(v)
  return isNaN(n) ? '-' : n.toFixed(decimals)
}

function formatPrice(p: number) {
  const n = Number(p)
  return isNaN(n) ? '-' : n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatPercent(p: number) {
  const n = Number(p)
  if (isNaN(n)) return '-'
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(2)}%`
}

function formatPoints(p: number) {
  const n = Number(p)
  if (isNaN(n)) return '-'
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(2)}`
}

function onSectorClick(data: any) {
  const name = data.name || ''
  router.push({ path: `/sector/${encodeURIComponent(name)}` })
}

onMounted(() => {
  loadIndices()
  loadHotStocks()
  loadSectorData()
})
</script>

<style scoped lang="scss">
.home-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: $spacing-lg;
}

.section { margin-bottom: $spacing-xl; }

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
  grid-template-columns: repeat(3, 1fr);
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
</style>
