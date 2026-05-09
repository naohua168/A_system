import request from './request'

/** 获取所有指数列表（含最新行情） */
export function getIndexList() {
  return request.get('/index/list')
}

/** 获取指数基本信息 */
export function getIndexInfo(code: string) {
  return request.get(`/index/${code}`)
}

/** 获取指数K线数据 */
export function getIndexKline(code: string, params?: { days?: number }) {
  return request.get(`/index/${code}/kline`, { params })
}
