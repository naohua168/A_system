/**
 * 技术指标计算模块
 * 用于 K 线图叠加指标和底部指标计算（纯前端计算，基于 OHLCV 数据）
 *
 * 数据格式约定: number[][] where each row is:
 *   [timestamp, open, close, low, high, volume]
 */

/** 移动平均线 (MA) */
export function calcMA(data: number[][], days: number): (number | null)[] {
  const result: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (i < days - 1) { result.push(null); continue }
    let sum = 0
    for (let j = i - days + 1; j <= i; j++) sum += (data[j][2] + data[j][3]) / 2
    result.push(+(sum / days).toFixed(2))
  }
  return result
}

export interface BOLLResult {
  up: (number | null)[]
  mid: (number | null)[]
  down: (number | null)[]
}

/** 布林带 (BOLL) */
export function calcBOLL(data: number[][], period = 20, k = 2): BOLLResult {
  const mid = calcMA(data, period)
  const up: (number | null)[] = []
  const down: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (mid[i] === null) { up.push(null); down.push(null); continue }
    let sum = 0
    for (let j = i - period + 1; j <= i; j++) {
      const avg = (data[j][2] + data[j][3]) / 2
      sum += (avg - (mid[i] as number)) ** 2
    }
    const std = Math.sqrt(sum / period)
    up.push(parseFloat(((mid[i] as number) + k * std).toFixed(2)))
    down.push(parseFloat(((mid[i] as number) - k * std).toFixed(2)))
  }
  return { up, mid, down }
}

export interface MACDResult {
  dif: number[]
  dea: number[]
  macd: number[]
}

/** MACD 指标 */
export function calcMACD(data: number[][], fast = 12, slow = 26, signal = 9): MACDResult {
  const closes = data.map(d => (d[2] + d[3]) / 2)
  const emaF: number[] = []
  const emaS: number[] = []
  const dif: number[] = []
  const dea: number[] = []
  const macd: number[] = []

  for (let i = 0; i < closes.length; i++) {
    if (i === 0) {
      emaF[i] = closes[i]
      emaS[i] = closes[i]
    } else {
      emaF[i] = emaF[i - 1] * (fast - 1) / (fast + 1) + closes[i] * 2 / (fast + 1)
      emaS[i] = emaS[i - 1] * (slow - 1) / (slow + 1) + closes[i] * 2 / (slow + 1)
    }
    dif[i] = emaF[i] - emaS[i]
    dea[i] = i === 0 ? dif[i] : dea[i - 1] * (signal - 1) / (signal + 1) + dif[i] * 2 / (signal + 1)
    macd[i] = (dif[i] - dea[i]) * 2
  }

  return {
    dif: dif.map(v => +v.toFixed(4)),
    dea: dea.map(v => +v.toFixed(4)),
    macd: macd.map(v => +v.toFixed(4)),
  }
}

export interface KDJResult {
  k: number[]
  d: number[]
  j: number[]
}

/** KDJ 指标 */
export function calcKDJ(data: number[][], period = 9): KDJResult {
  const kV: number[] = []
  const dV: number[] = []
  const jV: number[] = []

  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) { kV.push(50); dV.push(50); jV.push(50); continue }

    const window = data.slice(i - period + 1, i + 1)
    const low = Math.min(...window.map(d => d[3]))
    const high = Math.max(...window.map(d => d[1]))
    const close = data[i][2]
    const rsv = ((close - low) / (high - low)) * 100

    const k = kV[i - 1] || 50
    const kVal = k * 2 / 3 + rsv / 3
    const dVal = (dV[i - 1] || 50) * 2 / 3 + kVal / 3

    kV.push(+kVal.toFixed(1))
    dV.push(+dVal.toFixed(1))
    jV.push(+(3 * kVal - 2 * dVal).toFixed(1))
  }

  return { k: kV, d: dV, j: jV }
}

/** RSI 指标 */
export function calcRSI(data: number[][], period = 14): (number | null)[] {
  const closes = data.map(d => d[2])
  const rsi: (number | null)[] = []

  for (let i = 0; i < closes.length; i++) {
    if (i < period) { rsi.push(null); continue }

    let gains = 0, losses = 0
    for (let j = i - period + 1; j <= i; j++) {
      const diff = closes[j] - closes[j - 1]
      if (diff > 0) gains += diff
      else losses -= diff
    }

    const rs = gains / (losses || 0.001)
    rsi.push(+((100 - 100 / (1 + rs)).toFixed(1)))
  }

  return rsi
}
