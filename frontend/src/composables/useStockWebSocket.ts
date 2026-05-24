/**
 * WebSocket 实时行情推送 composable
 *
 * 连接后端 /ws/stock/{code} 端点，接收实时 K 线更新推送。
 * 自动重连 + ping/pong 保活。
 */
import { ref, onBeforeUnmount, type Ref } from 'vue'

export type WsStatus = 'disconnected' | 'connecting' | 'connected'

export interface KlineUpdateData {
  tradeDate?: string
  openPrice?: number
  closePrice?: number
  highPrice?: number
  lowPrice?: number
  volume?: number
  amount?: number
  changePercent?: number
}

export function useStockWebSocket(stockCode: Ref<string> | string) {
  const wsStatus = ref<WsStatus>('disconnected')
  const lastKlineUpdate = ref<KlineUpdateData | null>(null)

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let pingTimer: ReturnType<typeof setInterval> | null = null

  const RECONNECT_DELAY = 3000
  const PING_INTERVAL = 25000

  /** 构建 WS URL — 生产环境同域，开发环境通过环境变量指定后端地址 */
  function getWsUrl(code: string): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    // 优先使用环境变量 VITE_WS_HOST（开发环境指向后端），否则使用当前页面 host
    const wsHost = import.meta.env.VITE_WS_HOST || window.location.host
    return `${protocol}//${wsHost}/ws/stock/${code}`
  }

  /** 发起连接 */
  function connect() {
    const code = typeof stockCode === 'string' ? stockCode : stockCode.value
    if (!code || wsStatus.value === 'connecting') return

    wsStatus.value = 'connecting'
    const url = getWsUrl(code)

    try {
      ws = new WebSocket(url)
    } catch (err) {
      console.error('[WS] 创建 WebSocket 失败:', err)
      wsStatus.value = 'disconnected'
      scheduleReconnect()
      return
    }

    ws.onopen = () => {
      console.log('[WS] 已连接:', code)
      wsStatus.value = 'connected'
      startPing()
    }

    ws.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data)
        handleMessage(msg)
      } catch {
        console.warn('[WS] 消息解析失败:', event.data)
      }
    }

    ws.onclose = () => {
      console.log('[WS] 连接已关闭:', code)
      wsStatus.value = 'disconnected'
      stopPing()
      scheduleReconnect()
    }

    ws.onerror = (err) => {
      console.error('[WS] 连接错误:', err)
      wsStatus.value = 'disconnected'
    }
  }

  /** 处理服务端消息 */
  function handleMessage(msg: Record<string, unknown>) {
    switch (msg.type) {
      case 'connected':
      case 'subscribed':
      case 'unsubscribed':
        break
      case 'pong':
        break
      case 'kline_update':
        if (msg.data) {
          lastKlineUpdate.value = msg.data as KlineUpdateData
        }
        break
      default:
        console.debug('[WS] 未知消息类型:', msg.type)
    }
  }

  /** 发送消息 */
  function send(data: Record<string, unknown>) {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data))
    }
  }

  /** 订阅股票 */
  function subscribe(code: string) {
    send({ type: 'subscribe', code })
  }

  /** 取消订阅 */
  function unsubscribe(code: string) {
    send({ type: 'unsubscribe', code })
  }

  /** Ping 保活 */
  function startPing() {
    stopPing()
    pingTimer = setInterval(() => {
      send({ type: 'ping' })
    }, PING_INTERVAL)
  }

  function stopPing() {
    if (pingTimer) {
      clearInterval(pingTimer)
      pingTimer = null
    }
  }

  /** 自动重连 */
  function scheduleReconnect() {
    if (reconnectTimer) return
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      connect()
    }, RECONNECT_DELAY)
  }

  /** 断开连接 */
  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    stopPing()
    if (ws) {
      ws.onclose = null // 阻止触发重连
      ws.close()
      ws = null
    }
    wsStatus.value = 'disconnected'
  }

  // 组件卸载时自动断开
  onBeforeUnmount(() => {
    disconnect()
  })

  return {
    wsStatus,
    lastKlineUpdate,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
  }
}
