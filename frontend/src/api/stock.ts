import request from './request'

export function getStockList(params?: {
  page?: number
  size?: number
  keyword?: string
  industry?: string
  sortField?: string
  sortOrder?: 'asc' | 'desc'
}) {
  return request.get('/stock/list', { params })
}

export function getStockByCode(code: string) {
  return request.get(`/stock/${code}`)
}

export function getKlineData(code: string, params?: { days?: number; freq?: string }) {
  return request.get(`/stock/kline/${code}`, { params })
}

/** 搜索股票（自动补全） */
export function searchStocks(keyword: string) {
  return request.get('/stock/search', { params: { keyword, size: 10 } })
}

/** 获取行业列表 */
export function getIndustries() {
  return request.get('/stock/industries')
}
