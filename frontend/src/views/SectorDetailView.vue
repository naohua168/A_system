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
    <div class="chart-main" ref="chartRef">
      <div class="kline-chart" ref="klineChartRef"></div>
      <div class="bottom-chart" ref="bottomChartRef"></div>
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
            <div class="stat"><span class="label">MA5</span><span class="val">{{ quant.ma5.toFixed(2) }}</span></div>
            <div class="stat"><span class="label">MA20</span><span class="val">{{ quant.ma20.toFixed(2) }}</span></div>
            <div class="stat"><span class="label">MACD</span><span class="val" :class="quant.macd >= 0 ? 'text-rise' : 'text-fall'">{{ quant.macd.toFixed(4) }}</span></div>
            <div class="stat"><span class="label">RSI</span><span class="val" :class="quant.rsi > 70 ? 'text-rise' : quant.rsi < 30 ? 'text-fall' : ''">{{ quant.rsi.toFixed(1) }}</span></div>
            <div class="stat"><span class="label">KDJ-K</span><span class="val">{{ quant.kdjK.toFixed(1) }}</span></div>
            <div class="stat"><span class="label">KDJ-D</span><span class="val">{{ quant.kdjD.toFixed(1) }}</span></div>
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
        <h4>成分股 ({{ constituents.length }})</h4>
      </div>
      <div class="constituent-table">
        <div class="table-header">
          <span>名称</span><span>代码</span><span>现价</span><span>涨跌幅</span><span>涨跌额</span>
        </div>
        <div v-for="s in constituents" :key="s.code"
          class="table-row"
          @click="$router.push(`/stock/${s.code}`)"
        >
          <span><strong>{{ s.name }}</strong></span>
          <span class="caption">{{ s.code }}</span>
          <span>{{ s.price.toFixed(2) }}</span>
          <span :class="s.changePercent >= 0 ? 'text-rise' : 'text-fall'">{{ s.changePercent >= 0 ? '+' : '' }}{{ s.changePercent.toFixed(2) }}%</span>
          <span :class="s.changePercent >= 0 ? 'text-rise' : 'text-fall'">{{ s.change >= 0 ? '+' : '' }}{{ s.change.toFixed(2) }}</span>
        </div>
      </div>
    </section>
  </div>

  <!-- 参数设置弹窗 -->
  <el-dialog v-model="paramsDialogVisible" :title="`${paramsDialogTitle} 参数设置`" width="380px" :modal="false" class="params-dialog">
    <div v-if="paramsTarget === 'macd'" class="params-form">
      <div class="param-item"><label>快线周期 (EMA短)</label><el-input-number v-model="params.macd.fast" :min="5" :max="30" size="small" controls-position="right" /></div>
      <div class="param-item"><label>慢线周期 (EMA长)</label><el-input-number v-model="params.macd.slow" :min="10" :max="60" size="small" controls-position="right" /></div>
      <div class="param-item"><label>信号周期 (DEA)</label><el-input-number v-model="params.macd.signal" :min="5" :max="30" size="small" controls-position="right" /></div>
    </div>
    <div v-if="paramsTarget === 'kdj'" class="params-form">
      <div class="param-item"><label>计算周期 (N)</label><el-input-number v-model="params.kdj.period" :min="5" :max="30" size="small" controls-position="right" /></div>
    </div>
    <div v-if="paramsTarget === 'rsi'" class="params-form">
      <div class="param-item"><label>计算周期 (N)</label><el-input-number v-model="params.rsi.period" :min="5" :max="30" size="small" controls-position="right" /></div>
    </div>
    <div v-if="paramsTarget === 'ma'" class="params-form">
      <div class="param-item"><label>MA1 周期</label><el-input-number v-model="params.ma.periods[0]" :min="3" :max="60" size="small" controls-position="right" /></div>
      <div class="param-item"><label>MA2 周期</label><el-input-number v-model="params.ma.periods[1]" :min="3" :max="120" size="small" controls-position="right" /></div>
    </div>
    <div v-if="paramsTarget === 'boll'" class="params-form">
      <div class="param-item"><label>计算周期</label><el-input-number v-model="params.boll.period" :min="5" :max="60" size="small" controls-position="right" /></div>
      <div class="param-item"><label>标准差倍数</label><el-input-number v-model="params.boll.multiplier" :min="1" :max="5" :step="0.5" size="small" controls-position="right" /></div>
    </div>
    <template #footer>
      <el-button @click="paramsDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="applyParams">确认</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Star, Setting } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getStockList } from '@/api/stock'
import { getSectorRanking } from '@/api/analysis'

const route = useRoute()
const sectorName = decodeURIComponent(route.params.name as string)
const activePeriod = ref('day')
const showChanlun = ref(false)

// 缓存K线数据（仅由后续逻辑填充，当前无API）
let cachedKlineData: number[][] | null = null
function getKlineData() {
  return cachedKlineData || []
}

const loading = ref(true)

const chartRef = ref<HTMLElement>()
const klineChartRef = ref<HTMLElement>()
const bottomChartRef = ref<HTMLElement>()

let klineChart: echarts.ECharts | null = null
let bottomChart: echarts.ECharts | null = null

const periods = [
  { key: '5min', label: '5分' }, { key: '15min', label: '15分' },
  { key: '30min', label: '30分' }, { key: '60min', label: '60分' },
  { key: 'day', label: '日K' }, { key: 'week', label: '周K' }, { key: 'month', label: '月K' },
]

// --- 指标分组 ---
const overlayIndicators = ref([
  { key: 'ma', label: 'MA', active: true },
  { key: 'boll', label: 'BOLL', active: false },
])

const bottomIndicators = ref([
  { key: 'macd', label: 'MACD' },
  { key: 'kdj', label: 'KDJ' },
  { key: 'rsi', label: 'RSI' },
])

const bottomActive = ref<string | null>(null)

function toggleOverlay(ind: { key: string; active: boolean }) {
  ind.active = !ind.active
  renderChart()
}

function selectBottomIndicator(ind: { key: string }) {
  bottomActive.value = bottomActive.value === ind.key ? null : ind.key
  renderChart()
}

// --- 参数设置 ---
const paramsDialogVisible = ref(false)
const paramsDialogTitle = ref('')
const paramsTarget = ref('')
const params = reactive({
  macd: { fast: 12, slow: 26, signal: 9 },
  kdj: { period: 9 },
  rsi: { period: 14 },
  ma: { periods: [5, 20] },
  boll: { period: 20, multiplier: 2 },
})

function openParams(ind: { key: string; label: string }) {
  paramsTarget.value = ind.key
  paramsDialogTitle.value = ind.label
  paramsDialogVisible.value = true
}

function applyParams() {
  paramsDialogVisible.value = false
  renderChart()
}

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

// 从 API 加载板块数据
async function loadSectorData() {
  loading.value = true
  try {
    // 1. 获取行业排行数据
    const ranking: any = await getSectorRanking()
    if (Array.isArray(ranking)) {
      const mySector = ranking.find((s: any) => s.industry === sectorName)
      if (mySector) {
        Object.assign(sector, {
          code: sectorName,
          name: sectorName,
          stockCount: Number(mySector.stockCount) || 0,
          upCount: Number(mySector.upCount) || 0,
          downCount: (Number(mySector.stockCount) || 0) - (Number(mySector.upCount) || 0),
          changePercent: Number(mySector.avgChangePct) || 0,
        })
      }
    }
    // 2. 获取该行业的成分股
    const stockRes: any = await getStockList({ industry: sectorName, page: 1, size: 50 })
    if (stockRes?.records?.length) {
      constituents.value = stockRes.records.map((r: any) => ({
        code: r.stockCode,
        name: r.stockName,
        price: Number(r.price) || 0,
        changePercent: Number(r.changePct) || 0,
        change: Number(r.change) || 0,
      }))
      // 用成分股的平均价作为板块指数价格
      if (constituents.value.length > 0) {
        sector.price = constituents.value.reduce((s, c) => s + c.price, 0) / constituents.value.length
      }
    }
  } catch (_e) { console.warn('[Sector] 加载板块数据失败:', _e) }
  finally { loading.value = false }
}

// 缠论数据（当前无后端API，仅保留空结构供前端占位）
function getEmptyChanlunData() {
  return { bi: [] as any[], zhongshu: [] as any[], fengxing: [] as any[] }
}

// --- Technical Indicator Calculations (same as StockDetailView) ---
function calcMA(data: number[][], days: number) {
  const result: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (i < days - 1) { result.push(null); continue }
    let sum = 0
    for (let j = i - days + 1; j <= i; j++) sum += (data[j][2] + data[j][3]) / 2
    result.push(+(sum / days).toFixed(2))
  }
  return result
}

function calcBOLL(data: number[][], period = 20, k = 2) {
  const mid = calcMA(data, period)
  const up: (number | null)[] = []; const down: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (mid[i] === null) { up.push(null); down.push(null); continue }
    let sum = 0
    for (let j = i - period + 1; j <= i; j++) {
      const avg = (data[j][2] + data[j][3]) / 2
      sum += (avg - (mid[i] as number)) ** 2
    }
    const std = Math.sqrt(sum / period)
    up.push(parseFloat(((mid[i] as number) + k * std).toFixed(2)))
    down.push(parseFloat(((mid[i] as number) - k * std).toFixed(2)))
  }
  return { up, mid, down }
}

function calcMACD(data: number[][], fast = 12, slow = 26, signal = 9) {
  const closes = data.map(d => (d[2] + d[3]) / 2)
  const emaF: number[] = []; const emaS: number[] = []
  const dif: number[] = []; const dea: number[] = []; const macd: number[] = []
  for (let i = 0; i < closes.length; i++) {
    if (i === 0) { emaF[i] = closes[i]; emaS[i] = closes[i] }
    else { emaF[i] = emaF[i - 1] * (fast - 1) / (fast + 1) + closes[i] * 2 / (fast + 1); emaS[i] = emaS[i - 1] * (slow - 1) / (slow + 1) + closes[i] * 2 / (slow + 1) }
    dif[i] = emaF[i] - emaS[i]
    dea[i] = i === 0 ? dif[i] : dea[i - 1] * (signal - 1) / (signal + 1) + dif[i] * 2 / (signal + 1)
    macd[i] = (dif[i] - dea[i]) * 2
  }
  return { dif: dif.map(v => +v.toFixed(4)), dea: dea.map(v => +v.toFixed(4)), macd: macd.map(v => +v.toFixed(4)) }
}

function calcKDJ(data: number[][], period = 9) {
  const kV: number[] = []; const dV: number[] = []; const jV: number[] = []
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) { kV.push(50); dV.push(50); jV.push(50); continue }
    const low = Math.min(...data.slice(i - period + 1, i + 1).map(d => d[3]))
    const high = Math.max(...data.slice(i - period + 1, i + 1).map(d => d[1]))
    const close = data[i][2]; const rsv = ((close - low) / (high - low)) * 100
    const k = kV[i - 1] || 50; const kVal = k * 2 / 3 + rsv / 3; const dVal = dV[i - 1] * 2 / 3 + kVal / 3
    kV.push(+kVal.toFixed(1)); dV.push(+dVal.toFixed(1)); jV.push(+(3 * kVal - 2 * dVal).toFixed(1))
  }
  return { k: kV, d: dV, j: jV }
}

function calcRSI(data: number[][], period = 14) {
  const closes = data.map(d => d[2]); const rsi: (number | null)[] = []
  for (let i = 0; i < closes.length; i++) {
    if (i < period) { rsi.push(null); continue }
    let gains = 0, losses = 0
    for (let j = i - period + 1; j <= i; j++) { const diff = closes[j] - closes[j - 1]; if (diff > 0) gains += diff; else losses -= diff }
    rsi.push(+((100 - 100 / (1 + gains / (losses || 0.001))).toFixed(1)))
  }
  return rsi
}

function renderChart() {
  if (!klineChartRef.value) return
  const klineData = getKlineData()
  if (klineData.length === 0) return
  const dates = klineData.map(d => new Date(d[0]).toLocaleDateString('zh-CN'))
  const volumes = klineData.map(d => d[5])

  if (!klineChart) klineChart = echarts.init(klineChartRef.value)

  const maData: { [key: string]: (number | null)[] } = {}
  params.ma.periods.forEach(p => { maData[`ma${p}`] = calcMA(klineData, p) })
  const bollData = calcBOLL(klineData, params.boll.period, params.boll.multiplier)

  const series: any[] = [{
    name: 'K线', type: 'candlestick',
    data: klineData.map(d => [d[1], d[2], d[3], d[4]]),
    itemStyle: { color: '#e74c3c', color0: '#27ae60', borderColor: '#e74c3c', borderColor0: '#27ae60' },
  }]

  // MA overlay
  const maActive = overlayIndicators.value.find(i => i.key === 'ma')?.active
  if (maActive) {
    const maColors = ['#f39c12', '#9b59b6', '#1abc9c', '#e67e22']
    params.ma.periods.forEach((p, idx) => {
      series.push({
        name: `MA${p}`, type: 'line', data: maData[`ma${p}`],
        smooth: true, symbol: 'none',
        lineStyle: { width: 1, color: maColors[idx % maColors.length] },
      })
    })
  }

  // BOLL overlay
  const bollActive = overlayIndicators.value.find(i => i.key === 'boll')?.active
  if (bollActive) {
    series.push(
      { name: 'BOLL-UP', type: 'line', data: bollData.up, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#3498db', type: 'dashed' } },
      { name: 'BOLL-MID', type: 'line', data: bollData.mid, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#3498db' } },
      { name: 'BOLL-DN', type: 'line', data: bollData.down, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#3498db', type: 'dashed' }, areaStyle: { color: 'rgba(52,152,219,0.05)' } },
    )
  }

  // 缠论 (TradingView风格)
  if (showChanlun.value) {
    const clData = getEmptyChanlunData()
    // 中枢 - 半透明框 + 虚线边框
    clData.zhongshu.forEach(zs => {
      series.push({
        type: 'custom',
        renderItem: (pa: any, api: any) => {
          const s = api.coord([zs.startX, zs.high]); const e = api.coord([zs.endX, zs.low])
          return {
            type: 'group', children: [
              { type: 'rect', shape: { x: s[0], y: s[1], width: e[0] - s[0], height: e[1] - s[1] }, style: { fill: 'rgba(41,151,255,0.12)', stroke: '#2997ff', lineWidth: 1.5, lineDash: [4, 3] } },
            ]
          }
        }, data: [0], z: 10,
      })
    })
    // 笔 - 红色上涨/绿色下跌
    clData.bi.forEach(b => {
      const isUp = b.y1 >= b.y0
      series.push({
        type: 'line', data: [[b.x0, b.y0], [b.x1, b.y1]], symbol: 'none',
        lineStyle: { width: 2, color: isUp ? '#e74c3c' : '#27ae60' }, z: 11,
      })
    })
    // 分型 - 三角形标记
    const dings = clData.fengxing.filter(f => f.type === 'ding')
    const dis = clData.fengxing.filter(f => f.type === 'di')
    if (dings.length) {
      series.push({
        name: '顶分型', type: 'scatter',
        data: dings.map(f => [f.x, f.price]),
        symbol: 'triangle', symbolSize: [14, 10], symbolRotate: 180,
        itemStyle: { color: '#e74c3c' }, z: 12,
        label: { show: true, formatter: '顶', color: '#e74c3c', fontSize: 10, fontWeight: 'bold', position: 'top' },
      })
    }
    if (dis.length) {
      series.push({
        name: '底分型', type: 'scatter',
        data: dis.map(f => [f.x, f.price]),
        symbol: 'triangle', symbolSize: [14, 10],
        itemStyle: { color: '#27ae60' }, z: 12,
        label: { show: true, formatter: '底', color: '#27ae60', fontSize: 10, fontWeight: 'bold', position: 'bottom' },
      })
    }
  }

  klineChart.setOption({
    animation: false,
    grid: { left: '8%', right: '8%', top: '12%', bottom: '15%' },
    xAxis: { type: 'category', data: dates, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { fontSize: 11, color: '#999' } },
    yAxis: { scale: true, splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } }, axisLabel: { fontSize: 11, color: '#999' } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, backgroundColor: 'rgba(30,30,30,0.9)', borderColor: 'rgba(255,255,255,0.1)', textStyle: { color: '#fff', fontSize: 12 } },
    dataZoom: [{
      type: 'inside',
      start: 65,
      end: 100,
      minValueSpan: 10,
    }, {
      type: 'slider',
      start: 65,
      end: 100,
      height: 24,
      bottom: 2,
      borderColor: 'rgba(0,0,0,0.08)',
      backgroundColor: 'rgba(0,0,0,0.02)',
      fillerColor: 'rgba(41,151,255,0.25)',
      borderColor: 'rgba(41,151,255,0.3)',
      handleStyle: { color: '#2997ff', borderColor: '#2997ff', borderWidth: 2, shadowBlur: 4, shadowColor: 'rgba(41,151,255,0.3)' },
      textStyle: { fontSize: 11, color: '#666' },
      dataBackground: { lineStyle: { color: '#ddd', width: 1 }, areaStyle: { color: 'rgba(0,0,0,0.03)' } },
      selectedDataBackground: { lineStyle: { color: '#2997ff', width: 1 }, areaStyle: { color: 'rgba(41,151,255,0.1)' } },
    }],
    series,
  }, true)

  // --- 底部图 (VOL 或 指标) ---
  if (!bottomChart) bottomChart = echarts.init(bottomChartRef.value)

  let bottomOption: echarts.EChartsOption

  if (bottomActive.value === 'macd') {
    const macdData = calcMACD(klineData, params.macd.fast, params.macd.slow, params.macd.signal)
    bottomOption = {
      animation: false, grid: { left: '8%', right: '8%', top: '15%', bottom: '6%' },
      xAxis: { type: 'category', data: dates, axisTick: { show: false }, axisLabel: { show: false } },
      yAxis: { scale: true, splitLine: { show: false }, axisLabel: { fontSize: 10, color: '#999' } },
      series: [
        { name: 'DIF', type: 'line', data: macdData.dif, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#3498db' } },
        { name: 'DEA', type: 'line', data: macdData.dea, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#e67e22' } },
        { name: 'MACD', type: 'bar', data: macdData.macd.map((v: number) => ({ value: v, itemStyle: { color: v >= 0 ? '#e74c3c' : '#27ae60', opacity: 0.6 } })), barWidth: '50%' },
      ],
    }
  } else if (bottomActive.value === 'kdj') {
    const kdjData = calcKDJ(klineData, params.kdj.period)
    bottomOption = {
      animation: false, grid: { left: '8%', right: '8%', top: '12%', bottom: '6%' },
      xAxis: { type: 'category', data: dates, axisTick: { show: false }, axisLabel: { show: false } },
      yAxis: { scale: true, splitLine: { show: false }, axisLabel: { fontSize: 10, color: '#999' } },
      series: [
        { name: 'K', type: 'line', data: kdjData.k, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#3498db' } },
        { name: 'D', type: 'line', data: kdjData.d, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#e67e22' } },
        { name: 'J', type: 'line', data: kdjData.j, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#9b59b6' } },
      ],
    }
  } else if (bottomActive.value === 'rsi') {
    const rsiData = calcRSI(klineData, params.rsi.period)
    bottomOption = {
      animation: false, grid: { left: '8%', right: '8%', top: '12%', bottom: '6%' },
      xAxis: { type: 'category', data: dates, axisTick: { show: false }, axisLabel: { show: false } },
      yAxis: { scale: false, min: 0, max: 100, splitLine: { show: false }, axisLabel: { fontSize: 10, color: '#999' } },
      series: [{
        name: 'RSI', type: 'line', data: rsiData, smooth: true, symbol: 'none',
        lineStyle: { width: 1.5, color: '#f39c12' },
        markLine: { silent: true, symbol: 'none', data: [
          { yAxis: 70, label: { show: true, formatter: '超买 70', color: '#e74c3c', position: 'insideEndTop' }, lineStyle: { color: '#e74c3c', type: 'dashed', width: 1 } },
          { yAxis: 30, label: { show: true, formatter: '超卖 30', color: '#27ae60', position: 'insideEndBottom' }, lineStyle: { color: '#27ae60', type: 'dashed', width: 1 } },
        ] },
      }],
    }
  } else {
    // 默认: 成交量 VOL
    bottomOption = {
      animation: false, grid: { left: '8%', right: '8%', top: '10%', bottom: '4%' },
      xAxis: { type: 'category', data: dates, axisTick: { show: false }, axisLabel: { show: false } },
      yAxis: { type: 'value', splitLine: { show: false }, axisLabel: { fontSize: 10, color: '#999' } },
      series: [{
        type: 'bar',
        data: volumes.map((v, i) => ({ value: v, itemStyle: { color: klineData[i][2] >= klineData[i][1] ? '#e74c3c' : '#27ae60', opacity: 0.5 } })),
        barWidth: '60%',
      }],
    }
  }

  bottomChart.setOption(bottomOption, true)
}

function handleResize() { klineChart?.resize(); bottomChart?.resize() }

onMounted(async () => {
  await loadSectorData()
  nextTick(renderChart)
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  klineChart?.dispose(); bottomChart?.dispose()
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
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid $divider-soft;

    &:last-child { border-bottom: none; }

    label { font-size: 13px; color: $ink; }
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
