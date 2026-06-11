<template>
  <div class="ic-page">
    <!-- ═══ 顶栏 ═══ -->
    <header class="ic-top">
      <h1>行业对比</h1>
      <div class="ic-toolbar">
        <ReviewDatePicker @change="(d:string) => { reviewDate.value = d; fetchData() }" />
        <span class="today-label">{{ reviewDate ? reviewDate : '今日 · ' + todayStr }}</span>
        <el-radio-group v-model="sortBy" size="small" @change="onSortChange">
          <el-radio-button value="changePct">涨跌幅</el-radio-button>
          <el-radio-button value="top">涨跌榜</el-radio-button>
        </el-radio-group>
      </div>
    </header>

    <!-- 骨架 -->
    <template v-if="loading">
      <div class="ic-sk" v-for="i in 4" :key="i"></div>
    </template>

    <!-- 错误 / 空数据 -->
    <div v-else-if="error" class="ic-empty">
      <p>数据加载失败</p>
      <el-button size="small" @click="fetchData">重试</el-button>
    </div>
    <div v-else-if="!sortedRecords.length" class="ic-empty">
      <p>今日暂无行业数据</p>
      <el-button size="small" @click="fetchData">刷新重试</el-button>
    </div>

    <template v-else>
      <!-- ═══ ① 概览统计 ═══ -->
      <section class="ic-summary">
        <div class="ic-sum-item">
          <span class="ic-sum-lb">行业总数</span>
          <span class="ic-sum-v">{{ totalCount }}</span>
        </div>
        <div class="ic-sum-item up">
          <span class="ic-sum-lb">上涨</span>
          <span class="ic-sum-v">{{ upCount }}</span>
          <span class="ic-sum-r">{{ upRatio }}%</span>
        </div>
        <div class="ic-sum-item dn">
          <span class="ic-sum-lb">下跌</span>
          <span class="ic-sum-v">{{ dnCount }}</span>
          <span class="ic-sum-r">{{ dnRatio }}%</span>
        </div>
        <div class="ic-sum-item">
          <span class="ic-sum-lb">涨跌比</span>
          <span class="ic-sum-v">{{ upDownRatio }}</span>
        </div>
        <div class="ic-sum-item flat">
          <span class="ic-sum-lb">平均涨跌</span>
          <span class="ic-sum-v" :class="avgChange >= 0 ? 'r' : 'g'">{{ avgChangeDisplay }}</span>
        </div>
      </section>

      <!-- ═══ ② 涨跌进度条 ═══ -->
      <section class="ic-progress">
        <div class="ic-progress-bar">
          <div class="ic-progress-up" :style="{ width: upRatio + '%' }">
            <span v-if="upRatio > 15">上涨 {{ upCount }}</span>
          </div>
          <div class="ic-progress-dn" :style="{ width: dnRatio + '%' }">
            <span v-if="dnRatio > 15">下跌 {{ dnCount }}</span>
          </div>
        </div>
        <div class="ic-progress-ruler">
          <span v-for="p in [0,25,50,75,100]" :key="p" :style="{ left: p + '%' }">{{ p }}%</span>
        </div>
      </section>

      <!-- ═══ ③ 双栏排行：左侧涨幅 TOP 右侧跌幅 TOP ═══ -->
      <section class="ic-double">
        <div class="ic-card">
          <div class="ic-card-title">涨幅前十</div>
          <table class="ic-rank-table">
            <tr><th class="ic-rk-num">#</th><th>行业</th><th class="ic-rk-val">涨跌幅</th></tr>
            <tr v-for="(item, i) in topGainers" :key="item.industryName" class="ic-rank-row" @click="goToSector(item.industryName)">
              <td class="ic-rk-num">{{ i + 1 }}</td>
              <td class="ic-rk-name">{{ item.industryName }}</td>
              <td class="ic-rk-val r">{{ safeNum(item.changePct, 2) }}%</td>
            </tr>
          </table>
        </div>
        <div class="ic-card">
          <div class="ic-card-title">跌幅前十</div>
          <table class="ic-rank-table">
            <tr><th class="ic-rk-num">#</th><th>行业</th><th class="ic-rk-val">涨跌幅</th></tr>
            <tr v-for="(item, i) in topLosers" :key="item.industryName" class="ic-rank-row" @click="goToSector(item.industryName)">
              <td class="ic-rk-num">{{ i + 1 }}</td>
              <td class="ic-rk-name">{{ item.industryName }}</td>
              <td class="ic-rk-val g">{{ safeNum(item.changePct, 2) }}%</td>
            </tr>
          </table>
        </div>
      </section>

      <!-- ═══ ④ 行业涨跌分布图（水平柱状图） ═══ -->
      <section class="ic-card ic-chart-card">
        <div class="ic-card-title">
          <span>行业涨跌分布</span>
          <span class="ic-card-sub">按{{ sortBy === 'changePct' ? '涨跌幅' : '涨跌榜' }}排序，显示前20</span>
        </div>
        <div ref="chartRef" class="ic-chart-body"></div>
      </section>

      <!-- ═══ ⑤ 全行业明细表 ═══ -->
      <section class="ic-card">
        <div class="ic-card-title">
          <span>全行业列表（{{ totalCount }}个）</span>
          <el-input v-model="searchQuery" placeholder="搜索行业" size="small" style="width:160px" clearable />
        </div>
        <el-table
          :data="filteredTableData"
          stripe
          size="small"
          style="width:100%"
          @row-click="goToSector"
          :header-cell-style="{ background: '#f5f6fa', color: '#666', borderBottom: '1px solid #eee', fontSize: '12px', fontWeight: 500, padding: '9px 0' }"
          :cell-style="{ fontSize: '12px', padding: '7px 0', color: '#333' }"
        >
          <el-table-column label="#" width="45" type="index" />
          <el-table-column prop="industryName" label="行业" min-width="130" />
          <el-table-column label="涨跌幅" width="110" align="right" sortable prop="changePct">
            <template #default="{ row }">
              <span class="ic-chg-tag" :class="(row.changePct || 0) >= 0 ? 'r' : 'g'">
                {{ (row.changePct || 0) >= 0 ? '+' : '' }}{{ safeNum(row.changePct, 2) }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column label="涨跌趋势" min-width="140">
            <template #default="{ row }">
              <div class="ic-trend-bar">
                <span class="ic-trend-up" :style="{ width: trendWidth(row) + '%' }"></span>
                <span class="ic-trend-dn" :style="{ width: (100 - trendWidth(row)) + '%' }"></span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="成分股" width="80" align="center">
            <template #default="{ row }">{{ row.stockCount || '-' }}</template>
          </el-table-column>
          <el-table-column label="成交额(亿)" width="110" align="right">
            <template #default="{ row }">{{ row.totalAmount || '-' }}</template>
          </el-table-column>
        </el-table>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { getIndustryCompare, getHistoryIndustryCompare } from '@/api/signal'
import echarts from '@/utils/echarts'
import { useApiRetry, safeRecords, safeNum } from '@/composables/useApiRetry'
import { useAutoRefresh } from '@/composables/useAutoRefresh'
import ReviewDatePicker from '@/components/common/ReviewDatePicker.vue'


const todayStr = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
const reviewDate = ref('')
const sortBy = ref('changePct')
const searchQuery = ref('')
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const { data: rawData, loading, error, fetch: fetchData } = useApiRetry(
  () => reviewDate.value ? getHistoryIndustryCompare(reviewDate.value) : getIndustryCompare(),
  { maxRetries: 1, showError: false, errorMessage: '行业对比数据加载失败' }
)

const records = computed(() => safeRecords(rawData.value, 'records'))

const sortedRecords = computed(() => {
  const data = [...records.value] as any[]
  if (!data.length) return []
  try {
    return data.sort((a, b) => (b.changePct || 0) - (a.changePct || 0))
  } catch { return data }
})

// 统计
const totalCount = computed(() => sortedRecords.value.length)
const upCount = computed(() => sortedRecords.value.filter((r: any) => (r.changePct || 0) > 0).length)
const dnCount = computed(() => sortedRecords.value.filter((r: any) => (r.changePct || 0) < 0).length)
const flatCount = computed(() => totalCount.value - upCount.value - dnCount.value)
const upRatio = computed(() => totalCount.value ? Math.round((upCount.value / totalCount.value) * 100) : 0)
const dnRatio = computed(() => totalCount.value ? Math.round((dnCount.value / totalCount.value) * 100) : 0)
const upDownRatio = computed(() => `${upCount.value}:${dnCount.value}`)
const avgChange = computed(() => {
  const vals = sortedRecords.value.map((r: any) => r.changePct || 0)
  return vals.length ? vals.reduce((a: number, b: number) => a + b, 0) / vals.length : 0
})
const avgChangeDisplay = computed(() => {
  const v = avgChange.value
  return (v >= 0 ? '+' : '') + v.toFixed(2) + '%'
})

const topGainers = computed(() => sortedRecords.value.slice(0, 10))
const topLosers = computed(() => [...sortedRecords.value].reverse().slice(0, 10))

// 涨跌幅映射到0~100的进度条宽度（基于当前数据集中的最大值）
const maxAbsChange = computed(() => {
  const vals = sortedRecords.value.map((r: any) => Math.abs(r.changePct || 0))
  return vals.length ? Math.max(...vals) : 1
})
function trendWidth(row: any): number {
  const val = (row.changePct || 0)
  return ((val + maxAbsChange.value) / (maxAbsChange.value * 2)) * 100
}

// 搜索过滤
const filteredTableData = computed(() => {
  if (!searchQuery.value) return sortedRecords.value
  const q = searchQuery.value.toLowerCase()
  return (sortedRecords.value as any[]).filter((r: any) =>
    (r.industryName || '').toLowerCase().includes(q)
  )
})

// 图表渲染
function renderChart() {
  if (!chartRef.value || !sortedRecords.value.length) return
  if (!chart) chart = echarts.init(chartRef.value)
  const top20 = sortedRecords.value.slice(0, 20).reverse() as any[]
  const names = top20.map((d: any) => d.industryName || '')
  const vals = top20.map((d: any) => d.changePct || 0)

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#fff',
      borderColor: '#e8e8e8',
      textStyle: { color: '#333', fontSize: 12 },
      formatter: (params: any[]) => {
        const p = params[0]
        return `<b>${p.name}</b><br/>涨跌幅：<span style="color:${p.value >= 0 ? '#D93026' : '#34A853'};font-weight:600">${p.value >= 0 ? '+' : ''}${p.value.toFixed(2)}%</span>`
      },
    },
    grid: { left: 90, right: 50, top: 8, bottom: 10 },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#999', fontSize: 11, formatter: (v: number) => v.toFixed(1) + '%' },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: { color: '#333', fontSize: 11, fontWeight: 500 },
      axisTick: { show: false },
    },
    series: [{
      type: 'bar',
      data: vals.map((v: number) => ({
        value: v,
        itemStyle: {
          color: v >= 0 ? { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#e57373' }, { offset: 1, color: '#D93026' }] }
            : { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#34A853' }, { offset: 1, color: '#81C784' }] },
          borderRadius: [0, 2, 2, 0],
        },
      })),
      barWidth: 14,
      label: {
        show: true,
        position: 'right',
        color: '#666',
        fontSize: 11,
        formatter: (p: any) => (p.value >= 0 ? '+' : '') + p.value.toFixed(2) + '%',
      },
    }],
  }, { notMerge: true })
  chart?.resize()
}

function goToSector(_row: any) {
  // 板块详情页已移除，保留无操作
}

function onSortChange() { renderChart() }

watch(sortedRecords, () => nextTick(renderChart))
watch(error, () => chart?.clear())

function handleResize() { chart?.resize() }
onMounted(() => { fetchData(); window.addEventListener('resize', handleResize) })
useAutoRefresh(() => { if (!reviewDate.value) fetchData() }, 120_000)
onUnmounted(() => { chart?.dispose(); window.removeEventListener('resize', handleResize) })
</script>

<style scoped lang="scss">
.ic-page { padding: 16px 24px; max-width: 1200px; margin: 0 auto; }

// 顶栏
.ic-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.ic-top h1 { font-size: 20px; font-weight: 600; color: #222; margin: 0; }
.ic-toolbar { display: flex; align-items: center; gap: 8px; }

// 空态
.ic-empty { text-align: center; padding: 60px 0; color: #999; p { margin-bottom: 10px; } }

// ① 概览
.ic-summary {
  display: flex; gap: 10px; margin-bottom: 10px; flex-wrap: wrap;
}
.ic-sum-item {
  flex: 1; min-width: 100px;
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  padding: 14px 10px; background: #fff; border: 1px solid #e8e8e8; border-radius: 6px;
  &.up { border-left: 3px solid #D93026; }
  &.dn { border-left: 3px solid #34A853; }
  &.flat { border-left: 3px solid #ddd; }
}
.ic-sum-lb { font-size: 11px; color: #888; }
.ic-sum-v { font-size: 20px; font-weight: 700; color: #333; }
.ic-sum-r { font-size: 11px; }

// ② 进度条
.ic-progress { background: #fff; border: 1px solid #e8e8e8; border-radius: 6px; padding: 16px; margin-bottom: 10px; }
.ic-progress-bar { display: flex; height: 22px; border-radius: 4px; overflow: hidden; }
.ic-progress-up, .ic-progress-dn { display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; color: #fff; transition: width 0.4s; }
.ic-progress-up { background: linear-gradient(90deg, #D93026, #e57373); }
.ic-progress-dn { background: linear-gradient(90deg, #81C784, #34A853); }
.ic-progress-ruler { position: relative; height: 16px; margin-top: 4px; }
.ic-progress-ruler span { position: absolute; font-size: 10px; color: #bbb; transform: translateX(-50%); }

// 通用卡片
.ic-card { background: #fff; border: 1px solid #e8e8e8; border-radius: 6px; overflow: hidden; }
.ic-card-title {
  display: flex; justify-content: space-between; align-items: center;
  padding: 11px 16px; font-size: 14px; font-weight: 600; color: #333;
  border-bottom: 1px solid #f0f0f0;
}
.ic-card-sub { font-size: 11px; color: #aaa; font-weight: 400; }

// ③ 双栏排行
.ic-double { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }
@media (max-width: 700px) { .ic-double { grid-template-columns: 1fr; } }
.ic-rank-table {
  width: 100%; border-collapse: collapse;
  th { padding: 8px 12px 6px; font-size: 11px; color: #888; font-weight: 500; text-align: left; border-bottom: 1px solid #f0f0f0; }
  .ic-rk-num { width: 36px; text-align: center; }
  .ic-rk-val { text-align: right; width: 80px; font-weight: 600; }
}
.ic-rank-row {
  cursor: pointer; transition: background 0.1s;
  td { padding: 7px 12px; font-size: 13px; color: #333; border-bottom: 1px solid #f7f7f7; }
  &:hover td { background: #f0f5ff; }
  .ic-rk-name { font-weight: 500; }
}

// ④ 图表
.ic-chart-card { margin-bottom: 10px; }
.ic-chart-body { height: 340px; }

// ⑤ 表格
.ic-chg-tag { font-weight: 600; }
.ic-trend-bar { display: flex; height: 6px; border-radius: 3px; overflow: hidden; background: #f0f0f0; }
.ic-trend-up { background: #D93026; height: 100%; transition: width 0.3s; }
.ic-trend-dn { background: #34A853; height: 100%; transition: width 0.3s; }

// 骨架
.ic-sk { height: 12px; margin: 6px 0; background: #f5f5f5; border-radius: 3px; animation: ic-shimmer 1.5s infinite; }
@keyframes ic-shimmer { 0%,100% { opacity: 0.4; } 50% { opacity: 0.8; } }

// 全局色
.r, .up { color: #D93026; }
.g, .dn { color: #34A853; }
</style>
