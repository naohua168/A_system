<template>
  <div class="northbound-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">北向资金</h2>
        <span class="page-subtitle">沪深港通实时资金流向 · 同花顺数据源</span>
      </div>
      <div class="header-right">
        <el-date-picker v-model="startDate" type="date" placeholder="开始日期"
          value-format="YYYY-MM-DD" size="small" @change="fetchData" />
        <span class="date-sep">~</span>
        <el-date-picker v-model="endDate" type="date" placeholder="结束日期"
          value-format="YYYY-MM-DD" size="small" @change="fetchData" />
      </div>
    </div>

    <div class="summary-cards">
      <div class="card">
        <div class="card-label">沪股通净流入</div>
        <div class="card-value" :class="latestHgt >= 0 ? 'text-rise' : 'text-fall'">
          {{ latestHgt >= 0 ? '+' : '' }}{{ latestHgt }}<span class="unit">亿</span>
        </div>
      </div>
      <div class="card">
        <div class="card-label">深股通净流入</div>
        <div class="card-value" :class="latestSgt >= 0 ? 'text-rise' : 'text-fall'">
          {{ latestSgt >= 0 ? '+' : '' }}{{ latestSgt }}<span class="unit">亿</span>
        </div>
      </div>
      <div class="card">
        <div class="card-label">合计净流入</div>
        <div class="card-value" :class="(latestHgt + latestSgt) >= 0 ? 'text-rise' : 'text-fall'">
          {{ (latestHgt + latestSgt) >= 0 ? '+' : '' }}{{ (latestHgt + latestSgt).toFixed(2) }}<span class="unit">亿</span>
        </div>
      </div>
    </div>

    <div class="chart-container">
      <div ref="chartRef" class="chart"></div>
    </div>

    <el-table v-loading="loading" :data="records" stripe style="width:100%">
      <el-table-column prop="tradeDate" label="日期" width="120" />
      <el-table-column prop="hgtYi" label="沪股通(亿)" width="150" align="right">
        <template #default="{ row }">
          <span :class="row.hgtYi >= 0 ? 'text-rise' : 'text-fall'">{{ row.hgtYi >= 0 ? '+' : '' }}{{ row.hgtYi }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="sgtYi" label="深股通(亿)" width="150" align="right">
        <template #default="{ row }">
          <span :class="row.sgtYi >= 0 ? 'text-rise' : 'text-fall'">{{ row.sgtYi >= 0 ? '+' : '' }}{{ row.sgtYi }}</span>
        </template>
      </el-table-column>
      <el-table-column label="合计(亿)" width="150" align="right">
        <template #default="{ row }">
          <span :class="(row.hgtYi + row.sgtYi) >= 0 ? 'text-rise' : 'text-fall'">
            {{ (row.hgtYi + row.sgtYi) >= 0 ? '+' : '' }}{{ (row.hgtYi + row.sgtYi).toFixed(2) }}
          </span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { getNorthboundLatest } from '@/api/signal'
import * as echarts from 'echarts'

const loading = ref(false)
const records = ref<any[]>([])
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
const today = new Date()
const startDate = ref(new Date(today.getFullYear(), today.getMonth() - 1, today.getDate()).toISOString().slice(0, 10))
const endDate = ref(today.toISOString().slice(0, 10))
const latestHgt = ref(0)
const latestSgt = ref(0)

function renderChart(data: any[]) {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const dates = data.map(d => d.tradeDate).reverse()
  const hgt = data.map(d => d.hgtYi).reverse()
  const sgt = data.map(d => d.sgtYi).reverse()
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['沪股通', '深股通'], textStyle: { color: 'rgba(255,255,255,0.6)' } },
    grid: { left: 60, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { color: 'rgba(255,255,255,0.4)', fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { color: 'rgba(255,255,255,0.4)' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    series: [
      { name: '沪股通', type: 'bar', data: hgt, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#2997ff' }, { offset: 1, color: '#1a6bb5' }]) } },
      { name: '深股通', type: 'bar', data: sgt, itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#52c41a' }, { offset: 1, color: '#389e0d' }]) } },
    ],
  })
}

async function fetchData() {
  loading.value = true
  try {
    const res = await getNorthboundLatest(60)
    records.value = (res as any).data || res || []
    if (records.value.length > 0) {
      latestHgt.value = records.value[0].hgtYi
      latestSgt.value = records.value[0].sgtYi
    }
    await nextTick()
    renderChart(records.value)
  } catch { records.value = [] }
  finally { loading.value = false }
}

function handleResize() { chart?.resize() }

onMounted(() => { fetchData(); window.addEventListener('resize', handleResize) })
onUnmounted(() => { chart?.dispose(); window.removeEventListener('resize', handleResize) })
</script>

<style scoped lang="scss">
.northbound-page { padding: 24px; max-width: 1200px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 700; color: #fff; margin: 0; }
.page-subtitle { display: block; font-size: 13px; color: rgba(255,255,255,0.4); margin-top: 4px; }
.date-sep { color: rgba(255,255,255,0.3); margin: 0 4px; }
.summary-cards { display: flex; gap: 16px; margin-bottom: 20px; }
.card { flex: 1; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 20px; }
.card-label { font-size: 13px; color: rgba(255,255,255,0.5); margin-bottom: 8px; }
.card-value { font-size: 28px; font-weight: 700; line-height: 1; }
.unit { font-size: 14px; font-weight: 400; color: rgba(255,255,255,0.3); margin-left: 2px; }
.chart-container { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 16px; margin-bottom: 20px; }
.chart { height: 320px; }
</style>
