import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '@/stores/user'
import AppHeader from '@/components/common/AppHeader.vue'

describe('AppHeader.vue', () => {
  let router: ReturnType<typeof createRouter>

  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', redirect: '/home' },
        { path: '/home', name: 'Home', component: { template: '<div>Home</div>' } },
        { path: '/stocks', name: 'StockList', component: { template: '<div>Stocks</div>' } },
        { path: '/login', name: 'Login', component: { template: '<div>Login</div>' } },
      ],
    })
  })

  it('renders logo and navigation links', async () => {
    const wrapper = mount(AppHeader, {
      global: { plugins: [router] },
    })
    // Logo
    expect(wrapper.find('.logo').exists()).toBe(true)
    expect(wrapper.find('.logo-text').text()).toBe('StockAI')
    // Nav items
    const navLinks = wrapper.findAll('.nav-link')
    const navTexts = navLinks.map((el) => el.text())
    expect(navTexts.some((t) => t.includes('行情'))).toBe(true)
    expect(navTexts.some((t) => t.includes('AI分析'))).toBe(true)
  })

  it('shows login text when not authenticated', async () => {
    const wrapper = mount(AppHeader, {
      global: { plugins: [router] },
    })
    expect(wrapper.text()).toContain('登录')
  })

  it('shows username when authenticated', async () => {
    const store = useUserStore()
    store.token = 'mock-token'
    store.userInfo = { id: 1, username: 'testuser' } as any

    const wrapper = mount(AppHeader, {
      global: { plugins: [router] },
    })
    expect(wrapper.text()).toContain('testuser')
    expect(wrapper.find('.avatar').text()).toBe('T')
  })

  it('navigates to login on logout', async () => {
    const store = useUserStore()
    store.token = 'mock-token'
    store.logout = vi.fn()

    const wrapper = mount(AppHeader, {
      global: { plugins: [router] },
    })
    // Click user menu to open it
    await wrapper.find('.user-info').trigger('click')
    // Click logout
    const logoutItem = wrapper.findAll('.menu-item').at(-1)
    if (logoutItem) {
      await logoutItem.trigger('click')
    }
    expect(store.logout).toHaveBeenCalled()
  })
})
