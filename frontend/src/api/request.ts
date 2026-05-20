import axios from 'axios'
import type { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

/** 后端统一响应包装结构 */
interface UnifiedResponse<T = unknown> {
  code: number
  message: string
  data: T
  timestamp: number
}

// ============================================================
// 前端 API 响应缓存层 — 基于 TTL 的 Map 缓存
// 只缓存 GET 请求，按 URL+params 生成 key，过期后自动释放
// ============================================================

interface CacheEntry {
  data: unknown
  expireAt: number
}

class ApiCache {
  private cache = new Map<string, CacheEntry>()
  private pending = new Map<string, Promise<unknown>>()  // 请求去重

  /** 生成缓存 key（URL + 序列化参数） */
  private buildKey(url: string, params?: Record<string, unknown>): string {
    return params ? `${url}::${JSON.stringify(params)}` : url
  }

  /** 获取缓存（未过期返回数据，已过期删除并返回 null） */
  get<T>(url: string, params?: Record<string, unknown>): T | null {
    const key = this.buildKey(url, params)
    const entry = this.cache.get(key)
    if (!entry) return null
    if (Date.now() > entry.expireAt) {
      this.cache.delete(key)
      return null
    }
    return entry.data as T
  }

  /** 设置缓存（默认 TTL=30s） */
  set<T>(url: string, data: T, params?: Record<string, unknown>, ttlMs = 30000): void {
    const key = this.buildKey(url, params)
    this.cache.set(key, { data, expireAt: Date.now() + ttlMs })
    // 清理已完成的去重记录
    this.pending.delete(key)
  }

  /** 请求去重：相同 URL+params 的并发请求合并为一次 */
  dedup<T>(key: string, fetcher: () => Promise<T>): Promise<T> {
    const existing = this.pending.get(key) as Promise<T> | undefined
    if (existing) return existing
    const promise = fetcher().finally(() => this.pending.delete(key))
    this.pending.set(key, promise)
    return promise
  }

  /** 按前缀清除缓存（如退出时清理 /api/market 下的所有缓存） */
  clearByPrefix(prefix: string): void {
    for (const key of this.cache.keys()) {
      if (key.startsWith(prefix)) this.cache.delete(key)
    }
  }

  /** 清除全部缓存 */
  clearAll(): void {
    this.cache.clear()
    this.pending.clear()
  }
}

const apiCache = new ApiCache()

// ============================================================
// Axios 实例
// ============================================================

const request: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/** 需要缓存的 API 路径前缀及其 TTL（毫秒） */
const CACHE_RULES: [string, number][] = [
  ['/api/market/list', 15000],       // 股票列表 15s
  ['/api/market/industry', 30000],   // 行业列表 30s
  ['/api/analysis', 60000],          // 技术分析 60s
  ['/api/signal', 30000],           // 信号数据 30s
  ['/api/fund', 60000],            // 基金数据 60s
  ['/api/index', 60000],           // 指数数据 60s
]

function getCacheTtl(url: string): number {
  for (const [prefix, ttl] of CACHE_RULES) {
    if (url.startsWith(prefix)) return ttl
  }
  return 30000 // 默认 30s
}

/** 是否需要缓存该请求 */
function shouldCache(config: InternalAxiosRequestConfig): boolean {
  if (config.method?.toUpperCase() !== 'GET') return false
  // 跳过带 cancelToken/signal 的请求（如搜索、翻页竞态控制）
  if (config.signal?.aborted) return false
  return true
}

// -----------------------------------------------------------
// 请求拦截器 — 注入 token + 检查缓存
// -----------------------------------------------------------

request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // GET 请求检查缓存命中（通过自定义标记避免二次拦截）
    if (shouldCache(config) && !config.headers?.['x-cache-bypass']) {
      const cached = apiCache.get<any>(config.url || '', config.params as Record<string, unknown> | undefined)
      if (cached !== null) {
        // 注入适配器直接返回缓存，不发起真实请求
        config.adapter = () => Promise.resolve({
          data: cached as unknown,
          status: 200,
          statusText: 'OK (cache)',
          headers: { 'x-cache': 'HIT' },
          config,
        })
      }
    }

    return config
  },
  (error) => Promise.reject(error)
)

/**
 * 响应拦截器 — 兼容统一 ApiResponse 和原始数据两种格式
 *
 * 处理逻辑:
 *   1) 统一格式 { code, data, message } → code===200/201 时返回 data, 否则报错
 *   2) 原始数据（如 ResponseBodyAdvice 包装的数组/对象）→ 直接透传
 *   3) 401 → 跳转登录页
 *   4) GET 请求成功 → 写入缓存层
 */
request.interceptors.response.use(
  (response: AxiosResponse) => {
    const body = response.data as UnifiedResponse

    // 格式1: 统一 ApiResponse 格式
    if (body && typeof body.code === 'number') {
      if (body.code === 200 || body.code === 201) {
        const data = body.data

        // GET 请求成功 → 写入缓存
        const reqConfig = response.config
        if (reqConfig?.method?.toUpperCase() === 'GET' && !response.headers?.['x-cache']) {
          const url = reqConfig.url || ''
          if (url.startsWith('/api/')) {
            apiCache.set(url, data, reqConfig.params as Record<string, unknown> | undefined, getCacheTtl(url))
          }
        }

        return data as unknown
      }
      if (body.code === 401) {
        localStorage.removeItem('token')
        apiCache.clearAll()
        const currentPath = window.location.pathname
        if (currentPath !== '/login') {
          ElMessage.warning('登录已过期，请重新登录')
          window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`
        }
        return Promise.reject(new Error(body.message || '未授权'))
      }
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(new Error(body.message || '请求失败'))
    }

    // 格式2: 原始数据直接透传（也尝试缓存）
    const reqConfig = response.config
    if (reqConfig?.method?.toUpperCase() === 'GET') {
      const url = reqConfig.url || ''
      if (url.startsWith('/api/')) {
        apiCache.set(url, response.data, reqConfig.params as Record<string, unknown> | undefined, getCacheTtl(url))
      }
    }

    return response.data
  },
  (error) => {
    // 401 时清除所有缓存
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      apiCache.clearAll()
      window.location.href = '/login'
    } else {
      const msg = error.response?.data?.message || error.message || '网络请求失败'
      ElMessage.error(msg)
    }
    return Promise.reject(error)
  }
)

export { apiCache }
export default request
