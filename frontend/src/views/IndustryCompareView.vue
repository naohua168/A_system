<template>
  <div class="industry-compare-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">行业对比</h2>
        <span class="page-subtitle">同花顺90行业涨跌排行 · 资金流向</span>
      </div>
      <div class="header-right">
        <el-date-picker v-model="selectedDate" type="date" placeholder="选择日期"
          value-format="YYYY-MM-DD" :disabled-date="(d: Date) => d > today"
          @change="onDateChange" size="small" />
        <el-radio-group v-model="sortBy" size="small" @change="sortData" style="margin-left:12px">
          <el-radio-button value="changePct">涨跌幅</el-radio-button>
          <el-radio-button value="netInflowYi">资金流入</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- 加载骨架 -->
    <template v-if="loading">
      <div class="chart-container"><SkeletonLoader type="chart" /></div>
      <SkeletonLoader type="table" :rows="5" :col-widths="['15%', '12%', '12%', '14%', '12%']" />
    </template>

    <!-- 错误状态 -->
    <template v-else-if="error">
      <div class="chart-container"></div>
      <EmptyState type="error" :title="error" description="请检查网络连接后重试" size="lg">
        <template #actions>
          <el-button type="primary" size="small" @click="fetchData">重新加载</el-button>
        </template>
      </EmptyState>
    </template>

    <!-- 空数据 -->
    <template v-else-if="!sortedRecords.length">
      <EmptyState type="empty" title="暂无行业对比数据" :sub="selectedDate" size="lg">
        <template #actions>
          <el-button size="small" @click="selectedDate = yesterday; onDateChange()">查看最近交易日</el-button>
        </template>
      </EmptyState>
    </template>

    <!-- 正常数据 -->
    <template v-else>
      <div class="chart-container">
        <div ref="chartRef" class="chart"></div>
      </div>
      <el-table :data="sortedRecords" stripe style="width:100%" @row-click="goToSector">
        <el-table-column label="#" width="50" type="index" />
        <el-table-column prop="industryName" label="行业" min-width="140" />
        <el-table-column prop="changePct" label="涨跌幅%" width="120" align="right" sortable>
          <template #default="{ row }">
            <span :class="(row.changePct || 0) >= 0 ? 'text-rise' : 'text-fall'">
              {{ (row.changePct || 0) >= 0 ? '+' : '' }}{{ safeNum(row.changePct, 2) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="turnoverYi" label="成交额(亿)" width="120" align="right" />
        <el-table-column prop="netInflowYi" label="净流入(亿)" width="120" align="right" sortable>
          <template #default="{ row }">
            <span :class="(row.netInflowYi || 0) >= 0 ? 'text-rise' : 'text-fall'">
              {{ (row.netInflowYi || 0) >= 0 ? '+' : '' }}{{ safeNum(row.netInflowYi, 2) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="涨跌家数" width="160" align="center">
          <template #default="{ row }">
            <span class="text-rise">{{ row.upCount || 0 }}</span>
            <span style="color:rgba(255,255,255,0.3);margin:0 4px;">/</span>
            <span class="text-fall">{{ row.downCount || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="leader" label="领涨股" min-width="120" show-overflow-tooltip />
      </el-table>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getIndustryCompare } from '@/api/signal'
import * as echarts from 'echarts'
import { useApiRetry, safeRecords, safeNum } from '@/composables/useApiRetry'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const router = useRouter()
const today = new Date()
const yesterday = new Date(today.getTime() - 86400000).toISOString().slice(0, 10)
const selectedDate = ref(yesterday)
const sortBy = ref('changePct')
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const { data: rawData, loading, error, fetch: fetchData } = useApiRetry(
  () => getIndustryCompare(selectedDate.value),
  { maxRetries: 1, showError: false, errorMessage: '行业对比数据加载失败' }
)

const records = computed(() => safeRecords(rawData.value, 'records'))
const sortedRecords = computed(() => {
  const data = [...records.value]
  if (!data.length) return []
  try {
    if (sortBy.value === 'changePct') return data.sort((a, b) => (b.changePct || 0) - (a.changePct || 0))
    return data.sort((a, b) => (b.netInflowYi || 0) - (a.netInflowYi || 0))
  } catch { return data }
})

function renderChart(data: any[]) {
  if (!chartRef.value || !data.length) return
  if (!chart) chart = echarts.init(chartRef.value)
  const top10 = data.slice(0, 10).reverse()
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 100, right: 60, top: 10, bottom: 20 },
    xAxis: { type: 'value', axisLabel: { color: 'rgba(255,255,255,0.4)', formatter: (v: number) => v + '%' } },
    yAxis: { type: 'category', data: top10.map((d: any) => d.industryName || ''), axisLabel: { color: 'rgba(255,255,255,0.6)' } },
    series: [{
      type: 'bar', data: top10.map((d: any) => ({
        value: d.changePct || 0,
        itemStyle: { color: (d.changePct || 0) >= 0 ? '#ec4d4c' : '#2997ff' }
      })),
      barWidth: 16,
    }],
  })
}

function sortData() { renderChart(sortedRecords.value) }
function onDateChange() { fetchData() }

function goToSector(row: any) {
  if (row.industryName) router.push(`/sector/${encodeURIComponent(row.industryName)}`)
}

function handleResize() { chart?.resize() }

watch(sortedRecords, (val) => { nextTick(() => renderChart(val)) })
watch(error, () => { chart?.clear() })

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
