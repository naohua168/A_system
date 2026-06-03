<template>
  <div class="stock-detail">
    <!-- 股票基本信息 -->
    <div class="stock-header">
      <div class="stock-info">
        <h2>{{ stock.name }} <span class="stock-code">{{ stock.code }}</span></h2>
        <div class="stock-price-section">
          <span class="current-price" :class="stock.changePercent >= 0 ? 'text-rise' : 'text-fall'">
            {{ safeNum(stock.price, 2) }}
          </span>
          <span class="price-change" :class="stock.changePercent >= 0 ? 'text-rise' : 'text-fall'">
            {{ stock.changePercent >= 0 ? '+' : '' }}{{ safeNum(stock.changePercent, 2) }}%
          </span>
        </div>
        <div class="stock-meta caption">
          <span>最高: {{ safeNum(stock.high, 2) }}</span>
          <span>最低: {{ safeNum(stock.low, 2) }}</span>
          <span>开盘: {{ safeNum(stock.open, 2) }}</span>
          <span>昨收: {{ safeNum(stock.preClose, 2) }}</span>
          <span>成交量: {{ stock.volume ? formatVol(stock.volume) : '-' }}</span>
          <span>成交额: {{ stock.amount ? formatVol(stock.amount) : '-' }}</span>
        </div>
      </div>
      <div class="stock-actions">
        <el-button :type="isWatched ? 'danger' : 'primary'" plain round @click="toggleWatch">
          <el-icon><Star /></el-icon> {{ isWatched ? '已自选' : '加自选' }}
        </el-button>
      </div>
    </div>

    <!-- K线图控制栏 -->
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
            <!-- 参数设置按钮 -->
            <span class="ind-settings" v-if="bottomActive === ind.key" @click.stop="openParams(ind)">
              <el-icon><Setting /></el-icon>
            </span>
          </label>
        </div>
      </div>
    </div>

    <!-- K线图 -->
    <div class="chart-main" ref="chartRef" v-loading="chartLoading">
      <template v-if="!chartLoading && (!cachedKlineData || cachedKlineData.length < 10)">
        <div class="chart-empty">
          <span class="chart-empty-text">暂无K线数据</span>
        </div>
      </template>
      <template v-else>
        <div class="kline-chart" ref="klineChartRef"></div>
        <div class="bottom-chart" ref="bottomChartRef"></div>
      </template>
    </div>

    <!-- 底部信息区域 (新排版) -->
    <div class="bottom-section">
      <!-- 上行: 盘口信息 + 量化指标 + AI入口 -->
      <div class="row-2col">
        <div class="info-card">
          <h4>盘口信息</h4>
          <div class="info-grid-2col">
            <div class="info-row"><span class="label">市盈率</span><span class="val">{{ stock.pe || '-' }}</span></div>
            <div class="info-row"><span class="label">市净率</span><span class="val">{{ stock.pb || '-' }}</span></div>
            <div class="info-row"><span class="label">总市值</span><span class="val">{{ stock.totalMarketCap ? formatVol(stock.totalMarketCap) : '-' }}</span></div>
            <div class="info-row"><span class="label">流通市值</span><span class="val">{{ stock.floatMarketCap ? formatVol(stock.floatMarketCap) : '-' }}</span></div>
            <div class="info-row"><span class="label">换手率</span><span class="val">{{ safeNum(stock.turnoverRate, 2) }}%</span></div>
            <div class="info-row"><span class="label">振幅</span><span class="val">{{ safeNum(stock.amplitude, 2) }}%</span></div>
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

      <!-- 下行: 缠论分析 (数据面板) — 仅开关开启时显示 -->
      <div class="chanlun-panel" v-if="showChanlun">
        <!-- 面板头部 -->
        <div class="cl-header">
          <div class="cl-header-left">
            <svg class="cl-icon" viewBox="0 0 20 20" fill="none" width="18" height="18">
              <path d="M2 18L6 8L10 13L14 3L18 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M2 2V18H18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.3"/>
            </svg>
            <span class="cl-title">缠论技术分析</span>
          </div>
          <div class="cl-header-right">
            <span :class="['cl-trend-badge', chanlunStats.trendType === '上涨趋势' ? 'rise' : chanlunStats.trendType === '下跌趋势' ? 'fall' : 'flat']">
              <span class="cl-trend-dot"></span>
              {{ chanlunStats.trendType }}
            </span>
            <div class="cl-overview-chips">
              <div class="cl-chip">
                <span class="chip-label">级别</span>
                <span class="chip-val">{{ chanlunStats.level }}</span>
              </div>
              <div class="cl-chip">
                <span class="chip-label">当前笔</span>
                <span class="chip-val" :class="chanlunStats.currentBi.includes('向上') ? 'rise' : 'fall'">{{ chanlunStats.currentBi }}</span>
              </div>
              <div class="cl-chip">
                <span class="chip-label">位置</span>
                <span :class="['chip-val', 'pos', chanlunStats.pricePosition === '上方' ? 'above' : chanlunStats.pricePosition === '下方' ? 'below' : 'inside']">{{ chanlunStats.pricePosition }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 核心指标 2x2 -->
        <div class="cl-metrics-grid">
          <div class="cl-metric-card ding">
            <div class="metric-icon"><svg viewBox="0 0 16 16" fill="none" width="14" height="14"><path d="M8 2V14M2 8H14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></div>
            <div class="metric-val">{{ chanlunStats.dingCount }}</div>
            <div class="metric-label">顶分型</div>
          </div>
          <div class="cl-metric-card di">
            <div class="metric-icon"><svg viewBox="0 0 16 16" fill="none" width="14" height="14"><path d="M2 8H14M8 14V2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></div>
            <div class="metric-val">{{ chanlunStats.diCount }}</div>
            <div class="metric-label">底分型</div>
          </div>
          <div class="cl-metric-card bi">
            <div class="metric-icon"><svg viewBox="0 0 16 16" fill="none" width="14" height="14"><path d="M2 3L14 13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></div>
            <div class="metric-val">{{ chanlunStats.biCount }}</div>
            <div class="metric-label">笔</div>
          </div>
          <div class="cl-metric-card zs">
            <div class="metric-icon"><svg viewBox="0 0 16 16" fill="none" width="14" height="14"><rect x="3" y="5" width="10" height="6" rx="2" stroke="currentColor" stroke-width="1.5"/></svg></div>
            <div class="metric-val">{{ chanlunStats.zhongshuCount }}</div>
            <div class="metric-label">中枢</div>
          </div>
        </div>

        <!-- 详情区域 2列 -->
        <div class="cl-detail-row">
          <!-- 左列: 中枢区间 + 背驰 -->
          <div class="cl-detail-card">
            <div class="cl-detail-header">
              <svg viewBox="0 0 16 16" fill="none" width="14" height="14"><rect x="3" y="5" width="10" height="6" rx="2" stroke="currentColor" stroke-width="1.5"/><line x1="6" y1="4" x2="6" y2="12" stroke="currentColor" stroke-width="1" opacity="0.3"/><line x1="10" y1="4" x2="10" y2="12" stroke="currentColor" stroke-width="1" opacity="0.3"/></svg>
              中枢区间
            </div>
            <div class="cl-detail-body">
              <div class="zs-list">
                <div v-for="zs in chanlunStats.zhongshuInfo" :key="zs.name" class="zs-item">
                  <span class="zs-tag">{{ zs.name }}</span>
                  <span class="zs-price">{{ zs.zd.toFixed(2) }} – {{ zs.zg.toFixed(2) }}</span>
                </div>
                <div v-if="!chanlunStats.zhongshuInfo.length" class="zs-empty">暂无中枢</div>
              </div>
            </div>
          </div>

          <!-- 右列: 分型 + 买卖点 + 背驰 -->
          <div class="cl-detail-card">
            <div class="cl-detail-header">
              <svg viewBox="0 0 16 16" fill="none" width="14" height="14"><path d="M4 6L8 2L12 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M4 10L8 14L12 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              买卖信号
            </div>
            <div class="cl-detail-body">
              <!-- 分型对 -->
              <div class="fx-pair">
                <div class="fx-item ding">
                  <span class="fx-label">最近顶</span>
                  <span class="fx-price">{{ chanlunStats.lastDingFeng.price ?? '-' }}</span>
                  <span class="fx-date">{{ chanlunStats.lastDingFeng.date || '' }}</span>
                </div>
                <div class="fx-item di">
                  <span class="fx-label">最近底</span>
                  <span class="fx-price">{{ chanlunStats.lastDiFeng.price ?? '-' }}</span>
                  <span class="fx-date">{{ chanlunStats.lastDiFeng.date || '' }}</span>
                </div>
              </div>

              <!-- 买卖点标签 -->
              <div class="bp-row">
                <template v-if="chanlunStats.buyPoints.length || chanlunStats.sellPoints.length">
                  <span v-for="bp in chanlunStats.buyPoints" :key="bp.type" class="bp-tag buy">
                    {{ bp.type.replace('_', ' ') }}
                    <span class="bp-desc">{{ bp.desc }}</span>
                  </span>
                  <span v-for="sp in chanlunStats.sellPoints" :key="sp.type" class="bp-tag sell">
                    {{ sp.type.replace('_', ' ') }}
                    <span class="bp-desc">{{ sp.desc }}</span>
                  </span>
                </template>
                <span v-else class="bp-none">暂无买卖点</span>
              </div>

              <!-- 背驰 -->
              <div class="beichi-row">
                <span class="beichi-label">背驰</span>
                <span :class="['beichi-val', chanlunStats.beichi === '顶背驰' ? 'ding' : chanlunStats.beichi === '底背驰' ? 'di' : 'none']">
                  {{ chanlunStats.beichi }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 信号底栏 -->
        <div v-if="chanlunStats.signals.length" class="cl-signals-bar">
          <span class="cl-signals-label">提示</span>
          <span v-for="s in chanlunStats.signals" :key="s.text" :class="['cl-signal', s.type]">{{ s.text.replace('_', ' ') }}</span>
        </div>
      </div>
    </div>

    <!-- 参数设置弹窗（指标参数配置） -->
    <el-dialog v-model="paramsDialogVisible" :title="`${paramsDialogTitle} 参数设置`" width="420px" :modal="false" class="params-dialog" destroy-on-close>
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Star, Setting } from '@element-plus/icons-vue'
import { getStockByCode, getKlineData } from '@/api/market'
import { useStockStore } from '@/stores/stock'
import { useWatchlistStore } from '@/stores/watchlist'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { safeNum, safeVal, formatVol, parseTradeDate } from '@/utils/format'
import { getChanlunAnalysis } from '@/api/analysis'
import type { ChanlunBi, ChanlunZhongshu, ChanlunFengxing } from '@/types'
import { useTechnicalChart } from '@/composables/useTechnicalChart'
import { useIndicatorParams } from '@/composables/useIndicatorParams'
import { useStockWebSocket } from '@/composables/useStockWebSocket'
import type { KlineUpdateData } from '@/composables/useStockWebSocket'

const route = useRoute()
const stockCode = route.params.code as string
const stockStore = useStockStore()
const watchlistStore = useWatchlistStore()
const userStore = useUserStore()

// ── WebSocket 实时行情 ──
const { wsStatus, lastKlineUpdate, connect: wsConnect, disconnect: wsDisconnect } = useStockWebSocket(stockCode)

const chartRef = ref<HTMLElement>()
const klineChartRef = ref<HTMLElement>()
const bottomChartRef = ref<HTMLElement>()

const chartLoading = ref(false)
const showChanlun = ref(false)
const activePeriod = ref('day')
const isWatched = computed(() => watchlistStore.isInWatchlist(stockCode))

// ── 共享指标参数管理（在 useTechnicalChart 之前创建，避免依赖环） ──
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

// ── K线图渲染器 ──
const { renderChart, handleResize, dispose: disposeChart, setChanlunData } = useTechnicalChart(
  klineChartRef as any,
  bottomChartRef as any,
  {
    getKlineData: () => getCachedKlineData(),
    params: params as any,
    showMA: computed(() => overlayIndicators.value.find(i => i.key === 'ma')?.active ?? true),
    showBOLL: computed(() => overlayIndicators.value.find(i => i.key === 'boll')?.active ?? false),
    bottomActive: bottomActive as any,
    period: activePeriod,
  }
)

// 将渲染函数注入指标管理器，使指标切换自动触发重绘
indicator.setRenderCallback(renderChart)

// 缓存K线数据（仅由 API 填充）
let cachedKlineData: number[][] | null = null
function getCachedKlineData() {
  return cachedKlineData || []
}

// 真实股票数据（从 API 加载）
const stock = reactive({
  code: stockCode,
  name: '',
  price: 0, changePercent: 0,
  open: 0, high: 0, low: 0, preClose: 0,
  volume: 0, amount: 0,
  pe: 0, pb: 0,
  totalMarketCap: 0, floatMarketCap: 0,
  turnoverRate: 0, amplitude: 0,
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

import type { ChanlunBuySellPoint, ChanlunStats } from '@/types'

/** 缠论API原始数据包装 */
interface ChanlunRawData {
  bi: ChanlunBi[]
  zhongshu: ChanlunZhongshu[]
  fengxing: ChanlunFengxing[]
  buy_sell_points: ChanlunBuySellPoint[]
  stats: ChanlunStats
}

/** 从后端加载缠论分析数据 */
async function fetchChanlunData() {
  if (!showChanlun.value) return
  try {
    const data = await getChanlunAnalysis(stockCode, 365)
    // 后端返回 error 字段时静默处理（Python 分析失败）
    if (data && (data as any).error) {
      console.warn(`[Chanlun] API 返回错误: ${(data as any).error}`)
      setChanlunData(null, true)
      return
    }
    const stats = data.stats || {} as ChanlunStats
    const bp = (data.buy_sell_points || []) as ChanlunBuySellPoint[]
    const zs = data.zhongshu || []
    const fx = data.fengxing || []
    setChanlunData({ bi: data.bi || [], zhongshu: zs, fengxing: fx, buy_sell_points: bp, stats } as any, true)

    const buys = bp.filter((p) => p.type.startsWith('buy_'))
    const sells = bp.filter((p) => p.type.startsWith('sell_'))
    const dingFx = fx.filter((f) => f.type === 'ding')
    const diFx = fx.filter((f) => f.type === 'di')
    const hasBeiChi = buys.some((p) => p.type === 'buy_1') || sells.some((p) => p.type === 'sell_1')

    Object.assign(chanlunStats, {
      dingCount: stats.top_fractals || dingFx.length,
      diCount: stats.bottom_fractals || diFx.length,
      biCount: stats.pens || data.bi?.length || 0,
      zhongshuCount: stats.centers || zs.length,
      trendType: bp.length > 0 ? (hasBeiChi ? '趋势背驰段' : '中枢震荡') : '无信号',
      level: '日线',
      currentBi: data.bi?.length > 0 ? '向上笔' : '无',
      zhongshuInfo: zs.map((z, i) => ({
        name: `中枢${i + 1}`,
        zg: z.high,
        zd: z.low,
      })),
      pricePosition: zs.length > 0 ? (bp.find((p) => p.type === 'buy_1') ? '下方' : '内部') : '未知',
      lastDingFeng: { price: dingFx[dingFx.length - 1]?.price || 0, date: '' },
      lastDiFeng: { price: diFx[diFx.length - 1]?.price || 0, date: '' },
      buyPoints: buys.slice(0, 3).map((p) => ({ type: p.type, price: p.price, desc: p.description || '' })),
      sellPoints: sells.slice(0, 3).map((p) => ({ type: p.type, price: p.price, desc: p.description || '' })),
      beichi: hasBeiChi ? (bp[0]?.type === 'buy_1' ? '底背驰' : '顶背驰') : '无背驰',
      signals: bp.map((p) => ({ type: p.type.startsWith('buy') ? 'buy' : 'sell', text: p.type })),
    })
    console.log(`[Chanlun] API 加载成功: ${stockCode}, bi=${data.bi?.length}, zhongshu=${zs.length}, fengxing=${fx.length}`)
  } catch (e) {
    console.warn(`[Chanlun] API 异常: ${stockCode}, ${e instanceof Error ? e.message : e}`)
    setChanlunData(null, true)
  }
}

// 缓存K线数据（仅由 API 填充）
async function toggleWatch() {
  if (!userStore.isLoggedIn || !userStore.userInfo) {
    ElMessage.warning('请先登录')
    return
  }
  const isAdd = !watchlistStore.isInWatchlist(stockCode)
  try {
    if (isAdd) {
      await watchlistStore.add(userStore.userInfo.id, stockCode, 0)
      ElMessage.success('已添加自选')
    } else {
      await watchlistStore.remove(userStore.userInfo.id, stockCode, 0)
      ElMessage.success('已移除自选')
    }
    watchlistStore.optimisticToggle(stockCode, stock.name)
  } catch {
    ElMessage.error('操作失败')
  }
}

function handleResizeCb() {
  if (!klineChartRef.value?.offsetParent && !bottomChartRef.value?.offsetParent) return
  handleResize()
}

async function loadData() {
  chartLoading.value = true
  try {
    // 1. 加载股票基本信息
    const info = await getStockByCode(stockCode)
    if (info) {
      stock.name = info.stockName || (info as any).name || stockCode
      stock.pe = info.pe || 0
      stock.pb = info.pb || 0
      stock.totalMarketCap = info.totalMarketCap || 0
      stock.floatMarketCap = info.floatMarketCap || 0
    }

    // 2. 加载 K 线数据（支持多周期）
    const klineRaw = await getKlineData(stockCode, getDaysForPeriod(activePeriod.value), activePeriod.value)
    if (klineRaw && klineRaw.length > 1) {
      cachedKlineData = klineRaw.map((d) => [
        parseTradeDate(d.tradeDate),
        safeVal(d.openPrice),
        safeVal(d.closePrice),
        safeVal(d.lowPrice),
        safeVal(d.highPrice),
        safeVal(d.volume),
      ])
      // 从 K 线实时计算量化指标（API 返回降序，最新在前）
      const closes = cachedKlineData.map(d => d[2])  // close
      const highs = cachedKlineData.map(d => d[4])   // high
      const lows = cachedKlineData.map(d => d[3])    // low
      const len = closes.length
      if (len >= 5) quant.ma5 = closes.slice(0, 5).reduce((s, v) => s + v, 0) / 5
      if (len >= 20) quant.ma20 = closes.slice(0, 20).reduce((s, v) => s + v, 0) / 20
      if (len >= 26) {
        // 数据降序（最新在前），需要反转后计算 EMA
        const ascCloses = [...closes].reverse()
        const ema = (prev: number, price: number, n: number) => price * (2 / (n + 1)) + prev * (1 - 2 / (n + 1))
        let ema12 = ascCloses.slice(0, 12).reduce((s, v) => s + v, 0) / 12
        let ema26 = ascCloses.slice(0, 26).reduce((s, v) => s + v, 0) / 26
        let macdLine = 0, signal = 0
        for (let i = 26; i < len; i++) {
          ema12 = ema(ema12, ascCloses[i], 12)
          ema26 = ema(ema26, ascCloses[i], 26)
          if (i >= 26) {
            macdLine = ema12 - ema26
            signal = i === 26 ? macdLine : signal * (2 / 10) + macdLine * (1 - 2 / 10)
          }
        }
        quant.macd = Math.round((macdLine - signal) * 10000) / 10000
      }
      if (len >= 15) {
        const ascCloses = [...closes].reverse()
        let gain = 0, loss = 0
        for (let i = len - 14; i < len; i++) {
          const diff = ascCloses[i] - ascCloses[i - 1]
          if (diff > 0) gain += diff; else loss -= diff
        }
        const avgGain = gain / 14, avgLoss = loss / 14
        quant.rsi = avgLoss === 0 ? 100 : Math.round(100 - 100 / (1 + avgGain / avgLoss))
      }
      if (len >= 9) {
        const ascCloses = [...closes].reverse()
        const ascHighs = [...highs].reverse()
        const ascLows = [...lows].reverse()
        const hn = Math.max(...ascHighs.slice(-9))
        const ln = Math.min(...ascLows.slice(-9))
        const rsv = hn === ln ? 50 : (ascCloses[len - 1] - ln) / (hn - ln) * 100
        quant.kdjK = Math.round((2 / 3 * 50 + 1 / 3 * rsv) * 10) / 10
        quant.kdjD = Math.round((2 / 3 * 50 + 1 / 3 * quant.kdjK) * 10) / 10
      }
      // 缠论基础趋势判断
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
        chanlunStats.trendType = '横盘震荡'
        chanlunStats.level = '日线级别'
        chanlunStats.currentBi = '方向不明'
      }
      // 最近顶底分型
      if (highs.length > 5) {
        const maxIdx = highs.indexOf(Math.max(...highs.slice(-5)))
        chanlunStats.lastDingFeng = { price: highs[len - 5 + maxIdx], date: '' }
      }
      if (lows.length > 5) {
        const minIdx = lows.indexOf(Math.min(...lows.slice(-5)))
        chanlunStats.lastDiFeng = { price: lows[len - 5 + minIdx], date: '' }
      }
    }
    // 3. 从 API 提取实时行情（优先使用 stock API，其含涨跌幅兜底计算）
    if (info) {
      Object.assign(stock, {
        price: info.price ?? 0,
        open: info.open ?? 0,
        high: info.high ?? 0,
        low: info.low ?? 0,
        preClose: info.preClose ?? 0,
        changePercent: info.changePct ?? info.changePercent ?? 0,
        pe: info.pe ?? 0,
        pb: info.pb ?? 0,
        totalMarketCap: info.mcapYi ?? 0,
        floatMarketCap: info.floatMcapYi ?? info.mcapYi ?? 0,
        turnoverRate: info.turnoverPct ?? 0,
      })
    }
    // 从 K 线补充 volume/amount/turnoverRate 以及 info 未提供的字段
    if (klineRaw && klineRaw.length > 0) {
      const last = klineRaw[0] // API 返回降序，第一条最新
      stock.volume = safeVal(last.volume)
      stock.amount = safeVal(last.amount)
      if (!stock.turnoverRate) stock.turnoverRate = safeVal(last.turnoverRate)
      // 若 stock API 未提供字段（或为 0），从 K 线兜底
      if (!stock.price) stock.price = safeVal(last.closePrice)
      if (!stock.changePercent) stock.changePercent = safeVal(last.changePct ?? last.changePercent)
      if (!stock.open) stock.open = safeVal(last.openPrice)
      if (!stock.high) stock.high = safeVal(last.highPrice)
      if (!stock.low) stock.low = safeVal(last.lowPrice)
      if (!stock.preClose) stock.preClose = safeVal(last.preClose) || safeVal(last.closePrice) * 0.99
      // 振幅计算需 K 线极值
      const high = safeVal(last.highPrice)
      const low = safeVal(last.lowPrice)
      stock.amplitude = high && low ? ((high - low) / ((high + low) / 2)) * 100 : 0
    }
  } catch (_e) {
    console.warn('[StockDetail] 加载数据失败:', _e)
  } finally {
    chartLoading.value = false
  }
}

onMounted(async () => {
  await loadData()
  nextTick(() => renderChart())
  window.addEventListener('resize', handleResizeCb)
  // 建立 WebSocket 连接，接收实时推送
  wsConnect()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResizeCb)
  wsDisconnect()
  disposeChart()
})

watch(showChanlun, (val) => {
  if (val) { fetchChanlunData() }
  else { setChanlunData(null, false); renderChart() }
})
/** 周期切换时重新加载K线数据 */
function getDaysForPeriod(p: string): number {
  if (p === 'month') return 720
  if (p === 'week') return 365
  return 120
}
async function reloadKlineData() {
  try {
    const klineRaw = await getKlineData(stockCode, getDaysForPeriod(activePeriod.value), activePeriod.value)
    if (klineRaw && klineRaw.length > 1) {
      cachedKlineData = klineRaw.map((d) => [
        parseTradeDate(d.tradeDate),
        safeVal(d.openPrice),
        safeVal(d.closePrice),
        safeVal(d.lowPrice),
        safeVal(d.highPrice),
        safeVal(d.volume),
      ]).sort((a, b) => a[0] - b[0])
    }
  } catch (_e) { console.warn('[Stock] 周期K线加载失败:', _e) }
  renderChart()
}

watch(activePeriod, () => { reloadKlineData() })

// WebSocket 实时推送 → 更新盘口数据
watch(lastKlineUpdate, (update: KlineUpdateData | null) => {
  if (!update) return
  stock.price = update.closePrice ?? stock.price
  stock.open = update.openPrice ?? stock.open
  stock.high = update.highPrice ?? stock.high
  stock.low = update.lowPrice ?? stock.low
  stock.volume = update.volume ?? stock.volume
  stock.amount = update.amount ?? stock.amount
  stock.changePercent = (update as any).changePct ?? update.changePercent ?? stock.changePercent
})
</script>

<style scoped lang="scss">
.stock-detail {
  max-width: 1200px;
  margin: 0 auto;
  padding: $spacing-lg;
}

.stock-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: $spacing-lg;
}

.stock-info {
  h2 {
    font-size: 22px;
    margin-bottom: $spacing-xs;
    .stock-code { font-size: 14px; color: $ink-muted-48; font-weight: 400; }
  }
  .current-price { font-family: $font-display; font-size: 36px; font-weight: 600; }
  .price-change { font-size: 18px; font-weight: 500; margin-left: $spacing-md; }
  .stock-meta { display: flex; gap: $spacing-md; margin-top: $spacing-xs; color: $ink-muted-48; }
}

.chart-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-sm;
  padding: 0 0 $spacing-sm;
  flex-wrap: wrap;
  gap: $spacing-sm;

  .period-tabs {
    display: flex;
    gap: 2px;
    background: $canvas-parchment;
    border-radius: $rounded-sm;
    padding: 2px;

    .period-btn {
      padding: 6px 14px; border: none; background: transparent; font-size: 13px;
      color: $ink-muted-48; cursor: pointer; border-radius: $rounded-xs; transition: all 0.15s;
      &:hover { color: $ink; }
      &.active { background: $canvas; color: $primary; font-weight: 600; box-shadow: $shadow-card; }
    }
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: $spacing-md;
    flex-wrap: wrap;
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

  .group-label {
    font-size: 11px;
    color: $ink-muted-48;
    margin-right: 2px;
    opacity: 0.6;
  }
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

  &.vol-chip {
    font-weight: 600;
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
  position: relative;
}

.kline-chart { height: 420px; }
.bottom-chart { height: 150px; border-top: 1px solid $divider-soft; }

.chart-empty {
  height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
  .chart-empty-text {
    font-size: 14px;
    color: $ink-muted-48;
  }
}

.bottom-section {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
}

.row-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $spacing-md;
}

.info-card {
  background: $canvas-parchment;
  border-radius: $rounded-lg;
  padding: $spacing-lg;

  h4 { font-size: 15px; margin-bottom: $spacing-md; }

  .info-grid-2col {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0 $spacing-lg;
  }

  .info-row {
    display: flex;
    justify-content: space-between;
    padding: 5px 0;
    border-bottom: 1px solid $divider-soft;
    font-size: 13px;
    &:nth-last-child(-n+2) { border-bottom: none; }
    .label { color: $ink-muted-48; }
    .val { font-weight: 500; }
  }
}

.quant-card {
  position: relative;
}

// ============================================================
// 缠论分析面板 — Apple 风格数据面板
// ============================================================
.chanlun-panel {
  background: $canvas;
  border: 1px solid $hairline;
  border-radius: $rounded-md;
  padding: $spacing-md $spacing-lg;

  // ── 面板头部 ──
  .cl-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: $spacing-sm;
    margin-bottom: $spacing-sm;
    padding-bottom: $spacing-xs;
    border-bottom: 1px solid $divider-soft;

    .cl-header-left {
      display: flex;
      align-items: center;
      gap: 6px;

      .cl-icon { color: $ink-muted-48; }
      .cl-title { font-size: 13px; font-weight: 600; color: $ink; letter-spacing: 0.3px; }
    }

    .cl-header-right {
      display: flex;
      align-items: center;
      gap: $spacing-sm;
      flex-wrap: wrap;
    }

    .cl-trend-badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 11px;
      font-weight: 600;
      padding: 3px 12px;
      border-radius: $rounded-pill;

      .cl-trend-dot {
        width: 6px; height: 6px;
        border-radius: 50%;
      }

      &.rise { background: $rise-bg; color: $rise; .cl-trend-dot { background: $rise; } }
      &.fall { background: $fall-bg; color: $fall; .cl-trend-dot { background: $fall; } }
      &.flat { background: rgba(41,151,255,0.08); color: $primary; .cl-trend-dot { background: $primary; } }
    }
  }

  // ── 概览 chips ──
  .cl-overview-chips {
    display: flex;
    gap: 6px;
  }

  .cl-chip {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 2px 10px;
    background: $canvas-parchment;
    border-radius: $rounded-pill;

    .chip-label { font-size: 10px; color: $ink-muted-48; }
    .chip-val { font-size: 11px; font-weight: 600; color: $ink;
      &.rise { color: $rise; }
      &.fall { color: $fall; }
      &.pos {
        &.above { color: $rise; }
        &.inside { color: $primary; }
        &.below { color: $fall; }
      }
    }
  }

  // ── 核心指标 2x2 ──
  .cl-metrics-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: $spacing-xs;
    margin-bottom: $spacing-sm;
  }

  .cl-metric-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: $spacing-xs;
    background: $canvas-parchment;
    border-radius: $rounded-sm;
    border: 1px solid $divider-soft;
    transition: all 0.2s;

    .metric-icon {
      opacity: 0.5;
      margin-bottom: 2px;
    }

    .metric-val {
      font-size: 22px;
      font-weight: 700;
      font-family: $font-display;
      line-height: 1.1;
    }

    .metric-label {
      font-size: 10px;
      color: $ink-muted-48;
      font-weight: 500;
    }

    &.ding { .metric-icon { color: $rise; } .metric-val { color: $rise; } }
    &.di { .metric-icon { color: $fall; } .metric-val { color: $fall; } }
    &.bi { .metric-icon { color: $ink; } .metric-val { color: $ink; } }
    &.zs { .metric-icon { color: $primary; } .metric-val { color: $primary; } }
  }

  // ── 详情区域 2列 ──
  .cl-detail-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: $spacing-sm;
    margin-bottom: $spacing-xs;
  }

  .cl-detail-card {
    background: $canvas-parchment;
    border: 1px solid $divider-soft;
    border-radius: $rounded-sm;
    overflow: hidden;

    .cl-detail-header {
      display: flex;
      align-items: center;
      gap: 5px;
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: $ink-muted-48;
      padding: $spacing-xs $spacing-sm;
      border-bottom: 1px solid $divider-soft;
    }

    .cl-detail-body {
      padding: $spacing-xs $spacing-sm;
    }
  }

  // ── 中枢列表 ──
  .zs-list {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .zs-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 3px 0;

    .zs-tag {
      font-size: 11px;
      font-weight: 500;
      color: $primary;
      padding: 1px 8px;
      background: rgba(41,151,255,0.06);
      border-radius: $rounded-xs;
    }
    .zs-price {
      font-size: 11px;
      color: $ink-muted-80;
      font-family: $font-display;
      font-weight: 500;
    }
  }

  .zs-empty { font-size: 11px; color: $ink-muted-48; font-style: italic; }

  // ── 分型对 ──
  .fx-pair {
    display: flex;
    gap: $spacing-xs;
    margin-bottom: $spacing-xs;
    padding-bottom: $spacing-xs;
    border-bottom: 1px solid $divider-soft;
  }

  .fx-item {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    background: rgba(0,0,0,0.015);
    border-radius: $rounded-xs;

    .fx-label { font-size: 10px; color: $ink-muted-48; min-width: 32px; }
    .fx-price { font-size: 14px; font-weight: 700; font-family: $font-display; }
    .fx-date { font-size: 10px; color: $ink-muted-48; margin-left: auto; }

    &.ding { .fx-price { color: $rise; } }
    &.di { .fx-price { color: $fall; } }
  }

  // ── 买卖点 ──
  .bp-row {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: $spacing-xs;
  }

  .bp-tag {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: $rounded-xs;

    &.buy { background: rgba(231,76,60,0.08); color: $rise; }
    &.sell { background: rgba(39,174,96,0.08); color: $fall; }

    .bp-desc { font-weight: 400; opacity: 0.7; font-size: 10px; }
  }

  .bp-none { font-size: 11px; color: $ink-muted-48; font-style: italic; }

  // ── 背驰 ──
  .beichi-row {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    padding-top: $spacing-xs;
    border-top: 1px solid $divider-soft;

    .beichi-label { font-size: 11px; color: $ink-muted-48; }

    .beichi-val {
      font-size: 11px;
      font-weight: 600;
      padding: 2px 10px;
      border-radius: $rounded-pill;

      &.ding { background: rgba(231,76,60,0.1); color: $rise; }
      &.di { background: rgba(39,174,96,0.1); color: $fall; }
      &.none { background: rgba(0,0,0,0.03); color: $ink-muted-48; }
    }
  }

  // ── 信号底栏 ──
  .cl-signals-bar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: $spacing-xs;
    padding: $spacing-xs 0 0;
    border-top: 1px solid $divider-soft;

    .cl-signals-label { font-size: 10px; color: $ink-muted-48; font-weight: 600; margin-right: 2px; }
    .cl-signal {
      font-size: 10px;
      font-weight: 600;
      padding: 2px 10px;
      border-radius: $rounded-pill;

      &.buy { background: rgba(231,76,60,0.08); color: $rise; }
      &.hold { background: rgba(243,156,18,0.08); color: #f39c12; }
      &.sell { background: rgba(39,174,96,0.08); color: $fall; }
    }
  }
}

.quant-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-sm;

  .stat {
    display: flex;
    flex-direction: column;
    gap: 2px;
    .label { font-size: 12px; color: $ink-muted-48; }
    .val { font-size: 18px; font-weight: 600; }
  }
}

/* 参数设置弹窗 */
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
</style>
