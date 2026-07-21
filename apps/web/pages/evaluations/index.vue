<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'onboarding'] })

const { api } = useApi()

interface RunSummary {
  id: string
  agent_version_id: string
  dataset_version_id: string
  mode: string
  status: string
  pass_rate: number | null
  total_cost: number | null
  progress: { completed_cases?: number; total_cases?: number }
  started_at: string
  completed_at: string | null
}

const runs = ref<RunSummary[]>([])
const loading = ref(true)

onMounted(load)

async function load() {
  loading.value = true
  try {
    runs.value = await api<RunSummary[]>('/evaluations/runs')
  } finally {
    loading.value = false
  }
}

function statusLabel(status: string) {
  return status.replace('_', ' ')
}
</script>

<template>
  <div>
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="text-3xl font-semibold">Evaluations</h1>
        <p class="mt-1 text-[var(--muted)]">Quick Check and Standard runs against test datasets</p>
      </div>
      <div class="flex gap-2">
        <NuxtLink
          to="/evaluations/datasets"
          class="rounded-lg border border-[var(--border)] px-4 py-2 text-sm font-medium"
        >
          Datasets
        </NuxtLink>
        <NuxtLink
          to="/reviews/blind-ab"
          class="rounded-lg border border-[var(--border)] px-4 py-2 text-sm font-medium"
        >
          Blind A/B
        </NuxtLink>
        <NuxtLink
          to="/evaluations/runs/new"
          class="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white"
        >
          New run
        </NuxtLink>
      </div>
    </div>

    <div class="mt-8 grid gap-6 lg:grid-cols-3">
      <div class="lg:col-span-2">
        <section>
          <h2 class="font-medium">Recent runs</h2>
          <p v-if="loading" class="mt-4 text-sm text-[var(--muted)]">Loading...</p>
          <EmptyState
            v-else-if="!runs.length"
            title="No evaluation runs yet"
            description="Create a dataset, then run Quick Check for fast feedback."
            :actions="[
              { label: 'Create dataset', to: '/evaluations/datasets' },
              { label: 'Evaluation guide', to: '/learning/what-is-evaluation' },
            ]"
          />
          <ul v-else class="mt-4 space-y-3">
            <li
              v-for="run in runs"
              :key="run.id"
              class="rounded-lg border border-[var(--border)] bg-white p-4"
            >
              <NuxtLink
                :to="`/evaluations/runs/${run.id}`"
                class="font-medium hover:text-[var(--accent)]"
              >
                {{ run.mode }} run
              </NuxtLink>
              <p class="mt-1 text-sm text-[var(--muted)]">
                {{ statusLabel(run.status) }}
                <span v-if="run.pass_rate != null"> · {{ Math.round(run.pass_rate * 100) }}% pass</span>
                <span v-if="run.total_cost != null"> · ${{ run.total_cost.toFixed(4) }}</span>
              </p>
              <p
                v-if="run.progress.total_cases"
                class="mt-2 text-xs text-[var(--muted)]"
              >
                {{ run.progress.completed_cases || 0 }}/{{ run.progress.total_cases }} cases
              </p>
            </li>
          </ul>
        </section>
      </div>

      <HelpPanel
        title="Evaluation workflow"
        why="Structured cases measure correctness, groundedness, and tool use."
        :needs="['Evaluation dataset', 'Agent version', 'Metric preset']"
        :steps="['Import starter pack', 'Estimate cost', 'Run Quick Check', 'Review failures']"
        :mistakes="['Skipping security cases', 'No citation checks for RAG agents']"
        :next-action="{ label: 'What is evaluation?', to: '/learning/what-is-evaluation' }"
      />
    </div>
  </div>
</template>
