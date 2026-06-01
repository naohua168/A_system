/**
 * 技术指标K线图渲染组合函数
 * 东方财富风格：dataZoom 索引模式，右侧永远固定为最新数据
 *
 * 关键设计：
 * - dataZoom 使用 startValue/endValue（数据索引），endValue 始终 = dataLen - 1
 * - K线主图：inside（滚轮缩放）+ slider（底部滑块）
 * - 滑块始终显示在 K线图底部（不依赖 VOL 模式）
 * - 缩放只改变 startValue，右侧永远锁死
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
  }
) {
  let klineChart: echarts.ECharts | null = null
  let bottomChart: echarts.ECharts | null = null
  let disposed = false
  let connected = false

  /** dataZoom 索引模式 — endValue 永远 = dataLen - 1 */
  let startValue = 0
  let endValue = 0    // = dataLen - 1
  let dataLen = 0

  let isSyncing = false
  let isRendering = false
  let pendingRender = false

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

      const dates = klineData.map((d) => {
        try { return new Date(d[0]).toLocaleDateString('zh-CN') }
        catch { return d[0] ? String(d[0]) : '-' }
      })
      const volumes = klineData.map((d) => d[5])

      if (!klineChart && klineChartRef.value?.isConnected) {
        try { klineChart = echarts.init(klineChartRef.value) } catch { return }
      }
      if (!klineChart) return

      const len = klineData.length
      ensureZoomState(len)

      // 全量 Y 轴范围（12% 留白，缩放不改变 Y 轴，避免越界）
      const [yMin, yMax] = calcGlobalYRange(klineData)

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
        // 1. 中枢 — markArea（比 custom series 更稳定）
        if (cld.zhongshu?.length) {
          klineSeries.markArea = {
            silent: true, animation: false, z: 10,
            data: cld.zhongshu.map((z: any, idx: number) => [
              { xAxis: z.startX, yAxis: z.high, label: { show: true, position: 'insideTopLeft', fontSize: 10, fontWeight: 'bold', color: '#3498db', formatter: `中枢${idx + 1}` } },
              { xAxis: z.endX, yAxis: z.low },
            ]),
            itemStyle: { color: 'rgba(52,152,219,0.08)', borderColor: '#3498db', borderWidth: 1.5, borderType: 'dashed' },
          }
        }

        // 2. 分型 — markPoint
        if (cld.fengxing?.length) {
          const mpData: any[] = []
          cld.fengxing.forEach((f: any, idx: number) => {
            const isDing = f.type === 'ding'
            mpData.push({
              name: isDing ? `顶${idx + 1}` : `底${idx + 1}`,
              coord: [f.x, f.price],
              symbol: 'triangle', symbolSize: 18, symbolRotate: isDing ? 180 : 0,
              itemStyle: { color: isDing ? '#ef5350' : '#26a69a' },
              label: {
                show: true,
                formatter: `{a|${isDing ? '顶' : '底'}${idx + 1}}\n{b|${Number(f.price).toFixed(2)}}`,
                rich: {
                  a: { color: isDing ? '#ef5350' : '#26a69a', fontSize: 10, fontWeight: 'bold', align: 'center' },
                  b: { color: isDing ? '#ef5350' : '#26a69a', fontSize: 9, align: 'center' },
                },
                position: isDing ? 'top' : 'bottom', distance: 6,
              },
            })
          })
          klineSeries.markPoint = { silent: true, animation: false, z: 15, data: mpData }
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

        // 4. 买卖信号
        if (cld.buy_sell_points?.length) {
          const bps = cld.buy_sell_points.filter((p: any) => (p.x ?? -1) >= 0)
          const buys = bps.filter((p: any) => p.type?.startsWith('buy_'))
          const sells = bps.filter((p: any) => p.type?.startsWith('sell_'))
          if (buys.length) {
            series.push({
              type: 'scatter', z: 16, symbol: 'pin', symbolSize: 24,
              itemStyle: { color: '#ef5350' },
              data: buys.map((p: any) => ({
                value: [p.x, p.price],
                label: { show: true, formatter: `${p.type.replace('buy_','B').toUpperCase()}\n${p.price.toFixed(2)}`, position: 'top', distance: 4, fontSize: 9, color: '#ef5350' },
              })),
            })
          }
          if (sells.length) {
            series.push({
              type: 'scatter', z: 16, symbol: 'pin', symbolSize: 24,
              itemStyle: { color: '#26a69a' },
              data: sells.map((p: any) => ({
                value: [p.x, p.price],
                label: { show: true, formatter: `${p.type.replace('sell_','S').toUpperCase()}\n${p.price.toFixed(2)}`, position: 'bottom', distance: 4, fontSize: 9, color: '#26a69a' },
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
      minValueSpan: 15,
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

    klineChart.setOption({
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
        { type: 'inside', startValue, endValue, minValueSpan: 15 },
        { type: 'slider', startValue, endValue, ...sliderStyle },
      ],
      series,
    })

    // ── dataZoom 事件：dispatchAction 强制右端固定，echarts.connect 自动同步 ──
    klineChart.off('dataZoom')
    klineChart.on('dataZoom', (params: any) => {
      try {
        if (disposed || !klineChart || klineChart.isDisposed()) return
        if (isSyncing) return
        const zoom = params.batch?.[0] ?? params
        const newSV = Number(zoom.startValue ?? startValue)
        if (newSV === startValue && (zoom.endValue ?? dataLen - 1) === dataLen - 1) return
        startValue = newSV
        endValue = dataLen - 1
        isSyncing = true
        try {
          // dispatchAction 会更新内部状态并重绘 slider，触发的 datazoom 事件被 isSyncing 锁阻挡
          klineChart.dispatchAction({
            type: 'dataZoom',
            startValue: startValue,
            endValue: dataLen - 1,
          })
        } finally {
          isSyncing = false
        }
      } catch { /* ignore zoom error */ }
    })

    // ── 底部指标图 ──
    if (!bottomChart && bottomChartRef.value?.isConnected) bottomChart = echarts.init(bottomChartRef.value)
    if (!bottomChart) return

    // 底部图 dataZoom 事件：同步到底部，dispatchAction 确保 slider 同步
    bottomChart.off('dataZoom')
    bottomChart.on('dataZoom', (params: any) => {
      try {
        if (disposed || !bottomChart || bottomChart.isDisposed()) return
        if (isSyncing) return
        const zoom = params.batch?.[0] ?? params
        const newSV = Number(zoom.startValue ?? startValue)
        if (newSV === startValue && (zoom.endValue ?? dataLen - 1) === dataLen - 1) return
        startValue = newSV
        endValue = dataLen - 1
        isSyncing = true
        try {
          if (!klineChart || klineChart.isDisposed()) return
          klineChart.dispatchAction({
            type: 'dataZoom',
            startValue: startValue,
            endValue: dataLen - 1,
          })
        } finally {
          isSyncing = false
        }
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

    // ── echarts.connect 双图缩放同步 ──
    if (!connected && klineChart && bottomChart && !klineChart.isDisposed() && !bottomChart.isDisposed()) {
      try {
        (echarts as any).connect([klineChart, bottomChart])
        connected = true
      } catch { /* ignore connect error */ }
    }
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
    connected = false
  }

  return { renderChart, handleResize, dispose, setChanlunData }
}
