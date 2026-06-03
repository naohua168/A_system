/**
 * 市场数据 WebSocket — 替代 polling，服务端主动推送 market data
 *
 * Topics: indices | signals | stats | sector
 * 连接 ws://host/ws/market → subscribe({topic}) → 接收 update 消息
 */
import { ref, onBeforeUnmount, type Ref } from 'vue'

type WsStatus = 'disconnected' | 'connecting' | 'connected'

export function useMarketWebSocket() {
  const status = ref<WsStatus>('disconnected')
  const wsRef = ref<WebSocket | null>(null)
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let pingTimer: ReturnType<typeof setInterval> | null = null
  const subscribed = ref<Set<string>>(new Set())

  const RECONNECT_DELAY = 3000
  const PING_INTERVAL = 25000

  /** 消息回调注册表：topic → handler */
  const handlers = new Map<string, (data: any) => void>()

  function getWsUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_WS_HOST || window.location.host
    return `${protocol}//${host}/ws/market`
  }

  function connect() {
    if (status.value === 'connecting' || status.value === 'connected') return
    status.value = 'connecting'
    try {
      const ws = new WebSocket(getWsUrl())
      wsRef.value = ws

      ws.onopen = () => {
        status.value = 'connected'
        startPing()
        // 重连后重新订阅所有 topic
        for (const topic of subscribed.value) {
          ws.send(JSON.stringify({ type: 'subscribe', topic }))
        }
      }

      ws.onmessage = (event: MessageEvent) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'update' && msg.topic && handlers.has(msg.topic)) {
            handlers.get(msg.topic)!(msg.data)
          } else if (msg.type === 'pong') {
            // 保活响应
          }
        } catch { /* ignore */ }
      }

      ws.onclose = () => {
        status.value = 'disconnected'
        stopPing()
        scheduleReconnect()
      }

      ws.onerror = () => { status.value = 'disconnected' }
    } catch {
      status.value = 'disconnected'
      scheduleReconnect()
    }
  }

  function disconnect() {
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
    stopPing()
    if (wsRef.value) {
      wsRef.value.onclose = null
      wsRef.value.close()
      wsRef.value = null
    }
    status.value = 'disconnected'
  }

  /** 订阅 topic，注册回调 */
  function subscribe(topic: string, handler: (data: any) => void) {
    handlers.set(topic, handler)
    subscribed.value.add(topic)
    if (wsRef.value?.readyState === WebSocket.OPEN) {
      wsRef.value.send(JSON.stringify({ type: 'subscribe', topic }))
    }
    // 首次调用时自动连接
    if (status.value === 'disconnected') connect()
  }

  /** 取消订阅 */
  function unsubscribe(topic: string) {
    handlers.delete(topic)
    subscribed.value.delete(topic)
    if (wsRef.value?.readyState === WebSocket.OPEN) {
      wsRef.value.send(JSON.stringify({ type: 'unsubscribe', topic }))
    }
  }

  /* ping/pong */
  function startPing() {
    stopPing()
    pingTimer = setInterval(() => {
      wsRef.value?.send(JSON.stringify({ type: 'ping' }))
    }, PING_INTERVAL)
  }
  function stopPing() {
    if (pingTimer) { clearInterval(pingTimer); pingTimer = null }
  }
  function scheduleReconnect() {
    if (reconnectTimer) return
    reconnectTimer = setTimeout(() => { reconnectTimer = null; connect() }, RECONNECT_DELAY)
  }

  onBeforeUnmount(() => disconnect())

  return { status, connect, disconnect, subscribe, unsubscribe }
}
