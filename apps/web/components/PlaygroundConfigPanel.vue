<script setup lang="ts">
import { usePlaygroundStore } from '~/stores/playground'

const store = usePlaygroundStore()
const models = ref<Array<{ provider: string; model: string }>>([])
const collections = ref<Array<{ id: string; name: string }>>([])
const linkedIds = ref<string[]>([])
const ragEnabled = ref(false)
const savingRag = ref(false)
const toolModes = ref<Record<string, string>>({
  calculator: 'auto',
  knowledge_search: 'auto',
  current_datetime: 'auto',
})
const savingTools = ref(false)

const toolNames = ['calculator', 'knowledge_search', 'current_datetime']
const modeOptions = ['auto', 'approval', 'disabled']

onMounted(async () => {
  const { api } = useApi()
  models.value = await api<Array<{ provider: string; model: string }>>('/models')
  collections.value = await api<Array<{ id: string; name: string }>>('/knowledge/collections')
  if (store.agentId && store.versionId) {
    await loadVersionConfig()
  }
})

async function loadVersionConfig() {
  const { api } = useApi()
  const version = await api<{ rag_enabled: boolean; tool_config?: Record<string, string> }>(
    `/agents/${store.agentId}/versions/${store.versionId}`,
  )
  ragEnabled.value = version.rag_enabled
  const linked = await api<{ collection_ids: string[] }>(
    `/agents/${store.agentId}/versions/${store.versionId}/collections`,
  )
  linkedIds.value = linked.collection_ids
  const cfg = version.tool_config || {}
  for (const name of toolNames) {
    toolModes.value[name] = String(cfg[name] || 'disabled')
  }
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

async function saveToolConfig() {
  if (!store.agentId || !store.versionId) return
  savingTools.value = true
  const { api } = useApi()
  try {
    await api(`/agents/${store.agentId}/versions/${store.versionId}/tools`, {
      method: 'PATCH',
      body: JSON.stringify({ tool_config: { ...toolModes.value } }),
    })
  } finally {
    savingTools.value = false
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
      <p class="font-medium">Tools</p>
      <p class="mt-1 text-xs text-[var(--muted)]">Per-tool execution mode for this version.</p>
      <div v-for="name in toolNames" :key="name" class="mt-2 flex items-center justify-between">
        <span class="text-xs">{{ name }}</span>
        <select
          v-model="toolModes[name]"
          class="rounded border border-[var(--border)] px-2 py-1 text-xs"
          @change="saveToolConfig"
        >
          <option v-for="m in modeOptions" :key="m" :value="m">{{ m }}</option>
        </select>
      </div>
      <p v-if="savingTools" class="mt-2 text-xs text-[var(--muted)]">Saving tool settings...</p>
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
