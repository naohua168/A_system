import request from './request'

/** 获取用户自选列表 */
export function getWatchlist(userId: number, assetType?: number) {
  return request.get(`/watchlist/${userId}`, { params: { assetType } })
}

/** 添加入自选 */
export function addWatchlist(userId: number, assetCode: string, assetType: number) {
  return request.post('/watchlist/add', { userId, assetCode, assetType })
}

/** 移除自选 */
export function removeWatchlist(userId: number, assetCode: string, assetType: number) {
  return request.delete('/watchlist/remove', { params: { userId, assetCode, assetType } })
}
