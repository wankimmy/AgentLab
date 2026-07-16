import { defineStore } from 'pinia'

export interface PlaygroundOverrides {
  system_prompt: string
  model: string
  temperature: number
  memory_mode: string
}

export const usePlaygroundStore = defineStore('playground', {
  state: () => ({
    base: {
      system_prompt: '',
      model: 'mock-model',
      temperature: 0.3,
      memory_mode: 'conversation',
    } as PlaygroundOverrides,
    overrides: {
      system_prompt: '',
      model: '',
      temperature: null as number | null,
      memory_mode: '',
    },
    agentId: '' as string,
    versionId: '' as string,
  }),
  getters: {
    isDirty(state): boolean {
      return (
        (state.overrides.system_prompt !== '' &&
          state.overrides.system_prompt !== state.base.system_prompt) ||
        (state.overrides.model !== '' && state.overrides.model !== state.base.model) ||
        state.overrides.temperature !== null ||
        (state.overrides.memory_mode !== '' &&
          state.overrides.memory_mode !== state.base.memory_mode)
      )
    },
    effective(state): PlaygroundOverrides {
      return {
        system_prompt: state.overrides.system_prompt || state.base.system_prompt,
        model: state.overrides.model || state.base.model,
        temperature: state.overrides.temperature ?? state.base.temperature,
        memory_mode: state.overrides.memory_mode || state.base.memory_mode,
      }
    },
    apiOverrides(state): Record<string, unknown> | null {
      const eff = {
        system_prompt:
          state.overrides.system_prompt && state.overrides.system_prompt !== state.base.system_prompt
            ? state.overrides.system_prompt
            : undefined,
        model:
          state.overrides.model && state.overrides.model !== state.base.model
            ? state.overrides.model
            : undefined,
        temperature: state.overrides.temperature ?? undefined,
        memory_mode:
          state.overrides.memory_mode && state.overrides.memory_mode !== state.base.memory_mode
            ? state.overrides.memory_mode
            : undefined,
      }
      const filtered = Object.fromEntries(
        Object.entries(eff).filter(([, v]) => v !== undefined && v !== null),
      )
      return Object.keys(filtered).length ? filtered : null
    },
  },
  actions: {
    initFromVersion(
      agentId: string,
      versionId: string,
      version: {
        system_prompt: string
        model: string
        model_settings?: { temperature?: number }
        memory_config?: { mode?: string }
      },
    ) {
      this.agentId = agentId
      this.versionId = versionId
      this.base = {
        system_prompt: version.system_prompt,
        model: version.model,
        temperature: version.model_settings?.temperature ?? 0.3,
        memory_mode: version.memory_config?.mode ?? 'conversation',
      }
      this.overrides = {
        system_prompt: '',
        model: '',
        temperature: null,
        memory_mode: '',
      }
    },
    discard() {
      this.overrides = {
        system_prompt: '',
        model: '',
        temperature: null,
        memory_mode: '',
      }
    },
  },
})
