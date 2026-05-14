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
      <div class="kline-chart" ref="klineChartRef"></div>
      <div class="bottom-chart" ref="bottomChartRef"></div>
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

        <!-- 长行布局: 统计+中枢+分型+买卖点 -->
        <div class="cl-wide-row">
          <!-- 核心统计 -->
          <div class="cl-wide-item">
            <span class="section-label">统计</span>
            <div class="chanlun-stats-h">
              <div class="stat-h"><span class="label">顶分型</span><span class="val cl-ding">{{ chanlunStats.dingCount }}</span></div>
              <div class="stat-h"><span class="label">底分型</span><span class="val cl-di">{{ chanlunStats.diCount }}</span></div>
              <div class="stat-h"><span class="label">笔</span><span class="val">{{ chanlunStats.biCount }}</span></div>
              <div class="stat-h"><span class="label">中枢</span><span class="val cl-zs">{{ chanlunStats.zhongshuCount }}</span></div>
            </div>
          </div>

          <!-- 中枢详情 -->
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

          <!-- 分型 -->
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

          <!-- 买卖点+背驰 -->
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

        <!-- 信号 -->
        <div class="signals">
          <div v-for="s in chanlunStats.signals" :key="s.text" :class="['signal-badge', s.type]">{{ s.text }}</div>
        </div>
      </div>
    </div>

    <!-- 信号层数据 - 资金流向/龙虎榜/解禁/财务 -->
    <div class="signal-section">
      <el-tabs v-model="signalTab" class="signal-tabs">
        <el-tab-pane label="资金流向" name="flow">
          <div v-if="!flowData.length" class="signal-empty">暂无资金流向数据，请先运行数据采集</div>
          <el-table v-else :data="flowData" size="small" stripe style="width:100%">
            <el-table-column prop="date" label="日期" width="100" />
            <el-table-column prop="close" label="收盘价" width="90" align="right" />
            <el-table-column prop="changePct" label="涨跌幅%" width="90" align="right">
              <template #default="{ row }"><span :class="row.changePct >= 0 ? 'text-rise' : 'text-fall'">{{ row.changePct >= 0 ? '+' : '' }}{{ row.changePct }}%</span></template>
            </el-table-column>
            <el-table-column label="主力净流入" width="110" align="right">
              <template #default="{ row }"><span :class="row.mainIn >= 0 ? 'text-rise' : 'text-fall'">{{ row.mainIn }}万</span></template>
            </el-table-column>
            <el-table-column label="超大单" width="90" align="right" prop="superNetIn" />
            <el-table-column label="大单" width="90" align="right" prop="largeNetIn" />
            <el-table-column label="散户" width="90" align="right" prop="littleNetIn" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="龙虎榜" name="dt">
          <div v-if="!dtData.length" class="signal-empty">暂无龙虎榜数据</div>
          <el-table v-else :data="dtData" size="small" stripe style="width:100%" @row-click="dtStock = $event; dtVisible = true">
            <el-table-column prop="tradeDate" label="日期" width="100" />
            <el-table-column prop="reason" label="上榜原因" min-width="180" show-overflow-tooltip />
            <el-table-column label="净买入" width="110" align="right">
              <template #default="{ row }"><span :class="row.netBuyWan >= 0 ? 'text-rise' : 'text-fall'">{{ row.netBuyWan >= 0 ? '+' : '' }}{{ row.netBuyWan }}万</span></template>
            </el-table-column>
            <el-table-column prop="changePct" label="涨幅%" width="80" align="right">
              <template #default="{ row }">{{ row.changePct >= 0 ? '+' : '' }}{{ row.changePct }}%</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="限售解禁" name="lockup">
          <div v-if="!lockupData.length" class="signal-empty">暂无解禁数据</div>
          <el-table v-else :data="lockupData" size="small" stripe style="width:100%">
            <el-table-column prop="lockupDate" label="解禁日期" width="110" />
            <el-table-column prop="lockupType" label="类型" min-width="140" show-overflow-tooltip />
            <el-table-column label="数量" width="130" align="right">
              <template #default="{ row }">{{ formatShares(row.shares) }}</template>
            </el-table-column>
            <el-table-column prop="floatRatio" label="占流通股%" width="110" align="right" />
            <el-table-column label="状态" width="80" align="center">
              <template #default="{ row }"><el-tag :type="row.isUpcoming ? 'warning' : 'info'" size="small">{{ row.isUpcoming ? '待解禁' : '已解禁' }}</el-tag></template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="财务指标" name="financial">
          <div v-if="!financialData.length" class="signal-empty">暂无财务数据</div>
          <div v-else class="financial-grid">
            <div v-for="f in financialData" :key="f.label" class="fi-card">
              <div class="fi-label">{{ f.label }}</div>
              <div class="fi-value">{{ f.value }}</div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 龙虎榜详情弹窗 -->
    <el-dialog v-model="dtVisible" title="龙虎榜详情" width="420px">
      <div class="dt-detail" v-if="dtStock">
        <div class="dt-row"><span class="label">上榜日期</span><span>{{ dtStock.tradeDate }}</span></div>
        <div class="dt-row"><span class="label">上榜原因</span><span>{{ dtStock.reason }}</span></div>
        <div class="dt-row"><span class="label">净买额</span><span :class="(dtStock.netBuyWan || 0) >= 0 ? 'text-rise' : 'text-fall'">{{ dtStock.netBuyWan }}万</span></div>
        <div class="dt-row"><span class="label">总买入</span><span>{{ dtStock.buyWan }}万</span></div>
        <div class="dt-row"><span class="label">总卖出</span><span>{{ dtStock.sellWan }}万</span></div>
        <div class="dt-row"><span class="label">涨幅</span><span :class="(dtStock.changePct || 0) >= 0 ? 'text-rise' : 'text-fall'">{{ dtStock.changePct }}%</span></div>
      </div>
    </el-dialog>

    <!-- 参数设置弹窗 -->
    <el-dialog v-model="paramsDialogVisible" :title="`${paramsDialogTitle} 参数设置`" width="380px" :modal="false" class="params-dialog">
      <div v-if="paramsTarget === 'macd'" class="params-form">
        <div class="param-item">
          <label>快线周期 (EMA短)</label>
          <el-input-number v-model="params.macd.fast" :min="5" :max="30" size="small" controls-position="right" />
        </div>
        <div class="param-item">
          <label>慢线周期 (EMA长)</label>
          <el-input-number v-model="params.macd.slow" :min="10" :max="60" size="small" controls-position="right" />
        </div>
        <div class="param-item">
          <label>信号周期 (DEA)</label>
          <el-input-number v-model="params.macd.signal" :min="5" :max="30" size="small" controls-position="right" />
        </div>
      </div>
      <div v-if="paramsTarget === 'kdj'" class="params-form">
        <div class="param-item">
          <label>计算周期 (N)</label>
          <el-input-number v-model="params.kdj.period" :min="5" :max="30" size="small" controls-position="right" />
        </div>
      </div>
      <div v-if="paramsTarget === 'rsi'" class="params-form">
        <div class="param-item">
          <label>计算周期 (N)</label>
          <el-input-number v-model="params.rsi.period" :min="5" :max="30" size="small" controls-position="right" />
        </div>
      </div>
      <div v-if="paramsTarget === 'ma'" class="params-form">
        <div class="param-item">
          <label>MA1 周期</label>
          <el-input-number v-model="params.ma.periods[0]" :min="3" :max="60" size="small" controls-position="right" />
        </div>
        <div class="param-item">
          <label>MA2 周期</label>
          <el-input-number v-model="params.ma.periods[1]" :min="3" :max="120" size="small" controls-position="right" />
        </div>
      </div>
      <div v-if="paramsTarget === 'boll'" class="params-form">
        <div class="param-item">
          <label>计算周期</label>
          <el-input-number v-model="params.boll.period" :min="5" :max="60" size="small" controls-position="right" />
        </div>
        <div class="param-item">
          <label>标准差倍数</label>
          <el-input-number v-model="params.boll.multiplier" :min="1" :max="5" :step="0.5" size="small" controls-position="right" />
        </div>
      </div>
      <template #footer>
        <el-button @click="paramsDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="applyParams">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Star, Setting } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getStockByCode, getKlineData } from '@/api/stock'
import { useStockStore } from '@/stores/stock'
import { useUserStore } from '@/stores/user'
import { addWatchlist, removeWatchlist } from '@/api/watchlist'
import { ElMessage } from 'element-plus'
import { safeNum, safeVal, formatVol, parseTradeDate, formatDateShort } from '@/utils/format'
import { calcMA, calcBOLL, calcMACD, calcKDJ, calcRSI } from '@/utils/indicators'

const route = useRoute()
const stockCode = route.params.code as string
const stockStore = useStockStore()
const userStore = useUserStore()

const chartRef = ref<HTMLElement>()
const klineChartRef = ref<HTMLElement>()
const bottomChartRef = ref<HTMLElement>()

let klineChart: echarts.ECharts | null = null
let bottomChart: echarts.ECharts | null = null

const chartLoading = ref(false)
const showChanlun = ref(false)
const activePeriod = ref('day')
const isWatched = computed(() => stockStore.isInWatchlist(stockCode))


// 缓存K线数据（仅由 API 填充）
let cachedKlineData: number[][] | null = null
function getCachedKlineData() {
  return cachedKlineData || []
}

const periods = [
  { key: '5min', label: '5分' }, { key: '15min', label: '15分' },
  { key: '30min', label: '30分' }, { key: '60min', label: '60分' },
  { key: 'day', label: '日K' }, { key: 'week', label: '周K' }, { key: 'month', label: '月K' },
]

// --- 指标分组 ---
// 叠加指标（画在K线图上）
const overlayIndicators = ref([
  { key: 'ma', label: 'MA', active: true },
  { key: 'boll', label: 'BOLL', active: false },
])

// 底部指标（互斥，替换成交量区域）
const bottomIndicators = ref([
  { key: 'macd', label: 'MACD' },
  { key: 'kdj', label: 'KDJ' },
  { key: 'rsi', label: 'RSI' },
])

// bottomActive = null 表示显示VOL成交量
const bottomActive = ref<string | null>(null)

function toggleOverlay(ind: { key: string; active: boolean }) {
  ind.active = !ind.active
  renderChart()
}

function selectBottomIndicator(ind: { key: string }) {
  if (bottomActive.value === ind.key) {
    bottomActive.value = null // 切换回VOL
  } else {
    bottomActive.value = ind.key
  }
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

// ======== 信号层数据（资金流向/龙虎榜/解禁/财务） ========
const signalTab = ref('flow')
const flowData = ref<any[]>([])
const dtData = ref<any[]>([])
const lockupData = ref<any[]>([])
const financialData = ref<any[]>([])
const dtVisible = ref(false)
const dtStock = ref<any>(null)

function formatShares(shares: number) {
  if (!shares) return '-'
  const s = Number(shares)
  if (s >= 100000000) return (s / 100000000).toFixed(2) + '亿'
  if (s >= 10000) return (s / 10000).toFixed(2) + '万'
  return s.toString()
}

async function loadSignalData(code: string) {
  try {
    const [dtRes, lockRes] = await Promise.allSettled([
      import('@/api/signal').then(m => m.getDragonTigerByStock(code)),
      import('@/api/signal').then(m => m.getLockupByStock(code)),
    ])
    if (dtRes.status === 'fulfilled') dtData.value = dtRes.value.data || []
    if (lockRes.status === 'fulfilled') lockupData.value = lockRes.value.data || []
    // 资金流向和财务数据使用模拟
    flowData.value = [
      { date: '2026-05-08', close: 157.17, changePct: 0.05, mainIn: 2146, superNetIn: 1256, largeNetIn: 890, littleNetIn: -780 },
      { date: '2026-05-07', close: 157.09, changePct: -2.22, mainIn: -4476, superNetIn: -3356, largeNetIn: -1120, littleNetIn: 1560 },
      { date: '2026-05-06', close: 160.66, changePct: 4.43, mainIn: 7966, superNetIn: 5621, largeNetIn: 2345, littleNetIn: -2560 },
      { date: '2026-04-30', close: 153.84, changePct: -4.10, mainIn: -6417, superNetIn: -4521, largeNetIn: -1896, littleNetIn: 2135 },
      { date: '2026-04-29', close: 160.42, changePct: 1.89, mainIn: 4851, superNetIn: 3562, largeNetIn: 1289, littleNetIn: -2156 },
    ]
    financialData.value = [
      { label: '每股收益(EPS)', value: '1.85元' },
      { label: '每股净资产(BVPS)', value: '12.56元' },
      { label: '净资产收益率(ROE)', value: '14.72%' },
      { label: '净利润', value: '125.6亿' },
      { label: '营业收入', value: '892.3亿' },
      { label: '总股本', value: '67.8亿股' },
    ]
  } catch { /* silent */ }
}

// 缠论数据（当前无后端API，仅保留空结构供前端占位）
function getEmptyChanlunData() {
  return { bi: [] as any[], zhongshu: [] as any[], fengxing: [] as any[] }
}

// --- Render ---
function renderChart() {
  if (!klineChartRef.value) return
  const klineData = getCachedKlineData()
  if (klineData.length === 0) return
  const dates = klineData.map(d => {
    try {
      return new Date(d[0]).toLocaleDateString('zh-CN')
    } catch {
      return d[0] ? String(d[0]) : '-'
    }
  })
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
    // 中枢 - 半透明框 + 标注区间价格
    clData.zhongshu.forEach(zs => {
      series.push({
        type: 'custom',
        renderItem: (pa: any, api: any) => {
          const s = api.coord([zs.startX, zs.high]); const e = api.coord([zs.endX, zs.low])
          const midX = (s[0] + e[0]) / 2
          return {
            type: 'group', children: [
              { type: 'rect', shape: { x: s[0], y: s[1], width: e[0] - s[0], height: e[1] - s[1] }, style: { fill: 'rgba(41,151,255,0.12)', stroke: '#2997ff', lineWidth: 1.5, lineDash: [4, 3] } },
            ]
          }
        }, data: [0], z: 10,
      })
    })
    // 笔 - 红色上涨/绿色下跌 (TradingView配色)
    clData.bi.forEach(b => {
      const isUp = b.y1 >= b.y0
      series.push({
        type: 'line', data: [[b.x0, b.y0], [b.x1, b.y1]], symbol: 'none',
        lineStyle: { width: 2, color: isUp ? '#e74c3c' : '#27ae60' }, z: 11,
      })
    })
    // 分型 - 三角形标记 (TradingView风格)
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

// --- Technical Indicator Calculations ---
async function toggleWatch() {
  if (!userStore.isLoggedIn || !userStore.userInfo) {
    ElMessage.warning('请先登录')
    return
  }
  const isAdd = !stockStore.isInWatchlist(stockCode)
  try {
    if (isAdd) {
      await addWatchlist(userStore.userInfo.id, stockCode, 0)
      ElMessage.success('已添加自选')
    } else {
      await removeWatchlist(userStore.userInfo.id, stockCode, 0)
      ElMessage.success('已移除自选')
    }
    // 更新本地状态
    const fakeStock = { stockCode, stockName: stock.name, market: '', industry: '' } as any
    stockStore.toggleStockInWatchlist(fakeStock)
  } catch (_e) {
    ElMessage.error('操作失败')
  }
}

function formatVol(v: number) {
  const n = safeVal(v)
  if (n >= 100000000) return `¥${(n / 100000000).toFixed(2)}亿`
  if (n >= 10000) return `¥${(n / 10000).toFixed(2)}万`
  return n > 0 ? n.toLocaleString() : '-'
}

function handleResize() { klineChart?.resize(); bottomChart?.resize() }

async function loadData() {
  chartLoading.value = true
  try {
    // 1. 加载股票基本信息
    const info: any = await getStockByCode(stockCode)
    if (info) {
      stock.name = info.stockName || info.name || stockCode
      stock.pe = info.pe || '-'
      stock.pb = info.pb || '-'
      stock.totalMarketCap = info.totalMarketCap || 0
      stock.floatMarketCap = info.floatMarketCap || 0
    }

    // 2. 加载 K 线数据
    const klineRaw: any[] | undefined = await getKlineData(stockCode, { days: 120 })
    if (klineRaw && klineRaw.length > 10) {
      // 后端返回 [{stockCode, tradeDate, openPrice, highPrice, lowPrice, closePrice, volume, amount, changePercent, ...}]
      cachedKlineData = klineRaw.map((d: any) => [
        parseTradeDate(d.tradeDate),
        safeVal(d.openPrice),
        safeVal(d.closePrice),
        safeVal(d.lowPrice),
        safeVal(d.highPrice),
        safeVal(d.volume),
      ])
      // 取最新一条作为当前行情
      const last = klineRaw[klineRaw.length - 1]
      const high = safeVal(last.highPrice)
      const low = safeVal(last.lowPrice)
      Object.assign(stock, {
        price: safeVal(last.closePrice),
        open: safeVal(last.openPrice),
        high: high,
        low: low,
        preClose: safeVal(last.preClose) || safeVal(last.closePrice) * 0.99,
        volume: safeVal(last.volume),
        amount: safeVal(last.amount),
        changePercent: safeVal(last.changePercent),
        turnoverRate: safeVal(last.turnoverRate),
        amplitude: high && low ? safeVal(((high - low) / ((high + low) / 2)) * 100) : 0,
      })
      loadSignalData(stockCode)
    }
  } catch (_e) {
    console.warn('[StockDetail] 加载数据失败:', _e)
  } finally {
    chartLoading.value = false
  }
}

onMounted(async () => {
  await loadData()
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
}

.kline-chart { height: 420px; }
.bottom-chart { height: 150px; border-top: 1px solid $divider-soft; }

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

.chanlun-card {
  h4 {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: $spacing-sm;
  }
}

.trend-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 10px;
  border-radius: $rounded-pill;

  &.rise { background: rgba(231,76,60,0.1); color: $rise; }
  &.fall { background: rgba(39,174,96,0.1); color: $fall; }
  &.flat { background: rgba(0,102,204,0.1); color: $primary; }
}

.cl-overview {
  display: flex;
  gap: $spacing-lg;
  margin-bottom: $spacing-md;

  .ov-item {
    display: flex;
    flex-direction: column;
    gap: 2px;

    .label { font-size: 11px; color: $ink-muted-48; }
    .val { font-size: 14px; font-weight: 600; }
  }
}

.cl-wide-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-md;
  margin-bottom: $spacing-md;
}

.cl-wide-item {
  .section-label {
    display: block;
    font-size: 10px;
    font-weight: 600;
    color: $ink-muted-48;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
  }
}

.chanlun-stats-h {
  display: flex;
  gap: 2px;

  .stat-h {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    background: rgba(0,0,0,0.02);
    border-radius: $rounded-xs;
    padding: 6px 2px;

    .label { font-size: 10px; color: $ink-muted-48; }
    .val { font-size: 18px; font-weight: 700; font-family: $font-display; }
    &.cl-ding { color: #e74c3c; }
    &.cl-di { color: #27ae60; }
    &.cl-zs { color: $primary; }
  }
}

.zhongshu-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-bottom: $spacing-xs;

  .zhongshu-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 3px 8px;
    background: rgba(41,151,255,0.06);
    border-radius: $rounded-xs;
    border-left: 3px solid rgba(41,151,255,0.4);

    .zs-name { font-size: 11px; font-weight: 500; color: $ink; }
    .zs-range { font-size: 11px; color: $ink-muted-48; font-family: $font-display; }
  }
}

.position-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2px 0;

  .label { font-size: 11px; color: $ink-muted-48; }
  .pos-badge { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: $rounded-pill;
    &.above { background: rgba(231,76,60,0.1); color: $rise; }
    &.inside { background: rgba(41,151,255,0.1); color: $primary; }
    &.below { background: rgba(39,174,96,0.1); color: $fall; }
  }
}

.fengxing-list {
  display: flex;
  flex-direction: column;
  gap: 4px;

  .fengxing-item {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    padding: 3px 6px;
    background: rgba(0,0,0,0.02);
    border-radius: $rounded-xs;

    .label { font-size: 10px; color: $ink-muted-48; min-width: 32px; }
    .val { font-size: 14px; font-weight: 700; font-family: $font-display; min-width: 56px; }
    .date { font-size: 10px; color: $ink-muted-48; }
    .ding-price { color: #e74c3c; }
    .di-price { color: #27ae60; }
  }
}

.signal-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: $spacing-xs;
}

.point-badge {
  font-size: 12px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: $rounded-xs;

  &.buy {
    background: rgba(231,76,60,0.08);
    color: $rise;
  }
  &.sell {
    background: rgba(39,174,96,0.08);
    color: $fall;
  }

  .point-desc { font-weight: 400; opacity: 0.8; }
}

.no-points { font-size: 12px; color: $ink-muted-48; font-style: italic; }

.beichi-row {
  .beichi-badge {
    font-size: 12px;
    font-weight: 600;
    padding: 3px 12px;
    border-radius: $rounded-pill;

    &.ding { background: rgba(231,76,60,0.1); color: $rise; }
    &.di { background: rgba(39,174,96,0.1); color: $fall; }
    &.none { background: rgba(0,0,0,0.03); color: $ink-muted-48; }
  }
}

.signals {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-xs;
  margin-top: $spacing-xs;
  padding-top: $spacing-xs;
  border-top: 1px solid $divider-soft;
}

.signal-badge {
  padding: 3px 10px; border-radius: $rounded-pill; font-size: 11px; font-weight: 500;
  &.buy { background: rgba(231,76,60,0.1); color: $rise; }
  &.hold { background: rgba(243,156,18,0.1); color: #f39c12; }
  &.sell { background: rgba(39,174,96,0.1); color: $fall; }
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

/* 信号层数据 Tab 区域 */
.signal-section { margin-top: 20px; background: $canvas; border: 1px solid $divider-soft; border-radius: $rounded-lg; padding: $spacing-md; }
.signal-tabs { :deep(.el-tabs__item) { color: $ink-muted-48; &.is-active { color: $primary; } } }
.signal-empty { text-align: center; padding: 40px 0; color: $ink-muted-48; font-size: 14px; }
.financial-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: $spacing-md; }
.fi-card { background: $canvas-parchment; border-radius: $rounded-md; padding: $spacing-md; text-align: center;
  .fi-label { font-size: 12px; color: $ink-muted-48; margin-bottom: 4px; }
  .fi-value { font-size: 20px; font-weight: 700; color: $ink; } }
.dt-detail { .dt-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid $divider-soft;
  .label { color: $ink-muted-48; } &:last-child { border: none; } } }

/* 参数设置弹窗 */
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

    label {
      font-size: 13px;
      color: $ink;
    }
  }
}
</style>
