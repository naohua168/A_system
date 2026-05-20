/**
 * useStockWebSocket composable 单元测试
 *
 * 测试内容:
 * - 初始状态为 disconnected
 * - connect/disconnect 生命周期
 * - 消息处理逻辑
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useStockWebSocket } from '@/composables/useStockWebSocket'

describe('useStockWebSocket', () => {
  beforeEach(() => {
    // Mock WebSocket
    vi.stubGlobal('WebSocket', vi.fn(() => ({
      readyState: 3, // CLOSED
      send: vi.fn(),
      close: vi.fn(),
    })))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('初始状态为 disconnected', () => {
    const { wsStatus } = useStockWebSocket('000001')
    expect(wsStatus.value).toBe('disconnected')
  })

  it('connect 将状态切换为 connecting', () => {
    const { wsStatus, connect } = useStockWebSocket('000001')
    connect()
    expect(wsStatus.value).toBe('connecting')
  })

  it('未提供 stockCode 时 connect 不做任何操作', () => {
    const { wsStatus, connect } = useStockWebSocket('')
    connect()
    expect(wsStatus.value).toBe('disconnected')
  })

  it('disconnect 将状态重置为 disconnected', () => {
    const { wsStatus, disconnect } = useStockWebSocket('000001')
    disconnect()
    expect(wsStatus.value).toBe('disconnected')
  })

  it('lastKlineUpdate 初始为 null', () => {
    const { lastKlineUpdate } = useStockWebSocket('000001')
    expect(lastKlineUpdate.value).toBeNull()
  })

  it('构建的 WS URL 格式正确', () => {
    // window.location 需要 mock
    Object.defineProperty(window, 'location', {
      value: { protocol: 'http:', host: 'localhost:5173' },
      writable: true,
    })
    const { connect } = useStockWebSocket('000001')
    connect()
    // WebSocket 被调用时使用了正确的 url
    expect(WebSocket).toHaveBeenCalledWith('ws://localhost:5173/ws/stock/000001')
  })

  it('HTTPS 环境下使用 wss 协议', () => {
    Object.defineProperty(window, 'location', {
      value: { protocol: 'https:', host: 'example.com' },
      writable: true,
    })
    const { connect } = useStockWebSocket('000001')
    connect()
    expect(WebSocket).toHaveBeenCalledWith('wss://example.com/ws/stock/000001')
  })
})
