<template>
  <div class="fund-flow-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">资金流向</h2>
        <span class="page-subtitle">个股主力资金净流入跟踪 · 百度数据源</span>
      </div>
      <div class="header-right">
        <el-input v-model="stockCode" placeholder="输入股票代码" size="small" style="width:140px;margin-right:8px" />
        <el-button type="primary" size="small" @click="fetchData" :loading="loading">查询</el-button>
      </div>
    </div>

    <div v-if="!records.length && !loading" class="empty-state">
      <el-icon class="empty-icon" :size="48"><TrendCharts /></el-icon>
      <div class="empty-text">输入股票代码查询资金流向</div>
      <div class="empty-hint">例如: 000858（五粮液）、600519（贵州茅台）</div>
    </div>

    <template v-if="records.length">
      <div class="summary-cards">
        <div class="card" v-for="stat in stats" :key="stat.label">
          <div class="card-label">{{ stat.label }}</div>
          <div class="card-value" :class="stat.value >= 0 ? 'text-rise' : 'text-fall'">
            {{ stat.value >= 0 ? '+' : '' }}{{ Number(stat.value).toFixed(2) }}<span class="unit">万</span>
          </div>
        </div>
      </div>

      <div class="chart-container">
        <div ref="chartRef" class="chart"></div>
      </div>

      <el-table v-loading="loading" :data="records" stripe style="width:100%">
        <el-table-column prop="date" label="日期" width="110" />
        <el-table-column prop="close" label="收盘价" width="100" align="right" />
        <el-table-column prop="changePct" label="涨跌幅%" width="100" align="right">
          <template #default="{ row }">
            <span :class="row.changePct >= 0 ? 'text-rise' : 'text-fall'">
              {{ row.changePct >= 0 ? '+' : '' }}{{ row.changePct }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="主力净流入" width="130" align="right" sortable prop="mainIn">
          <template #default="{ row }">
            <span :class="row.mainIn >= 0 ? 'text-rise' : 'text-fall'">{{ row.mainIn }}万</span>
          </template>
        </el-table-column>
        <el-table-column label="超大单" width="120" align="right" prop="superNetIn">
          <template #default="{ row }">{{ row.superNetIn }}万</template>
        </el-table-column>
        <el-table-column label="大单" width="120" align="right" prop="largeNetIn">
          <template #default="{ row }">{{ row.largeNetIn }}万</template>
        </el-table-column>
      </el-table>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import * as echarts from 'echarts'
import { TrendCharts } from '@element-plus/icons-vue'

const loading = ref(false)
const stockCode = ref('000858')
const records = ref<any[]>([])
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

// 模拟数据 — 真实场景下调用后端API
const mockData: Record<string, any[]> = {
  '000858': [
    { date: '2026-04-29', close: 160.42, changePct: 1.89, superNetIn: 3562, largeNetIn: 1289, mediumNetIn: -892, littleNetIn: -2156, mainIn: 4851 },
    { date: '2026-04-30', close: 153.84, changePct: -4.10, superNetIn: -4521, largeNetIn: -1896, mediumNetIn: 1235, littleNetIn: 2135, mainIn: -6417 },
    { date: '2026-05-06', close: 160.66, changePct: 4.43, superNetIn: 5621, largeNetIn: 2345, mediumNetIn: -1120, littleNetIn: -2560, mainIn: 7966 },
    { date: '2026-05-07', close: 157.09, changePct: -2.22, superNetIn: -3356, largeNetIn: -1120, mediumNetIn: 890, littleNetIn: 1560, mainIn: -4476 },
    { date: '2026-05-08', close: 157.17, changePct: 0.05, superNetIn: 1256, largeNetIn: 890, mediumNetIn: -456, littleNetIn: -780, mainIn: 2146 },
  ],
  '600519': [
    { date: '2026-04-29', close: 1713.67, changePct: 1.35, superNetIn: 8956, largeNetIn: 3456, mediumNetIn: -2135, littleNetIn: -4210, mainIn: 12412 },
    { date: '2026-04-30', close: 1693.97, changePct: -1.15, superNetIn: -5621, largeNetIn: -2230, mediumNetIn: 1560, littleNetIn: 2456, mainIn: -7851 },
    { date: '2026-05-06', close: 1671.29, changePct: -1.34, superNetIn: -3345, largeNetIn: -1125, mediumNetIn: 892, littleNetIn: 1580, mainIn: -4470 },
    { date: '2026-05-07', close: 1699.50, changePct: 1.69, superNetIn: 6789, largeNetIn: 2560, mediumNetIn: -1120, littleNetIn: -2560, mainIn: 9349 },
    { date: '2026-05-08', close: 1695.27, changePct: -0.25, superNetIn: -1230, largeNetIn: -560, mediumNetIn: 320, littleNetIn: 890, mainIn: -1790 },
  ],
}

const stats = computed(() => {
  if (!records.value.length) return []
  return [
    { label: '期间主力净流入', value: records.value.reduce((s, r) => s + (r.mainIn || 0), 0) },
    { label: '期间超大单净流入', value: records.value.reduce((s, r) => s + (r.superNetIn || 0), 0) },
    { label: '期间大单净流入', value: records.value.reduce((s, r) => s + (r.largeNetIn || 0), 0) },
    { label: '期间散户净流入', value: records.value.reduce((s, r) => s + (r.littleNetIn || 0), 0) },
  ]
})

function renderChart(data: any[]) {
  if (!chartRef.value || !data.length) return
  if (!chart) chart = echarts.init(chartRef.value)
  const dates = data.map(d => d.date).reverse()
  const mainIn = data.map(d => (d.mainIn || 0)).reverse()
  const superIn = data.map(d => (d.superNetIn || 0)).reverse()
  const littleIn = data.map(d => (d.littleNetIn || 0)).reverse()
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['主力净流入', '超大单', '散户'], textStyle: { color: 'rgba(255,255,255,0.6)' } },
    grid: { left: 60, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { color: 'rgba(255,255,255,0.4)' } },
    yAxis: { type: 'value', axisLabel: { color: 'rgba(255,255,255,0.4)', formatter: (v: number) => v + '万' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    series: [
      { name: '主力净流入', type: 'bar', data: mainIn, itemStyle: { color: '#e74c3c' } },
      { name: '超大单', type: 'line', data: superIn, smooth: true, lineStyle: { color: '#2997ff' }, itemStyle: { color: '#2997ff' } },
      { name: '散户', type: 'line', data: littleIn, smooth: true, lineStyle: { color: '#7a7a7a' }, itemStyle: { color: '#7a7a7a' } },
    ],
  })
}

async function fetchData() {
  const code = stockCode.value.trim()
  if (!code) return
  loading.value = true
  try {
    // 真实场景调用后端API
    // const res = await getFundFlowHistory(code, 20)
    // records.value = res.data || []
    records.value = mockData[code] || mockData['000858']
    await nextTick()
    renderChart(records.value)
  } finally { loading.value = false }
}

function handleResize() { chart?.resize() }

onMounted(() => { fetchData(); window.addEventListener('resize', handleResize) })
onUnmounted(() => { chart?.dispose(); window.removeEventListener('resize', handleResize) })
</script>

<style scoped lang="scss">
.fund-flow-page { padding: $spacing-lg; max-width: 1200px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: $spacing-md; }
.page-title { font-family: $font-display; font-size: 24px; font-weight: 600; color: #fff; margin: 0; letter-spacing: -0.374px; }
.page-subtitle { display: block; font-size: 13px; color: rgba(255,255,255,0.4); margin-top: 4px; }
.empty-state { text-align: center; padding: $spacing-section 0;
  .empty-icon { margin-bottom: $spacing-sm; }
  .empty-text { font-size: 16px; color: rgba(255,255,255,0.5); }
  .empty-hint { font-size: 13px; color: rgba(255,255,255,0.3); margin-top: 4px; } }
.summary-cards { display: flex; gap: $spacing-md; margin-bottom: $spacing-md; flex-wrap: wrap; }
.card { flex: 1; min-width: 150px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: $rounded-lg; padding: $spacing-md; }
.card-label { font-size: 12px; color: rgba(255,255,255,0.5); margin-bottom: 6px; }
.card-value { font-size: 22px; font-weight: 700; }
.unit { font-size: 12px; font-weight: 400; opacity: 0.4; margin-left: 2px; }
.chart-container { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: $rounded-lg; padding: $spacing-md; margin-bottom: $spacing-md; }
.chart { height: 300px; }
</style>
