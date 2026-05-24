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
          <template v-if="signalLoading">
            <SkeletonLoader type="table" :rows="3" :col-widths="['14%','12%','12%','16%','12%','12%','12%']" />
          </template>
          <div v-else-if="!flowData.length" class="signal-empty">暂无资金流向数据，请先运行数据采集</div>
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
          <template v-if="signalLoading">
            <SkeletonLoader type="table" :rows="3" :col-widths="['14%','26%','16%','12%']" />
          </template>
          <div v-else-if="!dtData.length" class="signal-empty">暂无龙虎榜数据</div>
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
          <template v-if="signalLoading">
            <SkeletonLoader type="table" :rows="3" :col-widths="['16%','20%','18%','16%','12%']" />
          </template>
          <div v-else-if="!lockupData.length" class="signal-empty">暂无解禁数据</div>
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
          <template v-if="signalLoading">
            <SkeletonLoader type="card" :rows="2" :cols="4" />
          </template>
          <div v-else-if="!financialData.length" class="signal-empty">暂无财务数据</div>
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
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Star, Setting } from '@element-plus/icons-vue'
import { getStockByCode, getKlineData } from '@/api/market'
import { useStockStore } from '@/stores/stock'
import { useWatchlistStore } from '@/stores/watchlist'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { safeNum, safeVal, formatVol, parseTradeDate } from '@/utils/format'
import { safeNum as safeNumVal, safeStr } from '@/composables/useApiRetry'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
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
const chanlunData = ref<ChanlunRawData>({ bi: [], zhongshu: [], fengxing: [], buy_sell_points: [], stats: {} as ChanlunStats })
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
const { renderChart, handleResize, dispose: disposeChart } = useTechnicalChart(
  klineChartRef as any,
  bottomChartRef as any,
  {
    getKlineData: () => getCachedKlineData(),
    params: params as any,
    showMA: computed(() => overlayIndicators.value.find(i => i.key === 'ma')?.active ?? true),
    showBOLL: computed(() => overlayIndicators.value.find(i => i.key === 'boll')?.active ?? false),
    bottomActive: bottomActive as any,
    chanlunData: chanlunData as any,
    showChanlun: showChanlun as any,
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

import { getFundFlow, getDragonTigerByStock, getLockupByStock } from '@/api/signal'
import type { FundFlowRow, DragonTigerStockRow, LockupDisplayRow, FinancialMetric } from '@/types'

/** 信号层数据（资金流向/龙虎榜/解禁/财务） */
const signalTab = ref('flow')
const signalLoading = ref(true)
const flowData = ref<FundFlowRow[]>([])
const dtData = ref<DragonTigerStockRow[]>([])
const lockupData = ref<LockupDisplayRow[]>([])
const financialData = ref<FinancialMetric[]>([])
const dtVisible = ref(false)
const dtStock = ref<DragonTigerStockRow | null>(null)

/** 格式化股票数量 */
function formatShares(shares: number): string {
  if (!shares) return '-'
  if (shares >= 100_000_000) return (shares / 100_000_000).toFixed(2) + '亿'
  if (shares >= 10_000) return (shares / 10_000).toFixed(2) + '万'
  return shares.toString()
}

/** 加载个股信号层数据（资金流向+龙虎榜+解禁+财务） */
async function loadSignalData(code: string) {
  signalLoading.value = true
  try {
    const [flowRes, dtRes, lockRes] = await Promise.allSettled([
      getFundFlow(code, 20).catch(() => []),
      getDragonTigerByStock(code).catch(() => []),
      getLockupByStock(code).catch(() => []),
    ])
    if (flowRes.status === 'fulfilled' && Array.isArray(flowRes.value)) {
      flowData.value = flowRes.value.map((item) => ({
        date: safeStr(item.tradeDate),
        close: safeNum(item.close, 2),
        changePct: safeNum(item.changePct, 2),
        mainIn: safeNum(item.mainIn),
        superNetIn: safeNum(item.superNetIn),
        largeNetIn: safeNum(item.largeNetIn),
        littleNetIn: safeNum(item.littleNetIn),
      }))
    }
    if (dtRes.status === 'fulfilled' && Array.isArray(dtRes.value)) {
      dtData.value = dtRes.value.map((item) => ({
        ...item,
        netBuyWan: safeNum(item.netBuyWan, 2),
        changePct: safeNum(item.changePct, 2),
      })) as DragonTigerStockRow[]
    }
    if (lockRes.status === 'fulfilled' && Array.isArray(lockRes.value)) {
      lockupData.value = lockRes.value.map((item) => ({
        ...item,
        shares: safeNum(item.shares),
        floatRatio: safeNum(item.floatRatio, 2),
      })) as LockupDisplayRow[]
    }
  } catch {
    console.warn('[StockDetail] loadSignalData failed')
  } finally { signalLoading.value = false }
}

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
    const stats = data.stats || {} as ChanlunStats
    const bp = (data.buy_sell_points || []) as ChanlunBuySellPoint[]
    const zs = data.zhongshu || []
    const fx = data.fengxing || []
    chanlunData.value = { bi: data.bi || [], zhongshu: zs, fengxing: fx, buy_sell_points: bp, stats }

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
    nextTick(renderChart)
  } catch {
    chanlunData.value = { bi: [], zhongshu: [], fengxing: [], buy_sell_points: [], stats: {} as ChanlunStats }
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

function handleResizeCb() { handleResize() }

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

    // 2. 加载 K 线数据
    const klineRaw = await getKlineData(stockCode, 120)
    if (klineRaw && klineRaw.length > 10) {
      cachedKlineData = klineRaw.map((d) => [
        parseTradeDate(d.tradeDate),
        safeVal(d.openPrice),
        safeVal(d.closePrice),
        safeVal(d.lowPrice),
        safeVal(d.highPrice),
        safeVal(d.volume),
      ])
      const last = klineRaw[klineRaw.length - 1]
      const high = safeVal(last.highPrice)
      const low = safeVal(last.lowPrice)
      Object.assign(stock, {
        price: safeVal(last.closePrice),
        open: safeVal(last.openPrice),
        high,
        low,
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
  else { chanlunData.value = { bi: [], zhongshu: [], fengxing: [], buy_sell_points: [], stats: {} as any }; nextTick(() => renderChart()) }
})
watch(activePeriod, () => { nextTick(() => renderChart()) })

// WebSocket 实时推送 → 更新盘口数据
watch(lastKlineUpdate, (update: KlineUpdateData | null) => {
  if (!update) return
  stock.price = update.closePrice ?? stock.price
  stock.open = update.openPrice ?? stock.open
  stock.high = update.highPrice ?? stock.high
  stock.low = update.lowPrice ?? stock.low
  stock.volume = update.volume ?? stock.volume
  stock.amount = update.amount ?? stock.amount
  stock.changePercent = update.changePercent ?? stock.changePercent
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
