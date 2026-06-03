<template>
  <div class="nb-page">
    <!-- ═══ 顶栏 ═══ -->
    <header class="nb-top">
      <h1>北向资金</h1>
      <div class="nb-toolbar">
        <span class="nb-date-label">{{ todayLabel }}</span>
        <el-button size="small" @click="fetchData" :loading="loading">刷新</el-button>
      </div>
    </header>

    <!-- 骨架 -->
    <template v-if="loading">
      <div class="nb-sk" v-for="i in 4" :key="i"></div>
    </template>

    <!-- 错误/空 -->
    <div v-else-if="error" class="nb-empty"><p>{{ error }}</p><el-button size="small" @click="fetchData">重试</el-button></div>
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
          <span class="nb-m-val total" :class="total >= 0 ? 'r' : 'g'">{{ total >= 0 ? '+' : '' }}{{ total.toFixed(2) }}<span class="nb-m-unit">亿</span></span>
          <span class="nb-m-desc">{{ directionText }}</span>
        </div>
      </section>

      <!-- ═══ ② 关键统计（4个小卡片） ═══ -->
      <section class="nb-stats">
        <div class="nb-stat">
          <span class="nb-stat-lb">今日实时最高</span>
          <span class="nb-stat-v r">{{ maxTotal >= 0 ? '+' : '' }}{{ maxTotal.toFixed(2) }}亿</span>
        </div>
        <div class="nb-stat">
          <span class="nb-stat-lb">今日实时最低</span>
          <span class="nb-stat-v g">{{ minTotal >= 0 ? '+' : '' }}{{ minTotal.toFixed(2) }}亿</span>
        </div>
        <div class="nb-stat">
          <span class="nb-stat-lb">数据频率</span>
          <span class="nb-stat-v">{{ records.length }}笔 / 日</span>
        </div>
        <div class="nb-stat">
          <span class="nb-stat-lb">当前方向</span>
          <span class="nb-stat-v" :class="total >= 0 ? 'r' : 'g'">{{ total >= 0 ? '北向净买入' : '北向净卖出' }}</span>
        </div>
      </section>

      <!-- ═══ ③ 分时趋势图 ═══ -->
      <section class="nb-card nb-chart-card">
        <div class="nb-card-title">
          <span>今日分时趋势</span>
          <span class="nb-card-sub">沪股通 vs 深股通 实时资金流向</span>
        </div>
        <div ref="chartRef" class="nb-chart-body"></div>
      </section>

      <!-- ═══ ④ 逐笔明细表 ═══ -->
      <section class="nb-card">
        <div class="nb-card-title">
          <span>逐笔明细（{{ records.length }}条）</span>
          <span class="nb-card-sub">单位：亿元</span>
        </div>
        <el-table
          :data="tableData"
          stripe
          size="small"
          style="width:100%"
          :header-cell-style="{ background: '#f5f6fa', color: '#666', borderBottom: '1px solid #eee', fontSize: '12px', fontWeight: 500, padding: '9px 0' }"
          :cell-style="{ fontSize: '12px', padding: '7px 0', color: '#333' }"
        >
          <el-table-column prop="tradeDate" label="时间" width="80" />
          <el-table-column label="沪股通(亿)" width="130" align="right" sortable prop="hgtYi">
            <template #default="{ row }">
              <span :class="(row.hgtYi || 0) >= 0 ? 'r' : 'g'">{{ (row.hgtYi || 0) >= 0 ? '+' : '' }}{{ safeNum(row.hgtYi, 2) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="深股通(亿)" width="130" align="right" sortable prop="sgtYi">
            <template #default="{ row }">
              <span :class="(row.sgtYi || 0) >= 0 ? 'r' : 'g'">{{ (row.sgtYi || 0) >= 0 ? '+' : '' }}{{ safeNum(row.sgtYi, 2) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="合计(亿)" width="130" align="right" sortable prop="total">
            <template #default="{ row }">
              <span :class="row.total >= 0 ? 'r' : 'g'">{{ row.total >= 0 ? '+' : '' }}{{ row.total.toFixed(2) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="方向" width="80" align="center">
            <template #default="{ row }">
              <span :class="row.total >= 0 ? 'nb-badge r' : 'nb-badge g'">{{ row.total >= 0 ? '买入' : '卖出' }}</span>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { getNorthboundLatest } from '@/api/signal'
import echarts from '@/utils/echarts'
import { safeNum } from '@/composables/useApiRetry'
import { useAutoRefresh } from '@/composables/useAutoRefresh'

const loading = ref(false)
const records = ref<any[]>([])
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
const error = ref<string | null>(null)

const todayLabel = new Date().toISOString().slice(0, 10)

// 最近一条
const lastRecord = computed(() => records.value[records.value.length - 1] || {} as any)
const hgt = computed(() => safeNum(lastRecord.value.hgtYi))
const sgt = computed(() => safeNum(lastRecord.value.sgtYi))
const total = computed(() => hgt.value + sgt.value)

// 极值
const maxTotal = computed(() => {
  const vals = records.value.map(r => safeNum(r.hgtYi) + safeNum(r.sgtYi))
  return vals.length ? Math.max(...vals) : 0
})
const minTotal = computed(() => {
  const vals = records.value.map(r => safeNum(r.hgtYi) + safeNum(r.sgtYi))
  return vals.length ? Math.min(...vals) : 0
})

// 方向
function direction(v: number): string {
  const abs = Math.abs(v)
  if (abs >= 50) return '大幅'
  if (abs >= 10) return '明显'
  if (abs >= 1) return '小幅'
  return '微量'
}
const directionText = computed(() => {
  if (total.value > 5) return '外资积极流入 A 股'
  if (total.value > 0) return '外资小幅流入 A 股'
  if (total.value > -5) return '外资小幅流出 A 股'
  return '外资加速流出 A 股'
})

// 表格数据（最新在前）
const tableData = computed(() => {
  return [...records.value].reverse().map((r: any) => ({
    tradeDate: r.tradeDate,
    hgtYi: safeNum(r.hgtYi),
    sgtYi: safeNum(r.sgtYi),
    total: safeNum(r.hgtYi) + safeNum(r.sgtYi),
  }))
})

// 图表 — 用 watch 自动响应数据变化，不再手动调用
function renderChart() {
  const el = chartRef.value
  if (!el || !records.value.length) return
  // 销毁旧实例重建，确保 DOM 完全就绪
  chart?.dispose()
  try {
    chart = echarts.init(el)
  } catch {
    setTimeout(renderChart, 120)
    return
  }
  const data = records.value
  const times = data.map((d: any) => d.tradeDate)
  const h = data.map((d: any) => safeNum(d.hgtYi))
  const s = data.map((d: any) => safeNum(d.sgtYi))

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#fff',
      borderColor: '#e8e8e8',
      textStyle: { color: '#333', fontSize: 12 },
      formatter: (params: any[]) => {
        let s = `<b>${params[0].axisValue}</b>`
        params.forEach((p: any) => {
          const v = Number(p.value) || 0
          s += `<div style="display:flex;justify-content:space-between;gap:20px;font-size:12px">
            <span>${p.marker} ${p.seriesName}</span>
            <span style="font-weight:600;${v >= 0 ? 'color:#D93026' : 'color:#34A853'}">${v >= 0 ? '+' : ''}${v.toFixed(2)}亿</span>
          </div>`
        })
        return s
      },
    },
    legend: { data: ['沪股通', '深股通'], textStyle: { color: '#666', fontSize: 11 }, top: 4, itemWidth: 14, itemHeight: 8 },
    grid: { left: 50, right: 16, top: 32, bottom: 18 },
    xAxis: { type: 'category', data: times, axisLine: { lineStyle: { color: '#e8e8e8' } }, axisLabel: { color: '#999', fontSize: 11 }, axisTick: { show: false } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } }, axisLabel: { color: '#999', fontSize: 11, formatter: (v: number) => v.toFixed(0) + '亿' } },
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
    ],
  })
  chart?.resize()
}

// 当 records 变化时自动渲染图表
watch(records, (val) => {
  if (val.length) nextTick(renderChart)
})

// 数据加载
async function fetchData() {
  loading.value = true; error.value = null
  try {
    const res = await getNorthboundLatest(60) as any
    // 兼容多种响应格式：裸数组 / {data:[]} / {records:[]}
    let arr: any[] = []
    if (Array.isArray(res)) {
      arr = res
    } else if (res?.data && Array.isArray(res.data)) {
      arr = res.data
    } else if (res?.records && Array.isArray(res.records)) {
      arr = res.records
    }
    records.value = arr
    // watch 会自动触发图表渲染
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
useAutoRefresh(fetchData, 60_000)
onUnmounted(() => {
  chart?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped lang="scss">
.nb-page { padding: 16px 24px; max-width: 1200px; margin: 0 auto; }

// 顶栏
.nb-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.nb-top h1 { font-size: 20px; font-weight: 600; color: #222; margin: 0; }
.nb-toolbar { display: flex; align-items: center; gap: 10px; }
.nb-date-label { font-size: 12px; color: #888; }

// 空态
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

// ② 统计小卡片
.nb-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 10px; }
@media (max-width: 700px) { .nb-stats { grid-template-columns: repeat(2, 1fr); } }
.nb-stat {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding: 12px 8px; background: #fff; border: 1px solid #e8e8e8; border-radius: 6px;
}
.nb-stat-lb { font-size: 10px; color: #aaa; }
.nb-stat-v { font-size: 15px; font-weight: 600; }

// 通用卡片
.nb-card { background: #fff; border: 1px solid #e8e8e8; border-radius: 6px; overflow: hidden; }
.nb-card-title {
  display: flex; justify-content: space-between; align-items: center;
  padding: 11px 16px; font-size: 14px; font-weight: 600; color: #333;
  border-bottom: 1px solid #f0f0f0;
}
.nb-card-sub { font-size: 11px; color: #aaa; font-weight: 400; }

// ③ 图表
.nb-chart-card { margin-bottom: 10px; }
.nb-chart-body { height: 300px; }

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

// 全局
.r { color: #D93026; }
.g { color: #34A853; }
</style>
