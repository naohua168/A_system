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
        <el-button v-if="error" type="warning" size="small" @click="fetchData" :loading="loading">
          重试
        </el-button>
      </div>
    </div>

    <!-- 加载骨架 -->
    <template v-if="loading">
      <div class="summary-cards">
        <div v-for="i in 3" :key="i" class="card skeleton-card">
          <div class="skeleton-line skeleton-line--short" />
          <div class="skeleton-line skeleton-line--long" style="height:28px;margin-top:8px" />
        </div>
      </div>
      <div class="chart-container"><SkeletonLoader type="chart" /></div>
      <SkeletonLoader type="table" :rows="5" />
    </template>

    <!-- 错误状态 -->
    <template v-else-if="error">
      <EmptyState type="error" :title="error" description="检查网络连接后重试" size="lg">
        <template #actions>
          <el-button type="primary" size="small" @click="fetchData">重新加载</el-button>
        </template>
      </EmptyState>
    </template>

    <!-- 空数据 -->
    <template v-else-if="!records.length">
      <EmptyState type="empty" title="暂无北向资金数据" size="lg" />
    </template>

    <!-- 正常数据 -->
    <template v-else>
      <div class="summary-cards">
        <div class="card">
          <div class="card-label">沪股通净流入</div>
          <div class="card-value" :class="latestHgt >= 0 ? 'text-rise' : 'text-fall'">
            {{ latestHgt >= 0 ? '+' : '' }}{{ safeNum(latestHgt, 2) }}<span class="unit">亿</span>
          </div>
        </div>
        <div class="card">
          <div class="card-label">深股通净流入</div>
          <div class="card-value" :class="latestSgt >= 0 ? 'text-rise' : 'text-fall'">
            {{ latestSgt >= 0 ? '+' : '' }}{{ safeNum(latestSgt, 2) }}<span class="unit">亿</span>
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

      <el-table :data="records" stripe style="width:100%">
        <el-table-column prop="tradeDate" label="日期" width="120" />
        <el-table-column prop="hgtYi" label="沪股通(亿)" width="150" align="right">
          <template #default="{ row }">
            <span :class="(row.hgtYi || 0) >= 0 ? 'text-rise' : 'text-fall'">
              {{ (row.hgtYi || 0) >= 0 ? '+' : '' }}{{ safeNum(row.hgtYi, 2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="sgtYi" label="深股通(亿)" width="150" align="right">
          <template #default="{ row }">
            <span :class="(row.sgtYi || 0) >= 0 ? 'text-rise' : 'text-fall'">
              {{ (row.sgtYi || 0) >= 0 ? '+' : '' }}{{ safeNum(row.sgtYi, 2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="合计(亿)" width="150" align="right">
          <template #default="{ row }">
            <span :class="(safeNum(row.hgtYi) + safeNum(row.sgtYi)) >= 0 ? 'text-rise' : 'text-fall'">
              {{ (safeNum(row.hgtYi) + safeNum(row.sgtYi)) >= 0 ? '+' : '' }}{{ (safeNum(row.hgtYi) + safeNum(row.sgtYi)).toFixed(2) }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { getNorthboundLatest } from '@/api/signal'
import * as echarts from 'echarts'
import { useApiRetry, safeNum } from '@/composables/useApiRetry'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const loading = ref(false)
const records = ref<any[]>([])
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
const today = new Date()
const startDate = ref(new Date(today.getFullYear(), today.getMonth() - 1, today.getDate()).toISOString().slice(0, 10))
const endDate = ref(today.toISOString().slice(0, 10))
const latestHgt = ref(0)
const latestSgt = ref(0)
const error = ref<string | null>(null)

function renderChart(data: any[]) {
  if (!chartRef.value || !data.length) return
  if (!chart) chart = echarts.init(chartRef.value)
  const safeData = data.filter(d => d && d.tradeDate)
  if (!safeData.length) return
  const dates = safeData.map(d => d.tradeDate).reverse()
  const hgt = safeData.map(d => d.hgtYi || 0).reverse()
  const sgt = safeData.map(d => d.sgtYi || 0).reverse()
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
  error.value = null
  try {
    const res = await getNorthboundLatest(60)
    records.value = res || []
    if (records.value.length > 0 && records.value[0]) {
      latestHgt.value = safeNum(records.value[0].hgtYi)
      latestSgt.value = safeNum(records.value[0].sgtYi)
    }
    await nextTick()
    renderChart(records.value)
  } catch (e: any) {
    error.value = e?.message || '北向资金数据加载失败'
    records.value = []
  } finally { loading.value = false }
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
