<script setup lang="ts">
import { usePlaygroundStore } from '~/stores/playground'

const store = usePlaygroundStore()
const models = ref<Array<{ provider: string; model: string }>>([])

onMounted(async () => {
  const { api } = useApi()
  const data = await api<Array<{ provider: string; model: string }>>('/models')
  models.value = data
})

const memoryModes = ['none', 'conversation', 'summarised']
</script>

<template>
  <div class="space-y-4 text-sm">
    <div>
      <label class="mb-1 block font-medium">System prompt</label>
      <textarea
        v-model="store.overrides.system_prompt"
        :placeholder="store.base.system_prompt"
        rows="8"
        class="mono w-full rounded-lg border border-[var(--border)] px-3 py-2 text-xs"
      />
    </div>
    <div>
      <label class="mb-1 block font-medium">Model</label>
      <select
        v-model="store.overrides.model"
        class="w-full rounded-lg border border-[var(--border)] px-3 py-2"
      >
        <option value="">{{ store.base.model }} (default)</option>
        <option v-for="m in models" :key="`${m.provider}-${m.model}`" :value="m.model">
          {{ m.provider }}/{{ m.model }}
        </option>
      </select>
    </div>
    <div>
      <label class="mb-1 block font-medium">Temperature</label>
      <input
        v-model.number="store.overrides.temperature"
        type="number"
        min="0"
        max="2"
        step="0.1"
        :placeholder="String(store.base.temperature)"
        class="w-full rounded-lg border border-[var(--border)] px-3 py-2"
      >
    </div>
    <div>
      <label class="mb-1 block font-medium">Memory mode</label>
      <select
        v-model="store.overrides.memory_mode"
        class="w-full rounded-lg border border-[var(--border)] px-3 py-2"
      >
        <option value="">{{ store.base.memory_mode }} (default)</option>
        <option v-for="mode in memoryModes" :key="mode" :value="mode">{{ mode }}</option>
      </select>
    </div>
  </div>
</template>
