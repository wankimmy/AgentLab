<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

const { api } = useApi()
const router = useRouter()

interface Agent {
  id: string
  name: string
  active_version: { id: string }
}

interface Dataset {
  id: string
  name: string
  versions: { id: string; version_number: number; case_count: number }[]
}

interface Preset {
  id: string
  name: string
  description: string
}

interface Estimate {
  estimated_cost: number
  case_count: number
  mode: string
  warnings: string[]
}

const agents = ref<Agent[]>([])
const datasets = ref<Dataset[]>([])
const presets = ref<Preset[]>([])
const loading = ref(true)
const estimating = ref(false)
const starting = ref(false)
const estimate = ref<Estimate | null>(null)
const versionOptions = ref<{ id: string; label: string }[]>([])

const form = ref({
  agent_version_id: '',
  dataset_version_id: '',
  mode: 'quick',
  preset_id: 'customer_support_quality',
  include_semantic: true,
  judge_enabled: null as boolean | null,
})

onMounted(load)

async function load() {
  loading.value = true
  try {
    const [agentRes, dsList, presetList] = await Promise.all([
      api<{ items: Agent[] }>('/agents'),
      api<Dataset[]>('/evaluations/datasets'),
      api<Preset[]>('/evaluations/templates'),
    ])
    agents.value = agentRes.items
    datasets.value = dsList
    presets.value = presetList
    if (agentRes.items[0]?.active_version) {
      form.value.agent_version_id = agentRes.items[0].active_version.id
    }
    const firstDs = dsList[0]
    if (firstDs?.versions?.[0]) {
      form.value.dataset_version_id = firstDs.versions[0].id
    } else if (firstDs) {
      const detail = await api<Dataset>(`/evaluations/datasets/${firstDs.id}`)
      if (detail.versions?.[0]) {
        form.value.dataset_version_id = detail.versions[0].id
      }
    }
    await buildVersionOptions()
  } finally {
    loading.value = false
  }
}

async function buildVersionOptions() {
  const options: { id: string; label: string }[] = []
  for (const d of datasets.value) {
    let versions = d.versions
    if (!versions?.length) {
      const detail = await api<Dataset>(`/evaluations/datasets/${d.id}`)
      versions = detail.versions
    }
    for (const v of versions || []) {
      options.push({ id: v.id, label: `${d.name} v${v.version_number} (${v.case_count} cases)` })
    }
  }
  versionOptions.value = options
  if (!form.value.dataset_version_id && options[0]) {
    form.value.dataset_version_id = options[0].id
  }
}

async function runEstimate() {
  estimating.value = true
  estimate.value = null
  try {
    const body: Record<string, unknown> = { ...form.value }
    if (form.value.mode === 'standard' && form.value.judge_enabled === null) {
      body.judge_enabled = true
    }
    if (form.value.mode === 'release') {
      body.judge_enabled = true
    }
    if (form.value.mode === 'quick') {
      body.judge_enabled = form.value.judge_enabled ?? false
    }
    estimate.value = await api<Estimate>('/evaluations/runs/estimate', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  } finally {
    estimating.value = false
  }
}

async function confirmRun() {
  starting.value = true
  try {
    const body: Record<string, unknown> = { ...form.value }
    if (form.value.mode === 'standard' && form.value.judge_enabled === null) {
      body.judge_enabled = true
    }
    if (form.value.mode === 'release') {
      body.judge_enabled = true
    }
    const run = await api<{ id: string }>('/evaluations/runs', {
      method: 'POST',
      body: JSON.stringify(body),
    })
    await router.push(`/evaluations/runs/${run.id}`)
  } finally {
    starting.value = false
  }
}
</script>

<template>
  <div>
    <NuxtLink to="/evaluations" class="text-sm text-[var(--accent)]">← Evaluations</NuxtLink>
    <h1 class="mt-2 text-3xl font-semibold">New evaluation run</h1>
    <p class="mt-1 text-[var(--muted)]">Estimate cost, then confirm to start background run</p>

    <p v-if="loading" class="mt-8 text-sm text-[var(--muted)]">Loading...</p>

    <div v-else class="mt-8 max-w-xl space-y-4">
      <label class="block text-sm">
        <span class="font-medium">Agent version</span>
        <select v-model="form.agent_version_id" class="mt-1 w-full rounded-lg border px-3 py-2">
          <option v-for="a in agents" :key="a.id" :value="a.active_version.id">
            {{ a.name }}
          </option>
        </select>
      </label>

      <label class="block text-sm">
        <span class="font-medium">Dataset version</span>
        <select v-model="form.dataset_version_id" class="mt-1 w-full rounded-lg border px-3 py-2">
          <option v-for="v in versionOptions" :key="v.id" :value="v.id">{{ v.label }}</option>
        </select>
      </label>

      <label class="block text-sm">
        <span class="font-medium">Mode</span>
        <select v-model="form.mode" class="mt-1 w-full rounded-lg border px-3 py-2">
          <option value="quick">Quick Check</option>
          <option value="standard">Standard</option>
          <option value="release">Release</option>
        </select>
      </label>

      <label
        v-if="form.mode === 'standard'"
        class="flex items-center gap-2 text-sm"
      >
        <input
          v-model="form.judge_enabled"
          type="checkbox"
          :checked="form.judge_enabled !== false"
          @change="form.judge_enabled = ($event.target as HTMLInputElement).checked"
        >
        Enable LLM judge (default on for Standard)
      </label>

      <p v-if="form.mode === 'release'" class="text-sm text-[var(--muted)]">
        Release mode requires LLM judge on every case.
      </p>

      <label class="block text-sm">
        <span class="font-medium">Metric preset</span>
        <select v-model="form.preset_id" class="mt-1 w-full rounded-lg border px-3 py-2">
          <option v-for="p in presets" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
      </label>

      <label v-if="form.mode === 'standard'" class="flex items-center gap-2 text-sm">
        <input v-model="form.include_semantic" type="checkbox">
        Include semantic similarity metrics
      </label>

      <div class="flex gap-2 pt-2">
        <button
          type="button"
          class="rounded-lg border px-4 py-2 text-sm font-medium disabled:opacity-50"
          :disabled="estimating"
          @click="runEstimate"
        >
          {{ estimating ? 'Estimating...' : 'Estimate cost' }}
        </button>
      </div>

      <div v-if="estimate" class="rounded-lg border border-[var(--border)] bg-white p-4 text-sm">
        <p><strong>{{ estimate.case_count }}</strong> cases · est. <strong>${{ estimate.estimated_cost.toFixed(4) }}</strong></p>
        <ul v-if="estimate.warnings.length" class="mt-2 list-disc pl-5 text-[var(--muted)]">
          <li v-for="(w, i) in estimate.warnings" :key="i">{{ w }}</li>
        </ul>
        <button
          type="button"
          class="mt-4 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          :disabled="starting"
          @click="confirmRun"
        >
          {{ starting ? 'Starting...' : 'Confirm and run' }}
        </button>
      </div>
    </div>
  </div>
</template>
