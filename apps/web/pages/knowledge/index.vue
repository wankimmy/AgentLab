<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

const { api } = useApi()
const router = useRouter()

interface Collection {
  id: string
  name: string
  description: string
  purpose: string
  readiness_status: string
  document_count: number
  ready_document_count: number
}

const collections = ref<Collection[]>([])
const loading = ref(true)
const creating = ref(false)
const form = ref({ name: '', description: '', purpose: '' })

onMounted(load)

async function load() {
  loading.value = true
  try {
    collections.value = await api<Collection[]>('/knowledge/collections')
  } finally {
    loading.value = false
  }
}

async function createCollection() {
  if (!form.value.name.trim()) return
  creating.value = true
  try {
    const created = await api<Collection>('/knowledge/collections', {
      method: 'POST',
      body: JSON.stringify(form.value),
    })
    form.value = { name: '', description: '', purpose: '' }
    await router.push(`/knowledge/collections/${created.id}`)
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="text-3xl font-semibold">Knowledge</h1>
    <p class="mt-1 text-[var(--muted)]">Collections, document upload, and RAG readiness</p>

    <div class="mt-8 grid gap-6 lg:grid-cols-3">
      <div class="space-y-6 lg:col-span-2">
        <section class="rounded-xl border border-[var(--border)] bg-white p-6">
          <h2 class="font-medium">New collection</h2>
          <div class="mt-4 space-y-3">
            <input
              v-model="form.name"
              type="text"
              placeholder="Collection name"
              class="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
            >
            <textarea
              v-model="form.description"
              rows="2"
              placeholder="Description"
              class="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
            />
            <input
              v-model="form.purpose"
              type="text"
              placeholder="Purpose (e.g. ERP support policies)"
              class="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
            >
            <button
              type="button"
              class="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              :disabled="creating || !form.name.trim()"
              @click="createCollection"
            >
              Create collection
            </button>
          </div>
        </section>

        <section>
          <h2 class="font-medium">Your collections</h2>
          <p v-if="loading" class="mt-4 text-sm text-[var(--muted)]">Loading...</p>
          <EmptyState
            v-else-if="!collections.length"
            title="No knowledge collections yet"
            description="Upload approved documents to ground agent answers with citations."
            :actions="[
              { label: 'Read RAG guide', to: '/learning/what-is-rag' },
              { label: 'Retrieval debugger', to: '/retrieval-debugger' },
            ]"
          />
          <ul v-else class="mt-4 space-y-3">
            <li
              v-for="c in collections"
              :key="c.id"
              class="rounded-lg border border-[var(--border)] bg-white p-4"
            >
              <NuxtLink :to="`/knowledge/collections/${c.id}`" class="font-medium hover:text-[var(--accent)]">
                {{ c.name }}
              </NuxtLink>
              <p class="mt-1 text-sm text-[var(--muted)]">{{ c.description || 'No description' }}</p>
              <p class="mt-2 text-xs text-[var(--muted)]">
                {{ c.ready_document_count }}/{{ c.document_count }} ready · {{ c.readiness_status }}
              </p>
            </li>
          </ul>
        </section>
      </div>

      <HelpPanel
        title="Knowledge collections"
        why="RAG retrieves relevant document chunks before the model answers."
        :needs="['Approved PDFs or markdown', 'Sensitive data removed', 'Collection linked to agent']"
        :steps="['Create collection', 'Upload documents', 'Link to agent version', 'Test citations']"
        :mistakes="['Uploading draft policies', 'Mixing unrelated domains in one collection']"
        :next-action="{ label: 'Prepare knowledge guide', to: '/learning/how-to-prepare-knowledge' }"
      />
    </div>
  </div>
</template>
