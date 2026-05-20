import request from './request'
import type { UserInfo } from '@/types'

export interface LoginResult {
  token: string
  user: UserInfo
}

export function login(username: string, password: string): Promise<LoginResult> {
  return request.post('/user/login', { username, password })
}

export function getUserInfo(): Promise<UserInfo> {
  return request.get('/user/info')
}

export function register(data: { username: string; password: string; email?: string }): Promise<string> {
  return request.post('/user/register', data)
}
