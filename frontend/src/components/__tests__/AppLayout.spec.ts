import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import AppLayout from '@/components/common/AppLayout.vue'
import AppHeader from '@/components/common/AppHeader.vue'

describe('AppLayout.vue', () => {
  it('renders header and main slot', async () => {
    setActivePinia(createPinia())

    const router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: { template: '<div>Home</div>' } },
        { path: '/home', component: { template: '<div>Home</div>' } },
      ],
    })

    const wrapper = mount(AppLayout, {
      global: {
        plugins: [router],
        stubs: {
          'router-view': { template: '<div class="mock-view">Page Content</div>' },
        },
      },
    })

    expect(wrapper.findComponent(AppHeader).exists()).toBe(true)
    expect(wrapper.find('.main-content').exists()).toBe(true)
    expect(wrapper.find('.mock-view').exists()).toBe(true)
  })
})
