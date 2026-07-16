<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

const { api } = useApi()

interface Collection {
  id: string
  name: string
}

interface AgentItem {
  id: string
  name: string
  active_version?: { id: string }
}

interface DebugChunk {
  chunk_id: string
  document_name: string
  score: number
  heading: string | null
  excerpt: string
  content: string
}

const query = ref('')
const mode = ref('hybrid')
const topK = ref(5)
const collections = ref<Collection[]>([])
const agents = ref<AgentItem[]>([])
const selectedCollectionIds = ref<string[]>([])
const selectedVersionId = ref('')
const loading = ref(false)
const results = ref<DebugChunk[]>([])
const resultMode = ref('')

onMounted(async () => {
  collections.value = await api<Collection[]>('/knowledge/collections')
  const agentList = await api<{ items: AgentItem[] }>('/agents')
  agents.value = agentList.items
})

async function runDebug() {
  if (!query.value.trim()) return
  loading.value = true
  try {
    const body: Record<string, unknown> = {
      query: query.value,
      retrieval_config: { mode: mode.value, top_k: topK.value, threshold: 0 },
    }
    if (selectedVersionId.value) {
      body.agent_version_id = selectedVersionId.value
    } else if (selectedCollectionIds.value.length) {
      body.collection_ids = selectedCollectionIds.value
    }
    const data = await api<{ mode: string; chunks: DebugChunk[] }>('/knowledge/retrieval/debug', {
      method: 'POST',
      body: JSON.stringify(body),
    })
    results.value = data.chunks
    resultMode.value = data.mode
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="text-3xl font-semibold">Retrieval debugger</h1>
    <p class="mt-1 text-[var(--muted)]">Test hybrid search against linked collections</p>

    <section class="mt-8 space-y-4 rounded-xl border border-[var(--border)] bg-white p-6">
      <div>
        <label class="mb-1 block text-sm font-medium">Query</label>
        <textarea
          v-model="query"
          rows="3"
          class="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
          placeholder="What is three-way matching?"
        />
      </div>

      <div class="grid gap-4 sm:grid-cols-3">
        <div>
          <label class="mb-1 block text-sm font-medium">Mode</label>
          <select v-model="mode" class="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm">
            <option value="hybrid">Hybrid</option>
            <option value="semantic">Semantic</option>
            <option value="keyword">Keyword</option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium">Top K</label>
          <input v-model.number="topK" type="number" min="1" max="20" class="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm">
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium">Agent version (optional)</label>
          <select v-model="selectedVersionId" class="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm">
            <option value="">— Collections only —</option>
            <option
              v-for="agent in agents"
              :key="agent.id"
              :value="agent.active_version?.id || ''"
              :disabled="!agent.active_version"
            >
              {{ agent.name }} (active)
            </option>
          </select>
        </div>
      </div>

      <div v-if="!selectedVersionId">
        <label class="mb-1 block text-sm font-medium">Collections</label>
        <div class="flex flex-wrap gap-3 text-sm">
          <label v-for="c in collections" :key="c.id" class="flex items-center gap-2">
            <input v-model="selectedCollectionIds" type="checkbox" :value="c.id">
            {{ c.name }}
          </label>
        </div>
      </div>

      <button
        type="button"
        class="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        :disabled="loading"
        @click="runDebug"
      >
        Run retrieval
      </button>
    </section>

    <section v-if="results.length" class="mt-8">
      <h2 class="font-medium">Results ({{ resultMode }})</h2>
      <ol class="mt-4 space-y-3">
        <li
          v-for="(chunk, i) in results"
          :key="chunk.chunk_id"
          class="rounded-lg border border-[var(--border)] bg-white p-4 text-sm"
        >
          <p class="text-xs text-[var(--muted)]">
            #{{ i + 1 }} · {{ chunk.document_name }}
            <span v-if="chunk.heading"> · {{ chunk.heading }}</span>
            · score {{ chunk.score.toFixed(4) }}
          </p>
          <p class="mt-2 font-medium">{{ chunk.excerpt }}</p>
          <p class="mt-2 whitespace-pre-wrap text-[var(--muted)]">{{ chunk.content }}</p>
        </li>
      </ol>
    </section>
    <p v-else-if="!loading" class="mt-8 text-sm text-[var(--muted)]">No results yet.</p>
  </div>
</template>
