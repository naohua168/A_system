/**
 * 技术指标K线图渲染组合函数
 * 同花顺风格：dark professional、轻网格线、dataZoom 滑块、scale Y轴
 */
import { ref, onBeforeUnmount, type Ref } from 'vue'
import echarts from '@/utils/echarts'
import { calcMA, calcBOLL, calcMACD, calcKDJ, calcRSI } from '@/utils/indicators'
import type { ChanlunAnalysis } from '@/types'
import type { IndicatorParams } from '@/types'

export function useTechnicalChart(
  klineChartRef: Ref<HTMLElement | undefined>,
  bottomChartRef: Ref<HTMLElement | undefined>,
  options: {
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
  let disposed = false
  let zoomState = { start: 70, end: 100 }
  let isSyncing = false

  /** 双向同步 dataZoom：防止事件循环 */
  function syncZoom(start: number, end: number, source: 'kline' | 'bottom') {
    if (isSyncing || disposed) return
    isSyncing = true
    try {
      zoomState = { start, end }
      if (source !== 'kline' && klineChart && !klineChart.isDisposed() &&
          klineChartRef.value?.isConnected && klineChartRef.value?.offsetParent) {
        klineChart.setOption({ dataZoom: [{ start, end }] }, false)
      }
      if (source !== 'bottom' && bottomChart && !bottomChart.isDisposed() &&
          bottomChartRef.value?.isConnected && bottomChartRef.value?.offsetParent) {
        const isVol = options.bottomActive.value === null
        if (isVol) {
          bottomChart.setOption({ dataZoom: [
            { type: 'inside', start, end },
            { type: 'slider', start, end, height: 22, bottom: 1,
              minValueSpan: 15, maxValueSpan: 80,
              borderColor: '#e0e0e0', backgroundColor: '#fafafa',
              fillerColor: 'rgba(41,151,255,0.25)',
              handleSize: '100%',
              handleStyle: { color: '#fff', borderColor: '#aaa', borderWidth: 1.5 },
              textStyle: { fontSize: 10, color: '#888' },
              showDataShadow: false, showDetail: false,
              dataBackground: { lineStyle: { color: '#ccc', width: 1 }, areaStyle: { color: 'rgba(0,0,0,0.03)' } },
              selectedDataBackground: { lineStyle: { color: '#2997ff', width: 1.5 }, areaStyle: { color: 'rgba(41,151,255,0.12)' } },
            },
          ]}, false)
        } else {
          bottomChart.setOption({ dataZoom: [{ start, end }] }, false)
        }
      }
    } catch { /* ignore sync errors */ }
    finally { isSyncing = false }
  }

  /** 计算 K 线数据的 OHLC 范围（仅基于 low/high），避开均线历史值对 Y 轴的影响 */
  function calcVisibleYRange(data: number[][], startPct: number, endPct: number) {
    const len = data.length
    const si = Math.max(0, Math.floor(len * startPct / 100))
    const ei = Math.min(len, Math.ceil(len * endPct / 100))
    let mn = Infinity, mx = -Infinity
    for (let i = si; i < ei; i++) {
      const d = data[i]
      if (!d) continue
      if (d[3] < mn) mn = d[3]
      if (d[4] > mx) mx = d[4]
    }
    if (mn === Infinity) return [0, 100]
    const pad = (mx - mn) * 0.08 || 1
    return [
      Math.floor((mn - pad) * 100) / 100,
      Math.ceil((mx + pad) * 100) / 100,
    ]
  }

  function renderChart() {
    try {
      if (disposed || !klineChartRef.value || !bottomChartRef.value) return
      let klineData = options.getKlineData()
      if (klineData.length === 0) return
      // 按时间戳升序（从左到右从早到晚）
      if (klineData[0][0] > klineData[klineData.length - 1][0]) {
        klineData = [...klineData].sort((a, b) => a[0] - b[0])
      }

      const paramsVal = 'value' in (options.params as any)
        ? (options.params as Ref<IndicatorParams>).value
        : options.params as IndicatorParams
      const { showMA, showBOLL, bottomActive, chanlunData, showChanlun } = options

      const dates = klineData.map((d) => {
        try { return new Date(d[0]).toLocaleDateString('zh-CN') }
        catch { return d[0] ? String(d[0]) : '-' }
      })
      const volumes = klineData.map((d) => d[5])

      if (!klineChart && klineChartRef.value?.isConnected) klineChart = echarts.init(klineChartRef.value)
      if (!klineChart) return

      const dataLen = klineData.length
      // 用可见K线OHLC算Y轴范围（只取low/high），排除均线历史值拉宽
      const [yMin, yMax] = calcVisibleYRange(klineData, zoomState.start, zoomState.end)

    const maData: Record<string, (number | null)[]> = {}
    paramsVal.ma.periods.forEach((p) => { maData[`ma${p}`] = calcMA(klineData, p) })
    const bollData = calcBOLL(klineData, paramsVal.boll.period, paramsVal.boll.multiplier)

    const series: any[] = [
      {
        name: 'K线',
        type: 'candlestick',
        data: klineData.map((d) => [d[1], d[2], d[3], d[4]]),
        itemStyle: {
          color: '#e74c3c', color0: '#27ae60',
          borderColor: '#e74c3c', borderColor0: '#27ae60',
          borderWidth: 1.5,
        },
        barWidth: '60%',
      },
    ]

    if (showMA.value) {
      const maColors = ['#f39c12', '#9b59b6', '#1abc9c', '#e67e22']
      paramsVal.ma.periods.forEach((p, idx) => {
        series.push({
          name: `MA${p}`, type: 'line', data: maData[`ma${p}`],
          connectNulls: true, smooth: true, symbol: 'none',
          lineStyle: { width: 1.2, color: maColors[idx % maColors.length] },
        })
      })
    }

    if (showBOLL.value) {
      series.push(
        { name: 'BOLL-UP', type: 'line', data: bollData.up, connectNulls: true, smooth: true, symbol: 'none', lineStyle: { width: 0.8, color: '#3498db', type: 'dashed' } },
        { name: 'BOLL-MID', type: 'line', data: bollData.mid, connectNulls: true, smooth: true, symbol: 'none', lineStyle: { width: 0.8, color: '#3498db' } },
        { name: 'BOLL-DN', type: 'line', data: bollData.down, connectNulls: true, smooth: true, symbol: 'none', lineStyle: { width: 0.8, color: '#3498db', type: 'dashed' }, areaStyle: { color: 'rgba(52,152,219,0.06)' } },
      )
    }

    if (showChanlun?.value && chanlunData?.value) {
      const cld = chanlunData.value
      cld.zhongshu.forEach((zs) => {
        series.push({
          type: 'custom',
          renderItem: (_pa: any, api: any) => {
            const s = api.coord([zs.startX, zs.high])
            const e = api.coord([zs.endX, zs.low])
            return { type: 'group', children: [{ type: 'rect', shape: { x: s[0], y: s[1], width: e[0] - s[0], height: e[1] - s[1] }, style: { fill: 'rgba(52,152,219,0.08)', stroke: '#3498db', lineWidth: 1, lineDash: [4, 3] } }] }
          }, data: [0], z: 10,
        })
      })
      cld.bi.forEach((b) => {
        const isUp = b.y1 >= b.y0
        series.push({ type: 'line', data: [[b.x0, b.y0], [b.x1, b.y1]], symbol: 'none', lineStyle: { width: 1.5, color: isUp ? '#ef5350' : '#26a69a' }, z: 11 })
      })
      const dings = cld.fengxing.filter((f) => f.type === 'ding')
      const dis = cld.fengxing.filter((f) => f.type === 'di')
      if (dings.length) {
        series.push({ name: '顶分型', type: 'scatter', data: dings.map((f) => [f.x, f.price]), symbol: 'triangle', symbolSize: [14, 10], symbolRotate: 180, itemStyle: { color: '#ef5350' }, z: 12, label: { show: true, formatter: '顶', color: '#ef5350', fontSize: 10, fontWeight: 'bold', position: 'top' } })
      }
      if (dis.length) {
        series.push({ name: '底分型', type: 'scatter', data: dis.map((f) => [f.x, f.price]), symbol: 'triangle', symbolSize: [14, 10], itemStyle: { color: '#26a69a' }, z: 12, label: { show: true, formatter: '底', color: '#26a69a', fontSize: 10, fontWeight: 'bold', position: 'bottom' } })
      }
    }

    klineChart.setOption({
      animation: false,
      grid: { left: 60, right: 20, top: 20, bottom: 20 },
      xAxis: {
        type: 'category', data: dates,
        axisLine: { lineStyle: { color: '#ddd' } },
        axisTick: { show: false },
        axisLabel: { fontSize: 10, color: '#999', hideOverlap: true, interval: 'auto' },
        splitLine: { show: false },
      },
      yAxis: {
        min: yMin, max: yMax,
        splitLine: { lineStyle: { color: 'rgba(200,200,210,0.35)', type: 'dashed' } },
        axisLabel: { fontSize: 10, color: '#888' },
      },
      tooltip: {
        trigger: 'axis', axisPointer: { type: 'cross', crossStyle: { color: '#ccc' }, label: { backgroundColor: '#666', color: '#fff' } },
        backgroundColor: 'rgba(255,255,255,0.95)', borderColor: '#ddd', borderWidth: 1,
        textStyle: { color: '#333', fontSize: 12 },
      },
      dataZoom: [
        { type: 'inside', start: zoomState.start, end: zoomState.end, minValueSpan: 15, maxValueSpan: 80 },
      ],
      series,
    }, true)

    // 缩放时更新 Y 轴范围，双向同步底部图
    klineChart.off('dataZoom')
    klineChart.on('dataZoom', (params: any) => {
      try {
        if (disposed || !klineChartRef.value || !klineChart || klineChart.isDisposed()) return
        const zoom = params.batch?.[0] ?? params
        const start = (zoom.start ?? zoomState.start) as number
        const end = (zoom.end ?? zoomState.end) as number
        const [newMin, newMax] = calcVisibleYRange(klineData, start, end)
        if (!isSyncing && klineChart && !klineChart.isDisposed()) {
          klineChart.setOption({ yAxis: { min: newMin, max: newMax } }, false)
        }
        syncZoom(start, end, 'kline')
      } catch { /* ignore zoom error */ }
    })

    // ── 底部指标图 ──
    if (!bottomChart && bottomChartRef.value?.isConnected) bottomChart = echarts.init(bottomChartRef.value)
    if (!bottomChart) return

    // slider 样式统一配置（仅 VOL 量能柱模式使用）
    const volSlider = {
      type: 'slider' as const, start: zoomState.start, end: zoomState.end,
      height: 22, bottom: 1,
      minValueSpan: 15, maxValueSpan: 80,
      borderColor: '#e0e0e0', backgroundColor: '#fafafa',
      fillerColor: 'rgba(41,151,255,0.25)',
      handleSize: '100%',
      handleStyle: { color: '#fff' as const, borderColor: '#aaa' as const, borderWidth: 1.5 },
      textStyle: { fontSize: 10, color: '#888' as const },
      showDataShadow: false,
      showDetail: false,
      dataBackground: { lineStyle: { color: '#ccc' as const, width: 1 }, areaStyle: { color: 'rgba(0,0,0,0.03)' as const } },
      selectedDataBackground: { lineStyle: { color: '#2997ff' as const, width: 1.5 }, areaStyle: { color: 'rgba(41,151,255,0.12)' as const } },
    }

    const bottomDataZooom = [{ type: 'inside' as const, start: zoomState.start, end: zoomState.end }]

    let bottomOption: echarts.EChartsOption
    if (bottomActive.value === 'macd') {
      const macdData = calcMACD(klineData, paramsVal.macd.fast, paramsVal.macd.slow, paramsVal.macd.signal)
      bottomOption = {
        animation: false, grid: { left: '7%', right: '7%', top: '12%', bottom: '4%' },
        xAxis: { type: 'category', data: dates, axisTick: { show: false }, axisLabel: { show: false }, axisLine: { show: false }, splitLine: { show: false } },
        yAxis: { scale: true, splitLine: { show: false }, axisLabel: { fontSize: 9, color: '#999' } },
        dataZoom: bottomDataZooom,
        series: [
          { name: 'DIF', type: 'line', data: macdData.dif, smooth: true, symbol: 'none', lineStyle: { width: 0.8, color: '#3498db' } },
          { name: 'DEA', type: 'line', data: macdData.dea, smooth: true, symbol: 'none', lineStyle: { width: 0.8, color: '#e67e22' } },
          { name: 'MACD', type: 'bar', data: macdData.macd.map((v: number) => ({ value: v, itemStyle: { color: v >= 0 ? '#ef5350' : '#26a69a', opacity: 0.5 } })), barWidth: '50%' },
        ],
      }
    } else if (bottomActive.value === 'kdj') {
      const kdjData = calcKDJ(klineData, paramsVal.kdj.period, paramsVal.kdj.m1, paramsVal.kdj.m2)
      bottomOption = {
        animation: false, grid: { left: '7%', right: '7%', top: '10%', bottom: '4%' },
        xAxis: { type: 'category', data: dates, axisTick: { show: false }, axisLabel: { show: false }, axisLine: { show: false }, splitLine: { show: false } },
        yAxis: { scale: true, splitLine: { show: false }, axisLabel: { fontSize: 9, color: '#999' } },
        dataZoom: bottomDataZooom,
        series: [
          { name: 'K', type: 'line', data: kdjData.k, smooth: true, symbol: 'none', lineStyle: { width: 0.8, color: '#3498db' } },
          { name: 'D', type: 'line', data: kdjData.d, smooth: true, symbol: 'none', lineStyle: { width: 0.8, color: '#e67e22' } },
          { name: 'J', type: 'line', data: kdjData.j, smooth: true, symbol: 'none', lineStyle: { width: 0.8, color: '#9b59b6' } },
        ],
      }
    } else if (bottomActive.value === 'rsi') {
      const rsiData = calcRSI(klineData, paramsVal.rsi.period)
      bottomOption = {
        animation: false, grid: { left: '7%', right: '7%', top: '10%', bottom: '4%' },
        xAxis: { type: 'category', data: dates, axisTick: { show: false }, axisLabel: { show: false }, axisLine: { show: false }, splitLine: { show: false } },
        yAxis: { scale: false, min: 0, max: 100, splitLine: { show: false }, axisLabel: { fontSize: 9, color: '#999' } },
        dataZoom: bottomDataZooom,
        series: [{
          name: 'RSI', type: 'line', data: rsiData, smooth: true, symbol: 'none',
          lineStyle: { width: 1, color: '#e67e22' },
          markLine: { silent: true, symbol: 'none', data: [
            { yAxis: 70, label: { show: true, formatter: '70', color: '#e74c3c', position: 'insideEndTop', fontSize: 9 }, lineStyle: { color: '#e74c3c', type: 'dashed', width: 0.8 } },
            { yAxis: 30, label: { show: true, formatter: '30', color: '#27ae60', position: 'insideEndBottom', fontSize: 9 }, lineStyle: { color: '#27ae60', type: 'dashed', width: 0.8 } },
          ] },
        }],
      }
    } else {
      // VOL 量能柱模式：包含 slider 滑块
      bottomOption = {
        animation: false, grid: { left: '7%', right: '7%', top: '4%', bottom: '26%' },
        xAxis: { type: 'category', data: dates, axisTick: { show: false }, axisLabel: { show: false }, axisLine: { show: false }, splitLine: { show: false } },
        yAxis: { type: 'value', splitLine: { show: false }, axisLabel: { fontSize: 9, color: '#999' } },
        dataZoom: [...bottomDataZooom, volSlider] as any,
        series: [{
          type: 'bar',
          barMinHeight: 1,
          data: volumes.map((v, i) => ({ value: v, itemStyle: { color: klineData[i][2] >= klineData[i][1] ? '#e74c3c' : '#27ae60', opacity: 0.5 } })),
          barWidth: '55%',
        }],
      }
    }
    bottomChart.setOption(bottomOption, true)

    // 底部图 dataZoom 事件 → 反向同步到 K线图
    bottomChart.off('dataZoom')
    bottomChart.on('dataZoom', (params: any) => {
      try {
        if (disposed || !bottomChartRef.value || !bottomChart || bottomChart.isDisposed()) return
        const zoom = params.batch?.[0] ?? params
        const start = (zoom.start ?? zoomState.start) as number
        const end = (zoom.end ?? zoomState.end) as number
        syncZoom(start, end, 'bottom')
      } catch { /* ignore bottom zoom error */ }
    })
  } catch (e) { console.warn('[Chart] render error:', e) }
  }

  function handleResize() {
    try {
      if (disposed) return
      if (klineChart && !klineChart.isDisposed() &&
          klineChartRef.value?.isConnected && klineChartRef.value?.offsetParent) {
        klineChart.resize()
      }
      if (bottomChart && !bottomChart.isDisposed() &&
          bottomChartRef.value?.isConnected && bottomChartRef.value?.offsetParent) {
        bottomChart.resize()
      }
    } catch { /* ignore resize errors */ }
  }

  function dispose() {
    disposed = true
    try {
      if (klineChart) {
        klineChart.off('dataZoom')
        klineChart.dispose()
      }
      if (bottomChart) {
        bottomChart.off('dataZoom')
        bottomChart.dispose()
      }
    } catch { /* ignore dispose errors */ }
    klineChart = null
    bottomChart = null
  }

  return { renderChart, handleResize, dispose }
}
