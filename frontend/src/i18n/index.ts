/** 简易国际化支持 — 中英文切换 */
const messages: Record<string, Record<string, string>> = {
  'zh-CN': {
    'app.title': '基金股票智能分析系统',
    'nav.home': '首页',
    'nav.stocks': '股票',
    'nav.portfolio': '持有',
    'nav.watchlist': '自选',
    'nav.chat': 'AI分析',
    'nav.news': '资讯',
    'nav.hotReason': '题材热点',
    'nav.northbound': '北向资金',
    'nav.dragonTiger': '龙虎榜',
    'nav.industry': '行业对比',
    'nav.fundFlow': '资金流向',
    'nav.lockup': '限售解禁',
    'nav.consensus': '一致预期',
    'common.loading': '加载中...',
    'common.error': '获取数据失败',
    'common.retry': '重试',
    'common.empty': '暂无数据',
    'common.search': '搜索',
    'ai.title': 'AI 智能分析',
    'ai.input': '输入问题，例如：分析 000001 的技术面...',
    'ai.send': '发送',
  },
  'en-US': {
    'app.title': 'Stock Fund AI Analysis System',
    'nav.home': 'Home',
    'nav.stocks': 'Stocks',
    'nav.portfolio': 'Portfolio',
    'nav.watchlist': 'Watchlist',
    'nav.chat': 'AI Chat',
    'nav.news': 'News',
    'nav.hotReason': 'Hot Topics',
    'nav.northbound': 'Northbound',
    'nav.dragonTiger': 'Dragon Tiger',
    'nav.industry': 'Industry',
    'nav.fundFlow': 'Fund Flow',
    'nav.lockup': 'Lockup',
    'nav.consensus': 'Consensus',
    'common.loading': 'Loading...',
    'common.error': 'Failed to load',
    'common.retry': 'Retry',
    'common.empty': 'No data',
    'common.search': 'Search',
    'ai.title': 'AI Analysis',
    'ai.input': 'Ask anything, e.g. analyze 000001...',
    'ai.send': 'Send',
  },
}

let currentLocale = 'zh-CN'

export function t(key: string): string {
  return messages[currentLocale]?.[key] || messages['zh-CN']?.[key] || key
}

export function setLocale(locale: string) {
  if (messages[locale]) {
    currentLocale = locale
    localStorage.setItem('locale', locale)
    window.dispatchEvent(new CustomEvent('locale-changed', { detail: locale }))
  }
}

export function getLocale(): string {
  return currentLocale
}

// 初始化：从 localStorage 恢复
const saved = localStorage.getItem('locale')
if (saved && messages[saved]) {
  currentLocale = saved
}
