<script setup lang="ts">
import { usePlaygroundStore } from '~/stores/playground'

const store = usePlaygroundStore()
const models = ref<Array<{ provider: string; model: string }>>([])
const collections = ref<Array<{ id: string; name: string }>>([])
const linkedIds = ref<string[]>([])
const ragEnabled = ref(false)
const savingRag = ref(false)

onMounted(async () => {
  const { api } = useApi()
  const data = await api<Array<{ provider: string; model: string }>>('/models')
  models.value = data
  collections.value = await api<Array<{ id: string; name: string }>>('/knowledge/collections')
  if (store.agentId && store.versionId) {
    await loadRagConfig()
  }
})

async function loadRagConfig() {
  const { api } = useApi()
  const version = await api<{ rag_enabled: boolean }>(
    `/agents/${store.agentId}/versions/${store.versionId}`,
  )
  ragEnabled.value = version.rag_enabled
  const linked = await api<{ collection_ids: string[] }>(
    `/agents/${store.agentId}/versions/${store.versionId}/collections`,
  )
  linkedIds.value = linked.collection_ids
}

async function saveRagConfig() {
  if (!store.agentId || !store.versionId) return
  savingRag.value = true
  const { api } = useApi()
  try {
    await api(`/agents/${store.agentId}/versions/${store.versionId}/rag`, {
      method: 'PATCH',
      body: JSON.stringify({ rag_enabled: ragEnabled.value }),
    })
    await api(`/agents/${store.agentId}/versions/${store.versionId}/collections`, {
      method: 'PUT',
      body: JSON.stringify({ collection_ids: linkedIds.value }),
    })
  } finally {
    savingRag.value = false
  }
}

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

    <div class="border-t border-[var(--border)] pt-4">
      <label class="flex items-center gap-2 font-medium">
        <input v-model="ragEnabled" type="checkbox" @change="saveRagConfig">
        RAG enabled
      </label>
      <p class="mt-1 text-xs text-[var(--muted)]">Retrieve from linked collections before each turn.</p>
      <div v-if="collections.length" class="mt-3 space-y-2">
        <p class="text-xs font-medium text-[var(--muted)]">Linked collections</p>
        <label v-for="c in collections" :key="c.id" class="flex items-center gap-2 text-xs">
          <input v-model="linkedIds" type="checkbox" :value="c.id" @change="saveRagConfig">
          {{ c.name }}
        </label>
      </div>
      <NuxtLink v-else to="/knowledge" class="mt-2 inline-block text-xs text-[var(--accent)] hover:underline">
        Create a knowledge collection →
      </NuxtLink>
      <p v-if="savingRag" class="mt-2 text-xs text-[var(--muted)]">Saving RAG settings...</p>
    </div>
  </div>
</template>
