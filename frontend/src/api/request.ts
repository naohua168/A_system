import axios from 'axios'
import type { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import type { ApiResponse } from '@/types'
import { ElMessage } from 'element-plus'

const request: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

/**
 * 响应拦截器 — 兼容统一 ApiResponse 和原始数据两种格式
 *
 * 修复:
 * 1. 兼容后端 ResponseBodyAdvice 包装的 { code, data, message } 和部分未包装的原始 ResponseEntity
 * 2. 添加 ElMessage 统一错误提示
 * 3. 修复: 401 时保留当前页面 URL，登录后可跳回
 */
request.interceptors.response.use(
  (response: AxiosResponse<ApiResponse | any>) => {
    const body = response.data

    // 兼容格式1: 统一 ApiResponse { code, data, message, timestamp }
    if (body && typeof body.code === 'number') {
      if (body.code === 200 || body.code === 201) {
        return body.data as any
      }
      if (body.code === 401) {
        localStorage.removeItem('token')
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

    // 兼容格式2: 原始数据直接透传 (如后端某些接口直接返回数组/对象)
    return body
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    } else {
      const msg = error.response?.data?.message || error.message || '网络请求失败'
      ElMessage.error(msg)
    }
    return Promise.reject(error)
  }
)

export default request
