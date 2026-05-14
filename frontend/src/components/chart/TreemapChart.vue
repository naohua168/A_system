<template>
  <div ref="chartDom" style="width: 100%; height: 100%;"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

interface SectorNode {
  name: string
  value: number
  changePercent: number
  items?: SectorNode[]
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
    const intensity = Math.min(0.85, 0.25 + Math.abs(pct) * 0.12)
    return `rgba(231, 76, 60, ${intensity})`
  } else {
    const intensity = Math.min(0.85, 0.25 + Math.abs(pct) * 0.10)
    return `rgba(39, 174, 96, ${intensity})`
  }
}

function buildTreemapData(data: SectorNode[]): any[] {
  return data.map(item => ({
    name: item.name,
    value: item.value,
    changePercent: item.changePercent,
    itemStyle: {
      color: colorFor(item.changePercent),
      borderColor: 'rgba(255,255,255,0.35)',
      borderWidth: 3,
      borderRadius: 6,
    },
    children: item.items?.map(sub => ({
      name: sub.name,
      value: sub.value,
      changePercent: sub.changePercent,
      itemStyle: {
        color: colorFor(sub.changePercent),
        borderColor: 'rgba(255,255,255,0.2)',
        borderWidth: 2,
        borderRadius: 4,
      },
    })),
  }))
}

function renderChart() {
  if (!chartDom.value) return

  if (!chart) {
    chart = echarts.init(chartDom.value, undefined, { renderer: 'canvas' })
  }

  const option: echarts.EChartsOption = {
    tooltip: {
      backgroundColor: 'rgba(30, 30, 30, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      borderRadius: 8,
      padding: [10, 14],
      textStyle: { color: '#fff', fontSize: 13 },
      formatter: (params: any) => {
        const d = params.data
        if (!d || !d.name) return ''
        const sign = d.changePercent >= 0 ? '+' : ''
        const color = d.changePercent >= 0 ? '#e74c3c' : '#27ae60'
        // value > 1000 视为成交额(亿当量，前端格式化)，否则视为成分股数量
        const isCount = d.value && d.value < 1000
        const sub = isCount
          ? `成分股: ${d.value}只<br/>`
          : (d.value ? `成交额: ${(d.value / 100).toFixed(2)}亿<br/>` : '')
        return `<strong style="font-size:15px;">${d.name}</strong><br/>
                ${sub}
                <span style="color:${color};font-weight:600;">涨跌幅: ${sign}${(d.changePercent || 0).toFixed(2)}%</span>`
      },
    },
    series: [{
      type: 'treemap',
      data: buildTreemapData(props.data),
      roam: false,
      nodeClick: false,
      width: '100%',
      height: '100%',
      breadcrumb: { show: false },
      label: {
        show: true,
        formatter: (params: any) => {
          const d = params.data
          if (!d || !d.name) return ''
          const sign = d.changePercent >= 0 ? '+' : ''
          if (d.children) return `${d.name}`
          return `${d.name}\n${sign}${(d.changePercent || 0).toFixed(2)}%`
        },
        color: '#fff',
        fontSize: 13,
        fontWeight: 600,
        textShadowBlur: 6,
        textShadowColor: 'rgba(0,0,0,0.6)',
      },
      upperLabel: {
        show: true,
        height: 32,
        color: '#fff',
        fontSize: 14,
        fontWeight: 600,
        textShadowBlur: 6,
        textShadowColor: 'rgba(0,0,0,0.6)',
      },
      itemStyle: {
        borderColor: 'rgba(255,255,255,0.25)',
        borderWidth: 3,
        borderRadius: 6,
      },
      levels: [
        {
          colorSaturation: [0.3, 0.7],
          itemStyle: {
            borderColor: 'rgba(255,255,255,0.3)',
            borderWidth: 4,
            gapWidth: 3,
          },
        },
        {
          colorSaturation: [0.3, 0.6],
          itemStyle: {
            borderColor: 'rgba(255,255,255,0.15)',
            borderWidth: 2,
            gapWidth: 1,
          },
        },
      ],
      animationDurationUpdate: 500,
      animationEasing: 'cubicOut',
    }],
  }

  // 仅在首次渲染后绑定点击事件，避免 watch 重绘时误触
  if (!chart._clickBound) {
    chart.off('click')
    chart.on('click', (params: any) => {
      if (params.data && params.data.name && !params.data.children) {
        emit('click', params.data)
      }
    })
    chart._clickBound = true
  }

  chart.setOption(option, true)
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
