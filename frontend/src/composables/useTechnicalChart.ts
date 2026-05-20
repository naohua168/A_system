/**
 * 技术指标K线图渲染组合函数
 * 抽取 StockDetailView 与 SectorDetailView 共用的 ECharts 渲染逻辑
 */
import { ref, onBeforeUnmount, type Ref } from 'vue'
import * as echarts from 'echarts'
import { calcMA, calcBOLL, calcMACD, calcKDJ, calcRSI } from '@/utils/indicators'
import type { ChanlunAnalysis } from '@/types'
import type { IndicatorParams } from '@/types'

export function useTechnicalChart(
  klineChartRef: Ref<HTMLElement | undefined>,
  bottomChartRef: Ref<HTMLElement | undefined>,
  options: {
    /** K线数据 getter — 每次渲染时重新读取 */
    getKlineData: () => number[][]
    params: IndicatorParams | Ref<IndicatorParams>
    showMA: Ref<boolean>
    showBOLL: Ref<boolean>
    bottomActive: Ref<string | null>
    chanlunData?: Ref<ChanlunAnalysis>
    showChanlun?: Ref<boolean>
  }
) {
  let klineChart: echarts.ECharts | null = null
  let bottomChart: echarts.ECharts | null = null

  function renderChart() {
    if (!klineChartRef.value) return
    const klineData = options.getKlineData()
    if (klineData.length === 0) return

    const paramsVal = 'value' in (options.params as any)
      ? (options.params as Ref<IndicatorParams>).value
      : options.params as IndicatorParams
    const { showMA, showBOLL, bottomActive, chanlunData, showChanlun } = options

    const dates = klineData.map((d) => {
      try {
        return new Date(d[0]).toLocaleDateString('zh-CN')
      } catch {
        return d[0] ? String(d[0]) : '-'
      }
    })
    const volumes = klineData.map((d) => d[5])

    if (!klineChart) klineChart = echarts.init(klineChartRef.value)

    const maData: Record<string, (number | null)[]> = {}
    paramsVal.ma.periods.forEach((p) => {
      maData[`ma${p}`] = calcMA(klineData, p)
    })
    const bollData = calcBOLL(klineData, paramsVal.boll.period, paramsVal.boll.multiplier)

    const series: any[] = [
      {
        name: 'K线',
        type: 'candlestick',
        data: klineData.map((d) => [d[1], d[2], d[3], d[4]]),
        itemStyle: {
          color: '#e74c3c',
          color0: '#27ae60',
          borderColor: '#e74c3c',
          borderColor0: '#27ae60',
        },
      },
    ]

    if (showMA.value) {
      const maColors = ['#f39c12', '#9b59b6', '#1abc9c', '#e67e22']
      paramsVal.ma.periods.forEach((p, idx) => {
        series.push({
          name: `MA${p}`,
          type: 'line',
          data: maData[`ma${p}`],
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 1, color: maColors[idx % maColors.length] },
        })
      })
    }

    if (showBOLL.value) {
      series.push(
        { name: 'BOLL-UP', type: 'line', data: bollData.up, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#3498db', type: 'dashed' } },
        { name: 'BOLL-MID', type: 'line', data: bollData.mid, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#3498db' } },
        { name: 'BOLL-DN', type: 'line', data: bollData.down, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#3498db', type: 'dashed' }, areaStyle: { color: 'rgba(52,152,219,0.05)' } },
      )
    }

    if (showChanlun?.value && chanlunData?.value) {
      const clData = chanlunData.value
      clData.zhongshu.forEach((zs) => {
        series.push({
          type: 'custom',
          renderItem: (_pa: any, api: any) => {
            const s = api.coord([zs.startX, zs.high])
            const e = api.coord([zs.endX, zs.low])
            return {
              type: 'group',
              children: [{ type: 'rect', shape: { x: s[0], y: s[1], width: e[0] - s[0], height: e[1] - s[1] }, style: { fill: 'rgba(41,151,255,0.12)', stroke: '#2997ff', lineWidth: 1.5, lineDash: [4, 3] } }],
            }
          },
          data: [0], z: 10,
        })
      })
      clData.bi.forEach((b) => {
        const isUp = b.y1 >= b.y0
        series.push({
          type: 'line', data: [[b.x0, b.y0], [b.x1, b.y1]], symbol: 'none',
          lineStyle: { width: 2, color: isUp ? '#e74c3c' : '#27ae60' }, z: 11,
        })
      })
      const dings = clData.fengxing.filter((f) => f.type === 'ding')
      const dis = clData.fengxing.filter((f) => f.type === 'di')
      if (dings.length) {
        series.push({
          name: '顶分型', type: 'scatter', data: dings.map((f) => [f.x, f.price]),
          symbol: 'triangle', symbolSize: [14, 10], symbolRotate: 180,
          itemStyle: { color: '#e74c3c' }, z: 12,
          label: { show: true, formatter: '顶', color: '#e74c3c', fontSize: 10, fontWeight: 'bold', position: 'top' },
        })
      }
      if (dis.length) {
        series.push({
          name: '底分型', type: 'scatter', data: dis.map((f) => [f.x, f.price]),
          symbol: 'triangle', symbolSize: [14, 10],
          itemStyle: { color: '#27ae60' }, z: 12,
          label: { show: true, formatter: '底', color: '#27ae60', fontSize: 10, fontWeight: 'bold', position: 'bottom' },
        })
      }
    }

    klineChart.setOption({
      animation: false,
      grid: { left: '8%', right: '8%', top: '12%', bottom: '15%' },
      xAxis: { type: 'category', data: dates, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { fontSize: 11, color: '#999' } },
      yAxis: { scale: true, splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } }, axisLabel: { fontSize: 11, color: '#999' } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, backgroundColor: 'rgba(30,30,30,0.9)', borderColor: 'rgba(255,255,255,0.1)', textStyle: { color: '#fff', fontSize: 12 } },
      dataZoom: [
        { type: 'inside', start: 65, end: 100, minValueSpan: 10 },
        { type: 'slider', start: 65, end: 100, height: 24, bottom: 2, backgroundColor: 'rgba(0,0,0,0.02)', fillerColor: 'rgba(41,151,255,0.25)', borderColor: 'rgba(41,151,255,0.3)', handleStyle: { color: '#2997ff', borderColor: '#2997ff', borderWidth: 2, shadowBlur: 4, shadowColor: 'rgba(41,151,255,0.3)' }, textStyle: { fontSize: 11, color: '#666' }, dataBackground: { lineStyle: { color: '#ddd', width: 1 }, areaStyle: { color: 'rgba(0,0,0,0.03)' } }, selectedDataBackground: { lineStyle: { color: '#2997ff', width: 1 }, areaStyle: { color: 'rgba(41,151,255,0.1)' } } },
      ],
      series,
    }, true)

    if (!bottomChart) bottomChart = echarts.init(bottomChartRef.value!)

    let bottomOption: echarts.EChartsOption

    if (bottomActive.value === 'macd') {
      const macdData = calcMACD(klineData, paramsVal.macd.fast, paramsVal.macd.slow, paramsVal.macd.signal)
      bottomOption = {
        animation: false, grid: { left: '8%', right: '8%', top: '15%', bottom: '6%' },
        xAxis: { type: 'category', data: dates, axisTick: { show: false }, axisLabel: { show: false } },
        yAxis: { scale: true, splitLine: { show: false }, axisLabel: { fontSize: 10, color: '#999' } },
        series: [
          { name: 'DIF', type: 'line', data: macdData.dif, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#3498db' } },
          { name: 'DEA', type: 'line', data: macdData.dea, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#e67e22' } },
          { name: 'MACD', type: 'bar', data: macdData.macd.map((v: number) => ({ value: v, itemStyle: { color: v >= 0 ? '#e74c3c' : '#27ae60', opacity: 0.6 } })), barWidth: '50%' },
        ],
      }
    } else if (bottomActive.value === 'kdj') {
      const kdjData = calcKDJ(klineData, paramsVal.kdj.period)
      bottomOption = {
        animation: false, grid: { left: '8%', right: '8%', top: '12%', bottom: '6%' },
        xAxis: { type: 'category', data: dates, axisTick: { show: false }, axisLabel: { show: false } },
        yAxis: { scale: true, splitLine: { show: false }, axisLabel: { fontSize: 10, color: '#999' } },
        series: [
          { name: 'K', type: 'line', data: kdjData.k, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#3498db' } },
          { name: 'D', type: 'line', data: kdjData.d, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#e67e22' } },
          { name: 'J', type: 'line', data: kdjData.j, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#9b59b6' } },
        ],
      }
    } else if (bottomActive.value === 'rsi') {
      const rsiData = calcRSI(klineData, paramsVal.rsi.period)
      bottomOption = {
        animation: false, grid: { left: '8%', right: '8%', top: '12%', bottom: '6%' },
        xAxis: { type: 'category', data: dates, axisTick: { show: false }, axisLabel: { show: false } },
        yAxis: { scale: false, min: 0, max: 100, splitLine: { show: false }, axisLabel: { fontSize: 10, color: '#999' } },
        series: [{
          name: 'RSI', type: 'line', data: rsiData, smooth: true, symbol: 'none',
          lineStyle: { width: 1.5, color: '#f39c12' },
          markLine: { silent: true, symbol: 'none', data: [
            { yAxis: 70, label: { show: true, formatter: '超买 70', color: '#e74c3c', position: 'insideEndTop' }, lineStyle: { color: '#e74c3c', type: 'dashed', width: 1 } },
            { yAxis: 30, label: { show: true, formatter: '超卖 30', color: '#27ae60', position: 'insideEndBottom' }, lineStyle: { color: '#27ae60', type: 'dashed', width: 1 } },
          ] },
        }],
      }
    } else {
      bottomOption = {
        animation: false, grid: { left: '8%', right: '8%', top: '10%', bottom: '4%' },
        xAxis: { type: 'category', data: dates, axisTick: { show: false }, axisLabel: { show: false } },
        yAxis: { type: 'value', splitLine: { show: false }, axisLabel: { fontSize: 10, color: '#999' } },
        series: [{
          type: 'bar',
          data: volumes.map((v, i) => ({ value: v, itemStyle: { color: klineData[i][2] >= klineData[i][1] ? '#e74c3c' : '#27ae60', opacity: 0.5 } })),
          barWidth: '60%',
        }],
      }
    }

    bottomChart.setOption(bottomOption, true)
  }

  function handleResize() {
    klineChart?.resize()
    bottomChart?.resize()
  }

  function dispose() {
    klineChart?.dispose()
    bottomChart?.dispose()
    klineChart = null
    bottomChart = null
  }

  return { renderChart, handleResize, dispose }
}
