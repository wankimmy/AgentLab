<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

const route = useRoute()
const { api } = useApi()
const runId = route.params.id as string

interface MetricRow {
  metric_name: string
  metric_type: string
  passed: boolean
  score: number | null
}

interface HumanReview {
  verdict: string
  rating: number | null
  notes: string | null
}

interface ResultRow {
  id: string
  case_name: string
  status: string
  overall_pass: boolean
  actual_answer: string
  failure_explanation: string | null
  metrics: MetricRow[]
  human_review: HumanReview | null
  judge_overall_score: number | null
}

interface RunDetail {
  id: string
  status: string
  mode: string
  judge_enabled: boolean
  pass_rate: number | null
  total_cost: number | null
  progress: { completed_cases?: number; total_cases?: number }
  results: ResultRow[]
}

const run = ref<RunDetail | null>(null)
const expanded = ref<string | null>(null)
const reviewForms = ref<Record<string, { verdict: string; rating: number; notes: string }>>({})
const multiReview = ref<Record<string, { agreement_percent: number; mean_overall_score: number }>>({})
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
  if (!reviewForms.value[id]) {
    reviewForms.value[id] = { verdict: 'needs_review', rating: 3, notes: '' }
  }
}

async function saveReview(resultId: string) {
  const form = reviewForms.value[resultId]
  await api(`/evaluations/results/${resultId}/review`, {
    method: 'POST',
    body: JSON.stringify(form),
  })
  await load()
}

async function runMultiJudge(resultId: string) {
  const data = await api<{ agreement_percent: number; mean_overall_score: number }>(
    '/judges/multi-review',
    {
      method: 'POST',
      body: JSON.stringify({ evaluation_result_id: resultId }),
    },
  )
  multiReview.value = { ...multiReview.value, [resultId]: data }
}
</script>

<template>
  <div>
    <NuxtLink to="/evaluations" class="text-sm text-[var(--accent)]">← Evaluations</NuxtLink>
    <h1 class="mt-2 text-3xl font-semibold">Run {{ run?.mode || '' }}</h1>

    <div v-if="run" class="mt-4 flex flex-wrap gap-4 text-sm text-[var(--muted)]">
      <span>Status: {{ run.status }}</span>
      <span>Judge: {{ run.judge_enabled ? 'on' : 'off' }}</span>
      <span v-if="run.pass_rate != null">Pass rate: {{ Math.round(run.pass_rate * 100) }}%</span>
      <span v-if="run.total_cost != null">Cost: ${{ run.total_cost.toFixed(4) }}</span>
      <span v-if="run.progress.total_cases">
        Progress: {{ run.progress.completed_cases || 0 }}/{{ run.progress.total_cases }}
      </span>
    </div>

    <p class="mt-2 text-xs text-[var(--muted)]">
      Judge scores are probabilistic; deterministic failures always fail the case.
    </p>

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
              <span v-if="r.judge_overall_score != null" class="ml-2 text-xs text-[var(--muted)]">
                judge {{ r.judge_overall_score.toFixed(2) }}
              </span>
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
                {{ m.metric_name }} ({{ m.metric_type }}): {{ m.passed ? 'pass' : 'fail' }}
                <span v-if="m.score != null"> ({{ m.score.toFixed(3) }})</span>
              </li>
            </ul>
            <div v-if="r.human_review" class="mt-3 rounded bg-slate-50 p-2 text-xs">
              Human review: {{ r.human_review.verdict }}
              <span v-if="r.human_review.notes"> — {{ r.human_review.notes }}</span>
            </div>
            <div v-if="reviewForms[r.id]" class="mt-4 space-y-2 border-t pt-3">
              <p class="text-xs font-medium">Human review</p>
              <select
                v-model="reviewForms[r.id]!.verdict"
                class="w-full rounded border px-2 py-1"
              >
                <option value="pass">pass</option>
                <option value="fail">fail</option>
                <option value="needs_review">needs_review</option>
              </select>
              <input
                v-model.number="reviewForms[r.id]!.rating"
                type="number"
                min="1"
                max="5"
                class="w-full rounded border px-2 py-1"
              >
              <textarea
                v-model="reviewForms[r.id]!.notes"
                class="w-full rounded border px-2 py-1"
                rows="2"
                placeholder="Notes"
              />
              <button
                type="button"
                class="rounded bg-[var(--accent)] px-3 py-1 text-xs text-white"
                @click="saveReview(r.id)"
              >
                Save review
              </button>
            </div>
            <button
              type="button"
              class="mt-3 rounded border px-3 py-1 text-xs"
              @click="runMultiJudge(r.id)"
            >
              Run multi-judge (3)
            </button>
            <p v-if="multiReview[r.id]" class="mt-2 text-xs text-[var(--muted)]">
              Agreement {{ multiReview[r.id]!.agreement_percent }}% · mean
              {{ multiReview[r.id]!.mean_overall_score }}
            </p>
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
