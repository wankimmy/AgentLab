<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

const route = useRoute()
const { api } = useApi()
const runId = route.params.id as string

interface MetricRow {
  metric_name: string
  passed: boolean
  score: number | null
}

interface ResultRow {
  id: string
  case_name: string
  status: string
  overall_pass: boolean
  actual_answer: string
  failure_explanation: string | null
  metrics: MetricRow[]
}

interface RunDetail {
  id: string
  status: string
  mode: string
  pass_rate: number | null
  total_cost: number | null
  progress: { completed_cases?: number; total_cases?: number }
  results: ResultRow[]
}

const run = ref<RunDetail | null>(null)
const expanded = ref<string | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

async function load() {
  run.value = await api<RunDetail>(`/evaluations/runs/${runId}`)
}

onMounted(async () => {
  await load()
  pollTimer = setInterval(async () => {
    if (!run.value) return
    if (run.value.status === 'pending' || run.value.status === 'running') {
      await load()
    } else if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }, 1500)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

function toggle(id: string) {
  expanded.value = expanded.value === id ? null : id
}
</script>

<template>
  <div>
    <NuxtLink to="/evaluations" class="text-sm text-[var(--accent)]">← Evaluations</NuxtLink>
    <h1 class="mt-2 text-3xl font-semibold">Run {{ run?.mode || '' }}</h1>

    <div v-if="run" class="mt-4 flex flex-wrap gap-4 text-sm text-[var(--muted)]">
      <span>Status: {{ run.status }}</span>
      <span v-if="run.pass_rate != null">Pass rate: {{ Math.round(run.pass_rate * 100) }}%</span>
      <span v-if="run.total_cost != null">Cost: ${{ run.total_cost.toFixed(4) }}</span>
      <span v-if="run.progress.total_cases">
        Progress: {{ run.progress.completed_cases || 0 }}/{{ run.progress.total_cases }}
      </span>
    </div>

    <div
      v-if="run && (run.status === 'pending' || run.status === 'running')"
      class="mt-6 h-2 w-full max-w-md overflow-hidden rounded-full bg-[var(--border)]"
    >
      <div
        class="h-full bg-[var(--accent)] transition-all"
        :style="{
          width: run.progress.total_cases
            ? `${((run.progress.completed_cases || 0) / run.progress.total_cases) * 100}%`
            : '10%',
        }"
      />
    </div>

    <section class="mt-8">
      <h2 class="font-medium">Results</h2>
      <p v-if="!run" class="mt-4 text-sm text-[var(--muted)]">Loading...</p>
      <ul v-else-if="run.results.length" class="mt-4 space-y-3">
        <li
          v-for="r in run.results"
          :key="r.id"
          class="rounded-lg border border-[var(--border)] bg-white"
        >
          <button
            type="button"
            class="flex w-full items-center justify-between px-4 py-3 text-left"
            @click="toggle(r.id)"
          >
            <span>
              <span
                class="mr-2 inline-block h-2 w-2 rounded-full"
                :class="r.overall_pass ? 'bg-green-600' : 'bg-red-600'"
              />
              {{ r.case_name }}
            </span>
            <span class="text-sm text-[var(--muted)]">{{ r.status }}</span>
          </button>
          <div v-if="expanded === r.id" class="border-t px-4 py-3 text-sm">
            <p class="whitespace-pre-wrap text-[var(--muted)]">{{ r.actual_answer }}</p>
            <p v-if="r.failure_explanation" class="mt-3 whitespace-pre-wrap text-red-700">
              {{ r.failure_explanation }}
            </p>
            <ul v-if="r.metrics.length" class="mt-3 space-y-1">
              <li v-for="m in r.metrics" :key="m.metric_name">
                {{ m.metric_name }}: {{ m.passed ? 'pass' : 'fail' }}
                <span v-if="m.score != null"> ({{ m.score.toFixed(3) }})</span>
              </li>
            </ul>
          </div>
        </li>
      </ul>
      <EmptyState
        v-else
        class="mt-4"
        title="No results yet"
        description="Results appear as each case completes."
      />
    </section>
  </div>
</template>
