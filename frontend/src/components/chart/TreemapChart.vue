<template>
  <div ref="chartDom" style="width: 100%; height: 100%;"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import echarts from '@/utils/echarts'

interface SectorNode {
  name: string
  value: number
  changePercent: number
}

const props = defineProps<{
  data: SectorNode[]
}>()

const emit = defineEmits<{
  click: [data: any]
}>()

const chartDom = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

function colorFor(pct: number): string {
  if (pct >= 0) {
    const intensity = Math.min(0.92, 0.15 + Math.abs(pct) * 0.14)
    return `rgba(211, 47, 47, ${intensity})`
  } else {
    const intensity = Math.min(0.92, 0.15 + Math.abs(pct) * 0.14)
    return `rgba(46, 125, 50, ${intensity})`
  }
}

function fontSizeFor(value: number, maxValue: number): number {
  const ratio = value / maxValue
  if (ratio > 0.3) return 16
  if (ratio > 0.15) return 14
  if (ratio > 0.08) return 12
  if (ratio > 0.04) return 11
  return 10
}

function renderChart() {
  if (!chartDom.value || !props.data?.length) return

  if (!chart) {
    chart = echarts.init(chartDom.value, undefined, { renderer: 'canvas' })
  }

  const maxValue = Math.max(...props.data.map(d => d.value || 1), 1)
  const rawData = props.data.map(item => ({
    name: item.name,
    value: Math.max(item.value, 1),
    changePercent: item.changePercent,
    _maxValue: maxValue,
    itemStyle: {
      color: colorFor(item.changePercent),
      borderColor: 'rgba(0,0,0,0.10)',
      borderWidth: 0.5,
      borderRadius: 2,
    },
  }))

  const option: echarts.EChartsOption = {
    tooltip: {
      backgroundColor: 'rgba(20, 20, 20, 0.96)',
      borderColor: 'rgba(255, 255, 255, 0.08)',
      borderWidth: 1,
      borderRadius: 6,
      padding: [10, 14],
      textStyle: { color: '#fff', fontSize: 13 },
      formatter: (params: any) => {
        const d = params.data
        if (!d || !d.name) return ''
        const pct = d.changePercent || 0
        const sign = pct >= 0 ? '+' : ''
        const color = pct >= 0 ? '#ef5350' : '#66bb6a'
        return `
          <div style="font-size:15px;font-weight:700;margin-bottom:4px;">${d.name}</div>
          <div style="display:flex;justify-content:space-between;gap:20px;">
            <span style="color:rgba(255,255,255,0.5);">涨跌幅</span>
            <span style="color:${color};font-weight:700;">${sign}${(pct).toFixed(2)}%</span>
          </div>
          <div style="color:rgba(255,255,255,0.35);font-size:12px;margin-top:4px;">👆 点击查看详情</div>
        `
      },
    },
    series: [{
      type: 'treemap',
      data: rawData,
      roam: true,
      nodeClick: false,      // 禁用钻取，点击始终 emit 给父组件
      width: '100%',
      height: '100%',
      breadcrumb: { show: false },
      label: {
        show: true,
        formatter: (params: any) => {
          const d = params.data
          if (!d || !d.name) return ''
          const pct = d.changePercent || 0
          const sign = pct >= 0 ? '+' : ''
          const maxV = d._maxValue || maxValue
          const ratio = (d.value || 1) / maxV
          if (ratio < 0.02) return `${sign}${(pct).toFixed(2)}%`
          return `${d.name}\n${sign}${(pct).toFixed(2)}%`
        },
        color: '#fff',
        fontSize: (params: any) => {
          const d = params.data
          return fontSizeFor(d.value || 1, maxValue)
        },
        fontWeight: 600,
        textShadowBlur: 6,
        textShadowColor: 'rgba(0,0,0,0.8)',
        lineHeight: 20,
      },
      itemStyle: {
        borderColor: 'rgba(0,0,0,0.10)',
        borderWidth: 0.5,
        borderRadius: 2,
      },
      levels: [{
        colorSaturation: [0.35, 0.85],
        itemStyle: {
          borderColor: 'rgba(0,0,0,0.10)',
          borderWidth: 0.5,
          gapWidth: 0.5,
        },
      }],
      squareRatio: 1,
      leafDepth: 1,
      animationDurationUpdate: 600,
      animationEasing: 'cubicOut',
    }],
  }

  chart.setOption(option, true)

  // 点击事件
  const chartAny = chart as any
  if (!chartAny._clickBound) {
    chart.off('click')
    chart.on('click', (params: any) => {
      if (params.data && params.data.name) {
        emit('click', params.data)
      }
    })
    chartAny._clickBound = true
  }
}

function handleResize() {
  chart?.resize()
}

watch(() => props.data, () => {
  nextTick(renderChart)
}, { deep: true })

onMounted(() => {
  nextTick(renderChart)
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>
