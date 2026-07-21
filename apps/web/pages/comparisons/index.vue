<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

const { api } = useApi()
const router = useRouter()

interface ComparisonSummary {
  id: string
  status: string
  baseline_pass_rate: number | null
  candidate_pass_rate: number | null
  pass_rate_delta: number | null
}

const comparisons = ref<ComparisonSummary[]>([])
const baselineRunId = ref('')
const candidateRunId = ref('')
const creating = ref(false)
const error = ref('')

onMounted(load)

async function load() {
  comparisons.value = await api<ComparisonSummary[]>('/comparisons')
}

async function createComparison() {
  error.value = ''
  creating.value = true
  try {
    const detail = await api<{ id: string }>('/comparisons', {
      method: 'POST',
      body: JSON.stringify({
        baseline_run_id: baselineRunId.value,
        candidate_run_id: candidateRunId.value,
      }),
    })
    await router.push(`/comparisons/${detail.id}`)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to create comparison'
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div>
    <h1 class="text-3xl font-semibold">Comparisons</h1>
    <p class="mt-1 text-sm text-[var(--muted)]">
      Compare two completed evaluation runs. No single winner score — review deltas per case.
    </p>

    <section class="mt-8 max-w-xl rounded-xl border border-[var(--border)] bg-white p-6">
      <h2 class="font-medium">New comparison</h2>
      <label class="mt-4 block text-sm">
        Baseline run ID
        <input v-model="baselineRunId" class="mt-1 w-full rounded border px-3 py-2 font-mono text-xs">
      </label>
      <label class="mt-3 block text-sm">
        Candidate run ID
        <input v-model="candidateRunId" class="mt-1 w-full rounded border px-3 py-2 font-mono text-xs">
      </label>
      <p v-if="error" class="mt-2 text-sm text-red-600">{{ error }}</p>
      <button
        type="button"
        class="mt-4 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm text-white disabled:opacity-50"
        :disabled="creating || !baselineRunId || !candidateRunId"
        @click="createComparison"
      >
        {{ creating ? 'Comparing...' : 'Compare runs' }}
      </button>
    </section>

    <section class="mt-10">
      <h2 class="font-medium">Recent</h2>
      <ul class="mt-4 space-y-2">
        <li v-for="c in comparisons" :key="c.id">
          <NuxtLink :to="`/comparisons/${c.id}`" class="text-[var(--accent)]">
            {{ c.id.slice(0, 8) }}… delta
            {{ c.pass_rate_delta != null ? (c.pass_rate_delta * 100).toFixed(1) : '—' }}%
          </NuxtLink>
        </li>
      </ul>
    </section>
  </div>
</template>
