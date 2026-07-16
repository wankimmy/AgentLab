<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

const route = useRoute()
const collectionId = route.params.id as string
const { api } = useApi()

interface Collection {
  id: string
  name: string
  description: string
  purpose: string
  readiness_status: string
  planning_metadata: Record<string, string>
  document_count: number
  ready_document_count: number
}

interface DocumentRow {
  id: string
  filename: string
  status: string
  chunk_count: number
  error_info?: { message?: string } | null
}

const collection = ref<Collection | null>(null)
const documents = ref<DocumentRow[]>([])
const uploading = ref(false)
const checking = ref(false)
const reindexDocId = ref<string | null>(null)
const checklist = ref<Record<string, boolean>>({})
const readyMessages = ref<string[]>([])

const checklistFields = [
  { key: 'authoritative_source', label: 'Authoritative source identified' },
  { key: 'source_owner', label: 'Source owner identified' },
  { key: 'effective_date', label: 'Effective date recorded' },
  { key: 'review_schedule', label: 'Review schedule set' },
  { key: 'sensitive_data_removed', label: 'Sensitive data removed' },
]

onMounted(async () => {
  await refresh()
})

async function refresh() {
  collection.value = await api<Collection>(`/knowledge/collections/${collectionId}`)
  documents.value = await api<DocumentRow[]>(`/knowledge/collections/${collectionId}/documents`)
  const meta = collection.value.planning_metadata || {}
  checklist.value = Object.fromEntries(checklistFields.map((f) => [f.key, Boolean(meta[f.key])]))
}

async function saveMetadata() {
  if (!collection.value) return
  await api(`/knowledge/collections/${collectionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ planning_metadata: checklist.value }),
  })
  await refresh()
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploading.value = true
  try {
    const form = new FormData()
    form.append('file', file)
    const response = await fetch(`/api/v1/knowledge/collections/${collectionId}/documents`, {
      method: 'POST',
      credentials: 'include',
      body: form,
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || 'Upload failed')
    }
    await refresh()
    await pollUntilReady()
  } finally {
    uploading.value = false
    input.value = ''
  }
}

async function pollUntilReady(attempts = 12) {
  for (let i = 0; i < attempts; i++) {
    await refresh()
    const pending = documents.value.some((d) => d.status === 'processing' || d.status === 'uploaded')
    if (!pending) return
    await new Promise((r) => setTimeout(r, 500))
  }
}

async function runReadyCheck() {
  checking.value = true
  try {
    await saveMetadata()
    const result = await api<{
      ready: boolean
      readiness_status: string
      messages: string[]
    }>(`/knowledge/collections/${collectionId}/ready-check`, { method: 'POST' })
    readyMessages.value = result.messages
    await refresh()
  } finally {
    checking.value = false
  }
}

async function reindex(docId: string) {
  if (!confirm('Reindex will regenerate embeddings and may incur API cost. Continue?')) return
  reindexDocId.value = docId
  try {
    await api(`/knowledge/documents/${docId}/reindex`, { method: 'POST' })
    await pollUntilReady()
  } finally {
    reindexDocId.value = null
  }
}
</script>

<template>
  <div v-if="collection">
    <NuxtLink to="/knowledge" class="text-sm text-[var(--muted)] hover:text-[var(--accent)]">← Collections</NuxtLink>
    <h1 class="mt-4 text-3xl font-semibold">{{ collection.name }}</h1>
    <p class="mt-1 text-[var(--muted)]">{{ collection.purpose || collection.description }}</p>
    <p class="mt-2 text-sm">
      Status: <span class="font-medium">{{ collection.readiness_status }}</span>
      · {{ collection.ready_document_count }}/{{ collection.document_count }} documents ready
    </p>

    <section class="mt-8 rounded-xl border border-[var(--border)] bg-white p-6">
      <h2 class="font-medium">Upload documents</h2>
      <p class="mt-1 text-sm text-[var(--muted)]">MD, TXT, FAQ CSV, or text-based PDF (max 10MB)</p>
      <input
        type="file"
        accept=".md,.txt,.csv,.pdf"
        class="mt-4 block text-sm"
        :disabled="uploading"
        @change="onFileChange"
      >
      <p v-if="uploading" class="mt-2 text-sm text-[var(--muted)]">Uploading and processing...</p>
    </section>

    <section class="mt-8">
      <h2 class="font-medium">Documents</h2>
      <p v-if="!documents.length" class="mt-4 text-sm text-[var(--muted)]">No documents yet.</p>
      <ul v-else class="mt-4 space-y-3">
        <li
          v-for="doc in documents"
          :key="doc.id"
          class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--border)] bg-white p-4"
        >
          <div>
            <NuxtLink :to="`/knowledge/documents/${doc.id}`" class="font-medium hover:text-[var(--accent)]">
              {{ doc.filename }}
            </NuxtLink>
            <p class="text-sm text-[var(--muted)]">
              {{ doc.status }} · {{ doc.chunk_count }} chunks
              <span v-if="doc.error_info?.message"> · {{ doc.error_info.message }}</span>
            </p>
          </div>
          <button
            v-if="doc.status === 'ready'"
            type="button"
            class="text-sm text-[var(--accent)] hover:underline disabled:opacity-50"
            :disabled="reindexDocId === doc.id"
            @click="reindex(doc.id)"
          >
            Reindex
          </button>
        </li>
      </ul>
    </section>

    <section class="mt-8 rounded-xl border border-[var(--border)] bg-white p-6">
      <h2 class="font-medium">Readiness checklist</h2>
      <ul class="mt-4 space-y-2 text-sm">
        <li v-for="field in checklistFields" :key="field.key" class="flex items-center gap-2">
          <input v-model="checklist[field.key]" type="checkbox" @change="saveMetadata">
          {{ field.label }}
        </li>
      </ul>
      <button
        type="button"
        class="mt-4 rounded-lg border border-[var(--border)] px-4 py-2 text-sm hover:bg-slate-50"
        :disabled="checking"
        @click="runReadyCheck"
      >
        Run ready check
      </button>
      <ul v-if="readyMessages.length" class="mt-3 list-disc pl-5 text-sm text-amber-700">
        <li v-for="(msg, i) in readyMessages" :key="i">{{ msg }}</li>
      </ul>
    </section>
  </div>
</template>
