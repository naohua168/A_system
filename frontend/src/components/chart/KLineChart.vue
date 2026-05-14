<template>
  <div class="kline-chart" ref="chartRef" :style="{ height: height }">
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  stockCode: string
  height?: string
  showMa?: boolean
  showChanlun?: boolean
  days?: number
}>()

const emit = defineEmits<{
  (e: 'dataLoaded', data: any): void
}>()

const chartRef = ref<HTMLElement>()
const loading = ref(true)
const error = ref('')
let chart: echarts.ECharts | null = null

async function fetchKlineData() {
  try {
    const resp = await fetch(`/api/stock/kline/${props.stockCode}?days=${props.days || 60}`)
    if (!resp.ok) throw new Error('数据获取失败')
    return await resp.json()
  } catch (e: any) {
    throw new Error(e.message || '网络错误')
  }
}

function renderChart(data: any) {
  if (!chartRef.value || !data?.length) return

  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  const dates = data.map((d: any) => d.tradeDate || d.date)
  const volumes = data.map((d: any) => d.volume || 0)
  const klineData = data.map((d: any) => [
    d.openPrice || d.open,
    d.closePrice || d.close,
    d.lowPrice || d.low,
    d.highPrice || d.high,
  ])

  const option = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['K线', ...(props.showMa ? ['MA5', 'MA10', 'MA20'] : [])] },
    grid: [
      { left: '10%', right: '10%', top: 60, height: '55%' },
      { left: '10%', right: '10%', top: '78%', height: '15%' },
    ],
    xAxis: [
      { type: 'category', data: dates, gridIndex: 0 },
      { type: 'category', data: dates, gridIndex: 1 },
    ],
    yAxis: [
      { scale: true, gridIndex: 0 },
      { scale: true, gridIndex: 1 },
    ],
    dataZoom: [{ type: 'inside', xAxisIndex: [0, 1] }],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: klineData,
        itemStyle: {
          color: '#ef5350',
          color0: '#26a69a',
          borderColor: '#ef5350',
          borderColor0: '#26a69a',
        },
      },
      ...(props.showMa
        ? [
            {
              name: 'MA5',
              type: 'line',
              data: data.map((d: any) => d.ma5),
              smooth: true,
              lineStyle: { width: 1 },
              symbol: 'none',
            },
            {
              name: 'MA10',
              type: 'line',
              data: data.map((d: any) => d.ma10),
              smooth: true,
              lineStyle: { width: 1 },
              symbol: 'none',
            },
            {
              name: 'MA20',
              type: 'line',
              data: data.map((d: any) => d.ma20),
              smooth: true,
              lineStyle: { width: 1 },
              symbol: 'none',
            },
          ]
        : []),
      {
        name: '成交量',
        type: 'bar',
        data: volumes,
        xAxisIndex: 1,
        yAxisIndex: 1,
        itemStyle: { color: '#82b1ff' },
      },
    ],
  }

  chart.setOption(option, true)
  emit('dataLoaded', data)
}

onMounted(async () => {
  try {
    const data = await fetchKlineData()
    loading.value = false
    await nextTick()
    renderChart(data)
  } catch (e: any) {
    loading.value = false
    error.value = e.message
  }
})

onBeforeUnmount(() => {
  chart?.dispose()
  chart = null
})

watch(() => props.stockCode, async () => {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchKlineData()
    loading.value = false
    await nextTick()
    renderChart(data)
  } catch (e: any) {
    loading.value = false
    error.value = e.message
  }
})
</script>

<style scoped>
.kline-chart {
  width: 100%;
  min-height: 400px;
}
.loading,
.error {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: #999;
}
.error {
  color: #ef5350;
}
</style>
