<template>
  <div class="nb-page">
    <!-- ═══ 顶栏 ═══ -->
    <header class="nb-top">
      <h1>北向资金 · 分时走势</h1>
      <div class="nb-toolbar">
        <ReviewDatePicker @change="(d:string) => { reviewDate.value = d; fetchData() }" />
        <span class="nb-date-label">{{ todayLabel }}</span>
        <el-button size="small" @click="fetchData" :loading="loading">刷新</el-button>
      </div>
    </header>

    <!-- 骨架 -->
    <template v-if="loading">
      <div class="nb-sk" v-for="i in 4" :key="i"></div>
    </template>

    <!-- 错误/空 -->
    <div v-else-if="error" class="nb-empty">
      <p>{{ error }}</p>
      <el-button size="small" @click="fetchData">重试</el-button>
    </div>
    <div v-else-if="!records.length" class="nb-empty"><p>暂无北向资金数据</p></div>

    <template v-else>
      <!-- ═══ ① 今日概览（三大数字） ═══ -->
      <section class="nb-metrics">
        <div class="nb-metric">
          <span class="nb-m-lb">沪股通（沪港通）</span>
          <span class="nb-m-val" :class="hgt >= 0 ? 'r' : 'g'">{{ hgt >= 0 ? '+' : '' }}{{ hgt.toFixed(2) }}<span class="nb-m-unit">亿</span></span>
          <span class="nb-m-desc">{{ hgt >= 0 ? '净买入' : '净卖出' }} {{ direction(hgt) }}</span>
        </div>
        <div class="nb-metric">
          <span class="nb-m-lb">深股通（深港通）</span>
          <span class="nb-m-val" :class="sgt >= 0 ? 'r' : 'g'">{{ sgt >= 0 ? '+' : '' }}{{ sgt.toFixed(2) }}<span class="nb-m-unit">亿</span></span>
          <span class="nb-m-desc">{{ sgt >= 0 ? '净买入' : '净卖出' }} {{ direction(sgt) }}</span>
        </div>
        <div class="nb-metric">
          <span class="nb-m-lb">合计（沪深港通）</span>
          <span class="nb-m-val total" :class="totalAmt >= 0 ? 'r' : 'g'">{{ totalAmt >= 0 ? '+' : '' }}{{ totalAmt.toFixed(2) }}<span class="nb-m-unit">亿</span></span>
          <span class="nb-m-desc">{{ directionText }}</span>
        </div>
      </section>

      <!-- ═══ ② 分时趋势图（全量 262 个时间点） ═══ -->
      <section class="nb-card nb-chart-card">
        <div class="nb-card-title">
          <div class="nb-ct-left">
            <span>今日分时趋势</span>
            <span class="nb-card-sub">{{ records.length }} 个时间点 · 每分钟采样</span>
          </div>
          <div class="nb-range-switch">
            <span v-for="r in ranges" :key="r.key"
              :class="['nb-range-btn', { active: activeRange === r.key }]"
              @click="activeRange = r.key">{{ r.label }}</span>
          </div>
        </div>
        <div ref="chartRef" class="nb-chart-body" v-loading="chartLoading"></div>
      </section>

      <!-- ═══ ③ 关键统计 ═══ -->
      <section class="nb-stats">
        <div class="nb-stat">
          <span class="nb-stat-lb">全日最高（合计）</span>
          <span class="nb-stat-v" :class="maxTotal >= 0 ? 'r' : 'g'">{{ maxTotal >= 0 ? '+' : '' }}{{ maxTotal.toFixed(2) }}亿</span>
          <span class="nb-stat-t">{{ maxTime }}</span>
        </div>
        <div class="nb-stat">
          <span class="nb-stat-lb">全日最低（合计）</span>
          <span class="nb-stat-v" :class="minTotal >= 0 ? 'r' : 'g'">{{ minTotal >= 0 ? '+' : '' }}{{ minTotal.toFixed(2) }}亿</span>
          <span class="nb-stat-t">{{ minTime }}</span>
        </div>
        <div class="nb-stat">
          <span class="nb-stat-lb">日内振幅</span>
          <span class="nb-stat-v">{{ amplitude.toFixed(2) }}亿</span>
          <span class="nb-stat-t">最高 - 最低</span>
        </div>
        <div class="nb-stat">
          <span class="nb-stat-lb">数据点数</span>
          <span class="nb-stat-v">{{ records.length }}</span>
          <span class="nb-stat-t">09:10 ~ 15:00</span>
        </div>
      </section>

      <!-- ═══ ④ 逐笔明细表（范围过滤后） ═══ -->
      <section class="nb-card">
        <div class="nb-card-title">
          <span>逐笔明细 · {{ filteredRecords.length }} 条</span>
          <span class="nb-card-sub">单位：亿元（累计净流入）</span>
        </div>
        <el-table
          :data="filteredRecords"
          stripe
          size="small"
          height="380"
          style="width:100%"
          :header-cell-style="{ background: '#f5f6fa', color: '#666', borderBottom: '1px solid #eee', fontSize: '12px', fontWeight: 500, padding: '9px 0' }"
          :cell-style="{ fontSize: '12px', padding: '7px 0', color: '#333' }"
        >
          <el-table-column prop="time" label="时间" width="80" />
          <el-table-column label="沪股通(亿)" width="140" align="right" sortable>
            <template #default="{ row }">
              <span :class="(row.hgtYi || 0) >= 0 ? 'r' : 'g'">{{ (row.hgtYi || 0) >= 0 ? '+' : '' }}{{ safeNum(row.hgtYi, 2) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="深股通(亿)" width="140" align="right" sortable>
            <template #default="{ row }">
              <span :class="(row.sgtYi || 0) >= 0 ? 'r' : 'g'">{{ (row.sgtYi || 0) >= 0 ? '+' : '' }}{{ safeNum(row.sgtYi, 2) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="合计(亿)" width="140" align="right" sortable>
            <template #default="{ row }">
              <span :class="(safeNum(row.hgtYi) + safeNum(row.sgtYi)) >= 0 ? 'r' : 'g'">
                {{ (safeNum(row.hgtYi) + safeNum(row.sgtYi)) >= 0 ? '+' : '' }}{{ (safeNum(row.hgtYi) + safeNum(row.sgtYi)).toFixed(2) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="方向" width="80" align="center">
            <template #default="{ row }">
              <span :class="['nb-badge', (safeNum(row.hgtYi) + safeNum(row.sgtYi)) >= 0 ? 'r' : 'g']">
                {{ (safeNum(row.hgtYi) + safeNum(row.sgtYi)) >= 0 ? '净流入' : '净流出' }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { getNorthboundMinute } from '@/api/signal'
import echarts from '@/utils/echarts'
import { safeNum } from '@/composables/useApiRetry'
import { useAutoRefresh } from '@/composables/useAutoRefresh'
import ReviewDatePicker from '@/components/common/ReviewDatePicker.vue'

const loading = ref(false)
const chartLoading = ref(false)
const reviewDate = ref('')
const records = ref<any[]>([])
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
const error = ref<string | null>(null)
const activeRange = ref('full')

const todayLabel = new Date().toISOString().slice(0, 10)

const ranges = [
  { key: 'morning', label: '上午' },
  { key: 'afternoon', label: '下午' },
  { key: 'full', label: '全天' },
]

// 范围过滤
const rangeTimes: Record<string, [string, string]> = {
  morning: ['09:10', '11:30'],
  afternoon: ['13:00', '15:00'],
  full: ['09:10', '15:00'],
}
const filteredRecords = computed(() => {
  const [start, end] = rangeTimes[activeRange.value] || ['09:10', '15:00']
  return records.value.filter(r => r.time >= start && r.time <= end)
})

// 最近一条（最后值 = 收盘值）
const lastRecord = computed(() => records.value[records.value.length - 1] || {} as any)
const hgt = computed(() => safeNum(lastRecord.value.hgtYi))
const sgt = computed(() => safeNum(lastRecord.value.sgtYi))
const totalAmt = computed(() => hgt.value + sgt.value)

// 极值（从当前范围取）
const currentTotal = computed(() =>
  filteredRecords.value.map(r => safeNum(r.hgtYi) + safeNum(r.sgtYi))
)
const maxTotal = computed(() => currentTotal.value.length ? Math.max(...currentTotal.value) : 0)
const minTotal = computed(() => currentTotal.value.length ? Math.min(...currentTotal.value) : 0)
const amplitude = computed(() => maxTotal.value - minTotal.value)

// 极值时间
const maxTime = computed(() => {
  const i = currentTotal.value.indexOf(maxTotal.value)
  return i >= 0 ? filteredRecords.value[i]?.time || '' : ''
})
const minTime = computed(() => {
  const i = currentTotal.value.indexOf(minTotal.value)
  return i >= 0 ? filteredRecords.value[i]?.time || '' : ''
})

function direction(v: number): string {
  const abs = Math.abs(v)
  if (abs >= 50) return '大幅'
  if (abs >= 10) return '明显'
  if (abs >= 1) return '小幅'
  return '微量'
}
const directionText = computed(() => {
  if (totalAmt.value > 5) return '外资积极流入 A 股'
  if (totalAmt.value > 0) return '外资小幅流入 A 股'
  if (totalAmt.value > -5) return '外资小幅流出 A 股'
  return '外资加速流出 A 股'
})

// ── 图表渲染 ──
function renderChart() {
  const el = chartRef.value
  if (!el || !filteredRecords.value.length) return
  chartLoading.value = true
  chart?.dispose()
  try { chart = echarts.init(el) } catch {
    setTimeout(renderChart, 120)
    return
  }
  const data = filteredRecords.value
  const times = data.map(d => d.time)
  const h = data.map(d => safeNum(d.hgtYi))
  const s = data.map(d => safeNum(d.sgtYi))
  const totalLine = data.map(d => safeNum(d.hgtYi) + safeNum(d.sgtYi))

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#fff',
      borderColor: '#e8e8e8',
      textStyle: { color: '#333', fontSize: 12 },
      formatter: (params: any[]) => {
        let s = `<b style="font-size:13px">${params[0].axisValue}</b>`
        params.forEach((p: any) => {
          const v = Number(p.value) || 0
          s += `<div style="display:flex;justify-content:space-between;gap:24px;font-size:12px;margin-top:4px">
            <span>${p.marker} ${p.seriesName}</span>
            <span style="font-weight:600;${v >= 0 ? 'color:#D93026' : 'color:#34A853'}">${v >= 0 ? '+' : ''}${v.toFixed(2)}亿</span>
          </div>`
        })
        return s
      },
    },
    legend: {
      data: ['沪股通', '深股通', '合计'],
      textStyle: { color: '#666', fontSize: 11 },
      top: 4, itemWidth: 16, itemHeight: 8,
    },
    grid: { left: 50, right: 16, top: 38, bottom: 22 },
    xAxis: {
      type: 'category', data: times,
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: {
        color: '#999', fontSize: 11,
        formatter: (v: string, i: number) => i % Math.ceil(times.length / 12) === 0 ? v : '',
      },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
      axisLabel: { color: '#999', fontSize: 11, formatter: (v: number) => v.toFixed(0) + '亿' },
    },
    series: [
      {
        name: '沪股通', type: 'line', smooth: true,
        data: h, symbol: 'none',
        lineStyle: { color: '#1890FF', width: 2 },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(24,144,255,0.12)' }, { offset: 1, color: 'rgba(24,144,255,0)' }] } },
      },
      {
        name: '深股通', type: 'line', smooth: true,
        data: s, symbol: 'none',
        lineStyle: { color: '#D93026', width: 2 },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(217,48,38,0.1)' }, { offset: 1, color: 'rgba(217,48,38,0)' }] } },
      },
      {
        name: '合计', type: 'line', smooth: true,
        data: totalLine, symbol: 'none',
        lineStyle: { color: '#722ED1', width: 2, type: 'dashed' },
      },
    ],
  })
  chart?.resize()
  chartLoading.value = false
}

watch(filteredRecords, () => { if (filteredRecords.value.length) nextTick(renderChart) })

// ── 数据加载 ──
async function fetchData() {
  loading.value = true; error.value = null
  try {
    const res = await getNorthboundMinute(reviewDate.value || undefined) as any
    let arr: any[] = []
    if (Array.isArray(res)) arr = res
    else if (res?.data && Array.isArray(res.data)) arr = res.data
    records.value = arr
  } catch (e: any) {
    console.warn('[Northbound] fetch failed:', e)
    error.value = e?.message || '数据加载失败'
    records.value = []
  } finally { loading.value = false }
}

function handleResize() { chart?.resize() }
onMounted(() => {
  fetchData()
  window.addEventListener('resize', handleResize)
})
useAutoRefresh(() => { if (!reviewDate.value) fetchData() }, 60_000)
onUnmounted(() => {
  chart?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped lang="scss">
.nb-page { padding: 16px 24px; max-width: 1200px; margin: 0 auto; }

.nb-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.nb-top h1 { font-size: 20px; font-weight: 600; color: #222; margin: 0; }
.nb-toolbar { display: flex; align-items: center; gap: 10px; }
.nb-date-label { font-size: 12px; color: #888; }

.nb-empty { text-align: center; padding: 60px 0; color: #999; p { margin-bottom: 10px; } }

// ① 三大指标卡片
.nb-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 10px; }
@media (max-width: 700px) { .nb-metrics { grid-template-columns: 1fr; } }
.nb-metric {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 20px 16px; background: #fff; border: 1px solid #e8e8e8; border-radius: 6px;
}
.nb-m-lb { font-size: 12px; color: #888; }
.nb-m-val { font-size: 28px; font-weight: 700; &.total { font-size: 32px; } }
.nb-m-unit { font-size: 14px; font-weight: 400; opacity: 0.5; margin-left: 2px; }
.nb-m-desc { font-size: 11px; color: #999; }

// ② 图表区
.nb-chart-card { margin-bottom: 10px; }
.nb-chart-body { height: 360px; }
.nb-ct-left { display: flex; align-items: center; gap: 10px; }
.nb-range-switch { display: flex; gap: 0; border: 1px solid #e0e0e0; border-radius: 4px; overflow: hidden; }
.nb-range-btn {
  padding: 3px 12px; font-size: 11px; cursor: pointer; color: #666;
  border-right: 1px solid #e0e0e0; transition: all 0.15s;
  &:last-child { border-right: none; }
  &:hover { background: #f5f6fa; }
  &.active { background: #409eff; color: #fff; }
}

// ③ 统计小卡片
.nb-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 10px; }
@media (max-width: 700px) { .nb-stats { grid-template-columns: repeat(2, 1fr); } }
.nb-stat {
  display: flex; flex-direction: column; align-items: center; gap: 3px;
  padding: 12px 8px; background: #fff; border: 1px solid #e8e8e8; border-radius: 6px;
}
.nb-stat-lb { font-size: 10px; color: #aaa; }
.nb-stat-v { font-size: 15px; font-weight: 600; }
.nb-stat-t { font-size: 10px; color: #bbb; }

// 通用卡片
.nb-card { background: #fff; border: 1px solid #e8e8e8; border-radius: 6px; overflow: hidden; }
.nb-card-title {
  display: flex; justify-content: space-between; align-items: center;
  padding: 11px 16px; font-size: 14px; font-weight: 600; color: #333;
  border-bottom: 1px solid #f0f0f0;
}
.nb-card-sub { font-size: 11px; color: #aaa; font-weight: 400; }

// 方向标签
.nb-badge {
  display: inline-block; padding: 1px 8px; font-size: 11px; font-weight: 500;
  border-radius: 3px;
  &.r { background: #fef0ef; color: #D93026; }
  &.g { background: #edf8f1; color: #34A853; }
}

// 骨架
.nb-sk { height: 12px; margin: 6px 0; background: #f5f5f5; border-radius: 3px; animation: nb-shimmer 1.5s infinite; }
@keyframes nb-shimmer { 0%,100% { opacity: 0.4; } 50% { opacity: 0.8; } }

.r { color: #D93026; }
.g { color: #34A853; }
</style>
