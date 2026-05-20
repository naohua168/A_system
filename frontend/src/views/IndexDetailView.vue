<template>
  <div class="index-detail">
    <!-- 指数头 -->
    <div class="index-header">
      <div class="index-info">
        <h2>{{ info.name }} <span class="code-badge">{{ info.code }} / {{ info.market }}</span></h2>
        <div class="price-section">
          <span class="current-price" :class="info.changePercent >= 0 ? 'text-rise' : 'text-fall'">
            {{ safeNum(info.price) }}
          </span>
          <span class="price-change" :class="info.changePercent >= 0 ? 'text-rise' : 'text-fall'">
            {{ info.changePercent >= 0 ? '+' : '' }}{{ safeNum(info.changePercent, 2) }}%
          </span>
        </div>
        <div class="meta caption">
          <span>开盘: {{ safeNum(info.open) }}</span>
          <span>最高: {{ safeNum(info.high) }}</span>
          <span>最低: {{ safeNum(info.low) }}</span>
          <span>昨收: {{ safeNum(info.preClose) }}</span>
          <span>成交量: {{ formatVol(info.volume) }}</span>
        </div>
      </div>
    </div>

    <!-- K线图 -->
    <div class="kline-section" v-loading="loading">
      <div class="kline-chart" ref="chartRef"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { getIndexInfo, getIndexKline } from '@/api/index'
import { formatVol } from '@/utils/format'

const route = useRoute()
const code = route.params.code as string

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
const loading = ref(true)

const info = reactive({
  name: '', code: code, market: '',
  price: 0, changePercent: 0,
  open: 0, high: 0, low: 0, preClose: 0,
  volume: 0, amount: 0,
})

function safeNum(v: unknown, decimals = 2): string {
  const n = Number(v)
  return isNaN(n) || n === 0 ? '-' : n.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

async function loadData() {
  loading.value = true
  try {
    // 1. 基本信息
    const idxInfo: any = await getIndexInfo(code)
    if (idxInfo) {
      info.name = idxInfo.indexName || idxInfo.indexCode || code
      info.market = idxInfo.market || ''
    }

    // 2. K线数据
// @ts-ignore - API type mismatch
    const kline: any[] = await getIndexKline(code, { days: 120 })
    if (Array.isArray(kline) && kline.length > 10) {
      const dates = kline.map((d: any) => d.tradeDate || '')
      const points = kline.map((d: any) => [
        Number(d.closePoint),
        Number(d.openPoint),
        Number(d.lowPoint),
        Number(d.highPoint),
      ])
      const volumes = kline.map((d: any) => Number(d.volume) || 0)

      // 最新一条
      const last = kline[kline.length - 1]
      Object.assign(info, {
        price: Number(last.closePoint),
        open: Number(last.openPoint),
        high: Number(last.highPoint),
        low: Number(last.lowPoint),
        preClose: Number(last.preClose) || Number(last.closePoint) * 0.99,
        volume: Number(last.volume),
        amount: Number(last.amount),
        changePercent: Number(last.changePercent),
      })

      // 渲染图表
      nextTick(() => renderChart(dates, points, volumes))
    }
  } catch (_e) {
    console.warn('[Index] 加载指数数据失败:', _e)
  } finally {
    loading.value = false
  }
}

function renderChart(dates: string[], data: number[][], volumes: number[]) {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)

  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    grid: [{ left: '6%', right: '4%', top: '5%', height: '72%' }, { left: '6%', right: '4%', top: '82%', height: '14%' }],
    xAxis: [{ type: 'category', data: dates, axisLabel: { rotate: 30, fontSize: 10 }, gridIndex: 0 },
            { type: 'category', data: dates, gridIndex: 1 }],
    yAxis: [{ scale: true, gridIndex: 0 }, { scale: true, gridIndex: 1, axisLabel: { show: true } }],
    series: [
      { type: 'candlestick', data, name: 'K线',
        itemStyle: { color: '#e74c3c', color0: '#27ae60', borderColor: '#e74c3c', borderColor0: '#27ae60' } },
      { type: 'bar', data: volumes, name: '成交量', xAxisIndex: 1, yAxisIndex: 1,
        itemStyle: { color: (p: any) => p.dataIndex > 0 && data[p.dataIndex][0] >= data[p.dataIndex - 1]?.[0] ? '#e74c3c' : '#27ae60' } },
    ],
  })
}

function handleResize() { chart?.resize() }

onMounted(() => {
  loadData()
  window.addEventListener('resize', handleResize)
})
onBeforeUnmount(() => { chart?.dispose(); window.removeEventListener('resize', handleResize) })
</script>

<style scoped lang="scss">
.index-detail { max-width: 1200px; margin: 0 auto; padding: 20px; }
.index-header { margin-bottom: 20px; }
.index-info {
  h2 { font-size: 22px; margin-bottom: 8px; .code-badge { font-size: 13px; color: #999; font-weight: 400; margin-left: 8px; } }
  .current-price { font-size: 32px; font-weight: 600; }
  .price-change { font-size: 16px; margin-left: 12px; }
  .meta { display: flex; gap: 16px; margin-top: 6px; color: #999; font-size: 13px; }
}
.kline-chart { width: 100%; height: 500px; }
.text-rise { color: #e74c3c; }
.text-fall { color: #27ae60; }
</style>
