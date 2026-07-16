<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

const route = useRoute()
const { api } = useApi()
const datasetId = route.params.id as string

interface CaseRow {
  id: string
  name: string
  category: string
  user_message: string
  expected_answer: string | null
  severity: string
}

interface VersionDetail {
  id: string
  version_number: number
  case_count: number
  cases: CaseRow[]
}

interface DatasetDetail {
  id: string
  name: string
  description: string
  versions: { id: string; version_number: number; case_count: number }[]
}

const dataset = ref<DatasetDetail | null>(null)
const version = ref<VersionDetail | null>(null)
const loading = ref(true)
const importing = ref(false)
const newCase = ref({ name: '', user_message: '', category: '', expected_answer: '' })

onMounted(load)

async function load() {
  loading.value = true
  try {
    dataset.value = await api<DatasetDetail>(`/evaluations/datasets/${datasetId}`)
    const latest = dataset.value.versions[0]
    if (latest) {
      version.value = await api<VersionDetail>(
        `/evaluations/datasets/${datasetId}/versions/${latest.id}`,
      )
    }
  } finally {
    loading.value = false
  }
}

async function addCase() {
  if (!version.value || !newCase.value.name.trim() || !newCase.value.user_message.trim()) return
  await api(`/evaluations/datasets/${datasetId}/versions/${version.value.id}/cases`, {
    method: 'POST',
    body: JSON.stringify({
      name: newCase.value.name,
      user_message: newCase.value.user_message,
      category: newCase.value.category,
      expected_answer: newCase.value.expected_answer || null,
    }),
  })
  newCase.value = { name: '', user_message: '', category: '', expected_answer: '' }
  await load()
}

async function onImport(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  importing.value = true
  try {
    const form = new FormData()
    form.append('file', file)
    await fetch(`/api/v1/evaluations/datasets/${datasetId}/import`, {
      method: 'POST',
      body: form,
      credentials: 'include',
    })
    await load()
  } finally {
    importing.value = false
    input.value = ''
  }
}

function exportUrl(format: 'json' | 'csv') {
  return `/api/v1/evaluations/datasets/${datasetId}/export?format=${format}`
}
</script>

<template>
  <div>
    <NuxtLink to="/evaluations/datasets" class="text-sm text-[var(--accent)]">← Datasets</NuxtLink>
    <h1 class="mt-2 text-3xl font-semibold">{{ dataset?.name || 'Dataset' }}</h1>
    <p class="mt-1 text-[var(--muted)]">{{ dataset?.description }}</p>

    <p v-if="loading" class="mt-8 text-sm text-[var(--muted)]">Loading...</p>

    <div v-else class="mt-8 space-y-8">
      <section class="flex flex-wrap gap-3">
        <a
          :href="exportUrl('json')"
          class="rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
        >Export JSON</a>
        <a
          :href="exportUrl('csv')"
          class="rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
        >Export CSV</a>
        <label class="cursor-pointer rounded-lg border border-[var(--border)] px-3 py-2 text-sm">
          {{ importing ? 'Importing...' : 'Import file' }}
          <input type="file" accept=".json,.csv" class="hidden" :disabled="importing" @change="onImport">
        </label>
        <NuxtLink
          to="/evaluations/runs/new"
          class="rounded-lg bg-[var(--accent)] px-3 py-2 text-sm font-medium text-white"
        >
          Run evaluation
        </NuxtLink>
      </section>

      <section class="rounded-xl border border-[var(--border)] bg-white p-6">
        <h2 class="font-medium">Add case (v{{ version?.version_number }})</h2>
        <div class="mt-4 grid gap-3 sm:grid-cols-2">
          <input v-model="newCase.name" placeholder="Name" class="rounded-lg border px-3 py-2 text-sm">
          <input v-model="newCase.category" placeholder="Category" class="rounded-lg border px-3 py-2 text-sm">
          <textarea
            v-model="newCase.user_message"
            placeholder="User message"
            rows="2"
            class="sm:col-span-2 rounded-lg border px-3 py-2 text-sm"
          />
          <input
            v-model="newCase.expected_answer"
            placeholder="Expected answer (optional)"
            class="sm:col-span-2 rounded-lg border px-3 py-2 text-sm"
          >
        </div>
        <button
          type="button"
          class="mt-3 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm text-white"
          @click="addCase"
        >
          Add case
        </button>
      </section>

      <section>
        <h2 class="font-medium">Cases ({{ version?.case_count ?? 0 }})</h2>
        <table v-if="version?.cases.length" class="mt-4 w-full text-left text-sm">
          <thead>
            <tr class="border-b text-[var(--muted)]">
              <th class="py-2 pr-4">Name</th>
              <th class="py-2 pr-4">Category</th>
              <th class="py-2">Message</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in version.cases" :key="c.id" class="border-b border-[var(--border)]">
              <td class="py-3 pr-4 font-medium">{{ c.name }}</td>
              <td class="py-3 pr-4">{{ c.category }}</td>
              <td class="py-3 text-[var(--muted)]">{{ c.user_message }}</td>
            </tr>
          </tbody>
        </table>
        <EmptyState v-else class="mt-4" title="No cases" description="Add cases or import JSON/CSV." />
      </section>
    </div>
  </div>
</template>
