/**
 * 安全格式化数字：防止 NaN/undefined/null 导致页面显示异常
 */
function isNil(v: unknown): v is null | undefined {
  return v === null || v === undefined
}

export function safeNum(v: unknown, decimals = 2): string {
  if (isNil(v)) return '-'
  const n = Number(v)
  return isNaN(n) ? '-' : n.toFixed(decimals)
}

/** 安全取数字，失败时返回 fallback */
export function safeVal(v: unknown, fallback = 0): number {
  if (isNil(v)) return fallback
  const n = Number(v)
  return isNaN(n) ? fallback : n
}

/** 格式化成交量为可读字符串 */
export function formatVol(v: unknown): string {
  if (isNil(v)) return '-'
  const n = Number(v)
  if (!n || isNaN(n)) return '-'
  if (n >= 100000000) return (n / 100000000).toFixed(2) + '亿'
  if (n >= 10000) return (n / 10000).toFixed(2) + '万'
  return n.toLocaleString()
}

/** 格式化金额（带货币符号） */
export function formatMoney(v: number): string {
  return v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/** 格式化价格为带千分位的字符串 */
export function formatPrice(p: unknown): string {
  if (isNil(p)) return '-'
  const n = Number(p)
  return isNaN(n) ? '-' : n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/** 格式化涨跌幅 */
export function formatPercent(p: unknown): string {
  if (isNil(p)) return '-'
  const n = Number(p)
  if (isNaN(n)) return '-'
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(2)}%`
}

/** 格式化涨跌点数 */
export function formatPoints(p: unknown): string {
  if (isNil(p)) return '-'
  const n = Number(p)
  if (isNaN(n)) return '-'
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(2)}`
}

/**
 * 解析 "YYYY-MM-DD" 为时间戳（避免 new Date 字符串解析不一致）
 */
export function parseTradeDate(dateStr: string): number {
  if (!dateStr) return 0
  const parts = dateStr.split(/[-/]/)
  if (parts.length === 3) {
    return new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2])).getTime()
  }
  return new Date(dateStr).getTime() || 0
}

/** 格式化日期为 "M/D" 短格式 */
export function formatDateShort(dateStr: string): string {
  const ts = parseTradeDate(dateStr)
  if (!ts) return dateStr || ''
  const d = new Date(ts)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

/** 获取涨跌幅 CSS 类名 */
export function getChangeClass(pct: number): string {
  const n = Number(pct)
  if (isNaN(n)) return 'flat'
  if (n > 0) return 'rise'
  if (n < 0) return 'fall'
  return 'flat'
}

/** 格式化成交量（formatVol 的别名，供模板使用） */
export function formatVolume(v: unknown): string {
  return formatVol(v)
}
