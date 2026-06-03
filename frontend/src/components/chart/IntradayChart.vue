<template>
  <div class="intraday-chart" ref="chartRef" style="width:100%;height:100%;min-height:400px"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  data: number[][]          // [[timestamp, open, close, low, high, volume], ...]
  preClose: number          // 昨收盘价，用于计算涨跌幅
  code: string
}>()

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
let disposed = false

function render() {
  if (disposed) return
  if (!chartRef.value?.isConnected) return
  if (!props.data || props.data.length < 2) return

  if (!chart) {
    try { chart = echarts.init(chartRef.value) } catch { return }
  }

  const preClose = props.preClose || props.data[0][2] // fallback: first close
  // 分时图数据: 时间 -> close价格 + 涨跌幅
  const times: string[] = []
  const prices: number[] = []
  const chgPcts: number[] = []
  const volumes: number[] = []
  let minPrice = Infinity, maxPrice = -Infinity

  props.data.forEach((d) => {
    const ts = d[0]
    const close = d[2]
    const vol = d[5] || 0
    const dt = new Date(ts)
    times.push(`${String(dt.getHours()).padStart(2,'0')}:${String(dt.getMinutes()).padStart(2,'0')}`)
    prices.push(close)
    chgPcts.push(preClose > 0 ? (close - preClose) / preClose * 100 : 0)
    volumes.push(vol)
    if (close < minPrice) minPrice = close
    if (close > maxPrice) maxPrice = close
  })

  const padding = (maxPrice - minPrice) * 0.08 || 0.5
  const opt: any = {
    grid: [{ left: 48, right: 48, top: 12, height: '58%' }, { left: 48, right: 48, top: '74%', height: '18%' }],
    xAxis: [{
      type: 'category', data: times, axisLine: { onZero: false },
      axisTick: { show: false }, splitLine: { show: false },
      axisLabel: {
        fontSize: 10, color: '#888',
        formatter: (v: string) => {
          // 只显示关键时间点：09:30、10:30、11:30、13:00、14:00、15:00
          const keyTimes = ['09:30','10:00','10:30','11:00','11:30','13:00','13:30','14:00','14:30','15:00']
          return keyTimes.includes(v) ? v : ''
        },
      },
    }, {
      type: 'category', data: times, gridIndex: 1,
      axisLine: { show: false }, axisTick: { show: false },
      splitLine: { show: false }, axisLabel: { show: false },
    }],
    yAxis: [{
      min: minPrice - padding, max: maxPrice + padding,
      splitLine: { lineStyle: { color: 'rgba(200,200,210,0.3)', type: 'dashed' } },
      axisLabel: { fontSize: 10, color: '#888' },
    }, {
      gridIndex: 1, min: 0,
      splitLine: { show: false }, axisLabel: { show: false },
    }],
    series: [{
      type: 'line', data: prices, smooth: true, symbol: 'none',
      lineStyle: { width: 1.5, color: '#e74c3c' },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(231,76,60,0.25)' }, { offset: 1, color: 'rgba(231,76,60,0.02)' }] } },
      markLine: {
        silent: true, data: [{ yAxis: preClose }],
        lineStyle: { color: '#999', width: 0.5, type: 'dashed' },
        label: { show: true, formatter: `昨收 ${preClose.toFixed(2)}`, fontSize: 9, color: '#999', position: 'insideEndTop' },
      },
      // 午盘分割线（11:30）
      markArea: {
        silent: true, data: [[{ xAxis: '11:30' }, { xAxis: '13:00' }]],
        itemStyle: { color: 'rgba(200,200,210,0.04)' },
      },
    }, {
      type: 'bar', data: volumes, xAxisIndex: 1, yAxisIndex: 1,
      itemStyle: { color: (params: any) => {
        const idx = params.dataIndex
        const chg = chgPcts[idx] || 0
        return chg >= 0 ? '#e74c3c' : '#27ae60'
      } },
      barWidth: '60%',
    }],
    tooltip: {
      trigger: 'axis',
      formatter: (params: any[]) => {
        if (!params?.length) return ''
        const p = params[0]
        const idx = p.dataIndex
        const price = prices[idx]
        const chg = chgPcts[idx]
        const vol = volumes[idx]
        return `<div style="font-size:12px">
          <div>${times[idx]}</div>
          <div style="font-weight:600">${price.toFixed(2)}  <span style="color:${chg>=0?'#e74c3c':'#27ae60'}">${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%</span></div>
          <div style="color:#888">量: ${vol.toLocaleString()}</div>
        </div>`
      },
    },
  }
  chart.setOption(opt, { notMerge: true })
}

const resizeObserver = new ResizeObserver(() => {
  if (chart && !chart.isDisposed()) chart.resize()
})

onMounted(() => {
  if (chartRef.value) resizeObserver.observe(chartRef.value)
  render()
})

onBeforeUnmount(() => {
  disposed = true
  resizeObserver.disconnect()
  if (chart) { chart.dispose(); chart = null }
})

watch(() => [props.data, props.preClose], render, { deep: true })
</script>

<style scoped>
.intraday-chart {
  position: relative;
}
</style>
