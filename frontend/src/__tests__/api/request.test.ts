import { describe, it, expect } from 'vitest'

describe('API request module', () => {
  it('模块可正常加载', async () => {
    // 验证 request 模块可以正常 import
    const request = await import('@/api/request')
    expect(request.default).toBeDefined()
  })

  it('axios 实例已正确配置 baseURL', async () => {
    const request = await import('@/api/request')
    const instance = request.default
    // 检查实例的基本属性
    expect(instance.defaults).toBeDefined()
    expect(instance.defaults.baseURL).toBe('/api')
    expect(instance.defaults.timeout).toBe(15000)
  })
})
