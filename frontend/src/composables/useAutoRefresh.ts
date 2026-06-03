/**
 * 自动刷新组合函数 — 组件卸载时自动清理定时器
 *
 * @param fn 刷新回调
 * @param intervalMs 刷新间隔（毫秒），传 0 或负数则不启动
 * @param immediate 是否立即执行一次（默认 false，由调用方自行决定首次执行时机）
 * @returns stop 手动停止刷新的函数
 */
import { onBeforeUnmount, ref } from 'vue'

export function useAutoRefresh(fn: () => void, intervalMs: number, immediate = false) {
  if (intervalMs <= 0) return { stop: () => {} }

  const timer = ref<ReturnType<typeof setInterval> | null>(null)

  function start() {
    stop()
    timer.value = setInterval(fn, intervalMs)
  }

  function stop() {
    if (timer.value !== null) {
      clearInterval(timer.value)
      timer.value = null
    }
  }

  if (immediate) fn()
  start()
  onBeforeUnmount(stop)

  return { start, stop }
}
