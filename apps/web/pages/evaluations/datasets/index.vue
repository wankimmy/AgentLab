<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

const { api } = useApi()
const router = useRouter()

interface Dataset {
  id: string
  name: string
  description: string
  latest_version: number | null
  case_count: number
}

interface Template {
  id: string
  name: string
}

const datasets = ref<Dataset[]>([])
const templates = ref<Template[]>([])
const loading = ref(true)
const creating = ref(false)
const fromTemplate = ref('')
const form = ref({ name: '', description: '' })

onMounted(load)

async function load() {
  loading.value = true
  try {
    const [ds, tpl] = await Promise.all([
      api<Dataset[]>('/evaluations/datasets'),
      api<Template[]>('/templates'),
    ])
    datasets.value = ds
    templates.value = tpl
  } finally {
    loading.value = false
  }
}

async function createDataset() {
  if (!form.value.name.trim()) return
  creating.value = true
  try {
    const created = await api<Dataset>('/evaluations/datasets', {
      method: 'POST',
      body: JSON.stringify(form.value),
    })
    form.value = { name: '', description: '' }
    await router.push(`/evaluations/datasets/${created.id}`)
  } finally {
    creating.value = false
  }
}

async function createFromTemplate() {
  if (!fromTemplate.value) return
  creating.value = true
  try {
    const created = await api<Dataset>(`/evaluations/datasets/from-template/${fromTemplate.value}`, {
      method: 'POST',
    })
    fromTemplate.value = ''
    await router.push(`/evaluations/datasets/${created.id}`)
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between gap-4">
      <div>
        <h1 class="text-3xl font-semibold">Evaluation datasets</h1>
        <p class="mt-1 text-[var(--muted)]">Versioned test cases for agent quality checks</p>
      </div>
      <NuxtLink to="/evaluations" class="text-sm text-[var(--accent)]">← Runs</NuxtLink>
    </div>

    <div class="mt-8 grid gap-6 lg:grid-cols-3">
      <div class="space-y-6 lg:col-span-2">
        <section class="rounded-xl border border-[var(--border)] bg-white p-6">
          <h2 class="font-medium">New dataset</h2>
          <div class="mt-4 space-y-3">
            <input
              v-model="form.name"
              type="text"
              placeholder="Dataset name"
              class="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
            >
            <textarea
              v-model="form.description"
              rows="2"
              placeholder="Description"
              class="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
            />
            <button
              type="button"
              class="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              :disabled="creating || !form.name.trim()"
              @click="createDataset"
            >
              Create empty dataset
            </button>
          </div>
        </section>

        <section class="rounded-xl border border-[var(--border)] bg-white p-6">
          <h2 class="font-medium">From agent template</h2>
          <p class="mt-1 text-sm text-[var(--muted)]">Materialize eval_starter_pack cases from a template.</p>
          <div class="mt-4 flex flex-wrap gap-2">
            <select
              v-model="fromTemplate"
              class="min-w-[12rem] flex-1 rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
            >
              <option value="">Select template</option>
              <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.name }}</option>
            </select>
            <button
              type="button"
              class="rounded-lg border border-[var(--border)] px-4 py-2 text-sm font-medium disabled:opacity-50"
              :disabled="creating || !fromTemplate"
              @click="createFromTemplate"
            >
              Create from template
            </button>
          </div>
        </section>

        <section>
          <h2 class="font-medium">Your datasets</h2>
          <p v-if="loading" class="mt-4 text-sm text-[var(--muted)]">Loading...</p>
          <ul v-else-if="datasets.length" class="mt-4 space-y-3">
            <li
              v-for="d in datasets"
              :key="d.id"
              class="rounded-lg border border-[var(--border)] bg-white p-4"
            >
              <NuxtLink
                :to="`/evaluations/datasets/${d.id}`"
                class="font-medium hover:text-[var(--accent)]"
              >
                {{ d.name }}
              </NuxtLink>
              <p class="mt-1 text-sm text-[var(--muted)]">
                v{{ d.latest_version ?? 1 }} · {{ d.case_count }} cases
              </p>
            </li>
          </ul>
          <EmptyState
            v-else
            class="mt-4"
            title="No datasets"
            description="Create one or import from an agent template starter pack."
          />
        </section>
      </div>

      <HelpPanel
        title="Datasets"
        why="Immutable versions let you compare runs over time without case drift."
        :steps="['Create or import', 'Add cases', 'Run evaluation']"
        :mistakes="['Editing cases without versioning', 'Mixing prod and test data']"
      />
    </div>
  </div>
</template>
