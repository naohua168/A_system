<template>
  <div class="fund-detail">
    <!-- 头部: 基金名称 + 档案 -->
    <div class="fund-header">
      <div class="fund-brand">
        <h2>{{ fund.name }}</h2>
        <div class="fund-sub">
          <span class="fund-code">{{ fund.code }}</span>
          <span class="fund-badge">{{ fund.type }}</span>
          <span class="sep">|</span>
          <span>{{ fund.company }}</span>
          <span class="sep">|</span>
          <span>基金经理: {{ fund.manager }}</span>
        </div>
      </div>
      <div class="fund-actions">
        <el-button :type="isWatched ? 'danger' : 'primary'" plain round @click="isWatched = !isWatched">
          <el-icon><Star /></el-icon> {{ isWatched ? '已自选' : '加自选' }}
        </el-button>
      </div>
    </div>

    <!-- 关键指标卡片 -->
    <template v-if="fund.isMoneyMarket">
      <!-- 货币基金：显示七日年化卡片 -->
      <div class="nav-metrics">
        <div class="metric-card metric-primary">
          <span class="metric-label">7日年化</span>
          <span class="metric-value" style="color: #10b981;">{{ (fund.sevenDayYield ?? 0).toFixed(2) }}%</span>
          <span class="metric-sub">万份收益 {{ (fund.dailyReturnMoney ?? 0).toFixed(4) }}</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">近1月</span>
          <span class="metric-value" style="color: #10b981;">{{ fund.monthReturnMoney ?? '--' }}%</span>
          <span class="metric-sub">货币型</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">近1年</span>
          <span class="metric-value" style="color: #10b981;">{{ fund.yearReturnMoney ?? '--' }}%</span>
          <span class="metric-sub">累计收益</span>
        </div>
      </div>
    </template>
    <template v-else-if="fund.nav <= 0">
      <!-- 无净值数据的基金 -->
      <div class="nav-metrics">
        <div class="metric-card metric-primary" style="grid-column: 1 / -1; padding: 24px;">
          <span class="metric-label">基金状态</span>
          <span class="metric-value" style="font-size: 18px; color: #999;">暂无净值数据</span>
          <span class="metric-sub">{{ fund.name.includes('后端') ? '后端收费份额，通常无独立净值数据' : '该基金尚未获取到净值信息' }}</span>
        </div>
      </div>
    </template>
    <template v-else>
      <div class="nav-metrics">
        <div class="metric-card metric-primary">
          <span class="metric-label">最新净值</span>
          <span class="metric-value">{{ fund.nav.toFixed(4) }}</span>
          <span class="metric-change" :class="fund.dailyReturn >= 0 ? 'rise' : 'fall'">
            日涨跌 {{ fund.dailyReturn >= 0 ? '+' : '' }}{{ (fund.dailyReturn * 100).toFixed(2) }}%
          </span>
        </div>
        <div class="metric-card" v-if="fund.accumulatedNav > 0">
          <span class="metric-label">累计净值</span>
          <span class="metric-value">{{ fund.accumulatedNav.toFixed(4) }}</span>
          <span class="metric-sub">成立以来</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">近1月</span>
          <span v-if="fund.returns.month !== 0" class="metric-value" :class="fund.returns.month >= 0 ? 'rise' : 'fall'">
            {{ fund.returns.month >= 0 ? '+' : '' }}{{ fund.returns.month.toFixed(2) }}%
          </span>
          <span v-else class="metric-value muted">--</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">近3月</span>
          <span v-if="fund.returns.quarter !== 0" class="metric-value" :class="fund.returns.quarter >= 0 ? 'rise' : 'fall'">
            {{ fund.returns.quarter >= 0 ? '+' : '' }}{{ fund.returns.quarter.toFixed(2) }}%
          </span>
          <span v-else class="metric-value muted">--</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">近6月</span>
          <span v-if="fund.returns.sixMonth !== 0" class="metric-value" :class="fund.returns.sixMonth >= 0 ? 'rise' : 'fall'">
            {{ fund.returns.sixMonth >= 0 ? '+' : '' }}{{ fund.returns.sixMonth.toFixed(2) }}%
          </span>
          <span v-else class="metric-value muted">--</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">近1年</span>
          <span v-if="fund.returns.year !== 0" class="metric-value" :class="fund.returns.year >= 0 ? 'rise' : 'fall'">
            {{ fund.returns.year >= 0 ? '+' : '' }}{{ fund.returns.year.toFixed(2) }}%
          </span>
          <span v-else class="metric-value muted">--</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">成立以来</span>
          <span v-if="fund.returns.inception !== 0" class="metric-value" :class="fund.returns.inception >= 0 ? 'rise' : 'fall'">
            {{ fund.returns.inception >= 0 ? '+' : '' }}{{ fund.returns.inception.toFixed(2) }}%
          </span>
          <span v-else class="metric-value muted">--</span>
          <span class="metric-sub">成立 {{ fund.establishedYears }}年</span>
        </div>
      </div>
    </template>

    <!-- 净值走势 (含周期切换) -->
    <section class="section">
      <div class="section-header">
        <h4>净值走势</h4>
        <div class="chart-periods">
          <button v-for="p in navPeriods" :key="p.key"
            :class="['period-btn', { active: activeNavPeriod === p.key }]"
            @click="activeNavPeriod = p.key"
          >{{ p.label }}</button>
        </div>
      </div>
      <div class="chart-container" ref="navChartRef"></div>
    </section>

    <!-- 基金档案 -->
    <section class="section">
      <div class="section-header"><h4>基金档案</h4></div>
      <div class="profile-cards">
        <div class="profile-item"><span class="label">基金代码</span><span class="val">{{ fund.code }}</span></div>
        <div class="profile-item"><span class="label">基金类型</span><span class="val">{{ fund.type }}</span></div>
        <div class="profile-item"><span class="label">基金公司</span><span class="val">{{ fund.company }}</span></div>
        <div class="profile-item"><span class="label">基金经理</span><span class="val">{{ fund.manager }}</span></div>
        <div class="profile-item"><span class="label">成立日期</span><span class="val">{{ fund.establishDate }}</span></div>
        <div class="profile-item"><span class="label">基金规模</span><span class="val">{{ fund.scale }}</span></div>
      </div>
    </section>

    <!-- 前十大持仓 (蚂蚁财富百分比风格) -->
    <section class="section">
      <div class="section-header"><h4>前十大持仓</h4><span class="total-caption">合计 {{ totalHoldingRatio.toFixed(2) }}%</span></div>
      <div class="holdings-list">
        <div v-for="(h, idx) in fund.topHoldings" :key="h.code" class="holding-row" @click="$router.push(`/stock/${h.code}`)">
          <span class="h-rank">{{ idx + 1 }}</span>
          <div class="h-info">
            <span class="h-name">{{ h.name }}</span>
            <span class="h-code caption">{{ h.code }}</span>
          </div>
          <span class="h-ratio">{{ h.ratio.toFixed(2) }}%</span>
          <div class="h-bar-track">
            <div class="h-bar" :style="{ width: (h.ratio / fund.topHoldings[0].ratio * 100) + '%' }"
              :class="idx < 3 ? 'top3' : ''"></div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Star } from '@element-plus/icons-vue'
import echarts from '@/utils/echarts'
import { getFundInfo, getFundNav, getFundHoldings } from '@/api/fund'
import type { FundNav, FundHolding } from '@/types'

const route = useRoute()
const isWatched = ref(false)
const navChartRef = ref<HTMLElement>()
const activeNavPeriod = ref('year')
const loading = ref(true)
let navChart: echarts.ECharts | null = null

const navPeriods = [
  { key: 'month', label: '近1月' },
  { key: 'quarter', label: '近3月' },
  { key: 'halfyear', label: '近6月' },
  { key: 'year', label: '近1年' },
  { key: 'all', label: '全部' },
]

const fund = ref({
  code: route.params.code as string,
  name: '',
  type: '',
  company: '',
  manager: '',
  establishDate: '',
  scale: '',
  establishedYears: 0,
  nav: 0,
  accumulatedNav: 0,
  dailyReturn: 0,
  isMoneyMarket: false,
  sevenDayYield: 0 as number | null,
  dailyReturnMoney: 0 as number | null,
  monthReturnMoney: 0 as number | null,
  yearReturnMoney: 0 as number | null,
  returns: { month: 0, quarter: 0, sixMonth: 0, year: 0, inception: 0 },
  avgReturns: { month: 0, quarter: 0, sixMonth: 0, year: 0, inception: 0 },
  topHoldings: [] as { name: string; code: string; ratio: number }[],
})

const totalHoldingRatio = computed(() => fund.value.topHoldings.reduce((s, h) => s + h.ratio, 0))

let cachedNavData: FundNav[] = []

async function loadFundData() {
  loading.value = true
  try {
    const code = route.params.code as string
    // 1. 加载基金基本信息
    const info: any = await getFundInfo(code)
    if (info) {
      fund.value = {
        ...fund.value,
        code: info.fundCode || code,
        name: info.fundName || code,
        type: info.fundType || '',
        company: info.company || '',
        manager: info.manager || '',
        establishDate: info.establishDate || '',
        scale: info.scale || '',
        isMoneyMarket: !!info.isMoneyMarket,
        sevenDayYield: info.sevenDayYield ?? null,
        dailyReturnMoney: info.dailyReturnMoney ?? null,
        monthReturnMoney: info.monthReturnMoney ?? null,
        yearReturnMoney: info.yearReturnMoney ?? null,
        establishedYears: info.establishDate
          ? Math.round((Date.now() - new Date(info.establishDate).getTime()) / 365.25 / 86400000 * 10) / 10
          : 0,
        nav: Number(info.nav) || 0,
        accumulatedNav: Number(info.accumulatedNav) || 0,
      }
    }
    // 2. 加载净值数据
// @ts-ignore - API type mismatch
    const navData: any = await getFundNav(code, 1095)
    if (Array.isArray(navData) && navData.length > 0) {
      cachedNavData = navData
      // navData 按日期升序排列（旧→新）
      const last = navData[navData.length - 1]
      fund.value.nav = Number(last.nav) || fund.value.nav
      fund.value.accumulatedNav = Number(last.accumulatedNav) || fund.value.accumulatedNav
      if (navData.length >= 2) {
        const prev = navData[navData.length - 2]
        fund.value.dailyReturn = (Number(last.nav) - Number(prev.nav)) / Number(prev.nav)
      }
      // 计算各周期阶段收益率
      const lookups = { month: 22, quarter: 66, sixMonth: 130, year: 250 }
      const currentNav = Number(last.nav) || 0
      for (const [key, offset] of Object.entries(lookups)) {
        if (currentNav > 0 && navData.length > offset) {
          const idx = navData.length - 1 - offset
          const pastNav = Number(navData[idx]?.nav) || 0
          if (pastNav > 0) {
            fund.value.returns[key as keyof typeof fund.value.returns] = (currentNav - pastNav) / pastNav * 100
          }
        }
      }
      // 成立以来收益率
      if (currentNav > 0 && navData.length >= 2) {
        const firstNav = Number(navData[0]?.nav) || 0
        if (firstNav > 0) {
          fund.value.returns.inception = (currentNav - firstNav) / firstNav * 100
        }
      }
    }
    // 3. 加载持仓
    const holdings: FundHolding[] = await getFundHoldings(code) as FundHolding[]
    if (Array.isArray(holdings) && holdings.length > 0) {
      fund.value.topHoldings = holdings.map((h: FundHolding) => ({
        name: h.stockName || '',
        code: h.stockCode || '',
        ratio: Number(h.ratio) || 0,
      }))
    }
  } catch (_e) {
    console.warn('[Fund] 加载基金数据失败:', _e)
  } finally {
    loading.value = false
  }
}

function getNavDataByPeriod(key: string) {
  const days: Record<string, number> = { month: 22, quarter: 66, halfyear: 130, year: 250, all: 9999 }
  const limit = days[key] || 250
  if (cachedNavData.length === 0) return []
  const sliced = cachedNavData.slice(-limit)
  return sliced.map(d => ({
    date: d.navDate || '',
    nav: Number(d.nav) || 0,
    accNav: Number(d.accumulatedNav) > 0 ? Number(d.accumulatedNav) : null,
  }))
}

function getCountByPeriod(key: string) {
  const map: Record<string, number> = { month: 22, quarter: 66, halfyear: 130, year: 250, all: 500 }
  return map[key] || 250
}

function renderNavChart() {
  const el = navChartRef.value
  if (!el) return
  if (!navChart) {
    try {
      navChart = echarts.init(el)
    } catch {
      return
    }
  }

  const navData = getNavDataByPeriod(activeNavPeriod.value)
  const dates = navData.map(d => d.date)

  navChart.setOption({
    animation: false,
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(30,30,30,0.9)', borderColor: 'rgba(255,255,255,0.1)', textStyle: { color: '#fff' },
      formatter: function(params: any) {
        const p = Array.isArray(params) ? params[0] : params
        return `<div style="font-size:13px;font-weight:500;margin-bottom:4px">${p.axisValue}</div>` +
               `<div style="font-size:12px;color:#999">单位净值 <span style="float:right;color:#fff;font-weight:600;margin-left:16px">${Number(p.value).toFixed(4)}</span></div>`
      }
    },
    legend: { data: ['单位净值'], bottom: 0, textStyle: { fontSize: 12, color: '#999' } },
    grid: { left: '5%', right: '5%', top: '5%', bottom: '18%' },
    xAxis: { type: 'category', data: dates, axisTick: { show: false }, axisLabel: { fontSize: 11, color: '#999', interval: Math.max(1, Math.floor(dates.length / 8)) } },
    yAxis: { type: 'value', scale: true, splitLine: { lineStyle: { color: '#f5f5f5', type: 'dashed' } }, axisLabel: { fontSize: 11, color: '#999' } },
    series: [
      {
        name: '单位净值', type: 'line', data: navData.map(d => d.nav),
        smooth: true, symbol: 'none',
        lineStyle: { width: 2, color: '#0066cc' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(0,102,204,0.15)' }, { offset: 1, color: 'rgba(0,102,204,0)' }]) },
      },
    ],
  }, true)
}

function handleResize() { navChart?.resize() }

onMounted(async () => { await loadFundData(); nextTick(renderNavChart); window.addEventListener('resize', handleResize) })
onBeforeUnmount(() => { window.removeEventListener('resize', handleResize); navChart?.dispose() })
watch(activeNavPeriod, () => { nextTick(renderNavChart) })
</script>

<style scoped lang="scss">
.fund-detail {
  max-width: 1000px; margin: 0 auto; padding: $spacing-lg;
}

/* 头部 */
.fund-header {
  display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: $spacing-lg;
  .fund-brand {
    h2 { font-size: 24px; margin-bottom: 4px; }
    .fund-sub {
      display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
      font-size: 13px; color: $ink-muted-48;
      .fund-code { font-family: $font-display; font-weight: 500; color: $ink; }
      .fund-badge { font-size: 11px; padding: 2px 8px; background: rgba(0,102,204,0.1); color: $primary; border-radius: $rounded-xs; font-weight: 500; }
      .sep { color: #ddd; }
    }
  }
}

/* 关键指标 (蚂蚁财富卡片风格) */
.nav-metrics {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: $spacing-sm;
  margin-bottom: $spacing-xl;
}

.metric-card {
  background: $canvas-parchment;
  border-radius: $rounded-lg;
  padding: $spacing-md;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;

  &.metric-primary {
    background: linear-gradient(135deg, rgba(0,102,204,0.06), rgba(0,102,204,0.02));
    border: 1px solid rgba(0,102,204,0.1);
  }

  .metric-label { font-size: 11px; color: $ink-muted-48; font-weight: 500; }
  .metric-value { font-family: $font-display; font-size: 18px; font-weight: 700; }
  .metric-change { font-size: 12px; font-weight: 500; }
  .metric-sub { font-size: 10px; color: $ink-muted-48; }

  .rise { color: $rise; }
  .fall { color: $fall; }
}

/* 走势图 */
.section { margin-bottom: $spacing-xl; }
.section-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: $spacing-md;
  h4 { margin: 0; }
}
.total-caption { font-size: 13px; color: $ink-muted-48; }

.chart-periods { display: flex; gap: 2px; background: $canvas-parchment; border-radius: $rounded-sm; padding: 2px;
  .period-btn { padding: 5px 12px; border: none; background: transparent; font-size: 12px; color: $ink-muted-48; cursor: pointer; border-radius: $rounded-xs; transition: all 0.15s;
    &:hover { color: $ink; }
    &.active { background: $canvas; color: $primary; font-weight: 600; box-shadow: $shadow-card; }
  }
}

.chart-container { background: $canvas; border: 1px solid $divider-soft; border-radius: $rounded-lg; height: 380px; }

/* 基金档案 */
.profile-cards {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: $spacing-md;
  background: $canvas; border: 1px solid $divider-soft; border-radius: $rounded-lg; padding: $spacing-lg;
}
.profile-item { display: flex; flex-direction: column; gap: 2px;
  .label { font-size: 12px; color: $ink-muted-48; }
  .val { font-size: 15px; font-weight: 500; }
}

/* 持仓 (百分比条风格) */
.holdings-list {
  background: $canvas; border: 1px solid $divider-soft; border-radius: $rounded-lg; overflow: hidden;
}
.holding-row {
  display: grid; grid-template-columns: 28px 1fr 80px 1fr; align-items: center; gap: $spacing-sm;
  padding: $spacing-sm $spacing-lg; border-top: 1px solid $divider-soft;
  cursor: pointer; transition: background 0.15s;
  &:first-child { border-top: none; }
  &:hover { background: $surface-pearl; }
  .h-rank { font-size: 13px; font-weight: 600; color: $ink-muted-48; text-align: center; }
  .h-info { display: flex; flex-direction: column; gap: 1px;
    .h-name { font-size: 14px; font-weight: 500; }
    .h-code { font-size: 11px; color: $ink-muted-48; }
  }
  .h-ratio { font-family: $font-display; font-size: 15px; font-weight: 700; text-align: right; }
  .h-bar-track { height: 6px; background: #f0f0f0; border-radius: 3px; overflow: hidden; }
  .h-bar { height: 100%; border-radius: 3px; background: rgba(0,102,204,0.2); transition: width 0.3s;
    &.top3 { background: rgba(0,102,204,0.5); }
  }
}
</style>
