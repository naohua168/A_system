<template>
  <div class="sector-detail">
    <!-- 板块基本信息 -->
    <div class="sector-header">
      <div class="sector-info">
        <h2>{{ sector.name }} <span class="sector-code">{{ sector.code }}</span></h2>
        <div class="sector-price-section">
          <span class="current-price" :class="sector.changePercent >= 0 ? 'text-rise' : 'text-fall'">
            {{ sector.price.toFixed(2) }}
          </span>
          <span class="price-change" :class="sector.changePercent >= 0 ? 'text-rise' : 'text-fall'">
            {{ sector.changePercent >= 0 ? '+' : '' }}{{ sector.changePercent.toFixed(2) }}%
          </span>
        </div>
        <div class="sector-meta caption">
          <span>涨跌家数: <span class="text-rise">{{ sector.upCount }}</span> 家 / <span class="text-fall">{{ sector.downCount }}</span> 家</span>
          <span>总成交额: {{ sector.amount }}</span>
          <span>领涨股: {{ sector.leader }}</span>
        </div>
      </div>
      <div class="sector-actions">
        <el-button type="primary" plain round @click="$router.push('/watchlist')">
          <el-icon><Star /></el-icon> 关注板块
        </el-button>
      </div>
    </div>

    <!-- K线图控制栏 (与股票详情统一) -->
    <div class="chart-toolbar">
      <div class="toolbar-left">
        <div class="period-tabs">
          <button v-for="p in periods" :key="p.key"
            :class="['period-btn', { active: activePeriod === p.key }]"
            @click="activePeriod = p.key"
          >{{ p.label }}</button>
        </div>
      </div>
      <div class="toolbar-right">
        <!-- 缠论开关 -->
        <label class="switch-item" :class="{ active: showChanlun }">
          <el-switch v-model="showChanlun" size="small" />
          <span>缠论</span>
        </label>
        <!-- K线叠加指标 (MA/BOLL) -->
        <div class="indicator-group overlay-group">
          <label v-for="ind in overlayIndicators" :key="ind.key"
            :class="['indicator-chip', { active: ind.active }]"
            @click="toggleOverlay(ind)"
          >
            {{ ind.label }}
          </label>
        </div>
        <!-- 底部指标 (互斥,替换成交量) -->
        <div class="indicator-group bottom-group">
          <label
            :class="['indicator-chip', 'vol-chip', { active: bottomActive === null }]"
            @click="bottomActive = null; renderChart()"
          >
            VOL
          </label>
          <label v-for="ind in bottomIndicators" :key="ind.key"
            :class="['indicator-chip', { active: bottomActive === ind.key }]"
            @click="selectBottomIndicator(ind)"
          >
            {{ ind.label }}
            <span class="ind-settings" v-if="bottomActive === ind.key" @click.stop="openParams(ind)">
              <el-icon><Setting /></el-icon>
            </span>
          </label>
        </div>
      </div>
    </div>

    <!-- K线图 -->
    <div class="chart-main" ref="chartRef" v-loading="loading">
      <template v-if="!loading">
        <div class="kline-chart" ref="klineChartRef"></div>
        <div class="bottom-chart" ref="bottomChartRef"></div>
      </template>
    </div>

    <!-- 底部信息 -->
    <div class="bottom-section">
      <!-- 上行: 板块信息 + 量化指标 + AI入口 -->
      <div class="row-2col">
        <div class="info-card">
          <h4>板块信息</h4>
          <div class="info-grid-2col">
            <div class="info-row"><span class="label">涨跌家数</span><span class="val"><span class="text-rise">{{ sector.upCount }}</span> / <span class="text-fall">{{ sector.downCount }}</span></span></div>
            <div class="info-row"><span class="label">总成交额</span><span class="val">{{ sector.amount }}</span></div>
            <div class="info-row"><span class="label">领涨股</span><span class="val text-rise">{{ sector.leader }}</span></div>
            <div class="info-row"><span class="label">总市值</span><span class="val">{{ sector.totalMarketCap }}</span></div>
            <div class="info-row"><span class="label">上涨占比</span><span class="val">{{ ((sector.upCount / (sector.upCount + sector.downCount)) * 100).toFixed(1) }}%</span></div>
          </div>
        </div>
        <div class="info-card quant-card">
          <h4>量化指标</h4>
          <div class="quant-stats">
            <div class="stat"><span class="label">MA5</span><span class="val">{{ (quant.ma5 ?? 0).toFixed(2) }}</span></div>
            <div class="stat"><span class="label">MA20</span><span class="val">{{ (quant.ma20 ?? 0).toFixed(2) }}</span></div>
            <div class="stat"><span class="label">MACD</span><span class="val" :class="(quant.macd ?? 0) >= 0 ? 'text-rise' : 'text-fall'">{{ (quant.macd ?? 0).toFixed(4) }}</span></div>
            <div class="stat"><span class="label">RSI</span><span class="val" :class="(quant.rsi ?? 50) > 70 ? 'text-rise' : (quant.rsi ?? 50) < 30 ? 'text-fall' : ''">{{ (quant.rsi ?? 50).toFixed(1) }}</span></div>
            <div class="stat"><span class="label">KDJ-K</span><span class="val">{{ (quant.kdjK ?? 50).toFixed(1) }}</span></div>
            <div class="stat"><span class="label">KDJ-D</span><span class="val">{{ (quant.kdjD ?? 50).toFixed(1) }}</span></div>
          </div>
        </div>
      </div>

      <!-- 下行: 缠论分析 (全宽) -->
      <div class="info-card chanlun-card">
        <h4>
          <span>缠论分析</span>
          <span :class="['trend-badge', chanlunStats.trendType === '上涨趋势' ? 'rise' : chanlunStats.trendType === '下跌趋势' ? 'fall' : 'flat']">
            {{ chanlunStats.trendType }}
          </span>
        </h4>

        <div class="cl-overview">
          <div class="ov-item"><span class="label">级别</span><span class="val">{{ chanlunStats.level }}</span></div>
          <div class="ov-item"><span class="label">当前笔</span><span class="val" :class="chanlunStats.currentBi.includes('向上') ? 'text-rise' : 'text-fall'">{{ chanlunStats.currentBi }}</span></div>
        </div>

        <div class="cl-wide-row">
          <div class="cl-wide-item">
            <span class="section-label">统计</span>
            <div class="chanlun-stats-h">
              <div class="stat-h"><span class="label">顶分型</span><span class="val cl-ding">{{ chanlunStats.dingCount }}</span></div>
              <div class="stat-h"><span class="label">底分型</span><span class="val cl-di">{{ chanlunStats.diCount }}</span></div>
              <div class="stat-h"><span class="label">笔</span><span class="val">{{ chanlunStats.biCount }}</span></div>
              <div class="stat-h"><span class="label">中枢</span><span class="val cl-zs">{{ chanlunStats.zhongshuCount }}</span></div>
            </div>
          </div>

          <div class="cl-wide-item">
            <span class="section-label">中枢区间</span>
            <div class="zhongshu-list">
              <div v-for="zs in chanlunStats.zhongshuInfo" :key="zs.name" class="zhongshu-item">
                <span class="zs-name">{{ zs.name }}</span>
                <span class="zs-range">{{ zs.zd.toFixed(2) }} ~ {{ zs.zg.toFixed(2) }}</span>
              </div>
            </div>
            <div class="position-row">
              <span class="label">位置</span>
              <span :class="['pos-badge', chanlunStats.pricePosition === '上方' ? 'above' : chanlunStats.pricePosition === '下方' ? 'below' : 'inside']">
                {{ chanlunStats.pricePosition }}
              </span>
            </div>
          </div>

          <div class="cl-wide-item">
            <span class="section-label">分型</span>
            <div class="fengxing-list">
              <div class="fengxing-item">
                <span class="label">最近顶</span>
                <span class="val ding-price">{{ chanlunStats.lastDingFeng.price }}</span>
                <span class="date">{{ chanlunStats.lastDingFeng.date }}</span>
              </div>
              <div class="fengxing-item">
                <span class="label">最近底</span>
                <span class="val di-price">{{ chanlunStats.lastDiFeng.price }}</span>
                <span class="date">{{ chanlunStats.lastDiFeng.date }}</span>
              </div>
            </div>
          </div>

          <div class="cl-wide-item">
            <span class="section-label">信号</span>
            <div class="signal-tags">
              <span v-for="bp in chanlunStats.buyPoints" :key="bp.type" class="point-badge buy">
                {{ bp.type }} <span class="point-desc">{{ bp.desc }}</span>
              </span>
              <span v-for="sp in chanlunStats.sellPoints" :key="sp.type" class="point-badge sell">
                {{ sp.type }} <span class="point-desc">{{ sp.desc }}</span>
              </span>
              <span v-if="!chanlunStats.buyPoints.length && !chanlunStats.sellPoints.length" class="no-points">暂无</span>
            </div>
            <div class="beichi-row">
              <span class="label">背驰</span>
              <span :class="['beichi-badge', chanlunStats.beichi === '顶背驰' ? 'ding' : chanlunStats.beichi === '底背驰' ? 'di' : 'none']">
                {{ chanlunStats.beichi }}
              </span>
            </div>
          </div>
        </div>

        <div class="signals">
          <div v-for="s in chanlunStats.signals" :key="s.text" :class="['signal-badge', s.type]">{{ s.text }}</div>
        </div>
      </div>
    </div>

    <!-- 成分股列表 -->
    <section class="section">
      <div class="section-header">
        <h4>成分股 ({{ allConstituentsLoaded ? constituents.length : '前' + displayedConstituents.length + '/' + totalConstituents }})</h4>
      </div>
      <template v-if="loading">
        <SkeletonLoader type="table" :rows="5" :col-widths="['25%','15%','15%','15%','15%']" padding="0" />
      </template>
      <template v-else-if="!constituents.length">
        <EmptyState type="empty" title="暂无成分股数据" inline />
      </template>
      <template v-else>
        <div class="constituent-table">
        <div class="table-header">
          <span>名称</span><span>代码</span><span>现价</span><span>涨跌幅</span><span>涨跌额</span>
        </div>
        <div v-for="s in displayedConstituents" :key="s.code"
          class="table-row"
          @click="$router.push(`/stock/${s.code}`)"
        >
          <span><strong>{{ s.name || '-' }}</strong></span>
          <span class="caption">{{ s.code || '-' }}</span>
          <span>{{ (Number(s.price) || 0).toFixed(2) }}</span>
          <span :class="(s.changePercent || 0) >= 0 ? 'text-rise' : 'text-fall'">{{ (s.changePercent || 0) >= 0 ? '+' : '' }}{{ (Number(s.changePercent) || 0).toFixed(2) }}%</span>
          <span :class="(s.changePercent || 0) >= 0 ? 'text-rise' : 'text-fall'">{{ (s.change || 0) >= 0 ? '+' : '' }}{{ (Number(s.change) || 0).toFixed(2) }}</span>
        </div>
        <!-- 底部操作栏 -->
        <div v-if="!allConstituentsLoaded && totalConstituents > INITIAL_LIMIT" class="table-footer">
          <el-button text class="footer-btn" :loading="loadingAllConstituents" @click="loadAllConstituents">
            <el-icon><ArrowDown /></el-icon> 展示全部 {{ totalConstituents }} 只
          </el-button>
        </div>
        <div v-else-if="allConstituentsLoaded" class="table-footer">
          <el-button text class="footer-btn" @click="allConstituentsLoaded = false">
            <el-icon><ArrowUp /></el-icon> 收起
          </el-button>
        </div>
      </div>
      </template>
    </section>
  </div>

  <!-- 参数设置弹窗 -->
  <el-dialog v-model="paramsDialogVisible" :title="`${paramsDialogTitle} 参数设置`" width="420px" :modal="false" class="params-dialog">
    <div v-if="paramsTarget === 'macd'" class="params-form">
      <div class="param-item"><div class="param-row"><label>快线周期 (EMA短)</label><el-input-number v-model="params.macd.fast" :min="5" :max="30" size="small" controls-position="right" /></div><p class="param-hint">短周期 EMA 计算参数，值越小对价格越敏感。默认值 12。</p></div>
      <div class="param-item"><div class="param-row"><label>慢线周期 (EMA长)</label><el-input-number v-model="params.macd.slow" :min="10" :max="60" size="small" controls-position="right" /></div><p class="param-hint">长周期 EMA 计算参数，值越大趋势越平滑。默认值 26。</p></div>
      <div class="param-item"><div class="param-row"><label>信号周期 (DEA)</label><el-input-number v-model="params.macd.signal" :min="5" :max="30" size="small" controls-position="right" /></div><p class="param-hint">DIF 的移动平均周期，值越大信号越滞后。默认值 9。</p></div>
    </div>
    <div v-if="paramsTarget === 'kdj'" class="params-form">
      <div class="param-item"><div class="param-row"><label>计算周期 (N)</label><el-input-number v-model="params.kdj.period" :min="5" :max="30" size="small" controls-position="right" /></div><p class="param-hint">RSV 的计算周期，决定 K 值对价格变动的敏感度。默认值 9。</p></div>
      <div class="param-item"><div class="param-row"><label>K值平滑 (M1)</label><el-input-number v-model="params.kdj.m1" :min="2" :max="10" size="small" controls-position="right" /></div><p class="param-hint">K 值的平滑因子，值越小 K 线跟随 RSV 越快。默认值 3。</p></div>
      <div class="param-item"><div class="param-row"><label>D值平滑 (M2)</label><el-input-number v-model="params.kdj.m2" :min="2" :max="10" size="small" controls-position="right" /></div><p class="param-hint">D 值的平滑因子，值越小 D 线跟随 K 越快。默认值 3。</p></div>
    </div>
    <div v-if="paramsTarget === 'rsi'" class="params-form">
      <div class="param-item"><div class="param-row"><label>计算周期 (N)</label><el-input-number v-model="params.rsi.period" :min="5" :max="30" size="small" controls-position="right" /></div><p class="param-hint">RSI 的计算周期，值越小对价格波动越敏感。默认值 14。</p></div>
    </div>
    <div v-if="paramsTarget === 'ma'" class="params-form">
      <div class="param-item"><div class="param-row"><label>MA1 周期</label><el-input-number v-model="params.ma.periods[0]" :min="3" :max="120" size="small" controls-position="right" /></div><p class="param-hint">短期均线，常用值 5/10。默认值 5。</p></div>
      <div class="param-item"><div class="param-row"><label>MA2 周期</label><el-input-number v-model="params.ma.periods[1]" :min="3" :max="120" size="small" controls-position="right" /></div><p class="param-hint">中期均线，常用值 20/30。默认值 20。</p></div>
      <div class="param-item"><div class="param-row"><label>MA3 周期</label><el-input-number v-model="params.ma.periods[2]" :min="3" :max="250" size="small" controls-position="right" /></div><p class="param-hint">中长期均线，常用值 60。默认值 60。</p></div>
      <div class="param-item"><div class="param-row"><label>MA4 周期</label><el-input-number v-model="params.ma.periods[3]" :min="3" :max="250" size="small" controls-position="right" /></div><p class="param-hint">长期均线，常用值 120/250。默认值 120。</p></div>
    </div>
    <div v-if="paramsTarget === 'boll'" class="params-form">
      <div class="param-item"><div class="param-row"><label>计算周期</label><el-input-number v-model="params.boll.period" :min="5" :max="60" size="small" controls-position="right" /></div><p class="param-hint">布林带中轨 MA 的计算周期，值越大通道越平滑。默认值 20。</p></div>
      <div class="param-item"><div class="param-row"><label>标准差倍数</label><el-input-number v-model="params.boll.multiplier" :min="1" :max="5" :step="0.5" size="small" controls-position="right" /></div><p class="param-hint">通道宽度倍数，值越大上下轨越宽。默认值 2。</p></div>
    </div>
    <template #footer>
      <el-button @click="paramsDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="applyParams">确认</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Star, Setting, ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import { getStockList, getSectorKline } from '@/api/market'
import { getSectorRanking } from '@/api/analysis'
import { useTechnicalChart } from '@/composables/useTechnicalChart'
import { useIndicatorParams } from '@/composables/useIndicatorParams'
import { safeVal, parseTradeDate } from '@/utils/format'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const route = useRoute()
const sectorName = decodeURIComponent(route.params.name as string)
const activePeriod = ref('day')
const showChanlun = ref(false)

// ── 共享指标参数管理 ──
const indicator = useIndicatorParams()
const {
  periods,
  overlayIndicators,
  bottomIndicators,
  bottomActive,
  toggleOverlay,
  selectBottomIndicator,
  paramsDialogVisible,
  paramsDialogTitle,
  paramsTarget,
  params,
  openParams,
  applyParams,
} = indicator

// 缓存K线数据（仅由后续逻辑填充，当前无API）
let cachedKlineData: number[][] | null = null
function getKlineData() {
  return cachedKlineData || []
}

const loading = ref(true)

const chartRef = ref<HTMLElement>()
const klineChartRef = ref<HTMLElement>()
const bottomChartRef = ref<HTMLElement>()

// ── K线图渲染器 ──
const { renderChart, handleResize, dispose: disposeChart } = useTechnicalChart(
  klineChartRef as any,
  bottomChartRef as any,
  {
    getKlineData,
    params: params as any,
    showMA: computed(() => overlayIndicators.value.find(i => i.key === 'ma')?.active ?? true),
    showBOLL: computed(() => overlayIndicators.value.find(i => i.key === 'boll')?.active ?? false),
    bottomActive: bottomActive as any,
  }
)

// 将渲染函数注入指标管理器，使指标切换自动触发重绘
indicator.setRenderCallback(renderChart)

// 真实板块数据（从 API 加载）
const sector = reactive({
  code: sectorName,
  name: sectorName,
  price: 0,
  changePercent: 0,
  upCount: 0,
  downCount: 0,
  amount: '0',
  leader: '',
  totalMarketCap: '0',
  stockCount: 0,
})

const chanlunStats = reactive({
  dingCount: 0, diCount: 0, biCount: 0, zhongshuCount: 0,
  trendType: '', level: '', currentBi: '',
  zhongshuInfo: [] as { zg: number; zd: number; name: string }[],
  pricePosition: '',
  lastDingFeng: { price: 0, date: '' },
  lastDiFeng: { price: 0, date: '' },
  buyPoints: [] as { type: string; price: number; desc: string }[],
  sellPoints: [] as { type: string; price: number; desc: string }[],
  beichi: '',
  signals: [] as { type: string; text: string }[],
})

const quant = reactive({
  ma5: null as number | null, ma20: null as number | null,
  macd: null as number | null, rsi: null as number | null,
  kdjK: null as number | null, kdjD: null as number | null,
})

const constituents = ref<{ code: string; name: string; price: number; changePercent: number; change: number }[]>([])
const totalConstituents = ref(0)
const loadingAllConstituents = ref(false)
const allConstituentsLoaded = ref(false)

const INITIAL_LIMIT = 20

const displayedConstituents = computed(() => {
  if (allConstituentsLoaded.value) return constituents.value
  return constituents.value.slice(0, INITIAL_LIMIT)
})

/** 加载全部成分股（懒加载） */
async function loadAllConstituents() {
  if (loadingAllConstituents.value || allConstituentsLoaded.value) return
  loadingAllConstituents.value = true
  try {
    const res = await getStockList({ industry: sectorName, page: 1, size: 999 }) as any
    if (res?.records?.length) {
      constituents.value = res.records.map((r: any) => ({
        code: r.stockCode, name: r.stockName,
        price: Number(r.price) || 0,
        changePercent: Number(r.changePct) || 0,
        change: Number(r.change) || 0,
      }))
      allConstituentsLoaded.value = true
    }
  } catch (e) {
    console.warn('[Sector] loadAllConstituents failed:', e)
  } finally {
    loadingAllConstituents.value = false
  }
}

/** 从后端 API 加载板块数据（排行+成分股+K线） */
async function loadSectorData() {
  loading.value = true
  try {
    // 1. 获取行业排行数据
    const ranking = await getSectorRanking() as any[]
    if (Array.isArray(ranking)) {
      const mySector = ranking.find((s) => s.industry === sectorName)
      if (mySector) {
        Object.assign(sector, {
          code: sectorName, name: sectorName,
          stockCount: Number(mySector.stockCount) || 0,
          upCount: Number(mySector.upCount) || 0,
          downCount: (Number(mySector.stockCount) || 0) - (Number(mySector.upCount) || 0),
          changePercent: Number(mySector.avgChangePct) || 0,
        })
      }
    }
    // 2. 获取该行业的成分股（初始只加载前20只）
    const stockRes = await getStockList({ industry: sectorName, page: 1, size: 20 }) as any
    if (stockRes?.records?.length) {
      totalConstituents.value = stockRes.total || stockRes.records.length
      constituents.value = stockRes.records.map((r: any) => ({
        code: r.stockCode, name: r.stockName,
        price: Number(r.price) || 0,
        changePercent: Number(r.changePct) || 0,
        change: Number(r.change) || 0,
      }))
      if (constituents.value.length > 0) {
        sector.price = constituents.value.reduce((s, c) => s + c.price, 0) / constituents.value.length
        // 从成分股计算总成交额（取最大成交额的股票为领涨股）
        const totalVolume = stockRes.records.reduce((s: number, r: any) => s + (Number(r.volume) || 0), 0)
        sector.amount = totalVolume > 0 ? (totalVolume / 100000000).toFixed(2) + '亿' : '0'
        // 涨幅最高的为领涨股
        const sorted = [...stockRes.records].sort((a: any, b: any) => (Number(b.changePct) || 0) - (Number(a.changePct) || 0))
        if (sorted.length > 0) sector.leader = sorted[0].stockName || ''
        // 总市值（从 stock 表获取，这里用成交额估算）
        sector.totalMarketCap = '--'
      }
    }
    // 3. 加载板块 K 线数据（行业成分股均价聚合）
    const klineRaw = await getSectorKline(sectorName, 120) as any[]
    if (klineRaw && klineRaw.length > 10) {
      cachedKlineData = klineRaw.map((d) => [
        parseTradeDate(d.tradeDate),
        safeVal(d.openPrice),
        safeVal(d.closePrice),
        safeVal(d.lowPrice),
        safeVal(d.highPrice),
        safeVal(d.volume),
      ])
    }
    // 4. 从 K 线数据计算量化指标 + 缠论摘要
    if (cachedKlineData && cachedKlineData.length > 10) {
      const closes = cachedKlineData.map(d => d[2])  // index 2 = close price
      const highs = cachedKlineData.map(d => d[3])    // index 3 = high
      const lows = cachedKlineData.map(d => d[4])     // index 4 = low
      const len = closes.length

      // MA5 / MA20
      if (len >= 5) quant.ma5 = closes.slice(-5).reduce((s, v) => s + v, 0) / 5
      if (len >= 20) quant.ma20 = closes.slice(-20).reduce((s, v) => s + v, 0) / 20

      // MACD (12, 26, 9)
      if (len >= 26) {
        const ema = (prev: number, price: number, n: number) => price * (2 / (n + 1)) + prev * (1 - 2 / (n + 1))
        let ema12 = closes.slice(0, 12).reduce((s, v) => s + v, 0) / 12
        let ema26 = closes.slice(0, 26).reduce((s, v) => s + v, 0) / 26
        let macdLine = 0, signal = 0
        for (let i = 26; i < len; i++) {
          ema12 = ema(ema12, closes[i], 12)
          ema26 = ema(ema26, closes[i], 26)
          if (i >= 26) {
            macdLine = ema12 - ema26
            signal = i === 26 ? macdLine : signal * (2 / 10) + macdLine * (1 - 2 / 10)
          }
        }
        quant.macd = Math.round((macdLine - signal) * 10000) / 10000
      }

      // RSI (14)
      if (len >= 15) {
        let gain = 0, loss = 0
        for (let i = len - 14; i < len; i++) {
          const diff = closes[i] - closes[i - 1]
          if (diff > 0) gain += diff; else loss -= diff
        }
        const avgGain = gain / 14, avgLoss = loss / 14
        quant.rsi = avgLoss === 0 ? 100 : Math.round(100 - 100 / (1 + avgGain / avgLoss))
      }

      // KDJ (9, 3, 3)
      if (len >= 9) {
        const last9 = closes.slice(-9)
        const hn = Math.max(...highs.slice(-9))
        const ln = Math.min(...lows.slice(-9))
        const rsv = hn === ln ? 50 : (closes[len - 1] - ln) / (hn - ln) * 100
        quant.kdjK = Math.round((2 / 3 * 50 + 1 / 3 * rsv) * 10) / 10
        quant.kdjD = Math.round((2 / 3 * 50 + 1 / 3 * quant.kdjK) * 10) / 10
      }

      // 5. 缠论基础分析（趋势判断）
      const price = closes[len - 1]
      const ma5 = quant.ma5 ?? price
      const ma20 = quant.ma20 ?? price
      if (price > ma5 && ma5 > ma20) {
        chanlunStats.trendType = '上涨趋势'
        chanlunStats.level = '日线级别'
        chanlunStats.currentBi = '向上笔'
      } else if (price < ma5 && ma5 < ma20) {
        chanlunStats.trendType = '下跌趋势'
        chanlunStats.level = '日线级别'
        chanlunStats.currentBi = '向下笔'
      } else {
        chanlunStats.trendType = '震荡整理'
        chanlunStats.level = '日线级别'
        chanlunStats.currentBi = '盘整'
      }
      // 统计分型数量（简化: 用连续3日高低点判断）
      let dingCount = 0, diCount = 0
      for (let i = 2; i < len - 1; i++) {
        if (highs[i] > highs[i - 1] && highs[i] > highs[i + 1]) dingCount++
        if (lows[i] < lows[i - 1] && lows[i] < lows[i + 1]) diCount++
      }
      chanlunStats.dingCount = Math.round(dingCount * 0.3)
      chanlunStats.diCount = Math.round(diCount * 0.3)
      chanlunStats.biCount = Math.min(dingCount, diCount)
      chanlunStats.zhongshuCount = Math.max(0, chanlunStats.biCount - 2)
      // 最近顶底分型
      for (let i = len - 3; i >= 2; i--) {
        if (!chanlunStats.lastDingFeng.date && highs[i] > highs[i - 1] && highs[i] > highs[i + 1]) {
          chanlunStats.lastDingFeng = { price: Math.round(highs[i] * 100) / 100, date: String(cachedKlineData[i][0]) || '' }
        }
        if (!chanlunStats.lastDiFeng.date && lows[i] < lows[i - 1] && lows[i] < lows[i + 1]) {
          chanlunStats.lastDiFeng = { price: Math.round(lows[i] * 100) / 100, date: String(cachedKlineData[i][0]) || '' }
        }
        if (chanlunStats.lastDingFeng.date && chanlunStats.lastDiFeng.date) break
      }
      chanlunStats.pricePosition = price > ma5 ? '上方' : price < ma20 ? '下方' : '内部'
      chanlunStats.beichi = chanlunStats.trendType === '上涨趋势' ? '顶背驰' : chanlunStats.trendType === '下跌趋势' ? '底背驰' : '无背驰'
    }
  } catch (_e) { console.warn('[Sector] loadSectorData failed:', _e) }
  finally { loading.value = false }
}

function handleResizeCb() { handleResize() }

onMounted(async () => {
  await loadSectorData()
  nextTick(renderChart)
  window.addEventListener('resize', handleResizeCb)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResizeCb)
  disposeChart()
})

watch([showChanlun, activePeriod], () => { nextTick(renderChart) })
</script>

<style scoped lang="scss">
.sector-detail {
  max-width: 1200px;
  margin: 0 auto;
  padding: $spacing-lg;
}

.sector-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: $spacing-lg;
}

.sector-info {
  h2 {
    font-size: 22px;
    margin-bottom: $spacing-xs;

    .sector-code {
      font-size: 14px;
      color: $ink-muted-48;
      font-weight: 400;
      background: rgba(0,102,204,0.1);
      padding: 2px 8px;
      border-radius: $rounded-xs;
      margin-left: 8px;
    }
  }

  .current-price {
    font-family: $font-display;
    font-size: 36px;
    font-weight: 600;
  }

  .price-change {
    font-size: 18px;
    font-weight: 500;
    margin-left: $spacing-md;
  }

  .sector-meta {
    display: flex;
    gap: $spacing-md;
    margin-top: $spacing-xs;
    color: $ink-muted-48;
  }
}

.chart-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-sm;
  padding: 0 0 $spacing-sm;
  flex-wrap: wrap;
  gap: $spacing-sm;

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    flex-wrap: wrap;
  }

  .period-tabs {
    display: flex;
    gap: 2px;
    background: $canvas-parchment;
    border-radius: $rounded-sm;
    padding: 2px;

    .period-btn {
      padding: 6px 14px;
      border: none;
      background: transparent;
      font-size: 13px;
      color: $ink-muted-48;
      cursor: pointer;
      border-radius: $rounded-xs;
      transition: all 0.15s;

      &:hover { color: $ink; }
      &.active { background: $canvas; color: $primary; font-weight: 600; box-shadow: $shadow-card; }
    }
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: $spacing-md;
  }
}

.switch-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: $ink-muted-48;
  cursor: pointer;

  &.active { color: $primary; font-weight: 500; }
}

.indicator-group {
  display: flex;
  align-items: center;
  gap: 3px;

  .group-label { font-size: 11px; color: $ink-muted-48; margin-right: 2px; opacity: 0.6; }
}

.indicator-chip {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 4px 10px;
  border: 1px solid $hairline;
  border-radius: $rounded-pill;
  font-size: 12px;
  color: $ink-muted-48;
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;

  &:hover { border-color: $primary; color: $primary; }
  &.active { background: $primary; border-color: $primary; color: white; }

  &.vol-chip { font-weight: 600;
    &.active { background: $primary; border-color: $primary; color: white; }
  }

  .ind-settings {
    display: inline-flex;
    align-items: center;
    margin-left: 2px;
    font-size: 12px;
    padding: 2px;
    border-radius: 50%;
    transition: background 0.15s;

    &:hover { background: rgba(255,255,255,0.2); }
  }
}

.chart-main {
  background: $canvas;
  border: 1px solid $divider-soft;
  border-radius: $rounded-lg;
  overflow: hidden;
  margin-bottom: $spacing-lg;
}

.kline-chart { height: 420px; }
.bottom-chart { height: 150px; border-top: 1px solid $divider-soft; }

// 参数设置弹窗
:deep(.params-dialog) {
  .el-dialog__body { padding: 12px 20px; }
}

.params-form {
  .param-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 10px 0;
    border-bottom: 1px solid $divider-soft;

    &:last-child { border-bottom: none; }

    .param-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    label { font-size: 13px; color: $ink; font-weight: 500; }

    .param-hint {
      margin: 0;
      font-size: 11px;
      color: $ink-muted-48;
      line-height: 1.4;
    }
  }
}

.bottom-section { display: flex; flex-direction: column; gap: $spacing-md; }
.row-2col { display: grid; grid-template-columns: 1fr 1fr; gap: $spacing-md; }

.info-card {
  background: $canvas-parchment; border-radius: $rounded-lg; padding: $spacing-lg;
  h4 { font-size: 15px; margin-bottom: $spacing-md; }
  .info-grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 0 $spacing-lg; }
  .info-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid $divider-soft; font-size: 13px;
    &:nth-last-child(-n+2) { border-bottom: none; }
    .label { color: $ink-muted-48; }
    .val { font-weight: 500; }
  }
}

.quant-card { position: relative; }

.chanlun-card {
  h4 { display: flex; align-items: center; justify-content: space-between; margin-bottom: $spacing-sm; }
}
.trend-badge { font-size: 11px; font-weight: 500; padding: 2px 10px; border-radius: $rounded-pill;
  &.rise { background: rgba(231,76,60,0.1); color: $rise; }
  &.fall { background: rgba(39,174,96,0.1); color: $fall; }
  &.flat { background: rgba(0,102,204,0.1); color: $primary; }
}
.cl-overview { display: flex; gap: $spacing-lg; margin-bottom: $spacing-md;
  .ov-item { display: flex; flex-direction: column; gap: 2px;
    .label { font-size: 11px; color: $ink-muted-48; }
    .val { font-size: 14px; font-weight: 600; }
  }
}
.cl-wide-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: $spacing-md; margin-bottom: $spacing-md; }
.cl-wide-item { .section-label { display: block; font-size: 10px; font-weight: 600; color: $ink-muted-48; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; } }
.chanlun-stats-h { display: flex; gap: 2px;
  .stat-h { flex: 1; display: flex; flex-direction: column; align-items: center; background: rgba(0,0,0,0.02); border-radius: $rounded-xs; padding: 6px 2px;
    .label { font-size: 10px; color: $ink-muted-48; }
    .val { font-size: 18px; font-weight: 700; font-family: $font-display; }
    &.cl-ding { color: #e74c3c; } &.cl-di { color: #27ae60; } &.cl-zs { color: $primary; }
  }
}
.zhongshu-list { display: flex; flex-direction: column; gap: 3px; margin-bottom: $spacing-xs;
  .zhongshu-item { display: flex; align-items: center; justify-content: space-between; padding: 3px 8px; background: rgba(41,151,255,0.06); border-radius: $rounded-xs; border-left: 3px solid rgba(41,151,255,0.4);
    .zs-name { font-size: 11px; font-weight: 500; color: $ink; }
    .zs-range { font-size: 11px; color: $ink-muted-48; font-family: $font-display; }
  }
}
.position-row { display: flex; justify-content: space-between; align-items: center; padding: 2px 0;
  .label { font-size: 11px; color: $ink-muted-48; }
  .pos-badge { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: $rounded-pill;
    &.above { background: rgba(231,76,60,0.1); color: $rise; }
    &.inside { background: rgba(41,151,255,0.1); color: $primary; }
    &.below { background: rgba(39,174,96,0.1); color: $fall; }
  }
}
.fengxing-list { display: flex; flex-direction: column; gap: 4px;
  .fengxing-item { display: flex; align-items: center; gap: $spacing-xs; padding: 3px 6px; background: rgba(0,0,0,0.02); border-radius: $rounded-xs;
    .label { font-size: 10px; color: $ink-muted-48; min-width: 32px; }
    .val { font-size: 14px; font-weight: 700; font-family: $font-display; min-width: 56px; }
    .date { font-size: 10px; color: $ink-muted-48; }
    .ding-price { color: #e74c3c; } .di-price { color: #27ae60; }
  }
}
.signal-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: $spacing-xs; }
.point-badge { font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: $rounded-xs;
  &.buy { background: rgba(231,76,60,0.08); color: $rise; }
  &.sell { background: rgba(39,174,96,0.08); color: $fall; }
  .point-desc { font-weight: 400; opacity: 0.8; }
}
.no-points { font-size: 11px; color: $ink-muted-48; font-style: italic; }
.beichi-row { display: flex; align-items: center; gap: $spacing-xs;
  .label { font-size: 11px; color: $ink-muted-48; }
  .beichi-badge { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: $rounded-pill;
    &.ding { background: rgba(231,76,60,0.1); color: $rise; }
    &.di { background: rgba(39,174,96,0.1); color: $fall; }
    &.none { background: rgba(0,0,0,0.03); color: $ink-muted-48; }
  }
}
.signals { display: flex; flex-wrap: wrap; gap: $spacing-xs; margin-top: $spacing-xs; padding-top: $spacing-xs; border-top: 1px solid $divider-soft; }
.signal-badge { padding: 3px 10px; border-radius: $rounded-pill; font-size: 11px; font-weight: 500;
  &.buy { background: rgba(231,76,60,0.1); color: $rise; }
  &.hold { background: rgba(243,156,18,0.1); color: #f39c12; }
  &.sell { background: rgba(39,174,96,0.1); color: $fall; }
}
.quant-stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: $spacing-sm;
  .stat { display: flex; flex-direction: column; gap: 2px;
    .label { font-size: 12px; color: $ink-muted-48; }
    .val { font-size: 18px; font-weight: 600; }
  }
}

.section {
  margin-top: $spacing-lg;
  margin-bottom: $spacing-xl;
}

.section-header {
  margin-bottom: $spacing-md;
  h4 { margin: 0; }
}

.constituent-table {
  background: $canvas;
  border: 1px solid $divider-soft;
  border-radius: $rounded-lg;
  overflow: hidden;

  .table-header {
    display: grid;
    grid-template-columns: 1fr 80px 100px 100px 100px;
    gap: $spacing-sm;
    padding: $spacing-sm $spacing-lg;
    background: $canvas-parchment;
    font-size: 13px;
    color: $ink-muted-48;
  }

  .table-footer {
    display: flex;
    justify-content: center;
    padding: 16px 0;
    border-top: 1px solid $divider-soft;
    cursor: pointer;

    .footer-btn {
      font-size: 13px;
      font-weight: 500;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 24px;
      border-radius: 20px;
      color: rgba(255, 255, 255, 0.55);
      background: transparent;
      border: 1px solid rgba(255, 255, 255, 0.08);
      transition: all 0.25s ease;

      &:hover {
        color: #F59E0B;
        background: rgba(245, 158, 11, 0.08);
        border-color: rgba(245, 158, 11, 0.25);
      }

      &:active {
        transform: scale(0.97);
      }

      :deep(.el-icon) {
        font-size: 15px;
      }
    }
  }

  .table-row {
    display: grid;
    grid-template-columns: 1fr 80px 100px 100px 100px;
    gap: $spacing-sm;
    padding: $spacing-md $spacing-lg;
    border-top: 1px solid $divider-soft;
    font-size: 14px;
    align-items: center;
    cursor: pointer;
    transition: background 0.15s;

    &:hover { background: $surface-pearl; }
  }
}
</style>
