<template>
  <div class="industry-compare-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">行业对比</h2>
        <span class="page-subtitle">同花顺90行业涨跌排行 · 资金流向</span>
      </div>
      <div class="header-right">
        <el-date-picker v-model="selectedDate" type="date" placeholder="选择日期"
          value-format="YYYY-MM-DD" :disabled-date="d => d > today"
          @change="fetchData" size="small" />
        <el-radio-group v-model="sortBy" size="small" @change="sortData" style="margin-left:12px">
          <el-radio-button value="changePct">涨跌幅</el-radio-button>
          <el-radio-button value="netInflowYi">资金流入</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <div class="chart-container">
      <div ref="chartRef" class="chart"></div>
    </div>

    <el-table v-loading="loading" :data="sortedRecords" stripe style="width:100%" @row-click="goToSector">
      <el-table-column label="#" width="50" type="index" />
      <el-table-column prop="industryName" label="行业" min-width="140" />
      <el-table-column prop="changePct" label="涨跌幅%" width="120" align="right" sortable>
        <template #default="{ row }">
          <span :class="row.changePct >= 0 ? 'text-rise' : 'text-fall'">
            {{ row.changePct >= 0 ? '+' : '' }}{{ row.changePct }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="turnoverYi" label="成交额(亿)" width="120" align="right" />
      <el-table-column prop="netInflowYi" label="净流入(亿)" width="120" align="right" sortable>
        <template #default="{ row }">
          <span :class="row.netInflowYi >= 0 ? 'text-rise' : 'text-fall'">
            {{ row.netInflowYi >= 0 ? '+' : '' }}{{ Number(row.netInflowYi).toFixed(2) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="涨跌家数" width="160" align="center">
        <template #default="{ row }">
          <span class="text-rise">{{ row.upCount }}</span>
          <span style="color:rgba(255,255,255,0.3);margin:0 4px;">/</span>
          <span class="text-fall">{{ row.downCount }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="leader" label="领涨股" min-width="120" show-overflow-tooltip />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getIndustryCompare } from '@/api/signal'
import * as echarts from 'echarts'

const router = useRouter()
const today = new Date()
const loading = ref(false)
const selectedDate = ref(today.toISOString().slice(0, 10))
const records = ref<any[]>([])
const sortBy = ref('changePct')
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const sortedRecords = computed(() => {
  const data = [...records.value]
  if (sortBy.value === 'changePct') return data.sort((a, b) => b.changePct - a.changePct)
  return data.sort((a, b) => b.netInflowYi - a.netInflowYi)
})

function renderChart(data: any[]) {
  if (!chartRef.value || !data.length) return
  if (!chart) chart = echarts.init(chartRef.value)
  const top10 = data.slice(0, 10).reverse()
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 100, right: 60, top: 10, bottom: 20 },
    xAxis: { type: 'value', axisLabel: { color: 'rgba(255,255,255,0.4)', formatter: (v: number) => v + '%' } },
    yAxis: { type: 'category', data: top10.map(d => d.industryName), axisLabel: { color: 'rgba(255,255,255,0.6)' } },
    series: [{
      type: 'bar', data: top10.map(d => ({
        value: d.changePct,
        itemStyle: { color: d.changePct >= 0 ? '#ec4d4c' : '#2997ff' }
      })),
      barWidth: 16,
    }],
  })
}

function sortData() { renderChart(sortedRecords.value) }

async function fetchData() {
  loading.value = true
  try {
    const res = await getIndustryCompare(selectedDate.value)
    records.value = res.data.records || []
    await nextTick()
    renderChart(sortedRecords.value)
  } catch { records.value = [] }
  finally { loading.value = false }
}

function goToSector(row: any) {
  router.push(`/sector/${row.industryName}`)
}

function handleResize() { chart?.resize() }

watch(sortedRecords, () => renderChart(sortedRecords.value))

onMounted(() => { fetchData(); window.addEventListener('resize', handleResize) })
onUnmounted(() => { chart?.dispose(); window.removeEventListener('resize', handleResize) })
</script>

<style scoped lang="scss">
.industry-compare-page { padding: 24px; max-width: 1200px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 700; color: #fff; margin: 0; }
.page-subtitle { display: block; font-size: 13px; color: rgba(255,255,255,0.4); margin-top: 4px; }
.chart-container { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 16px; margin-bottom: 20px; }
.chart { height: 300px; }
</style>
