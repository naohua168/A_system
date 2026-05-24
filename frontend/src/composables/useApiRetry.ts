import { ref, type Ref } from 'vue'
import { ElMessage } from 'element-plus'

export interface ApiState<T> {
  data: Ref<T>
  loading: Ref<boolean>
  error: Ref<string | null>
  retryCount: Ref<number>
  fetch: () => Promise<void>
  reset: () => void
}

export interface ApiOptions {
  /** 最大重试次数（默认 2） */
  maxRetries?: number
  /** 重试间隔(ms)，首次失败后等待（默认 1000） */
  retryDelay?: number
  /** 重试间隔增长因子（默认 1.5） */
  backoffFactor?: number
  /** 失败时是否显示 ElMessage 错误提示（默认 false） */
  showError?: boolean
  /** 自定义错误消息 */
  errorMessage?: string
  /** 是否在 fetch 开始时立即显示错误（给兜底数据使用） */
  silent?: boolean
}

/**
 * API 调用 composable — 带自动重试、loading、错误状态
 *
 * @param fetcher 返回 Promise 的异步函数
 * @param options 配置选项
 * @returns { data, loading, error, retryCount, fetch, reset }
 *
 * @example
 * const { data, loading, error, fetch } = useApiRetry(
 *   () => getIndustryCompare(date),
 *   { maxRetries: 2, showError: true }
 * )
 * onMounted(fetch)
 */
export function useApiRetry<T = any>(
  fetcher: () => Promise<T>,
  options: ApiOptions = {}
): ApiState<T> {
  const {
    maxRetries = 2,
    retryDelay = 1000,
    backoffFactor = 1.5,
    showError = false,
    errorMessage,
    silent = false,
  } = options

  const data = ref<T>(null as unknown as T) as Ref<T>
  const loading = ref(false)
  const error = ref<string | null>(null)
  const retryCount = ref(0)

  async function fetch() {
    loading.value = true
    error.value = null
    retryCount.value = 0

    let lastError: any = null
    let delay = retryDelay

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const result = await fetcher()
        data.value = result
        loading.value = false
        return
      } catch (err: any) {
        lastError = err
        retryCount.value = attempt + 1

        if (attempt < maxRetries) {
          // 指数退避等待
          await new Promise(resolve => setTimeout(resolve, delay))
          delay *= backoffFactor
        }
      }
    }

    // 所有重试都失败
    loading.value = false
    const message = errorMessage || lastError?.message || '请求失败，请稍后重试'
    error.value = message

    if (showError && !silent) {
      ElMessage.error(message)
    }
  }

  function reset() {
    data.value = null as unknown as T
    loading.value = false
    error.value = null
    retryCount.value = 0
  }

  return { data, loading, error, retryCount, fetch, reset }
}

/**
 * 安全解析行业对比数据
 */
export function safeRecords(input: any, field = 'records'): any[] {
  if (!input) return []
  if (Array.isArray(input)) return input
  if (Array.isArray(input[field])) return input[field]
  return []
}

/**
 * 安全取值 — 防止渲染时因字段缺失崩溃
 */
export function safeNum(v: any, decimals = 2): number {
  const n = Number(v)
  return Number.isNaN(n) ? 0 : Number(n.toFixed(decimals))
}

export function safeStr(v: any, fallback = '-'): string {
  return (v != null && v !== '') ? String(v) : fallback
}

export function safeArr(v: any): any[] {
  return Array.isArray(v) ? v : []
}
