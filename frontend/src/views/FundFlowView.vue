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
import { getFundFlow } from '@/api/signal'
import type { FundFlow } from '@/types'

/** 资金流向展示行（含前端计算的累计字段） */
interface FundFlowDisplay {
  date: string
  close: number
  changePct: number
  mainIn: number
  superNetIn: number
  largeNetIn: number
  mediumNetIn: number
  littleNetIn: number
}

const loading = ref(false)
const stockCode = ref('000858')
const records = ref<FundFlowDisplay[]>([])
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

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

/** 从后端 API 加载资金流向数据 */
async function fetchData() {
  const code = stockCode.value.trim()
  if (!code) return
  loading.value = true
  try {
    const raw = await getFundFlow(code, 20) as FundFlow[]
    records.value = raw.map((item) => ({
      date: item.tradeDate,
      close: item.close,
      changePct: 0, // 后端 FundFlow 表不含涨跌幅，后续可从 K 线关联
      mainIn: Number(item.mainIn) || 0,
      superNetIn: Number(item.superNetIn) || 0,
      largeNetIn: 0,
      mediumNetIn: 0,
      littleNetIn: 0,
    }))
    await nextTick()
    renderChart(records.value)
  } catch (e) {
    console.warn('[FundFlow] fetchData failed:', e)
    records.value = []
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
