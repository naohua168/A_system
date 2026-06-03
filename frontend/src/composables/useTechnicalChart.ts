/**
 * 技术指标K线图渲染组合函数
 * 东方财富风格：dataZoom 索引模式，最小显示30根K线防止过度拉伸
 *
 * 关键设计：
 * - dataZoom 使用 startValue/endValue（数据索引），默认显示最新70%
 * - K线主图：inside（滚轮缩放）+ slider（底部滑块）
 * - 滑块始终显示在 K线图底部（不依赖 VOL 模式）
 * - minValueSpan=30 限制最小可见K线数量，避免过度放大成直线
 * - 缠论数据通过 setChanlunData() 独立设置，不依赖 Vue ref 传递
 */
import { type Ref } from 'vue'
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
    period?: Ref<string>           // 当前周期：day/week/month/5min/15min/30min/60min
  }
) {
  let klineChart: echarts.ECharts | null = null
  let bottomChart: echarts.ECharts | null = null
  let disposed = false

  /** dataZoom 索引模式 */
  let startValue = 0
  let endValue = 0
  let dataLen = 0

  let isSyncing = false
  let isRendering = false
  let pendingRender = false
  let isInitialRender = true

  /** 缠论数据（内部状态，不依赖 Vue ref 传递） */
  let internalChanlunData: ChanlunAnalysis | null = null
  let internalChanlunVisible = false

  /** 设置缠论数据并立刻触发重绘 */
  function setChanlunData(data: ChanlunAnalysis | null, visible: boolean) {
    internalChanlunData = data
    internalChanlunVisible = visible
    renderChart()
  }

  /** 按数据长度初始化/调整 zoom 状态 */
  function ensureZoomState(len: number) {
    if (len === dataLen) return
    if (dataLen === 0) {
      startValue = Math.max(0, Math.floor(len * 0.7))
    } else {
      startValue = Math.round(startValue / dataLen * len)
    }
    endValue = len - 1
    dataLen = len
  }

  /** 计算全量 K 线数据的 Y 轴范围 */
  function calcGlobalYRange(data: number[][]) {
    let mn = Infinity, mx = -Infinity
    for (const d of data) {
      if (!d) continue
      if (d[3] < mn) mn = d[3]
      if (d[4] > mx) mx = d[4]
    }
    if (mn === Infinity) return [0, 100]
    const range = mx - mn
    const pad = range * 0.12 || 1
    return [
      Math.floor((mn - pad) * 100) / 100,
      Math.ceil((mx + pad) * 100) / 100,
    ]
  }

  function renderChart() {
    if (isRendering) {
      pendingRender = true
      return
    }
    doRender()
  }

  function doRender() {
    isRendering = true
    try {
      if (disposed || !klineChartRef.value || !bottomChartRef.value) return
      let klineData = options.getKlineData()
      if (klineData.length === 0) return
      if (klineData[0][0] > klineData[klineData.length - 1][0]) {
        klineData = [...klineData].sort((a, b) => a[0] - b[0])
      }

      const paramsVal = 'value' in (options.params as any)
        ? (options.params as Ref<IndicatorParams>).value
        : options.params as IndicatorParams
      const { showMA, showBOLL, bottomActive } = options

      const periodVal = options.period?.value || 'day'
      const isMinute = ['5min', '15min', '30min', '60min'].includes(periodVal)
      const isMonth = periodVal === 'month'

      const dates = klineData.map((d) => {
        try {
          const dt = new Date(d[0])
          if (isMinute) {
            // 分钟K线 → HH:MM
            return `${String(dt.getHours()).padStart(2,'0')}:${String(dt.getMinutes()).padStart(2,'0')}`
          }
          if (isMonth) {
            // 月K线 → YYYY/MM
            return `${dt.getFullYear()}/${String(dt.getMonth()+1).padStart(2,'0')}`
          }
          // 日/周K线 → M/D
          return `${dt.getMonth()+1}/${dt.getDate()}`
        }
        catch { return d[0] ? String(d[0]) : '-' }
      })
      const volumes = klineData.map((d) => d[5])

      // v-if 隐藏后重建了 DOM，需要重新 init
      if (klineChart) {
        try {
          const dom = klineChart.getDom()
          if (!dom || !(dom as HTMLElement).isConnected) {
            klineChart.dispose()
            klineChart = null
          }
        } catch { klineChart = null }
      }
      if (!klineChart && klineChartRef.value?.isConnected) {
        try { klineChart = echarts.init(klineChartRef.value) } catch { return }
      }
      if (!klineChart) return

      const len = klineData.length
      ensureZoomState(len)

      // Y 轴由 scale:true 自动根据可见数据调整，无需手动计算

    const maData: Record<string, (number | null)[]> = {}
    paramsVal.ma.periods.forEach((p) => { maData[`ma${p}`] = calcMA(klineData, p) })
    const bollData = calcBOLL(klineData, paramsVal.boll.period, paramsVal.boll.multiplier)

    // ── K线（将在初始化后追加缠论 mark） ──
    const klineSeries: any = {
      name: 'K线', type: 'candlestick',
      data: klineData.map((d) => [d[1], d[2], d[3], d[4]]),
      itemStyle: {
        color: '#e74c3c', color0: '#27ae60',
        borderColor: '#e74c3c', borderColor0: '#27ae60',
        borderWidth: 1.5,
      },
      barWidth: '60%',
    }

    const series: any[] = [klineSeries]

    // ── 缠论渲染（中枢 markArea + 分型 markPoint + 笔线 line + 买卖信号 scatter）──
    if (internalChanlunVisible && internalChanlunData) {
      const cld = internalChanlunData
      try {
        // 1. 中枢 — markArea（仅虚线框，不显示编号文字保持简约）
        if (cld.zhongshu?.length) {
          klineSeries.markArea = {
            silent: true, animation: false, z: 10,
            data: cld.zhongshu.map((z: any) => [
              { xAxis: z.startX, yAxis: z.high, label: { show: false } },
              { xAxis: z.endX, yAxis: z.low },
            ]),
            itemStyle: { color: 'rgba(52,152,219,0.05)', borderColor: '#3498db', borderWidth: 1, borderType: 'dashed' },
          }
        }

        // 2. 分型 — markPoint（极小圆点，不显示任何文字）
        if (cld.fengxing?.length) {
          klineSeries.markPoint = {
            silent: true, animation: false, z: 15,
            symbol: 'circle', symbolSize: 4,
            itemStyle: { color: '#666' },
            data: cld.fengxing.map((f: any) => ({
              coord: [f.x, f.price],
              label: { show: false },
            })),
          }
        }

        // 3. 笔线
        if (cld.bi?.length) {
          cld.bi.forEach((b: any) => {
            series.push({
              type: 'line',
              data: [[b.x0, b.y0], [b.x1, b.y1]],
              symbol: 'none',
              lineStyle: { width: 2, color: b.y1 >= b.y0 ? '#ef5350' : '#26a69a' },
              z: 11,
            })
          })
        }

        // 4. 买卖信号（简约风格：小圆点 + 单字母标签）
        if (cld.buy_sell_points?.length) {
          const bps = cld.buy_sell_points.filter((p: any) => (p.x ?? -1) >= 0)
          const buys = bps.filter((p: any) => p.type?.startsWith('buy_'))
          const sells = bps.filter((p: any) => p.type?.startsWith('sell_'))
          if (buys.length) {
            series.push({
              type: 'scatter', z: 16, symbol: 'circle', symbolSize: 8,
              itemStyle: { color: '#ef5350' },
              data: buys.map((p: any) => ({
                value: [p.x, p.price],
                label: { show: true, formatter: 'B', position: 'top', distance: 2, fontSize: 10, fontWeight: 'bold', color: '#ef5350' },
              })),
            })
          }
          if (sells.length) {
            series.push({
              type: 'scatter', z: 16, symbol: 'circle', symbolSize: 8,
              itemStyle: { color: '#26a69a' },
              data: sells.map((p: any) => ({
                value: [p.x, p.price],
                label: { show: true, formatter: 'S', position: 'bottom', distance: 2, fontSize: 10, fontWeight: 'bold', color: '#26a69a' },
              })),
            })
          }
        }
      } catch (e) {
        console.warn('[Chart] 缠论 series 构建失败:', e)
      }
    }

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

    // ── 东方财富风格：底部滑块 + 滚轮缩放 ──
    const sliderStyle = {
      height: 24, bottom: 8, left: 56, right: 16,
      minValueSpan: 30,
      borderColor: '#e0e0e0', backgroundColor: '#fafafa',
      fillerColor: 'rgba(41,151,255,0.25)',
      handleSize: '100%',
      handleStyle: { color: '#fff', borderColor: '#aaa', borderWidth: 1.5 },
      textStyle: { fontSize: 10, color: '#888' },
      showDataShadow: false, showDetail: false,
      dataBackground: { lineStyle: { color: '#ccc', width: 1 }, areaStyle: { color: 'rgba(0,0,0,0.03)' } },
      selectedDataBackground: { lineStyle: { color: '#2997ff', width: 1.5 }, areaStyle: { color: 'rgba(41,151,255,0.12)' } },
    }

    // 先移除旧 dataZoom 事件，再 setOption（避免旧 handler 在渲染期间干扰）
    klineChart.off('dataZoom')

    // 触论/指标开关不需要重置 zoom
    const opt: any = {
      animation: false,
      grid: { left: 60, right: 20, top: 20, bottom: 52 },
      xAxis: {
        type: 'category', data: dates,
        axisLine: { lineStyle: { color: '#ddd' } },
        axisTick: { show: false },
        axisLabel: { fontSize: 10, color: '#999', hideOverlap: true, interval: 'auto' },
        splitLine: { show: false },
      },
      yAxis: {
        scale: true,  // Y轴自动跟随可见数据范围（同花顺风格）
        splitLine: { lineStyle: { color: 'rgba(200,200,210,0.35)', type: 'dashed' } },
        axisLabel: { fontSize: 10, color: '#888' },
      },
      tooltip: {
        trigger: 'axis', confine: true,
        axisPointer: { type: 'cross', crossStyle: { color: '#ccc' }, label: { backgroundColor: '#666', color: '#fff' } },
        backgroundColor: 'rgba(255,255,255,0.95)', borderColor: '#ddd', borderWidth: 1,
        textStyle: { color: '#333', fontSize: 12 },
      },
      dataZoom: [
        { type: 'inside', startValue, endValue, minValueSpan: 30 },
        { type: 'slider', startValue, endValue, ...sliderStyle },
      ],
      series,
    }

    // 始终用 notMerge 全量替换（replaceMerge 与 candlestick 数据变更不兼容）
    klineChart.setOption(opt, { notMerge: true })
    isInitialRender = false

    // ── dataZoom 事件：双向手动同步，不锁定右端让缩放自然 ──
    klineChart.off('dataZoom')
    klineChart.on('dataZoom', (params: any) => {
      try {
        if (disposed || !klineChart || klineChart.isDisposed()) return
        if (isSyncing) return
        const zoom = params.batch?.[0] ?? params
        const newSV = Number(zoom.startValue ?? startValue)
        const newEV = Number(zoom.endValue ?? endValue)
        if (newSV === startValue && newEV === endValue) return
        startValue = newSV
        endValue = newEV
        isSyncing = true
        try {
          const dz = { type: 'dataZoom' as const, startValue, endValue }
          if (bottomChart && !bottomChart.isDisposed()) bottomChart.dispatchAction(dz)
        } finally { isSyncing = false }
      } catch { /* ignore zoom error */ }
    })

    // ── 底部指标图 ──
    if (bottomChart) {
      try {
        const dom = bottomChart.getDom()
        if (!dom || !(dom as HTMLElement).isConnected) {
          bottomChart.dispose()
          bottomChart = null
        }
      } catch { bottomChart = null }
    }
    if (!bottomChart && bottomChartRef.value?.isConnected) bottomChart = echarts.init(bottomChartRef.value)
    if (!bottomChart) return

    // 底部图 dataZoom → K线图（同样不锁定右端）
    bottomChart.off('dataZoom')
    bottomChart.on('dataZoom', (params: any) => {
      try {
        if (disposed || !bottomChart || bottomChart.isDisposed()) return
        if (isSyncing) return
        const zoom = params.batch?.[0] ?? params
        const newSV = Number(zoom.startValue ?? startValue)
        const newEV = Number(zoom.endValue ?? endValue)
        if (newSV === startValue && newEV === endValue) return
        startValue = newSV
        endValue = newEV
        isSyncing = true
        try {
          if (!klineChart || klineChart.isDisposed()) return
          klineChart.dispatchAction({ type: 'dataZoom' as const, startValue, endValue })
        } finally { isSyncing = false }
      } catch { /* ignore zoom error */ }
    })

    // 底部图 dataZoom：只需 inside，echarts.connect 自动同步
    const botDZ = [{ type: 'inside' as const }]
    let bottomOption: echarts.EChartsOption
    if (bottomActive.value === 'macd') {
      const macdData = calcMACD(klineData, paramsVal.macd.fast, paramsVal.macd.slow, paramsVal.macd.signal)
      bottomOption = {
        animation: false, grid: { left: '7%', right: '7%', top: '12%', bottom: '4%' },
        xAxis: { type: 'category', data: dates, axisTick: { show: false }, axisLabel: { show: false }, axisLine: { show: false }, splitLine: { show: false } },
        yAxis: { scale: true, splitLine: { show: false }, axisLabel: { fontSize: 9, color: '#999' } },
        dataZoom: botDZ,
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
        dataZoom: botDZ,
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
        dataZoom: botDZ,
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
      // VOL 量能柱
      bottomOption = {
        animation: false, grid: { left: '7%', right: '7%', top: '4%', bottom: '4%' },
        xAxis: { type: 'category', data: dates, axisTick: { show: false }, axisLabel: { show: false }, axisLine: { show: false }, splitLine: { show: false } },
        yAxis: { type: 'value', splitLine: { show: false }, axisLabel: { fontSize: 9, color: '#999' } },
        dataZoom: botDZ,
        series: [{
          type: 'bar', barMinHeight: 1,
          data: volumes.map((v, i) => ({ value: v, itemStyle: { color: klineData[i][2] >= klineData[i][1] ? '#e74c3c' : '#27ae60', opacity: 0.5 } })),
          barWidth: '55%',
        }],
      }
    }
    bottomChart.setOption(bottomOption)

  } catch (e) { console.warn('[Chart] render error:', e) }
  finally {
    isRendering = false
    if (pendingRender) {
      pendingRender = false
      renderChart()
    }
  }
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

  return { renderChart, handleResize, dispose, setChanlunData }
}
