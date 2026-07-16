import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import HelpPanel from '../components/HelpPanel.vue'

describe('HelpPanel', () => {
  it('renders title and toggles content', async () => {
    const wrapper = mount(HelpPanel, {
      props: {
        title: 'Test help',
        why: 'Because testing matters',
        steps: ['Step one'],
      },
    })
    expect(wrapper.text()).toContain('Test help')
    expect(wrapper.text()).not.toContain('Step one')
    await wrapper.find('button').trigger('click')
    expect(wrapper.text()).toContain('Step one')
  })
})
