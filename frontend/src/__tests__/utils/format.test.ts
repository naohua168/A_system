import { describe, it, expect } from 'vitest'
import {
  safeNum, safeVal, formatVol, formatMoney,
  formatPrice, formatPercent, formatPoints,
  parseTradeDate, formatDateShort, getChangeClass,
} from '@/utils/format'

describe('format utils', () => {
  // ============================================================
  // safeNum
  // ============================================================
  describe('safeNum', () => {
    it('正常数字', () => {
      expect(safeNum(10.5)).toBe('10.50')
      expect(safeNum(100)).toBe('100.00')
      expect(safeNum(0)).toBe('0.00')
    })

    it('null/undefined 返回 -', () => {
      expect(safeNum(null)).toBe('-')
      expect(safeNum(undefined)).toBe('-')
    })

    it('NaN 返回 -', () => {
      expect(safeNum(NaN)).toBe('-')
    })

    it('字符串数字', () => {
      expect(safeNum('10.5')).toBe('10.50')
    })

    it('自定义小数位', () => {
      expect(safeNum(10.555, 4)).toBe('10.5550')
    })
  })

  // ============================================================
  // safeVal
  // ============================================================
  describe('safeVal', () => {
    it('正常数字返回本身', () => {
      expect(safeVal(42)).toBe(42)
    })

    it('null 返回默认值', () => {
      expect(safeVal(null)).toBe(0)
      expect(safeVal(null, -1)).toBe(-1)
    })

    it('NaN 返回默认值', () => {
      expect(safeVal(NaN, 100)).toBe(100)
    })
  })

  // ============================================================
  // formatVol
  // ============================================================
  describe('formatVol', () => {
    it('亿级别', () => {
      expect(formatVol(150000000)).toBe('1.50亿')
      expect(formatVol(100000000)).toBe('1.00亿')
    })

    it('万级别', () => {
      expect(formatVol(1500000)).toBe('150.00万')
      expect(formatVol(10000)).toBe('1.00万')
    })

    it('千级别以下', () => {
      expect(formatVol(5000)).toBe('5,000')
      expect(formatVol(0)).toBe('-')
    })

    it('null 返回 -', () => {
      expect(formatVol(null)).toBe('-')
    })
  })

  // ============================================================
  // formatMoney
  // ============================================================
  describe('formatMoney', () => {
    it('正常金额', () => {
      expect(formatMoney(12345.67)).toContain('12')
    })

    it('零值', () => {
      expect(formatMoney(0)).toBe('0.00')
    })
  })

  // ============================================================
  // formatPrice
  // ============================================================
  describe('formatPrice', () => {
    it('正常价格格式化', () => {
      expect(formatPrice(10.5)).toBe('10.50')
      expect(formatPrice(100.0)).toBe('100.00')
      expect(formatPrice(0)).toBe('0.00')
    })

    it('null/undefined 返回 -', () => {
      expect(formatPrice(null)).toBe('-')
      expect(formatPrice(undefined)).toBe('-')
    })

    it('NaN 返回 -', () => {
      expect(formatPrice(NaN)).toBe('-')
    })

    it('负数价格', () => {
      expect(formatPrice(-5.5)).toBe('-5.50')
    })
  })

  // ============================================================
  // formatPercent
  // ============================================================
  describe('formatPercent', () => {
    it('正数带 + 号', () => {
      expect(formatPercent(3.5)).toBe('+3.50%')
    })

    it('负数带 - 号', () => {
      expect(formatPercent(-2.0)).toBe('-2.00%')
    })

    it('零值', () => {
      expect(formatPercent(0)).toBe('0.00%')
    })

    it('null 返回 -', () => {
      expect(formatPercent(null)).toBe('-')
    })

    it('超大百分比', () => {
      expect(formatPercent(999.99)).toContain('%')
    })
  })

  // ============================================================
  // formatPoints
  // ============================================================
  describe('formatPoints', () => {
    it('正数带 + 号', () => {
      expect(formatPoints(15.5)).toBe('+15.50')
    })

    it('负数', () => {
      expect(formatPoints(-8.25)).toBe('-8.25')
    })

    it('NaN 返回 -', () => {
      expect(formatPoints(NaN)).toBe('-')
    })
  })

  // ============================================================
  // parseTradeDate / formatDateShort
  // ============================================================
  describe('parseTradeDate', () => {
    it('标准日期解析', () => {
      const ts = parseTradeDate('2025-01-02')
      expect(ts).toBeGreaterThan(0)
    })

    it('空字符串返回 0', () => {
      expect(parseTradeDate('')).toBe(0)
    })

    it('斜杠分隔', () => {
      expect(parseTradeDate('2025/01/02')).toBeGreaterThan(0)
    })
  })

  describe('formatDateShort', () => {
    it('标准日期', () => {
      expect(formatDateShort('2025-01-02')).toBe('1/2')
    })

    it('空字符串返回原值', () => {
      expect(formatDateShort('')).toBe('')
    })
  })

  // ============================================================
  // getChangeClass
  // ============================================================
  describe('getChangeClass', () => {
    it('正数返回 rise', () => {
      expect(getChangeClass(3.5)).toBe('rise')
    })

    it('负数返回 fall', () => {
      expect(getChangeClass(-2.0)).toBe('fall')
    })

    it('零值返回 flat', () => {
      expect(getChangeClass(0)).toBe('flat')
    })

    it('NaN 返回 flat', () => {
      expect(getChangeClass(NaN)).toBe('flat')
    })
  })
})
