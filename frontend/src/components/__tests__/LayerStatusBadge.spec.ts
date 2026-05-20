import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import LayerStatusBadge from '@/components/layer/LayerStatusBadge.vue'

describe('LayerStatusBadge.vue', () => {
  it('renders completed status correctly', () => {
    const wrapper = mount(LayerStatusBadge, {
      props: { status: 'completed' },
    })
    expect(wrapper.text()).toContain('已完成')
    expect(wrapper.find('.dot').exists()).toBe(true)
    expect(wrapper.classes()).toContain('status-completed')
  })

  it('renders in_progress status correctly', () => {
    const wrapper = mount(LayerStatusBadge, {
      props: { status: 'in_progress' },
    })
    expect(wrapper.text()).toContain('开发中')
    expect(wrapper.classes()).toContain('status-in-progress')
  })

  it('renders blocked status correctly', () => {
    const wrapper = mount(LayerStatusBadge, {
      props: { status: 'blocked' },
    })
    expect(wrapper.text()).toContain('阻塞')
    expect(wrapper.classes()).toContain('status-blocked')
  })

  it('renders pending status correctly', () => {
    const wrapper = mount(LayerStatusBadge, {
      props: { status: 'pending' },
    })
    expect(wrapper.text()).toContain('待开始')
    expect(wrapper.classes()).toContain('status-pending')
  })
})
