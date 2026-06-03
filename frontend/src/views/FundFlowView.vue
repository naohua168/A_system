<template>
  <div class="ff-page">
    <!-- ═══ 顶栏 ═══ -->
    <header class="ff-top">
      <h1 class="ff-title">资金流向</h1>
      <div class="ff-toolbar">
        <el-autocomplete
          v-model="stockCode"
          :fetch-suggestions="querySearchAsync"
          placeholder="股票代码/名称"
          :debounce="300"
          size="small"
          style="width:140px"
          @select="handleSelect"
          clearable
        >
          <template #default="{ item }">
            <span class="ff-ac-code">{{ item.code }}</span>
            <span class="ff-ac-name">{{ item.name }}</span>
          </template>
        </el-autocomplete>
        <el-button size="small" type="primary" @click="fetchData" :loading="loading">查询</el-button>
      </div>
    </header>

    <div v-if="!records.length && !loading" class="ff-empty">
      <p>输入股票代码，查看主力资金流向</p>
      <p class="ff-empty-sub">示例：000858 五粮液 · 600519 贵州茅台 · 300750 宁德时代</p>
    </div>

    <template v-if="records.length">
      <!-- ═══ ① 市场全景 + 个股全景 ═══ -->
      <section class="ff-double">
        <!-- 全市场 -->
        <div class="ff-card">
          <div class="ff-card-title">全市场资金流向</div>
          <div class="ff-card-body">
            <table class="ff-summary-table">
              <tr><td class="ff-label">主力净流入</td><td class="ff-val" :class="m.m >= 0 ? 'up' : 'dn'">{{ fmtTotal(m.m) }}</td></tr>
              <tr><td class="ff-label">超大单</td><td class="ff-val" :class="m.s >= 0 ? 'up' : 'dn'">{{ fmtCompact(m.s) }}</td><td class="ff-desc">≥500万</td></tr>
              <tr><td class="ff-label">大单</td><td class="ff-val" :class="m.l >= 0 ? 'up' : 'dn'">{{ fmtCompact(m.l) }}</td><td class="ff-desc">100—500万</td></tr>
              <tr><td class="ff-label">中单</td><td class="ff-val" :class="m.md >= 0 ? 'up' : 'dn'">{{ fmtCompact(m.md) }}</td><td class="ff-desc">30—100万</td></tr>
              <tr><td class="ff-label">小单</td><td class="ff-val" :class="m.sm >= 0 ? 'up' : 'dn'">{{ fmtCompact(m.sm) }}</td><td class="ff-desc">&lt;30万</td></tr>
            </table>
            <div class="ff-mkt-progress">
              <div class="ff-mkt-progress-bar"><span class="ff-mkt-up" :style="{ width: mUpPct + '%' }"></span><span class="ff-mkt-dn" :style="{ width: (100 - mUpPct) + '%' }"></span></div>
              <div class="ff-mkt-progress-label"><span class="up-text">上涨 {{ marketUp }}</span><span> / </span><span class="dn-text">下跌 {{ marketDn }}</span></div>
            </div>
          </div>
        </div>

        <!-- 个股 -->
        <div class="ff-card">
          <div class="ff-card-title">
            <span>{{ stockName || stockCode.trim() }}</span>
            <span class="ff-stock-code">{{ stockCode.trim() }}　{{ formatPrice(latestClose) }}</span>
          </div>
          <div class="ff-card-body">
            <table class="ff-summary-table">
              <tr><td class="ff-label">今日主力净流入</td><td class="ff-val" :class="lastDay?.mainIn >= 0 ? 'up' : 'dn'">{{ fmtVal(lastDay?.mainIn) }}</td><td class="ff-desc">占比 {{ calcRatio(lastDay?.mainIn, lastDay) }}</td></tr>
              <tr><td class="ff-label">超大单</td><td class="ff-val" :class="lastDay?.superNetIn >= 0 ? 'up' : 'dn'">{{ fmtCompact(lastDay?.superNetIn) }}</td><td class="ff-desc">{{ calcRatio(lastDay?.superNetIn, lastDay) }}</td></tr>
              <tr><td class="ff-label">大单</td><td class="ff-val" :class="lastDay?.largeNetIn >= 0 ? 'up' : 'dn'">{{ fmtCompact(lastDay?.largeNetIn) }}</td><td class="ff-desc">{{ calcRatio(lastDay?.largeNetIn, lastDay) }}</td></tr>
              <tr><td class="ff-label">中单</td><td class="ff-val" :class="lastDay?.mediumNetIn >= 0 ? 'up' : 'dn'">{{ fmtCompact(lastDay?.mediumNetIn) }}</td><td class="ff-desc">{{ calcRatio(lastDay?.mediumNetIn, lastDay) }}</td></tr>
              <tr><td class="ff-label">小单</td><td class="ff-val" :class="lastDay?.smallNetIn >= 0 ? 'up' : 'dn'">{{ fmtCompact(lastDay?.smallNetIn) }}</td><td class="ff-desc">{{ calcRatio(lastDay?.smallNetIn, lastDay) }}</td></tr>
            </table>
            <div class="ff-meta-info">日期：{{ lastDay?.tradeDate }} ｜ 统计区间：{{ records[records.length-1]?.tradeDate }} ~ {{ records[0]?.tradeDate }}</div>
          </div>
        </div>
      </section>

      <!-- ═══ ② 主力趋势图 ═══ -->
      <section class="ff-card ff-card-chart">
        <div class="ff-card-title">
          <span>主力净流入趋势</span>
          <div class="ff-chart-tabs">
            <button :class="['ff-tab', { act: activeChart === 'main' }]" @click="activeChart = 'main'">主力+收盘价</button>
            <button :class="['ff-tab', { act: activeChart === 'detail' }]" @click="activeChart = 'detail'">四单趋势线</button>
            <button :class="['ff-tab', { act: activeChart === 'stack' }]" @click="activeChart = 'stack'">堆叠柱状</button>
          </div>
        </div>
        <div ref="chartRef" class="ff-chart-body"></div>
      </section>

      <!-- ═══ ③ 多空 + 累计 ═══ -->
      <section class="ff-double">
        <div class="ff-card">
          <div class="ff-card-title">多空力量对比</div>
          <div class="ff-card-body ff-battle-body">
            <div class="ff-battle-bar">
              <div class="ff-battle-up" :style="{ width: bullPct + '%' }"><span v-if="bullPct > 15">多头 {{ bullPct.toFixed(0) }}%</span></div>
              <div class="ff-battle-dn" :style="{ width: bearPct + '%' }"><span v-if="bearPct > 15">空头 {{ bearPct.toFixed(0) }}%</span></div>
            </div>
            <div class="ff-battle-meta">
              <span><i class="ff-dot-dot" style="background:#D93026"></i>净流入 {{ bullDays }} 天</span>
              <span><i class="ff-dot-dot" style="background:#34A853"></i>净流出 {{ bearDays }} 天</span>
            </div>
          </div>
        </div>

        <div class="ff-card">
          <div class="ff-card-title">累计资金净流入</div>
          <div class="ff-card-body ff-cum-body">
            <div class="ff-cum-cell"><span class="ff-cum-label">5日</span><span class="ff-cum-val" :class="cum5d >= 0 ? 'up' : 'dn'">{{ fmtTotal(cum5d) }}</span></div>
            <div class="ff-cum-cell"><span class="ff-cum-label">10日</span><span class="ff-cum-val" :class="cum10d >= 0 ? 'up' : 'dn'">{{ fmtTotal(cum10d) }}</span></div>
            <div class="ff-cum-cell"><span class="ff-cum-label">20日</span><span class="ff-cum-val" :class="totalMain >= 0 ? 'up' : 'dn'">{{ fmtTotal(totalMain) }}</span></div>
          </div>
        </div>
      </section>

      <!-- ═══ ④ 逐日明细 ═══ -->
      <section class="ff-card">
        <div class="ff-card-title" style="border-bottom:none">逐日资金流向明细 <span class="ff-unit">（单位：万元）</span></div>
        <el-table
          :data="sortedRecords"
          stripe
          size="small"
          style="width:100%"
          :header-cell-style="{ background: '#f5f6fa', color: '#666', borderBottom: '1px solid #eee', fontSize: '12px', fontWeight: 500, padding: '10px 0 8px' }"
          :cell-style="{ fontSize: '12px', padding: '8px 0', color: '#333' }"
          :row-class-name="tableRowClass"
        >
          <el-table-column prop="tradeDate" label="日期" width="85" />
          <el-table-column label="收盘价" width="75" align="right">
            <template #default="{ row }">{{ formatPrice(row.close) }}</template>
          </el-table-column>
          <el-table-column label="主力净流入" width="115" align="right" prop="mainIn" sortable>
            <template #default="{ row }">
              <span :class="row.mainIn >= 0 ? 'up' : 'dn'">{{ fmtCompact(row.mainIn) }}</span>
              <span :class="['ff-ratio', row.mainIn >= 0 ? 'up' : 'dn']">{{ calcRatio(row.mainIn, row) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="超大单" width="95" align="right">
            <template #default="{ row }"><span :class="row.superNetIn >= 0 ? 'up' : 'dn'">{{ fmtCompact(row.superNetIn) }}</span></template>
          </el-table-column>
          <el-table-column label="大单" width="90" align="right">
            <template #default="{ row }"><span :class="row.largeNetIn >= 0 ? 'up' : 'dn'">{{ fmtCompact(row.largeNetIn) }}</span></template>
          </el-table-column>
          <el-table-column label="中单" width="90" align="right">
            <template #default="{ row }"><span :class="row.mediumNetIn >= 0 ? 'up' : 'dn'">{{ fmtCompact(row.mediumNetIn) }}</span></template>
          </el-table-column>
          <el-table-column label="小单" width="90" align="right">
            <template #default="{ row }"><span :class="row.smallNetIn >= 0 ? 'up' : 'dn'">{{ fmtCompact(row.smallNetIn) }}</span></template>
          </el-table-column>
        </el-table>
      </section>
    </template>

    <!-- 加载骨架 -->
    <template v-if="loading && !records.length">
      <div v-for="i in 4" :key="i" class="ff-sk" :style="{ width: 50 + i * 15 + '%' }"></div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import echarts from '@/utils/echarts'
import { getFundFlow } from '@/api/signal'
import { searchStocks } from '@/api/market'
import { formatPrice } from '@/utils/format'
import { useAutoRefresh } from '@/composables/useAutoRefresh'

interface Day { tradeDate: string; close: number; mainIn: number; superNetIn: number; largeNetIn: number; mediumNetIn: number; smallNetIn: number }
interface SItem { code: string; name: string }

const loading = ref(false)
const stockCode = ref('000858')
const stockName = ref('')
const records = ref<Day[]>([])
const activeChart = ref<'main' | 'detail' | 'stack'>('main')
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

// 全市场示例
const m = ref({ m: 2850000000, s: 1200000000, l: 950000000, md: 420000000, sm: 280000000 })
const marketUp = ref(2456); const marketDn = ref(1890)
const mUpPct = computed(() => { const t = marketUp.value + marketDn.value; return t > 0 ? (marketUp.value / t) * 100 : 50 })

const sortedRecords = computed(() => [...records.value].sort((a, b) => b.tradeDate.localeCompare(a.tradeDate)))
const lastDay = computed(() => records.value[records.value.length - 1])
const latestClose = computed(() => sortedRecords.value[0]?.close ?? 0)
const totalMain = computed(() => records.value.reduce((s, r) => s + r.mainIn, 0))
const cum5d = computed(() => records.value.slice(-5).reduce((s, r) => s + r.mainIn, 0))
const cum10d = computed(() => records.value.slice(-10).reduce((s, r) => s + r.mainIn, 0))
const bullDays = computed(() => records.value.filter(r => r.mainIn > 0).length)
const bearDays = computed(() => records.value.filter(r => r.mainIn < 0).length)
const bullPct = computed(() => records.value.length ? (bullDays.value / records.value.length) * 100 : 50)
const bearPct = computed(() => 100 - bullPct.value)

function fmtVal(v?: number): string {
  if (!v) return '0'; const w = v / 10000; const s = v >= 0 ? '+' : ''
  return Math.abs(w) >= 10000 ? s + (w / 10000).toFixed(2) + '亿' : s + w.toFixed(1) + '万'
}
function fmtTotal(v: number): string {
  const w = v / 10000; const s = v >= 0 ? '+' : ''
  return Math.abs(w) >= 10000 ? s + (w / 10000).toFixed(2) + '亿' : s + w.toFixed(0) + '万'
}
function fmtCompact(v?: number): string {
  if (!v) return '0'; const w = v / 10000
  return Math.abs(w) >= 10000 ? (w / 10000).toFixed(2) + '亿' : w.toFixed(1) + '万'
}
function calcRatio(v?: number, row?: Day): string {
  if (!row || !v) return ''
  const t = Math.abs(row.mainIn) + Math.abs(row.superNetIn) + Math.abs(row.largeNetIn) + Math.abs(row.mediumNetIn) + Math.abs(row.smallNetIn)
  return t ? (Math.abs(v) / t * 100).toFixed(0) + '%' : ''
}
function tableRowClass({ row }: { row: Day }) { return row.mainIn >= 0 ? '' : 'ff-row-out' }

async function querySearchAsync(q: string, cb: (items: SItem[]) => void) {
  if (!q) { cb([]); return }
  try { const r = await searchStocks(q) as any[]; cb(Array.isArray(r) ? r.map((x: any) => ({ code: x.stockCode || x.code, name: x.stockName || x.name })) : []) } catch { cb([]) }
}
function handleSelect(i: SItem) { stockCode.value = i.code; stockName.value = i.name; fetchData() }

async function fetchData() {
  const c = stockCode.value.trim()
  if (!c) return; loading.value = true
  try {
    const raw = await getFundFlow(c, 20) as any[]
    records.value = (Array.isArray(raw) ? raw : []).map(i => ({
      tradeDate: i.tradeDate, close: Number(i.close) || 0, mainIn: Number(i.mainIn) || 0,
      superNetIn: Number(i.superLargeIn) || 0, largeNetIn: Number(i.largeIn) || 0,
      mediumNetIn: Number(i.mediumIn) || 0, smallNetIn: Number(i.smallIn) || 0,
    }))
    if (!stockName.value && records.value.length) stockName.value = c
    await nextTick(); renderChart()
  } catch { records.value = [] } finally { loading.value = false }
}

function renderChart() {
  if (!chartRef.value || !records.value.length) return
  if (!chart) chart = echarts.init(chartRef.value, undefined, { renderer: 'canvas' })
  const d = records.value; const dates = d.map(x => x.tradeDate)

  if (activeChart.value === 'stack') {
    chart.setOption({
      color: ['#D93026', '#E68A2E', '#1890FF', '#34A853'],
      tooltip: { trigger: 'axis', backgroundColor: '#fff', borderColor: '#ddd', textStyle: { color: '#333', fontSize: 11 } },
      legend: { data: ['超大单','大单','中单','小单'], textStyle: { color: '#666', fontSize: 11 }, top: 4, itemWidth: 12, itemHeight: 8 },
      grid: { left: 50, right: 12, top: 32, bottom: 18 },
      xAxis: { type: 'category', data: dates, axisLine: { lineStyle: { color: '#e8e8e8' } }, axisLabel: { color: '#999', fontSize: 11 }, axisTick: { show: false } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } }, axisLabel: { color: '#999', fontSize: 11, formatter: (v: number) => { const a = Math.abs(v); return a >= 1e8 ? (v/1e8).toFixed(0)+'亿' : a >= 1e4 ? (v/1e4).toFixed(0)+'万' : v.toFixed(0) } } },
      series: [
        { name: '超大单', type: 'bar', stack: 'a', data: d.map(x => x.superNetIn), barWidth: 16 },
        { name: '大单', type: 'bar', stack: 'a', data: d.map(x => x.largeNetIn) },
        { name: '中单', type: 'bar', stack: 'a', data: d.map(x => x.mediumNetIn) },
        { name: '小单', type: 'bar', stack: 'a', data: d.map(x => x.smallNetIn) },
      ],
    }, { notMerge: true })
  } else if (activeChart.value === 'detail') {
    chart.setOption({
      color: ['#D93026', '#E68A2E', '#1890FF', '#34A853'],
      tooltip: { trigger: 'axis', backgroundColor: '#fff', borderColor: '#ddd', textStyle: { color: '#333', fontSize: 11 } },
      legend: { data: ['超大单','大单','中单','小单'], textStyle: { color: '#666', fontSize: 11 }, top: 4, itemWidth: 12, itemHeight: 8 },
      grid: { left: 50, right: 12, top: 32, bottom: 18 },
      xAxis: { type: 'category', data: dates, axisLine: { lineStyle: { color: '#e8e8e8' } }, axisLabel: { color: '#999', fontSize: 11 }, axisTick: { show: false } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } }, axisLabel: { color: '#999', fontSize: 11, formatter: (v: number) => { const a = Math.abs(v); return a >= 1e8 ? (v/1e8).toFixed(0)+'亿' : a >= 1e4 ? (v/1e4).toFixed(0)+'万' : v.toFixed(0) } } },
      series: [
        { name: '超大单', type: 'line', smooth: true, data: d.map(x => x.superNetIn), symbol: 'none', areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{offset: 0, color: 'rgba(217,48,38,0.08)'},{offset: 1, color: 'rgba(217,48,38,0)'}]} } },
        { name: '大单', type: 'line', smooth: true, data: d.map(x => x.largeNetIn), symbol: 'none', areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{offset: 0, color: 'rgba(230,138,46,0.08)'},{offset: 1, color: 'rgba(230,138,46,0)'}]} } },
        { name: '中单', type: 'line', smooth: true, data: d.map(x => x.mediumNetIn), symbol: 'none', areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{offset: 0, color: 'rgba(24,144,255,0.08)'},{offset: 1, color: 'rgba(24,144,255,0)'}]} } },
        { name: '小单', type: 'line', smooth: true, data: d.map(x => x.smallNetIn), symbol: 'none', areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{offset: 0, color: 'rgba(52,168,83,0.08)'},{offset: 1, color: 'rgba(52,168,83,0)'}]} } },
      ],
    }, { notMerge: true })
  } else {
    chart.setOption({
      color: ['#D93026', '#E68A2E'],
      tooltip: { trigger: 'axis', backgroundColor: '#fff', borderColor: '#ddd', textStyle: { color: '#333', fontSize: 11 } },
      grid: { left: 50, right: 50, top: 8, bottom: 18 },
      xAxis: { type: 'category', data: dates, axisLine: { lineStyle: { color: '#e8e8e8' } }, axisLabel: { color: '#999', fontSize: 11 }, axisTick: { show: false } },
      yAxis: [
        { type: 'value', splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } }, axisLabel: { color: '#999', fontSize: 11, formatter: (v: number) => { const a = Math.abs(v); return a >= 1e8 ? (v/1e8).toFixed(0)+'亿' : a >= 1e4 ? (v/1e4).toFixed(0)+'万' : v.toFixed(0) } } },
        { type: 'value', splitLine: { show: false }, axisLabel: { color: '#999', fontSize: 11, formatter: (v: number) => String(v.toFixed(0)) } },
      ],
      series: [
        { name: '主力净流入', type: 'bar', data: d.map(x => x.mainIn), itemStyle: { color: (p: any) => p.value >= 0 ? { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{offset: 0, color: '#D93026'},{offset: 1, color: '#e57373'}] } : { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{offset: 0, color: '#34A853'},{offset: 1, color: '#81C784'}] }, borderRadius: [2, 2, 0, 0] }, barWidth: 14 },
        { name: '收盘价', type: 'line', yAxisIndex: 1, smooth: true, data: d.map(x => x.close), lineStyle: { color: '#E68A2E', width: 2 }, symbol: 'diamond', symbolSize: 5 },
      ],
    }, { notMerge: true })
  }
  chart?.resize()
}

watch(activeChart, () => nextTick(renderChart))
const handleResize = () => chart?.resize()
onMounted(() => { fetchData(); window.addEventListener('resize', handleResize) })
useAutoRefresh(fetchData, 120_000)
onUnmounted(() => { chart?.dispose(); window.removeEventListener('resize', handleResize) })
</script>

<style scoped lang="scss">
// ═══════════ 同花顺风格：白底 + 深色字 + 红涨绿跌 ═══════════
.ff-page { padding: 16px 24px; max-width: 1200px; margin: 0 auto; }

// ── 顶栏 ──
.ff-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.ff-title { font-size: 20px; font-weight: 600; color: #222; margin: 0; }
.ff-toolbar { display: flex; align-items: center; gap: 6px; }
.ff-ac-code { color: #1890FF; font-weight: 600; font-size: 12px; }
.ff-ac-name { color: #666; font-size: 12px; margin-left: 6px; }

// ── 卡 ──
.ff-card { background: #fff; border: 1px solid #e8e8e8; border-radius: 6px; overflow: hidden; }
.ff-card-title {
  display: flex; align-items: center; gap: 8px;
  padding: 11px 16px; font-size: 14px; font-weight: 600; color: #333;
  border-bottom: 1px solid #f0f0f0;
}
.ff-card-body { padding: 14px 16px; }

// ── 双栏 ──
.ff-double { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }
@media (max-width: 900px) { .ff-double { grid-template-columns: 1fr; } }

// ── 空态 ──
.ff-empty { text-align: center; padding: 80px 0; color: #999; font-size: 14px; .ff-empty-sub { font-size: 12px; color: #bbb; margin-top: 4px; } }

// ── 概要表 ──
.ff-summary-table { width: 100%; border-collapse: collapse;
  tr { border-bottom: 1px solid #f7f7f7; &:last-child { border-bottom: none; } }
  td { padding: 6px 4px; vertical-align: middle; }
}
.ff-label { font-size: 12px; color: #888; width: 100px; }
.ff-val { font-size: 16px; font-weight: 600; text-align: right; min-width: 80px; }
.ff-desc { font-size: 10px; color: #bbb; text-align: right; padding-left: 8px; }

// ── 涨跌进度条 ──
.ff-mkt-progress { margin-top: 10px; }
.ff-mkt-progress-bar { display: flex; height: 4px; border-radius: 2px; overflow: hidden; background: #f0f0f0; }
.ff-mkt-up { background: #D93026; height: 100%; }
.ff-mkt-dn { background: #34A853; height: 100%; }
.ff-mkt-progress-label { display: flex; justify-content: center; gap: 4px; font-size: 11px; color: #999; margin-top: 4px; }
.up-text { color: #D93026; }
.dn-text { color: #34A853; }

// ── 个股代码 ──
.ff-stock-code { font-size: 12px; font-weight: 400; color: #999; margin-left: 8px; }

// ── 元信息 ──
.ff-meta-info { margin-top: 8px; font-size: 11px; color: #bbb; }

// ── 多空 ──
.ff-battle-body { padding: 18px 16px; }
.ff-battle-bar { display: flex; height: 26px; border-radius: 4px; overflow: hidden; margin-bottom: 8px; }
.ff-battle-up, .ff-battle-dn { display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; color: #fff; transition: width 0.4s; }
.ff-battle-up { background: linear-gradient(90deg, #D93026, #e57373); }
.ff-battle-dn { background: linear-gradient(90deg, #81C784, #34A853); }
.ff-battle-meta { display: flex; gap: 20px; font-size: 12px; color: #999; span { display: flex; align-items: center; gap: 5px; } }
.ff-dot-dot { width: 8px; height: 8px; border-radius: 2px; display: inline-block; }

// ── 累计 ──
.ff-cum-body { display: flex; justify-content: space-around; padding: 20px 16px; }
.ff-cum-cell { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.ff-cum-label { font-size: 12px; color: #888; }
.ff-cum-val { font-size: 17px; font-weight: 600; }

// ── 图表 ──
.ff-card-chart { margin-bottom: 10px; }
.ff-chart-tabs { display: flex; gap: 4px; margin-left: auto; }
.ff-tab {
  padding: 3px 10px; font-size: 11px; color: #888;
  background: #f5f6fa; border: 1px solid #e0e0e0; border-radius: 3px; cursor: pointer;
  &:hover { color: #333; }
  &.act { color: #1890FF; background: #e8f0fe; border-color: #1890FF; }
}
.ff-chart-body { height: 260px; }

// ── 表格 ──
.ff-unit { font-size: 11px; color: #aaa; font-weight: 400; margin-left: 6px; }
.ff-ratio { font-size: 10px; margin-left: 3px; opacity: 0.55; }
:deep(.ff-row-out td) { background: #fcfcfc; }

// ── 红涨绿跌 ──
:deep(.up) { color: #D93026; }
:deep(.dn) { color: #34A853; }
:deep(.el-table--striped .el-table__body tr.el-table__row--striped td) { background: #fafafa; }
:deep(.el-table--striped .el-table__body tr.el-table__row--striped.ff-row-out td) { background: #f7f7f7; }

// ── 骨架 ──
.ff-sk { height: 12px; margin: 8px 0; background: #f5f5f5; border-radius: 3px; animation: ff-shimmer 1.5s infinite; }
@keyframes ff-shimmer { 0%,100% { opacity: 0.4; } 50% { opacity: 0.8; } }
</style>
