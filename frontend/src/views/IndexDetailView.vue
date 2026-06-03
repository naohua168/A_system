<template>
  <div class="index-detail">
    <!-- 指数基本信息 -->
    <div class="index-header">
      <div class="index-info">
        <h2>{{ info.name }} <span class="code-badge">{{ info.code }} / {{ info.market }}</span></h2>
        <div class="price-section">
          <span class="current-price" :class="info.changePercent >= 0 ? 'text-rise' : 'text-fall'">
            {{ safeNum(info.price) }}
          </span>
          <span class="price-change" :class="info.changePercent >= 0 ? 'text-rise' : 'text-fall'">
            {{ info.changePercent >= 0 ? '+' : '' }}{{ safeNum(info.changePercent, 2) }}%
          </span>
        </div>
        <div class="meta caption">
          <span>开盘: {{ safeNum(info.open) }}</span>
          <span>最高: {{ safeNum(info.high) }}</span>
          <span>最低: {{ safeNum(info.low) }}</span>
          <span>昨收: {{ safeNum(info.preClose) }}</span>
          <span>成交量: {{ formatVol(info.volume) }}</span>
        </div>
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
        <label class="switch-item" :class="{ active: showChanlun }">
          <el-switch v-model="showChanlun" size="small" />
          <span>缠论</span>
        </label>
        <div class="indicator-group overlay-group">
          <label v-for="ind in overlayIndicators" :key="ind.key"
            :class="['indicator-chip', { active: ind.active }]"
            @click="toggleOverlay(ind)"
          >{{ ind.label }}</label>
        </div>
        <div class="indicator-group bottom-group">
          <label :class="['indicator-chip', 'vol-chip', { active: bottomActive === null }]"
            @click="bottomActive = null; renderChart()">VOL</label>
          <label v-for="ind in bottomIndicators" :key="ind.key"
            :class="['indicator-chip', { active: bottomActive === ind.key }]"
            @click="selectBottomIndicator(ind)"
          >{{ ind.label }}<span class="ind-settings" v-if="bottomActive === ind.key" @click.stop="openParams(ind)">
              <el-icon><Setting /></el-icon></span></label>
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
      <div class="row-2col">
        <div class="info-card">
          <h4>指数信息</h4>
          <div class="info-grid-2col">
            <div class="info-row"><span class="label">开盘</span><span class="val">{{ safeNum(info.open) }}</span></div>
            <div class="info-row"><span class="label">最高</span><span class="val text-rise">{{ safeNum(info.high) }}</span></div>
            <div class="info-row"><span class="label">最低</span><span class="val text-fall">{{ safeNum(info.low) }}</span></div>
            <div class="info-row"><span class="label">昨收</span><span class="val">{{ safeNum(info.preClose) }}</span></div>
            <div class="info-row"><span class="label">成交量</span><span class="val">{{ formatVol(info.volume) }}</span></div>
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

      <!-- 缠论分析（与个股统一风格）— 仅开关开启时显示 -->
      <div class="chanlun-panel" v-if="showChanlun">
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

        <div class="cl-detail-row">
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

          <div class="cl-detail-card">
            <div class="cl-detail-header">
              <svg viewBox="0 0 16 16" fill="none" width="14" height="14"><path d="M4 6L8 2L12 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M4 10L8 14L12 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              买卖信号
            </div>
            <div class="cl-detail-body">
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
              <div class="beichi-row">
                <span class="beichi-label">背驰</span>
                <span :class="['beichi-val', chanlunStats.beichi === '顶背驰' ? 'ding' : chanlunStats.beichi === '底背驰' ? 'di' : 'none']">
                  {{ chanlunStats.beichi }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="chanlunStats.signals.length" class="cl-signals-bar">
          <span class="cl-signals-label">提示</span>
          <span v-for="s in chanlunStats.signals" :key="s.text" :class="['cl-signal', s.type]">{{ s.text.replace('_', ' ') }}</span>
        </div>
      </div>
    </div>
  </div>

  <!-- 参数设置弹窗 -->
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
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Setting } from '@element-plus/icons-vue'
import { getIndexInfo, getIndexKline } from '@/api/index'
import { getChanlunAnalysis } from '@/api/analysis'
import { useTechnicalChart } from '@/composables/useTechnicalChart'
import { useIndicatorParams } from '@/composables/useIndicatorParams'
import { safeVal, parseTradeDate } from '@/utils/format'
import { formatVol } from '@/utils/format'

const route = useRoute()
const code = route.params.code as string
const activePeriod = ref('day')
const showChanlun = ref(false)

const indicator = useIndicatorParams()
const { periods, overlayIndicators, bottomIndicators, bottomActive,
  toggleOverlay, selectBottomIndicator,
  paramsDialogVisible, paramsDialogTitle, paramsTarget, params,
  openParams, applyParams } = indicator

let cachedKlineData: number[][] | null = null
function getKlineData() { return cachedKlineData || [] }

const loading = ref(true)
const chartRef = ref<HTMLElement>()
const klineChartRef = ref<HTMLElement>()
const bottomChartRef = ref<HTMLElement>()

const { renderChart, handleResize, dispose: disposeChart, setChanlunData } = useTechnicalChart(
  klineChartRef as any, bottomChartRef as any, {
    getKlineData, params: params as any,
    showMA: computed(() => overlayIndicators.value.find(i => i.key === 'ma')?.active ?? true),
    showBOLL: computed(() => overlayIndicators.value.find(i => i.key === 'boll')?.active ?? false),
    bottomActive: bottomActive as any,
    period: activePeriod,
  })
indicator.setRenderCallback(renderChart)

const info = reactive({
  name: '', code, market: '',
  price: 0, changePercent: 0,
  open: 0, high: 0, low: 0, preClose: 0,
  volume: 0, amount: 0,
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

function safeNum(v: unknown, decimals = 2): string {
  const n = Number(v)
  return isNaN(n) || n === 0 ? '-' : n.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

async function loadData() {
  loading.value = true
  try {
    // 1. 指数实时行情 — 从 market:index_list (auto_seed CSV 写入, 含实时 price/changePct)
    const idxInfo: any = await getIndexInfo(code)
    if (idxInfo) {
      info.name = idxInfo.indexName || idxInfo.indexCode || code
      info.market = idxInfo.market || ''
      // 实时行情优先使用 index_list 数据（与首页大盘卡片同源）
      info.price = Number(idxInfo.closePoint) || 0
      info.changePercent = Number(idxInfo.changePct ?? idxInfo.changePercent) || 0
      info.open = Number(idxInfo.openPoint) || 0
      info.high = Number(idxInfo.highPoint) || 0
      info.low = Number(idxInfo.lowPoint) || 0
      info.preClose = Number(idxInfo.preClose) || 0
      info.volume = Number(idxInfo.volume) || 0
      info.amount = Number(idxInfo.amount) || 0
    }

    // 2. K线数据 — 仅用于图表渲染和量化指标计算（支持多周期）
    const kline: any[] = await getIndexKline(code, getDaysForPeriod(activePeriod.value), activePeriod.value) as any[]
    if (Array.isArray(kline) && kline.length > 1) {
      // API 返回降序 [newest...oldest]，第一条是最新
      cachedKlineData = kline.map((d) => [
        parseTradeDate(d.tradeDate),
        safeVal(d.openPoint), safeVal(d.closePoint),
        safeVal(d.lowPoint), safeVal(d.highPoint),
        safeVal(d.volume),
      ]).sort((a, b) => a[0] - b[0])

      // 最新行情: K线数据作为兜底（如 index_list 字段缺失时补全）
      const last = kline[0]
      if (!info.price) info.price = Number(last.closePoint) || 0
      if (!info.changePercent) info.changePercent = Number(last.changePct ?? last.changePercent) || 0
      if (!info.open) info.open = Number(last.openPoint) || 0
      if (!info.high) info.high = Number(last.highPoint) || 0
      if (!info.low) info.low = Number(last.lowPoint) || 0
      if (!info.volume) info.volume = Number(last.volume) || 0
      if (!info.amount) info.amount = Number(last.amount) || 0
      if (!info.preClose) info.preClose = Number(last.preClose) || Number(last.closePoint) * 0.99
      // 量化指标 — cachedKlineData 已是升序，slice(-N) 取最后 N 个 = 最近 N 天
      const closes = cachedKlineData.map(d => d[2])
      const lows = cachedKlineData.map(d => d[3])
      const highs = cachedKlineData.map(d => d[4])
      const len = closes.length
      if (len >= 5) quant.ma5 = closes.slice(-5).reduce((s, v) => s + v, 0) / 5
      if (len >= 20) quant.ma20 = closes.slice(-20).reduce((s, v) => s + v, 0) / 20
      if (len >= 26) {
        const ema = (prev: number, price: number, n: number) => price * (2 / (n + 1)) + prev * (1 - 2 / (n + 1))
        let ema12 = closes.slice(0, 12).reduce((s, v) => s + v, 0) / 12
        let ema26 = closes.slice(0, 26).reduce((s, v) => s + v, 0) / 26
        let macdLine = 0, signal = 0
        for (let i = 26; i < len; i++) {
          ema12 = ema(ema12, closes[i], 12)
          ema26 = ema(ema26, closes[i], 26)
          if (i >= 26) { macdLine = ema12 - ema26; signal = i === 26 ? macdLine : signal * (2 / 10) + macdLine * (1 - 2 / 10) }
        }
        quant.macd = Math.round((macdLine - signal) * 10000) / 10000
      }
      if (len >= 15) {
        let gain = 0, loss = 0
        for (let i = len - 14; i < len; i++) { const diff = closes[i] - closes[i - 1]; if (diff > 0) gain += diff; else loss -= diff }
        const avgGain = gain / 14, avgLoss = loss / 14
        quant.rsi = avgLoss === 0 ? 100 : Math.round(100 - 100 / (1 + avgGain / avgLoss))
      }
      if (len >= 9) {
        const hn = Math.max(...highs.slice(-9)), ln = Math.min(...lows.slice(-9))
        const rsv = hn === ln ? 50 : (closes[len - 1] - ln) / (hn - ln) * 100
        quant.kdjK = Math.round((2 / 3 * 50 + 1 / 3 * rsv) * 10) / 10
        quant.kdjD = Math.round((2 / 3 * 50 + 1 / 3 * quant.kdjK) * 10) / 10
      }
      // 缠论：初始为空，开启开关后由 fetchChanlunData() 填充
    }
  } catch (_e) { console.warn('[Index] 加载失败:', _e) }
  finally { loading.value = false }
}

/** 从后端加载缠论 K 线 overlay 数据（同步更新面板统计） */
/** 缠论分析使用的数据天数 = 当前K线显示的条数 */
const chanlunDays = computed(() => getDaysForPeriod(activePeriod.value))
async function fetchChanlunData() {
  if (!showChanlun.value) return
  try {
    const data = await getChanlunAnalysis(code, chanlunDays.value, 'index')
    if (data && (data as any).error) {
      console.warn('[Index] 缠论API错误:', (data as any).error)
      setChanlunData(null, true)
      return
    }
    const stats = data.stats || {}
    const bp = data.buy_sell_points || []
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
        name: '中枢' + (i + 1),
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
    console.log(`[Index-Chanlun] API加载成功: ${code}, bi=${data.bi?.length}, zs=${zs.length}, fx=${fx.length}`)
  } catch (e) {
    console.warn('[Index] 缠论API异常:', e)
    setChanlunData(null, true)
  }
}

function handleResizeCb() {
  if (!klineChartRef.value?.offsetParent && !bottomChartRef.value?.offsetParent) return
  handleResize()
}

onMounted(async () => {
  await loadData()
  nextTick(renderChart)
  window.addEventListener('resize', handleResizeCb)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResizeCb)
  disposeChart()
})

watch(showChanlun, (val) => {
  if (val) fetchChanlunData()
  else { setChanlunData(null, false); renderChart() }
})
/** 周期切换时重新加载K线数据并重绘图表 */
function getDaysForPeriod(p: string): number {
  if (p === 'month') return 720   // 月K需要2年数据
  if (p === 'week') return 365    // 周K需要1年数据
  return 120                       // 日K/分钟K用120
}
async function reloadKlineData() {
  loading.value = true
  try {
    const kline: any[] = await getIndexKline(code, getDaysForPeriod(activePeriod.value), activePeriod.value) as any[]
    if (Array.isArray(kline) && kline.length > 1) {
      cachedKlineData = kline.map((d: any) => [
        parseTradeDate(d.tradeDate),
        safeVal(d.openPoint), safeVal(d.closePoint),
        safeVal(d.lowPoint), safeVal(d.highPoint),
        safeVal(d.volume),
      ]).sort((a: any, b: any) => a[0] - b[0])
    }
  } catch (_e) { console.warn('[Index] 周期K线加载失败:', _e) }
  finally {
    loading.value = false
    // 等 DOM 恢复后再渲染（nextTick 确保 kline-chart DOM 已重建）
    nextTick(() => {
      if (cachedKlineData && cachedKlineData.length > 1) renderChart()
    })
  }
}

watch(activePeriod, () => {
  reloadKlineData()
  // 缠论开启时也用新周期天数重新计算，确保X索引对齐
  if (showChanlun.value) fetchChanlunData()
})
</script>

<style scoped lang="scss">
.index-detail { max-width: 1200px; margin: 0 auto; padding: $spacing-lg; }
.index-header { margin-bottom: $spacing-lg; }
.index-info {
  h2 { font-size: 22px; margin-bottom: $spacing-xs;
    .code-badge { font-size: 13px; color: $ink-muted-48; font-weight: 400; margin-left: 8px; background: rgba(0,102,204,0.1); padding: 2px 8px; border-radius: $rounded-xs; } }
  .current-price { font-family: $font-display; font-size: 36px; font-weight: 600; }
  .price-change { font-size: 18px; margin-left: $spacing-md; }
  .meta { display: flex; gap: $spacing-md; margin-top: $spacing-xs; color: $ink-muted-48; }
}

.chart-toolbar {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: $spacing-sm;
  padding: 0 0 $spacing-sm; flex-wrap: wrap; gap: $spacing-sm;
  .toolbar-right { display: flex; align-items: center; gap: $spacing-md; flex-wrap: wrap; }
  .period-tabs { display: flex; gap: 2px; background: $canvas-parchment; border-radius: $rounded-sm; padding: 2px;
    .period-btn { padding: 6px 14px; border: none; background: transparent; font-size: 13px; color: $ink-muted-48; cursor: pointer; border-radius: $rounded-xs; transition: all 0.15s;
      &:hover { color: $ink; } &.active { background: $canvas; color: $primary; font-weight: 600; box-shadow: $shadow-card; } } }
}
.switch-item { display: flex; align-items: center; gap: 6px; font-size: 13px; color: $ink-muted-48; cursor: pointer; &.active { color: $primary; font-weight: 500; } }
.indicator-group { display: flex; align-items: center; gap: 3px; }
.indicator-chip { display: inline-flex; align-items: center; gap: 2px; padding: 4px 10px; border: 1px solid $hairline; border-radius: $rounded-pill; font-size: 12px; color: $ink-muted-48; cursor: pointer; transition: all 0.15s; user-select: none;
  &:hover { border-color: $primary; color: $primary; }
  &.active { background: $primary; border-color: $primary; color: white; }
  &.vol-chip { font-weight: 600; &.active { background: $primary; border-color: $primary; color: white; } }
  .ind-settings { display: inline-flex; align-items: center; margin-left: 2px; font-size: 12px; padding: 2px; border-radius: 50%; transition: background 0.15s;
    &:hover { background: rgba(255,255,255,0.2); } }
}
.chart-main { background: $canvas; border: 1px solid $divider-soft; border-radius: $rounded-lg; overflow: hidden; margin-bottom: $spacing-lg; }
.kline-chart { height: 420px; }
.bottom-chart { height: 150px; border-top: 1px solid $divider-soft; }

.params-dialog { :deep(.el-dialog__body) { padding: 12px 20px; } }
.params-form {
  .param-item { display: flex; flex-direction: column; gap: 4px; padding: 10px 0; border-bottom: 1px solid $divider-soft;
    &:last-child { border-bottom: none; }
    .param-row { display: flex; justify-content: space-between; align-items: center; }
    label { font-size: 13px; color: $ink; font-weight: 500; }
    .param-hint { margin: 0; font-size: 11px; color: $ink-muted-48; line-height: 1.4; } }
}

.bottom-section { display: flex; flex-direction: column; gap: $spacing-md; }
.row-2col { display: grid; grid-template-columns: 1fr 1fr; gap: $spacing-md; }
.info-card { background: $canvas-parchment; border-radius: $rounded-lg; padding: $spacing-lg;
  h4 { font-size: 15px; margin-bottom: $spacing-md; }
  .info-grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 0 $spacing-lg; }
  .info-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid $divider-soft; font-size: 13px;
    &:nth-last-child(-n+2) { border-bottom: none; }
    .label { color: $ink-muted-48; } .val { font-weight: 500; } }
}
.quant-card { position: relative; }
.quant-stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: $spacing-sm;
  .stat { display: flex; flex-direction: column; gap: 2px;
    .label { font-size: 12px; color: $ink-muted-48; } .val { font-size: 18px; font-weight: 600; } }
}
// 缠论分析面板 — Apple 风格数据面板（与个股统一）
.chanlun-panel {
  background: $canvas; border: 1px solid $hairline; border-radius: $rounded-md; padding: $spacing-md $spacing-lg;
  background: $canvas; border: 1px solid $hairline; border-radius: $rounded-md; padding: $spacing-md $spacing-lg;
  .cl-header {
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: $spacing-sm;
    margin-bottom: $spacing-sm; padding-bottom: $spacing-xs; border-bottom: 1px solid $divider-soft;
    .cl-header-left { display: flex; align-items: center; gap: 6px;
      .cl-icon { color: $ink-muted-48; } .cl-title { font-size: 13px; font-weight: 600; color: $ink; letter-spacing: 0.3px; } }
    .cl-header-right { display: flex; align-items: center; gap: $spacing-sm; flex-wrap: wrap; }
    .cl-trend-badge { display: inline-flex; align-items: center; gap: 5px; font-size: 11px; font-weight: 600;
      padding: 3px 12px; border-radius: $rounded-pill;
      .cl-trend-dot { width: 6px; height: 6px; border-radius: 50%; }
      &.rise { background: $rise-bg; color: $rise; .cl-trend-dot { background: $rise; } }
      &.fall { background: $fall-bg; color: $fall; .cl-trend-dot { background: $fall; } }
      &.flat { background: rgba(41,151,255,0.08); color: $primary; .cl-trend-dot { background: $primary; } } }
  }
  .cl-overview-chips { display: flex; gap: 6px; }
  .cl-chip { display: flex; align-items: center; gap: 4px; padding: 2px 10px; background: $canvas-parchment; border-radius: $rounded-pill;
    .chip-label { font-size: 10px; color: $ink-muted-48; }
    .chip-val { font-size: 11px; font-weight: 600; color: $ink;
      &.rise { color: $rise; } &.fall { color: $fall; }
      &.pos.above { color: $rise; } &.pos.inside { color: $primary; } &.pos.below { color: $fall; } } }
  .cl-metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: $spacing-xs; margin-bottom: $spacing-sm; }
  .cl-metric-card { display: flex; flex-direction: column; align-items: center; gap: 2px; padding: $spacing-xs;
    background: $canvas-parchment; border-radius: $rounded-sm; border: 1px solid $divider-soft;
    .metric-icon { opacity: 0.5; margin-bottom: 2px; }
    .metric-val { font-size: 22px; font-weight: 700; font-family: $font-display; line-height: 1.1; }
    .metric-label { font-size: 10px; color: $ink-muted-48; font-weight: 500; }
    &.ding .metric-icon, &.ding .metric-val { color: $rise; }
    &.di .metric-icon, &.di .metric-val { color: $fall; }
    &.bi .metric-icon, &.bi .metric-val { color: $ink; }
    &.zs .metric-icon, &.zs .metric-val { color: $primary; } }
  .cl-detail-row { display: grid; grid-template-columns: 1fr 1fr; gap: $spacing-sm; margin-bottom: $spacing-xs; }
  .cl-detail-card { background: $canvas-parchment; border: 1px solid $divider-soft; border-radius: $rounded-sm; overflow: hidden;
    .cl-detail-header { display: flex; align-items: center; gap: 5px; font-size: 10px; font-weight: 600;
      text-transform: uppercase; letter-spacing: 0.5px; color: $ink-muted-48;
      padding: $spacing-xs $spacing-sm; border-bottom: 1px solid $divider-soft; }
    .cl-detail-body { padding: $spacing-xs $spacing-sm; } }
  .zs-list { display: flex; flex-direction: column; gap: 3px; }
  .zs-item { display: flex; justify-content: space-between; align-items: center; padding: 3px 0;
    .zs-tag { font-size: 11px; font-weight: 500; color: $primary; padding: 1px 8px; background: rgba(41,151,255,0.06); border-radius: $rounded-xs; }
    .zs-price { font-size: 11px; color: $ink-muted-80; font-family: $font-display; font-weight: 500; } }
  .zs-empty { font-size: 11px; color: $ink-muted-48; font-style: italic; }
  .fx-pair { display: flex; gap: $spacing-xs; margin-bottom: $spacing-xs; padding-bottom: $spacing-xs; border-bottom: 1px solid $divider-soft; }
  .fx-item { flex: 1; display: flex; align-items: center; gap: 4px; padding: 4px 8px; background: rgba(0,0,0,0.015); border-radius: $rounded-xs;
    .fx-label { font-size: 10px; color: $ink-muted-48; min-width: 32px; }
    .fx-price { font-size: 14px; font-weight: 700; font-family: $font-display; }
    .fx-date { font-size: 10px; color: $ink-muted-48; margin-left: auto; }
    &.ding .fx-price { color: $rise; } &.di .fx-price { color: $fall; } }
  .bp-row { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: $spacing-xs; }
  .bp-tag { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: $rounded-xs;
    &.buy { background: rgba(231,76,60,0.08); color: $rise; }
    &.sell { background: rgba(39,174,96,0.08); color: $fall; }
    .bp-desc { font-weight: 400; opacity: 0.7; font-size: 10px; } }
  .bp-none { font-size: 11px; color: $ink-muted-48; font-style: italic; }
  .beichi-row { display: flex; align-items: center; gap: $spacing-xs; padding-top: $spacing-xs;
    border-top: 1px solid $divider-soft;
    .beichi-label { font-size: 11px; color: $ink-muted-48; }
    .beichi-val { font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: $rounded-pill;
      &.ding { background: rgba(231,76,60,0.1); color: $rise; }
      &.di { background: rgba(39,174,96,0.1); color: $fall; }
      &.none { background: rgba(0,0,0,0.03); color: $ink-muted-48; } } }
  .cl-signals-bar { display: flex; align-items: center; flex-wrap: wrap; gap: $spacing-xs;
    padding: $spacing-xs 0 0; border-top: 1px solid $divider-soft;
    .cl-signals-label { font-size: 10px; color: $ink-muted-48; font-weight: 600; margin-right: 2px; }
    .cl-signal { font-size: 10px; font-weight: 600; padding: 2px 10px; border-radius: $rounded-pill;
      &.buy { background: rgba(231,76,60,0.08); color: $rise; }
      &.hold { background: rgba(243,156,18,0.08); color: #f39c12; }
      &.sell { background: rgba(39,174,96,0.08); color: $fall; } } }
}
.text-fall { color: #27ae60; }
</style>
