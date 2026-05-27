<template>
  <div class="consensus-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">机构一致预期</h2>
        <span class="page-subtitle">券商机构盈利预测汇总 · 东方财富数据源</span>
      </div>
      <div class="header-right">
        <el-input v-model="searchCode" placeholder="输入股票代码" size="small" style="width:140px;margin-right:8px" />
        <el-button type="primary" size="small" @click="fetchData" :loading="loading">查询</el-button>
      </div>
    </div>

    <div v-if="!records.length && !loading" class="empty-state">
      <el-icon class="empty-icon" :size="48"><DataLine /></el-icon>
      <div class="empty-text">输入股票代码查询机构一致预期</div>
      <div class="empty-hint">例如: 688017（绿的谐波）、600519（贵州茅台）</div>
      <div class="sample-tags">
        <el-tag v-for="s in samples" :key="s" size="small" class="sample-tag" @click="searchCode = s; fetchData()">{{ s }}</el-tag>
      </div>
    </div>

    <template v-if="records.length">
      <div class="summary-cards">
        <div class="card">
          <div class="card-label">覆盖机构</div>
          <div class="card-value" style="color:#2997ff">{{ records.length }}<small style="font-size:14px;opacity:0.4">家</small></div>
        </div>
        <div class="card">
          <div class="card-label">本年度预期均值</div>
          <div class="card-value" style="color:#52c41a">{{ avgEps }}<small style="font-size:14px;opacity:0.4">元</small></div>
        </div>
      </div>

      <div class="chart-container">
        <div ref="chartRef" class="chart"></div>
      </div>

      <el-table :data="records" stripe style="width:100%">
        <el-table-column prop="year" label="年度" width="100" />
        <el-table-column label="预测机构数" width="120" align="right">
          <template #default="{ row }">{{ row.forecastCount }}家</template>
        </el-table-column>
        <el-table-column label="最小值" width="120" align="right">
          <template #default="{ row }">{{ row.min }}元</template>
        </el-table-column>
        <el-table-column label="均值" width="120" align="right">
          <template #default="{ row }"><strong>{{ row.avg }}</strong>元</template>
        </el-table-column>
        <el-table-column label="最大值" width="120" align="right">
          <template #default="{ row }">{{ row.max }}元</template>
        </el-table-column>
        <el-table-column label="行业平均" width="120" align="right">
          <template #default="{ row }">{{ row.industryAvg }}元</template>
        </el-table-column>
      </el-table>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import echarts from '@/utils/echarts'
import { DataLine } from '@element-plus/icons-vue'
import { getConsensusEps } from '@/api/info'
import type { ConsensusEps } from '@/types'

/** 一致预期展示行（含前端补全字段） */
interface EpsDisplayRow {
  year: string
  forecastCount: number
  min: number
  avg: number
  max: number
  industryAvg: string
}

const loading = ref(false)
const searchCode = ref('688017')
const samples = ['688017', '600519', '300750', '000858']
const records = ref<EpsDisplayRow[]>([])
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const avgEps = computed(() => {
  if (!records.value.length) return '0.00'
  return records.value[0].avg.toFixed(2)
})

function renderChart(data: EpsDisplayRow[]) {
  if (!chartRef.value || !data.length) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['均值', '最小值', '最大值'], textStyle: { color: 'rgba(255,255,255,0.6)' } },
    grid: { left: 60, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: data.map(d => d.year), axisLabel: { color: 'rgba(255,255,255,0.4)' } },
    yAxis: { type: 'value', name: 'EPS(元)', nameTextStyle: { color: 'rgba(255,255,255,0.3)' }, axisLabel: { color: 'rgba(255,255,255,0.4)' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } } },
    series: [
      { name: '均值', type: 'bar', data: data.map(d => d.avg), itemStyle: { color: '#0066cc' } },
      { name: '最小值', type: 'line', data: data.map(d => d.min), lineStyle: { color: '#ff8c00', type: 'dashed' }, itemStyle: { color: '#ff8c00' }, symbol: 'diamond' },
      { name: '最大值', type: 'line', data: data.map(d => d.max), lineStyle: { color: '#52c41a', type: 'dashed' }, itemStyle: { color: '#52c41a' }, symbol: 'diamond' },
    ],
  })
}

/** 从后端 API 加载一致预期数据 */
async function fetchData() {
  const code = searchCode.value.trim()
  if (!code) return
  loading.value = true
  try {
    const raw = await getConsensusEps(code) as ConsensusEps[]
    records.value = raw.map((item) => ({
      year: item.year,
      forecastCount: item.forecastCount,
      min: item.minEps,
      avg: item.avgEps,
      max: item.maxEps,
      industryAvg: '-', // 后端暂不返回行业平均
    }))
    await nextTick()
    renderChart(records.value)
  } catch (e) {
    console.warn('[ConsensusEps] fetchData failed:', e)
    records.value = []
  } finally { loading.value = false }
}

function handleResize() { chart?.resize() }

onMounted(() => { fetchData(); window.addEventListener('resize', handleResize) })
onUnmounted(() => { chart?.dispose(); window.removeEventListener('resize', handleResize) })
</script>

<style scoped lang="scss">
.consensus-page { padding: $spacing-lg; max-width: 1200px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: $spacing-md; }
.page-title { font-family: $font-display; font-size: 24px; font-weight: 600; color: #fff; margin: 0; letter-spacing: -0.374px; }
.page-subtitle { display: block; font-size: 13px; color: rgba(255,255,255,0.4); margin-top: 4px; }
.empty-state { text-align: center; padding: $spacing-section 0;
  .empty-icon { margin-bottom: $spacing-sm; }
  .empty-text { font-size: 16px; color: rgba(255,255,255,0.5); }
  .empty-hint { font-size: 13px; color: rgba(255,255,255,0.3); margin-top: 4px; }
  .sample-tags { margin-top: $spacing-md; display: flex; justify-content: center; gap: $spacing-xs;
    .sample-tag { cursor: pointer; &:hover { background: rgba($primary-on-dark,0.2); } } } }
.summary-cards { display: flex; gap: $spacing-md; margin-bottom: $spacing-md; }
.card { flex: 1; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: $rounded-lg; padding: $spacing-md; }
.card-label { font-size: 13px; color: rgba(255,255,255,0.5); margin-bottom: $spacing-xs; }
.card-value { font-size: 28px; font-weight: 700; }
.chart-container { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: $rounded-lg; padding: $spacing-md; margin-bottom: $spacing-md; }
.chart { height: 300px; }
</style>
