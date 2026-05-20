/**
 * 技术指标计算函数单元测试
 *
 * 测试 calcMA / calcBOLL / calcMACD / calcKDJ / calcRSI
 */
import { describe, it, expect } from 'vitest'
import {
  calcMA, calcBOLL, calcMACD, calcKDJ, calcRSI,
} from '@/utils/indicators'

/**
 * 生成模拟K线数据
 * 格式: [timestamp, open, close, low, high, volume]
 */
function makeKline(closePrices: number[], startTs = 1700000000000): number[][] {
  return closePrices.map((c, i) => [
    startTs + i * 86400000,  // timestamp
    c * 0.99,                // open
    c,                       // close
    c * 0.98,                // low
    c * 1.01,                // high
    1000000,                 // volume
  ])
}

describe('calcMA', () => {
  it('MA5 - 正常计算', () => {
    const data = makeKline([10, 11, 12, 13, 14, 15, 16, 17, 18, 19])
    const result = calcMA(data, 5)
    expect(result[0]).toBeNull()  // 不足5天
    expect(result[3]).toBeNull()
    expect(result[4]).not.toBeNull()
    expect(result[4]).toBeCloseTo(12, 0)
    expect(result).toHaveLength(10)
  })

  it('MA - 不足周期返回 null', () => {
    const data = makeKline([10, 11, 12])
    const result = calcMA(data, 10)
    expect(result.every(v => v === null)).toBe(true)
  })

  it('空数据返回空数组', () => {
    expect(calcMA([], 5)).toEqual([])
  })

  it('MA3 - 精确验证', () => {
    const data = makeKline([10, 20, 30])
    // 前三行 close一列: 10, 20, 30
    // avg(close+open/2? no - uses (close+high)/2 )
    // Actually looking at code: sum += (data[j][2] + data[j][3]) / 2
    // data[j][2] = close, data[j][3] = low
    // So for first row index 0: (10 + 9.8)/2 = 9.9
    // For index 1: (20 + 19.6)/2 = 19.8
    // For index 2: (30 + 29.4)/2 = 29.7
    // MA3 = (9.9 + 19.8 + 29.7) / 3 = 19.8
    const result = calcMA(data, 3)
    expect(result[2]).toBeCloseTo(19.8, 1)
  })
})

describe('calcBOLL', () => {
  const data = makeKline(
    Array.from({ length: 25 }, (_, i) => 10 + Math.sin(i * 0.5) * 2)
  )

  it('返回 up/mid/down 三数组', () => {
    const result = calcBOLL(data, 20, 2)
    expect(result).toHaveProperty('up')
    expect(result).toHaveProperty('mid')
    expect(result).toHaveProperty('down')
    expect(result.up).toHaveLength(25)
  })

  it('前期返回 null', () => {
    const result = calcBOLL(data, 20, 2)
    expect(result.up[0]).toBeNull()
    expect(result.up[18]).toBeNull()
  })

  it('后期有实际值', () => {
    const result = calcBOLL(data, 20, 2)
    expect(result.up[24]).not.toBeNull()
    expect(result.mid[24]).not.toBeNull()
    expect(result.down[24]).not.toBeNull()
  })

  it('上轨 > 中轨 > 下轨', () => {
    const result = calcBOLL(data, 20, 2)
    expect((result.up[24] as number) > (result.mid[24] as number)).toBe(true)
    expect((result.mid[24] as number) > (result.down[24] as number)).toBe(true)
  })
})

describe('calcMACD', () => {
  const data = makeKline(
    Array.from({ length: 40 }, (_, i) => 10 + Math.sin(i * 0.3) * 3)
  )

  it('返回 DIF/DEA/MACD 三数组', () => {
    const result = calcMACD(data, 12, 26, 9)
    expect(result).toHaveProperty('dif')
    expect(result).toHaveProperty('dea')
    expect(result).toHaveProperty('macd')
    expect(result.dif).toHaveLength(40)
    expect(result.dea).toHaveLength(40)
    expect(result.macd).toHaveLength(40)
  })

  it('DIF 和 DEA 值均为有限数字', () => {
    const result = calcMACD(data, 12, 26, 9)
    result.dif.forEach(v => expect(Number.isFinite(v)).toBe(true))
    result.dea.forEach(v => expect(Number.isFinite(v)).toBe(true))
  })

  it('空数据返回空数组', () => {
    const result = calcMACD([], 12, 26, 9)
    expect(result.dif).toEqual([])
    expect(result.dea).toEqual([])
    expect(result.macd).toEqual([])
  })
})

describe('calcKDJ', () => {
  const data = makeKline(
    Array.from({ length: 15 }, (_, i) => 10 + Math.sin(i * 0.4) * 2)
  )

  it('返回 K/D/J 三数组', () => {
    const result = calcKDJ(data, 9)
    expect(result).toHaveProperty('k')
    expect(result).toHaveProperty('d')
    expect(result).toHaveProperty('j')
    expect(result.k).toHaveLength(15)
    expect(result.d).toHaveLength(15)
    expect(result.j).toHaveLength(15)
  })

  it('前期值为 50（默认值）', () => {
    const result = calcKDJ(data, 9)
    for (let i = 0; i < 8; i++) {
      expect(result.k[i]).toBe(50)
      expect(result.d[i]).toBe(50)
      expect(result.j[i]).toBe(50)
    }
  })

  it('K/D/J 值均为有限数字', () => {
    const result = calcKDJ(data, 9)
    for (let i = 8; i < 15; i++) {
      expect(Number.isFinite(result.k[i])).toBe(true)
      expect(Number.isFinite(result.d[i])).toBe(true)
      expect(Number.isFinite(result.j[i])).toBe(true)
    }
  })

  it('空数据返回空数组', () => {
    const result = calcKDJ([], 9)
    expect(result.k).toEqual([])
  })
})

describe('calcRSI', () => {
  const data = makeKline(
    Array.from({ length: 20 }, (_, i) => 10 + Math.sin(i * 0.5) * 1)
  )

  it('前期返回 null', () => {
    const result = calcRSI(data, 14)
    for (let i = 0; i < 14; i++) {
      expect(result[i]).toBeNull()
    }
  })

  it('后期值在 0-100 范围内', () => {
    const result = calcRSI(data, 14)
    for (let i = 14; i < 20; i++) {
      expect(result[i]).toBeGreaterThanOrEqual(0)
      expect(result[i]).toBeLessThanOrEqual(100)
    }
  })

  it('全部上涨时 RSI 接近 100', () => {
    const upData = makeKline(
      Array.from({ length: 20 }, (_, i) => 10 + i * 0.5)
    )
    const result = calcRSI(upData, 14)
    // 最后几个值应该接近 100
    expect(result[19]).toBeGreaterThan(90)
  })

  it('空数据返回空数组', () => {
    expect(calcRSI([], 14)).toEqual([])
  })
})
