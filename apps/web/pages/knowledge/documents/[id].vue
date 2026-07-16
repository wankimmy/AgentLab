<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

const route = useRoute()
const documentId = route.params.id as string
const { api } = useApi()

interface DocumentDetail {
  id: string
  collection_id: string
  filename: string
  status: string
  chunk_count: number
  extracted_text: string
}

interface Chunk {
  id: string
  content: string
  token_count: number
  heading: string | null
  sort_order: number
}

const document = ref<DocumentDetail | null>(null)
const chunks = ref<Chunk[]>([])

onMounted(async () => {
  document.value = await api<DocumentDetail>(`/knowledge/documents/${documentId}`)
  chunks.value = await api<Chunk[]>(`/knowledge/documents/${documentId}/chunks`)
})
</script>

<template>
  <div v-if="document">
    <NuxtLink
      :to="`/knowledge/collections/${document.collection_id}`"
      class="text-sm text-[var(--muted)] hover:text-[var(--accent)]"
    >
      ← Back to collection
    </NuxtLink>
    <h1 class="mt-4 text-2xl font-semibold">{{ document.filename }}</h1>
    <p class="mt-1 text-sm text-[var(--muted)]">{{ document.status }} · {{ document.chunk_count }} chunks</p>

    <section class="mt-8 rounded-xl border border-[var(--border)] bg-white p-6">
      <h2 class="font-medium">Extracted text</h2>
      <pre class="mono mt-4 max-h-64 overflow-y-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-xs">{{ document.extracted_text || '(empty)' }}</pre>
    </section>

    <section class="mt-8">
      <h2 class="font-medium">Chunks</h2>
      <p v-if="!chunks.length" class="mt-4 text-sm text-[var(--muted)]">No chunks yet.</p>
      <ol v-else class="mt-4 space-y-3">
        <li
          v-for="chunk in chunks"
          :key="chunk.id"
          class="rounded-lg border border-[var(--border)] bg-white p-4 text-sm"
        >
          <p class="text-xs text-[var(--muted)]">
            #{{ chunk.sort_order + 1 }}
            <span v-if="chunk.heading"> · {{ chunk.heading }}</span>
            · ~{{ chunk.token_count }} tokens
          </p>
          <p class="mt-2 whitespace-pre-wrap">{{ chunk.content }}</p>
        </li>
      </ol>
    </section>
  </div>
</template>
