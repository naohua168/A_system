import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'

// Mock user API
vi.mock('@/api/user', () => ({
  login: vi.fn().mockResolvedValue({ token: 'mock-token', user: { id: 1, username: 'test' } }),
  getUserInfo: vi.fn().mockResolvedValue({ id: 1, username: 'test' }),
  register: vi.fn(),
}))

describe('useUserStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('初始状态 - 未登录', () => {
    const store = useUserStore()
    expect(store.token).toBeNull()
    expect(store.userInfo).toBeNull()
    expect(store.isLoggedIn).toBe(false)
  })

  it('从 localStorage 恢复 token', () => {
    localStorage.setItem('token', 'test-token-123')
    const store = useUserStore()
    expect(store.token).toBe('test-token-123')
    expect(store.isLoggedIn).toBe(true)
  })

  it('logout 清除 token 和用户信息', () => {
    localStorage.setItem('token', 'test-token')
    const store = useUserStore()
    store.logout()
    expect(store.token).toBeNull()
    expect(store.userInfo).toBeNull()
    expect(store.isLoggedIn).toBe(false)
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('login - 成功后保存 token 和用户信息', async () => {
    const store = useUserStore()
    const res = await store.login('testuser', 'password123')
    expect(res.token).toBe('mock-token')
    expect(store.token).toBe('mock-token')
    expect(store.isLoggedIn).toBe(true)
    expect(localStorage.getItem('token')).toBe('mock-token')
  })

  it('fetchUserInfo - 无 token 时不请求', async () => {
    const store = useUserStore()
    await store.fetchUserInfo()
    expect(store.userInfo).toBeNull()
  })

  it('fetchUserInfo - 有 token 时获取用户信息', async () => {
    localStorage.setItem('token', 'test-token')
    const store = useUserStore()
    await store.fetchUserInfo()
    expect(store.userInfo).not.toBeNull()
    expect(store.userInfo?.username).toBe('test')
  })
})
