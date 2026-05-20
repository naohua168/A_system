import request from './request'
import type { WatchlistItem } from '@/types'

/** 获取用户自选列表 */
export function getWatchlist(userId: number, assetType?: number): Promise<WatchlistItem[]> {
  return request.get(`/watchlist/${userId}`, { params: { assetType } })
}

/** 添加入自选 */
export function addWatchlist(userId: number, assetCode: string, assetType: number): Promise<string> {
  return request.post('/watchlist/add', { userId, assetCode, assetType })
}

/** 移除自选 */
export function removeWatchlist(userId: number, assetCode: string, assetType: number): Promise<void> {
  return request.delete('/watchlist/remove', { params: { userId, assetCode, assetType } })
}
