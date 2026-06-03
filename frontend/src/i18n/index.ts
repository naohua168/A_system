/** 简易国际化支持 — 中英文切换 */
const messages: Record<string, Record<string, string>> = {
  'zh-CN': {
    // ── 应用 ──
    'app.title': '基金股票智能分析系统',

    // ── 导航 ──
    'nav.home': '首页',
    'nav.stocks': '股票',
    'nav.portfolio': '持有',
    'nav.watchlist': '自选',
    'nav.chat': 'AI分析',
    'nav.news': '资讯',
    'nav.signal': '信号',
    'nav.hotReason': '题材热点',
    'nav.northbound': '北向资金',
    'nav.dragonTiger': '龙虎榜',
    'nav.industry': '行业对比',
    'nav.fundFlow': '资金流向',
    'nav.lockup': '限售解禁',
    'nav.consensus': '一致预期',
    'nav.layers': '架构',
    'nav.funds': '基金',
    'nav.index': '指数',

    // ── 通用 ──
    'common.loading': '加载中...',
    'common.error': '获取数据失败',
    'common.retry': '重试',
    'common.empty': '暂无数据',
    'common.search': '搜索',
    'common.back': '返回',
    'common.confirm': '确认',
    'common.cancel': '取消',
    'common.save': '保存',
    'common.delete': '删除',
    'common.edit': '编辑',
    'common.login': '登录',
    'common.logout': '退出登录',
    'common.register': '注册',
    'common.username': '用户名',
    'common.password': '密码',
    'common.page': '页',

    // ── 首页 ──
    'home.marketOverview': '市场概览',
    'home.sectorCloud': '板块云图',
    'home.topGainers': '涨幅榜',
    'home.topLosers': '跌幅榜',
    'home.activeStocks': '活跃个股',
    'home.marketIndex': '市场指数',

    // ── 个股详情 ──
    'stock.basicInfo': '基本信息',
    'stock.kline': 'K线图',
    'stock.technical': '技术指标',
    'stock.chanlun': '缠论分析',
    'stock.signal': '信号数据',
    'stock.fundamentals': '基本面',
    'stock.news': '相关资讯',
    'stock.code': '股票代码',
    'stock.name': '股票名称',
    'stock.price': '最新价',
    'stock.change': '涨跌幅',
    'stock.volume': '成交量',
    'stock.amount': '成交额',
    'stock.pe': '市盈率',
    'stock.pb': '市净率',
    'stock.marketCap': '总市值',

    // ── 行情列表 ──
    'market.list': '行情列表',
    'market.all': '全部',
    'market.sz': '深圳',
    'market.sh': '上海',
    'market.bj': '北京',
    'market.filter': '筛选',

    // ── 信号 ──
    'signal.hotReason': '题材热点',
    'signal.northbound': '北向资金',
    'signal.dragonTiger': '龙虎榜',
    'signal.industryCompare': '行业对比',
    'signal.fundFlow': '资金流向',
    'signal.lockup': '限售解禁',

    'signal.date': '日期',
    'signal.stock': '个股',
    'signal.netAmount': '净买入额',

    // ── 自选 ──
    'watchlist.title': '我的自选',
    'watchlist.add': '添加自选',
    'watchlist.remove': '删除',
    'watchlist.empty': '自选列表为空，搜索股票添加',

    // ── 基金 ──
    'fund.detail': '基金详情',
    'fund.nav': '净值',
    'fund.holding': '持仓',
    'fund.type': '基金类型',
    'fund.manager': '基金经理',

    // ── AI ──
    'ai.title': 'AI 智能分析',
    'ai.input': '输入问题，例如：分析 000001 的技术面...',
    'ai.send': '发送',
    'ai.analyzing': 'AI 正在分析...',
    'ai.analysis': '深度分析',
    'ai.debate': '多空辩论',

    // ── 资讯 ──
    'news.title': '市场资讯',
    'news.stockNews': '个股新闻',
    'news.cls': '财联社快讯',
    'news.global': '全球财经',
    'news.research': '机构研报',

    // ── 架构 ──
    'layers.title': '系统架构',
    'layers.overview': '架构概览',
    'layers.status': '运行状态',
    'layers.modules': '模块数',
    'layers.files': '文件数',
    'layers.tests': '测试数',

    // ── 用户 ──
    'user.profile': '个人中心',
    'user.settings': '设置',
    'user.changePassword': '修改密码',
    'user.oldPassword': '原密码',
    'user.newPassword': '新密码',
  },

  'en-US': {
    // ── App ──
    'app.title': 'Stock Fund AI Analysis System',

    // ── Navigation ──
    'nav.home': 'Home',
    'nav.stocks': 'Stocks',
    'nav.portfolio': 'Portfolio',
    'nav.watchlist': 'Watchlist',
    'nav.chat': 'AI Chat',
    'nav.news': 'News',
    'nav.signal': 'Signals',
    'nav.hotReason': 'Hot Topics',
    'nav.northbound': 'Northbound',
    'nav.dragonTiger': 'Dragon Tiger',
    'nav.industry': 'Industry',
    'nav.fundFlow': 'Fund Flow',
    'nav.lockup': 'Lockup',
    'nav.consensus': 'Consensus',
    'nav.layers': 'Architecture',
    'nav.funds': 'Funds',
    'nav.index': 'Index',

    // ── Common ──
    'common.loading': 'Loading...',
    'common.error': 'Failed to load',
    'common.retry': 'Retry',
    'common.empty': 'No data',
    'common.search': 'Search',
    'common.back': 'Back',
    'common.confirm': 'Confirm',
    'common.cancel': 'Cancel',
    'common.save': 'Save',
    'common.delete': 'Delete',
    'common.edit': 'Edit',
    'common.login': 'Login',
    'common.logout': 'Logout',
    'common.register': 'Register',
    'common.username': 'Username',
    'common.password': 'Password',
    'common.page': 'Page',

    // ── Home ──
    'home.marketOverview': 'Market Overview',
    'home.sectorCloud': 'Sector Cloud',
    'home.topGainers': 'Top Gainers',
    'home.topLosers': 'Top Losers',
    'home.activeStocks': 'Active Stocks',
    'home.marketIndex': 'Market Index',

    // ── Stock Detail ──
    'stock.basicInfo': 'Basic Info',
    'stock.kline': 'K-Line',
    'stock.technical': 'Technical Indicators',
    'stock.chanlun': 'Chanlun Analysis',
    'stock.signal': 'Signal Data',
    'stock.fundamentals': 'Fundamentals',
    'stock.news': 'Related News',
    'stock.code': 'Code',
    'stock.name': 'Name',
    'stock.price': 'Price',
    'stock.change': 'Change %',
    'stock.volume': 'Volume',
    'stock.amount': 'Amount',
    'stock.pe': 'P/E',
    'stock.pb': 'P/B',
    'stock.marketCap': 'Market Cap',

    // ── Market ──
    'market.list': 'Market List',
    'market.all': 'All',
    'market.sz': 'Shenzhen',
    'market.sh': 'Shanghai',
    'market.bj': 'Beijing',
    'market.filter': 'Filter',

    // ── Signal ──
    'signal.hotReason': 'Hot Topics',
    'signal.northbound': 'Northbound Flow',
    'signal.dragonTiger': 'Dragon Tiger',
    'signal.industryCompare': 'Industry Compare',
    'signal.fundFlow': 'Fund Flow',
    'signal.lockup': 'Lockup Calendar',

    'signal.date': 'Date',
    'signal.stock': 'Stock',
    'signal.netAmount': 'Net Amount',

    // ── Watchlist ──
    'watchlist.title': 'My Watchlist',
    'watchlist.add': 'Add',
    'watchlist.remove': 'Remove',
    'watchlist.empty': 'Watchlist is empty, search stocks to add',

    // ── Fund ──
    'fund.detail': 'Fund Detail',
    'fund.nav': 'NAV',
    'fund.holding': 'Holdings',
    'fund.type': 'Fund Type',
    'fund.manager': 'Fund Manager',

    // ── AI ──
    'ai.title': 'AI Analysis',
    'ai.input': 'Ask anything, e.g. analyze 000001...',
    'ai.send': 'Send',
    'ai.analyzing': 'AI is analyzing...',
    'ai.analysis': 'Deep Analysis',
    'ai.debate': 'Bull vs Bear Debate',

    // ── News ──
    'news.title': 'Market News',
    'news.stockNews': 'Stock News',
    'news.cls': 'CLS Flash',
    'news.global': 'Global Finance',
    'news.research': 'Research Reports',

    // ── Layers ──
    'layers.title': 'System Architecture',
    'layers.overview': 'Architecture Overview',
    'layers.status': 'Status',
    'layers.modules': 'Modules',
    'layers.files': 'Files',
    'layers.tests': 'Tests',

    // ── User ──
    'user.profile': 'Profile',
    'user.settings': 'Settings',
    'user.changePassword': 'Change Password',
    'user.oldPassword': 'Old Password',
    'user.newPassword': 'New Password',
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
